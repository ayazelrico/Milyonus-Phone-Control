"""A deterministic phone driven by a YAML scenario (A1.12).

It behaves like a real phone where that matters for agents and helpers:
  - taps on empty space "succeed" and change nothing (PITFALLS#android-silent-success);
  - text typed with no focused field disappears silently;
  - a locked phone refuses every input op and accepts no touches (PITFALLS#android-locked-taps);
  - lists scroll by exactly the requested delta (scroll) or with momentum (drag/swipe);
  - screens can refuse their tree (PITFALLS#android-idle-state) and fall back to "pixels".

Scenario format: see scenarios/settings_about.yaml (annotated). Every op in the vocabulary is
implemented, so the fake is also the reference for slot signatures.
"""

import base64
import os
import tempfile
import time
from pathlib import Path
from typing import Any

from mphone_core import tree as treeutil
from mphone_core.textnorm import match
from mphone_core.transport import Backend, OpCall
from mphone_protocol import (
    ERROR_CLASSES,
    DeviceAsleep,
    DeviceLocked,
    InvalidArgument,
    NotFound,
    TreeUnavailable,
)

from .render import render_png

LOCKED_ACTION = "Telefonun kilidini açın; PIN asla otomatik yazılmaz. Sonra işleme devam edin."
KNOWN_KEYS = {"enter", "back", "home", "tab", "del", "space", "menu", "search", "recents", "escape"}

Dict = dict[str, Any]


class FakeBackend(Backend):
    name = "fake"
    platform = "fake"

    def __init__(self, scenario: Dict, source: str = "<inline>") -> None:
        super().__init__()
        self.source = source
        self.scenario = scenario
        dev = scenario.get("device", {})
        self.w: int = int(dev.get("w", 1080))
        self.h: int = int(dev.get("h", 2400))
        self.state: str = scenario.get("state", "ready")
        self.screens: dict[str, Dict] = scenario["screens"]
        self.start: str = scenario.get("start", next(iter(self.screens)))
        self.current: str = self.start
        self.history: list[str] = []
        self.apps: list[Dict] = list(scenario.get("apps", []))
        self.offsets: dict[str, int] = {}
        self.values: dict[tuple[str, str], str] = {}
        self.focused: tuple[str, str] | None = None
        self.clipboard_text = ""
        self.files: dict[str, bytes] = {}
        self.lost_text: list[str] = []
        self.calls: list[tuple[str, Dict]] = []
        self.awake_kept = False
        self.streams: set[str] = set()
        self._fault_counts: dict[str, int] = {}
        self._faults: list[Dict] = [dict(f) for f in scenario.get("faults", [])]
        bar = scenario.get("status_bar")
        self._clock_minutes = 14 * 60 + 2
        self._bar: Dict | None = bar if isinstance(bar, dict) else ({"text": bar} if bar else None)

    # --- test controls ------------------------------------------------------

    def unlock(self) -> None:
        self.state = "ready"

    def lock(self) -> None:
        self.state = "locked"

    def value(self, element_id: str, screen: str | None = None) -> str:
        return self.values.get((screen or self.current, element_id), "")

    # --- plumbing -----------------------------------------------------------

    def _invoke(self, call: OpCall) -> Any:
        self.calls.append((call.op, dict(call.kw)))
        latency = self.scenario.get("latency_ms", {})
        delay = latency.get(call.op, latency.get("default", 0)) if isinstance(latency, dict) else 0
        if delay:
            time.sleep(delay / 1000)
        self._maybe_fault(call.op)
        return super()._invoke(call)

    def _maybe_fault(self, op: str) -> None:
        count = self._fault_counts[op] = self._fault_counts.get(op, 0) + 1
        for fault in self._faults:
            if fault.get("op") not in (op, "*") or count <= int(fault.get("after", 0)):
                continue
            if fault.get("times", 1) <= 0:
                continue
            fault["times"] = fault.get("times", 1) - 1
            cls = ERROR_CLASSES.get(fault["code"])
            if cls is None:
                raise InvalidArgument(f"fake scenario fault has unknown code {fault['code']!r}")
            raise cls(fault.get("message", f"injected {fault['code']} on {op}"))

    def _gate(self) -> None:
        """Input refuses unless the phone is awake and unlocked; nothing reaches the screen."""
        if self.state == "locked":
            raise DeviceLocked("the phone is locked", user_action=LOCKED_ACTION)
        if self.state == "asleep":
            raise DeviceAsleep("the screen is off", user_action="device.wake ile ekranı uyandırın.")

    def _screen(self, name: str | None = None) -> Dict:
        return self.screens[name or self.current]

    def _goto(self, name: str) -> None:
        if name not in self.screens:
            raise InvalidArgument(f"fake scenario has no screen {name!r}")
        if name != self.current:
            self.history.append(self.current)
        self.current = name
        self.focused = None

    def _do(self, action: Dict | None) -> None:
        if not action:
            return
        if "goto" in action:
            self._goto(action["goto"])
        elif "launch" in action:
            self._launch_app(self._find_app(action["launch"]))
        elif action.get("back"):
            self._nav_back()
        elif action.get("home"):
            self._nav_home()

    # --- the screen model ----------------------------------------------------

    def _list_rows(self, name: str) -> list[str]:
        spec = self._screen(name).get("list")
        if not spec:
            return []
        items = spec["items"]
        if isinstance(items, dict):
            return [str(items["pattern"]).format(i=i) for i in range(1, int(items["count"]) + 1)]
        return [str(i) for i in items]

    def _max_offset(self, name: str) -> int:
        spec = self._screen(name)["list"]
        content = len(self._list_rows(name)) * int(spec["row_h"])
        return max(0, content - (int(spec["bottom"]) - int(spec["top"])))

    def _elements(self, name: str) -> list[Dict]:
        """Static elements plus the list rows that are currently inside the viewport."""
        screen = self._screen(name)
        out: list[Dict] = []
        for el in screen.get("elements", []):
            item = dict(el)
            eid = item.get("id") or item.get("text", "")
            if item.get("editable"):
                value = self.values.get((name, eid), "")
                if value and item.get("password"):
                    value = "•" * len(value)  # Android masks password fields in the tree too
                item["text"] = value if value else item.get("hint", "")
                item["focused"] = self.focused == (name, eid)
            out.append(item)
        spec = screen.get("list")
        if spec:
            offset = self.offsets.get(name, 0)
            top, bottom, row_h = int(spec["top"]), int(spec["bottom"]), int(spec["row_h"])
            for i, text in enumerate(self._list_rows(name)):
                y_top = top + i * row_h - offset
                if y_top < top or y_top + row_h > bottom:
                    continue
                out.append(
                    {
                        "id": f"row{i}",
                        "row": True,
                        "text": text,
                        "x": int(spec.get("x", self.w // 2)),
                        "y": y_top + row_h // 2,
                        "w": int(spec.get("w", self.w - 80)),
                        "h": row_h - 8,
                        "clickable": True,
                    }
                )
        return out

    def _status_bar(self) -> Dict | None:
        if not self._bar:
            return None
        text = self._bar.get("text", "")
        if self._bar.get("tick"):
            self._clock_minutes += 1
            text = f"{self._clock_minutes // 60 % 24:02d}:{self._clock_minutes % 60:02d}"
        return {"id": "status_clock", "text": text, "x": 90, "y": 40, "w": 120, "h": 40}

    def _nodes(self) -> list[Dict]:
        name = self.current
        screen = self._screen(name)
        nodes: list[Dict] = [
            {
                "node_id": "root",
                "parent_id": None,
                "text": "",
                "class": "android.widget.FrameLayout",
                "package": screen.get("app"),
                "rect": {"left": 0, "top": 0, "right": self.w, "bottom": self.h},
            }
        ]
        bar = self._status_bar()
        elements = ([bar] if bar else []) + self._elements(name)
        for el in elements:
            rect = _rect(el)
            nid = f"n_{el.get('id') or el['text']}"
            if el.get("row"):
                # A row is a clickable container with a non-clickable label inside, as on Android:
                # helpers must tap the clickable ancestor, not trust the label to be clickable.
                nodes.append(
                    {
                        "node_id": nid,
                        "parent_id": "root",
                        "text": "",
                        "clickable": True,
                        "rect": rect,
                        "class": "android.widget.LinearLayout",
                        "package": screen.get("app"),
                    }
                )
                nodes.append(
                    {
                        "node_id": nid + "_t",
                        "parent_id": nid,
                        "text": el["text"],
                        "rect": rect,
                        "class": "android.widget.TextView",
                        "package": screen.get("app"),
                    }
                )
                continue
            nodes.append(
                {
                    "node_id": nid,
                    "parent_id": "root",
                    "text": el.get("text", ""),
                    "content_desc": el.get("content_desc"),
                    "resource_id": el.get("resource_id"),
                    "class": el.get(
                        "class",
                        "android.widget.EditText" if el.get("editable") else "android.widget.TextView",
                    ),
                    "package": screen.get("app"),
                    "rect": rect,
                    "clickable": bool(el.get("clickable") or el.get("editable") or el.get("on_tap")),
                    "editable": bool(el.get("editable")),
                    "password": bool(el.get("password")),
                    "focused": bool(el.get("focused")),
                }
            )
        return nodes

    def _hit(self, x: int, y: int) -> Dict | None:
        """The smallest element containing the point (the topmost, in practice)."""
        hits = [el for el in self._elements(self.current) if _contains(el, x, y)]
        hits.sort(key=lambda el: int(el.get("w", 0)) * int(el.get("h", 0)))
        return hits[0] if hits else None

    # --- screen ops ---------------------------------------------------------

    def _screen_bounds(self) -> Dict:
        return {"w": self.w, "h": self.h, "scale": 1.0, "rotation": 0}

    def _screen_capture(self, format: str, quality: int, max_side: int | None, path: str | None) -> Dict:
        if self.state == "asleep":
            elements: list[Dict] = []
        elif self.state == "locked":
            elements = [_lock_element(self.w, self.h)]
        else:
            elements = self._elements(self.current)
        data, w, h = render_png(self.w, self.h, elements, format, quality, max_side)
        if path is None:
            fd, path = tempfile.mkstemp(prefix="mphone-fake-", suffix=f".{format}")
            os.close(fd)
        Path(path).write_bytes(data)
        return {
            "w": w,
            "h": h,
            "format": format,
            "path": str(path),
            "data_b64": None,
            "artifact_id": None,
            "secure": bool(self._screen().get("secure")),
        }

    def _screen_text(self, min_confidence: float) -> list[Dict]:
        if self.state == "locked":
            return [treeutil.node_to_box({"node_id": "lock", **_lock_node(self.w, self.h)})]
        if self.state == "asleep":
            return []
        if self._screen().get("tree") is False:
            return self._screen_text_pixels(min_confidence, ["tr", "en"])
        return [b for b in treeutil.nodes_to_boxes(self._nodes()) if b["confidence"] >= min_confidence]

    def _screen_text_pixels(self, min_confidence: float, langs: list[str]) -> list[Dict]:
        boxes = treeutil.nodes_to_boxes(self._nodes())
        out: list[Dict] = []
        for b in boxes:
            if not b["text"]:
                continue
            out.append(
                {
                    "text": b["text"],
                    "confidence": 0.95,
                    "source": "pixels",
                    "x": b["x"],
                    "y": b["y"],
                    "w": b["w"],
                    "h": b["h"],
                }
            )
        return [b for b in out if b["confidence"] >= min_confidence]

    def _screen_stream_start(self, fps: int, max_side: int, codec: str) -> Dict:
        sid = f"fake-stream-{len(self.streams) + 1}"
        self.streams.add(sid)
        return {"stream_id": sid}

    def _screen_stream_stop(self, stream_id: str) -> None:
        self.streams.discard(stream_id)

    def _tree(self, compressed: bool) -> list[Dict]:
        self._gate()
        if self._screen().get("tree") is False:
            raise TreeUnavailable("could not get idle state", details={"screen": self.current})
        return self._nodes()

    def _ui_find(self, selector: Dict) -> list[Dict]:
        return treeutil.select(self._tree(True), selector)

    # --- input ops ----------------------------------------------------------

    def _input_tap(self, x: int, y: int) -> None:
        self._gate()
        el = self._hit(x, y)
        if el is None:
            return  # empty space: "succeeds", changes nothing
        name = self.current
        if el.get("editable"):
            self.focused = (name, el.get("id") or el.get("text", ""))
            return
        spec = self._screen().get("list") or {}
        if el.get("row"):
            actions = spec.get("on_tap", {})
            self._do(actions.get(el["text"]) or spec.get("on_tap_any"))
            return
        self._do(el.get("on_tap"))

    def _input_press(self, x: int, y: int, duration: float) -> None:
        self._gate()
        el = self._hit(x, y)
        if el is not None:
            self._do(el.get("on_long_press"))

    def _scroll_list(self, x: int, y: int, delta: int) -> None:
        spec = self._screen().get("list")
        if not spec or not (int(spec["top"]) <= y <= int(spec["bottom"])):
            return
        name = self.current
        self.offsets[name] = max(0, min(self._max_offset(name), self.offsets.get(name, 0) + delta))

    def _input_drag(self, x1: int, y1: int, x2: int, y2: int, duration: float, steps: int) -> None:
        self._gate()
        if abs(y2 - y1) >= abs(x2 - x1):
            momentum = 1.6 if duration < 0.3 else 1.0  # a quick flick coasts past rows
            self._scroll_list(x1, y1, round((y1 - y2) * momentum))

    def _input_scroll(self, x: int, y: int, dy: int, dx: int, steps: int) -> None:
        self._gate()
        if dy:
            self._scroll_list(x, y, dy)

    def _input_keys(self, combo: str) -> None:
        self._gate()
        key = combo.strip().lower()
        if key not in KNOWN_KEYS:
            raise InvalidArgument(f"unknown key {combo!r}; known: {sorted(KNOWN_KEYS)}")
        if key == "back":
            self._nav_back()
        elif key == "home":
            self._nav_home()
        elif key == "recents":
            self._nav_recents()
        elif key == "del" and self.focused:
            self.values[self.focused] = self.values.get(self.focused, "")[:-1]
        elif key == "space" and self.focused:
            self.values[self.focused] = self.values.get(self.focused, "") + " "
        elif key == "tab":
            editable = [e for e in self._screen().get("elements", []) if e.get("editable")]
            ids = [e.get("id") or e.get("text", "") for e in editable]
            if ids:
                nxt = (
                    0 if not self.focused or self.focused[1] not in ids else (ids.index(self.focused[1]) + 1)
                )
                self.focused = (self.current, ids[nxt % len(ids)])
        else:
            self._do(self._screen().get("on_key", {}).get(key))

    def _input_text(self, s: str, mode: str, delay: float) -> Dict:
        self._gate()
        used = mode if mode != "auto" else ("keystrokes" if s.isascii() else "ime")
        if self.focused is None:
            self.lost_text.append(s)  # like a real phone: no field, the text goes nowhere
        else:
            self.values[self.focused] = self.values.get(self.focused, "") + s
        return {"mode_used": used}

    def _input_clear(self) -> None:
        self._gate()
        if self.focused:
            self.values[self.focused] = ""

    # --- navigation ---------------------------------------------------------

    def _nav_home(self) -> None:
        self._gate()
        self.history.clear()
        self.current = self.start
        self.focused = None

    def _nav_back(self) -> None:
        self._gate()
        target = self._screen().get("back")
        if target:
            self.current = target
        elif self.history:
            self.current = self.history.pop()
        self.focused = None

    def _nav_recents(self) -> None:
        self._gate()
        if "recents" in self.screens:
            self._goto("recents")

    def _nav_notifications(self) -> None:
        self._gate()
        if "notifications" in self.screens:
            self._goto("notifications")

    # --- apps ---------------------------------------------------------------

    def _find_app(self, name: str) -> Dict:
        scored: list[tuple[int, Dict]] = []
        for app in self.apps:
            if name == app["app_id"]:
                return app
            names = [app.get("label", ""), *app.get("aliases", [])]
            best = min((s for n in names if (s := match(name, n)) is not None), default=None)
            if best is None and name.lower() in app["app_id"].lower():
                best = 5
            if best is not None:
                scored.append((best, app))
        if not scored:
            installed = [a.get("label") or a["app_id"] for a in self.apps]
            raise NotFound(
                f"no installed app matches {name!r}; installed: {installed}",
                details={"query": name, "installed": installed},
            )
        scored.sort(key=lambda t: t[0])
        return scored[0][1]

    def _launch_app(self, app: Dict) -> None:
        self._goto(app["screen"])

    def _apps_launch(self, name: str, fresh: bool) -> Dict:
        self._gate()
        app = self._find_app(name)
        if fresh:
            self.offsets.pop(app["screen"], None)
        self._launch_app(app)
        return {"app_id": app["app_id"]}

    def _apps_current(self) -> Dict | None:
        app = self._screen().get("app")
        return {"app_id": app} if app else None

    def _apps_list(self, include_system: bool) -> list[Dict]:
        return [
            {"app_id": a["app_id"], "label": a.get("label"), "system": bool(a.get("system"))}
            for a in self.apps
            if include_system or not a.get("system")
        ]

    def _apps_stop(self, app_id: str) -> None:
        self._gate()
        if self._screen().get("app") == app_id:
            self._nav_home()

    def _apps_install(self, artifact_id: str | None, url: str | None, path: str | None) -> Dict:
        source = path or url or artifact_id
        if not source:
            raise InvalidArgument("apps.install needs artifact_id, url or path")
        app_id = Path(source).stem
        self.apps.append({"app_id": app_id, "label": app_id, "screen": self.start})
        return {"app_id": app_id}

    def _apps_uninstall(self, app_id: str) -> None:
        before = len(self.apps)
        self.apps = [a for a in self.apps if a["app_id"] != app_id]
        if len(self.apps) == before:
            raise NotFound(f"{app_id!r} is not installed")

    # --- device -------------------------------------------------------------

    def _device_info(self) -> Dict:
        dev = self.scenario.get("device", {})
        return {
            "platform": "fake",
            "os_version": str(dev.get("os_version", "14")),
            "model": str(dev.get("model", "Fake Phone")),
            "manufacturer": dev.get("manufacturer", "Milyonus"),
            "serial_hash": "fake0000",
            "battery": dev.get("battery", 87),
            "charging": dev.get("charging", True),
            "locale": dev.get("locale", "tr-TR"),
            "timezone": dev.get("timezone", "Europe/Istanbul"),
        }

    def _device_state(self) -> str:
        return self.state

    def _device_require(self) -> Dict:
        if self.state == "asleep":
            self.state = "locked" if self.scenario.get("locked_when_woken") else "ready"
        if self.state == "locked":
            raise DeviceLocked("the phone is locked", user_action=LOCKED_ACTION)
        return self._screen_bounds()

    def _device_detail(self) -> str:
        return {
            "ready": "fake phone is ready",
            "locked": "the phone is locked",
            "asleep": "the screen is off",
        }.get(self.state, self.state)

    def _device_wake(self) -> None:
        if self.state == "asleep":
            self.state = "locked" if self.scenario.get("locked_when_woken") else "ready"

    def _device_keep_awake(self, on: bool) -> None:
        self.awake_kept = on

    # --- misc ---------------------------------------------------------------

    def _clipboard_get(self) -> str:
        return self.clipboard_text

    def _clipboard_set(self, text: str) -> None:
        self.clipboard_text = text

    def _notifications_list(self, limit: int) -> list[Dict]:
        return list(self.scenario.get("notifications", []))[:limit]

    def _focus_probe(self) -> list[bool]:
        return [True]

    def _focus_diff(self, before: Any, after: Any) -> Dict:
        return {"raised": False, "stole_focus": False}

    def _files_push(self, dest: str, artifact_id: str | None, path: str | None) -> None:
        if path is None:
            raise InvalidArgument("the fake phone pushes local files only (path=…)")
        self.files[dest] = Path(path).read_bytes()

    def _files_pull(self, path: str) -> Dict:
        if path not in self.files:
            raise NotFound(f"no such file on the fake phone: {path}")
        fd, local = tempfile.mkstemp(prefix="mphone-pull-")
        os.close(fd)
        Path(local).write_bytes(self.files[path])
        return {"artifact_id": None, "local_path": local}

    def _raw(self, cmd: str, binary: bool, timeout: float) -> Any:
        out = str(self.scenario.get("raw", {}).get(cmd, ""))
        return base64.b64encode(out.encode()).decode() if binary else out


def _rect(el: Dict) -> dict[str, int]:
    x, y, w, h = int(el["x"]), int(el["y"]), int(el.get("w", 200)), int(el.get("h", 60))
    return {"left": x - w // 2, "top": y - h // 2, "right": x - w // 2 + w, "bottom": y - h // 2 + h}


def _contains(el: Dict, x: int, y: int) -> bool:
    r = _rect(el)
    return r["left"] <= x < r["right"] and r["top"] <= y < r["bottom"]


def _lock_element(w: int, h: int) -> Dict:
    return {"text": "Kilidi açmak için kaydırın", "x": w // 2, "y": h - 300, "w": 700, "h": 80}


def _lock_node(w: int, h: int) -> Dict:
    return {"text": "Kilidi açmak için kaydırın", "rect": _rect(_lock_element(w, h))}
