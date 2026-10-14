"""Phone control — one flat API over any device (A1.07–A1.09, Plan.md §8.1.3).

Every helper is a thin wrapper over `send(op, **kw)`; nothing in this file knows which platform
it drives (CLAUDE.md §2). Helpers return observations, never verdicts: a phone reports nothing
about whether a tap "worked", so the caller names the change it expects and checks for it.

Two ways in:
    from mphone_core.helpers import *     # module functions act on the default phone
    other = connect("fake:notes_turkish") # a second Phone, side by side

Coordinates are device-local screenshot pixels everywhere (Plan.md §6.4).
"""

import base64
import sys
import tempfile
from collections.abc import Callable, Hashable
from pathlib import Path
from typing import Any, Literal

from mphone_protocol import ApprovalDenied, InvalidArgument, NeedsUser, NotFound

from . import connect as _connect
from .clock import Clock, RealClock
from .textnorm import match
from .transport import Backend

Box = dict[str, Any]
Direction = Literal["up", "down", "left", "right"]
At = tuple[int, int] | Box | None
HumanHandler = Callable[[Literal["human", "approval"], str, float], bool]

_OPPOSITE: dict[str, Direction] = {"down": "up", "up": "down", "left": "right", "right": "left"}

# Scroll-end detection ignores the status bar (a ticking clock) and the navigation strip:
# otherwise the clock changing a minute reads as movement and the end is never found.
CONTENT_TOP, CONTENT_BOTTOM = 0.06, 0.92


def _tty_handler(kind: Literal["human", "approval"], text: str, timeout: float) -> bool:
    """Local default: ask on the terminal; without one, stop and say what the user must do."""
    if not sys.stdin.isatty():
        if kind == "approval":
            raise NeedsUser(
                f"onay gerekiyor: {text}", user_action="Kullanıcıdan onay alın ve tekrar çalıştırın."
            )
        raise NeedsUser(f"insan gerekiyor: {text}", user_action=text)
    prompt = (
        "Onaylıyor musunuz? [e/H] "
        if kind == "approval"
        else "Bitince Enter'a basın ('iptal' ile vazgeçin): "
    )
    print(f"\n[mphone] {text}", file=sys.stderr)
    answer = input(prompt).strip().lower()
    if kind == "approval":
        return answer in ("e", "evet", "y", "yes")
    return answer not in ("iptal", "cancel")


def _clamp(v: int, hi: int) -> int:
    return max(0, min(hi - 1, v))


def _all_texts(boxes: list[Box]) -> list[Any]:
    return [o["text"].strip() for o in boxes if o["text"].strip()]


def _identity(item: Any) -> Hashable:
    return item


class Phone:
    """All helpers, bound to one backend."""

    def __init__(
        self,
        backend: Backend,
        *,
        clock: Clock | None = None,
        human: HumanHandler | None = None,
    ) -> None:
        self.backend = backend
        self.clock: Clock = clock or RealClock()
        self.human: HumanHandler = human or _tty_handler
        self.notes: list[str] = []

    # --- raw ----------------------------------------------------------------

    def send(self, op: str, /, **kw: Any) -> Any:
        """Raw transport: send("input.tap", x=100, y=200). Unsupported means the device
        genuinely cannot, not that the call failed."""
        return self.backend.send(op, **kw)

    def supports(self, op: str) -> bool:
        return self.backend.supports(op)

    def ops(self) -> list[str]:
        return self.backend.ops()

    # --- device -------------------------------------------------------------

    def ensure_device(self) -> Box:
        """Make the device usable and return its bounds, or raise telling the user what to do.
        The first line of every task."""
        return self.send("device.require")

    def connection_state(self) -> str:
        """ "ready" when usable; otherwise locked, asleep, offline, unauthorized, needs-user, busy."""
        return self.send("device.state")

    def connection_detail(self) -> str:
        return self.send("device.detail")

    def device_info(self) -> Box:
        return self.send("device.info")

    def bounds(self) -> Box:
        """{w, h, scale, rotation}: the coordinate space of every helper."""
        return self.send("screen.bounds")

    # --- eyes ---------------------------------------------------------------

    def screen(self, min_confidence: float = 0.3) -> list[Box]:
        """Visible text as {text, confidence, source, x, y, w, h, …}; x, y is a tap-ready centre.
        source "tree" = the OS reported it exactly, "pixels" = OCR, may be misread."""
        return self.send("screen.text", min_confidence=min_confidence)

    def screen_text(self, min_confidence: float = 0.3) -> list[str]:
        """Just the strings, top to bottom — cheaper to print than full boxes."""
        return [b["text"] for b in self.screen(min_confidence) if b["text"]]

    def screenshot(self, path: str | None = None, max_side: int | None = None) -> str:
        """Capture the screen to a PNG, print its path and return it. Costs more than screen();
        use it for what text cannot show: icons, images, state."""
        cap = self.send("screen.capture", format="png", path=path, max_side=max_side)
        out = cap.get("path")
        if out is None:
            if cap.get("data_b64") is None:
                raise InvalidArgument("the device returned neither a path nor image data")
            target = Path(path) if path else Path(tempfile.mkstemp(prefix="mphone-", suffix=".png")[1])
            target.write_bytes(base64.b64decode(cap["data_b64"]))
            out = str(target)
        print(out)
        return out

    def find_text(self, query: str, exact: bool = False) -> list[Box]:
        """Visible boxes matching `query`, best match first (Turkish-aware, see textnorm)."""
        scored: list[tuple[int, int, int, Box]] = []
        for b in self.screen():
            score = match(query, b["text"], exact)
            if score is not None:
                scored.append((score, b["y"], b["x"], b))
        scored.sort(key=lambda t: t[:3])
        return [t[3] for t in scored]

    # --- hands --------------------------------------------------------------

    def tap(self, x: int, y: int) -> None:
        self.send("input.tap", x=int(x), y=int(y))

    def long_press(self, x: int, y: int, duration: float = 0.8) -> None:
        self.send("input.press", x=int(x), y=int(y), duration=duration)

    def drag(self, x1: int, y1: int, x2: int, y2: int, duration: float = 0.35, steps: int = 14) -> None:
        """Finger from (x1, y1) to (x2, y2)."""
        self.send(
            "input.drag", x1=int(x1), y1=int(y1), x2=int(x2), y2=int(y2), duration=duration, steps=steps
        )

    def tap_text(self, query: str, index: int = 0, exact: bool = False) -> Box:
        """Tap the centre of visible text matching `query`. When nothing matches, the error lists
        what IS visible — read it before retrying."""
        hits = self.find_text(query, exact)
        if len(hits) <= index:
            visible = self.screen_text()
            raise NotFound(
                f"no visible text matches {query!r} (index {index}, {len(hits)} hit(s)); "
                f"visible: {visible[:15]}",
                details={"query": query, "visible": visible[:40]},
            )
        hit = hits[index]
        self.tap(hit["x"], hit["y"])
        return hit

    def tap_image_point(self, x: float, y: float, image_size: tuple[int, int]) -> tuple[int, int]:
        """Tap a point read off a RESIZED screenshot of size image_size = (width, height).
        A full-size screenshot needs no conversion: tap(x, y) directly."""
        b = self.bounds()
        px, py = round(x * b["w"] / image_size[0]), round(y * b["h"] / image_size[1])
        self.tap(px, py)
        return px, py

    def type_text(self, text: str, mode: str = "auto", delay: float = 0.03) -> Box:
        """Type into the FOCUSED field (tap it first; check with screen() afterwards).
        Unicode, Turkish included. mode: auto, paste, keystrokes, ime."""
        return self.send("input.text", s=text, mode=mode, delay=delay)

    def clear_text(self) -> None:
        self.send("input.clear")

    def press(self, combo: str) -> None:
        """A key: "enter", "back", "tab", "del"; chords like "cmd+space" where supported."""
        self.send("input.keys", combo=combo)

    # --- navigation and apps -------------------------------------------------

    def home(self) -> None:
        self.send("nav.home")

    def back(self) -> None:
        """System Back, where the device has one (iPhone Mirroring does not: Unsupported)."""
        self.send("nav.back")

    def recents(self) -> None:
        self.send("nav.recents")

    def notifications_panel(self) -> None:
        self.send("nav.notifications")

    def open_app(self, name: str, fresh: bool = False) -> str:
        """Launch by the name a person would say, an app id, or a fragment of one; returns the
        app id launched. Confirm it is in front with wait_for_app()."""
        return self.send("apps.launch", name=name, fresh=fresh)["app_id"]

    def current_app(self) -> str | None:
        current = self.send("apps.current")
        return None if current is None else current["app_id"]

    def list_apps(self, include_system: bool = False) -> list[Box]:
        return self.send("apps.list", include_system=include_system)

    def stop_app(self, app_id: str) -> None:
        self.send("apps.stop", app_id=app_id)

    # --- gestures -----------------------------------------------------------

    def _point(self, at: At, b: Box) -> tuple[int, int]:
        if at is None:
            return b["w"] // 2, b["h"] // 2
        if isinstance(at, dict):
            return int(at["x"]), int(at["y"])
        return int(at[0]), int(at[1])

    def swipe(self, direction: Direction, distance: float = 0.4, at: At = None) -> None:
        """A flick. `direction` is FINGER motion: swipe("up") is the thumb gesture for "next"."""
        b = self.bounds()
        x, y = self._point(at, b)
        if direction in ("up", "down"):
            d = round(b["h"] * distance / 2) * (1 if direction == "down" else -1)
            x1, y1, x2, y2 = x, y - d, x, y + d
        elif direction in ("left", "right"):
            d = round(b["w"] * distance / 2) * (1 if direction == "right" else -1)
            x1, y1, x2, y2 = x - d, y, x + d, y
        else:
            raise InvalidArgument(f"direction must be up, down, left or right, not {direction!r}")
        self.drag(_clamp(x1, b["w"]), _clamp(y1, b["h"]), _clamp(x2, b["w"]), _clamp(y2, b["h"]), 0.15, 8)

    def scroll(self, direction: Direction = "down", amount: float = 0.3, at: At = None) -> None:
        """Move content without momentum. `direction` is the content you want to SEE:
        scroll("down") reveals what is further down. Use it to walk lists without skipping rows."""
        b = self.bounds()
        x, y = self._point(at, b)
        dx = dy = 0
        if direction in ("up", "down"):
            dy = round(b["h"] * amount) * (1 if direction == "down" else -1)
        elif direction in ("left", "right"):
            dx = round(b["w"] * amount) * (1 if direction == "right" else -1)
        else:
            raise InvalidArgument(f"direction must be up, down, left or right, not {direction!r}")
        self.send("input.scroll", x=x, y=y, dy=dy, dx=dx, steps=10)

    def _content(self) -> list[Box]:
        b = self.bounds()
        top, bottom = b["h"] * CONTENT_TOP, b["h"] * CONTENT_BOTTOM
        return [o for o in self.screen() if top < o["y"] < bottom and o["confidence"] >= 0.4]

    @staticmethod
    def _text_set(boxes: list[Box]) -> frozenset[str]:
        return frozenset(o["text"].strip() for o in boxes if o["text"].strip())

    def _settle(self, settle: float) -> list[Box]:
        """Read until two consecutive reads are identical, or `settle` seconds pass. Exact
        equality: nothing to tune, and a screen that never settles just uses its budget."""
        boxes, previous, deadline = self._content(), None, self.clock.now() + settle
        while self.clock.now() < deadline:
            current = self._text_set(boxes)
            if current == previous:
                break
            previous = current
            self.clock.sleep(0.25)
            boxes = self._content()
        return boxes

    def scroll_screen(
        self, direction: Direction = "down", amount: float = 0.6, settle: float = 2.5, at: At = None
    ) -> dict[str, Any]:
        """One scroll, then the settled content. Returns {before, after, boxes, moved}; `moved`
        only says whether the text set changed — judging progress is the caller's call."""
        before = self._text_set(self._content())
        self.scroll(direction, amount, at)
        self.clock.sleep(0.4)
        boxes = self._settle(settle)
        after = self._text_set(boxes)
        return {"before": sorted(before), "after": sorted(after), "boxes": boxes, "moved": before != after}

    def scroll_until(
        self,
        done: Callable[[list[Box]], Any],
        direction: Direction = "down",
        amount: float = 0.6,
        max_scrolls: int = 60,
        settle: float = 2.5,
        at: At = None,
    ) -> Any:
        """Scroll until done(boxes) is truthy (that value is returned) or the screen stops
        changing (None). YOUR predicate decides success."""
        hit = done(self._content())
        if hit:
            return hit
        stale = 0
        for _ in range(max_scrolls):
            res = self.scroll_screen(direction, amount, settle, at)
            hit = done(res["boxes"])
            if hit:
                return hit
            stale = 0 if res["moved"] else stale + 1
            if stale >= 2:
                return None
        return None

    def scroll_collect(
        self,
        extract: Callable[[list[Box]], list[Any]] | None = None,
        key: Callable[[Any], Hashable] | None = None,
        direction: Direction = "down",
        amount: float = 0.6,
        max_scrolls: int = 400,
        end_after: int = 3,
        settle: float = 2.5,
        on_progress: Callable[[int, int, int], None] | None = None,
        at: At = None,
    ) -> dict[str, Any]:
        """Walk a list and de-duplicate. Returns {items, stop, scrolls}; stop is "reached-end"
        after `end_after` scrolls with no new item, else "max-scrolls". Keep amount < 1 so
        screens overlap and no row falls between captures."""
        extract_fn = extract or _all_texts
        key_fn = key or _identity
        seen: set[Hashable] = set()
        items: list[Any] = []

        def ingest(boxes: list[Box]) -> int:
            new = 0
            for item in extract_fn(boxes):
                k = key_fn(item)
                if k not in seen:
                    seen.add(k)
                    items.append(item)
                    new += 1
            return new

        def screen_keys(boxes: list[Box]) -> set[Hashable]:
            return {key_fn(item) for item in extract_fn(boxes)}

        first = self._content()
        ingest(first)
        last_keys = screen_keys(first)
        stale = 0
        for i in range(1, max_scrolls + 1):
            res = self.scroll_screen(direction, amount, settle, at)
            boxes = res["boxes"]
            keys = screen_keys(boxes)
            if res["moved"] and amount < 1 and last_keys and keys and not keys & last_keys:
                # None of this screen's items were on the previous one: the list moved further
                # than asked (a fling) and rows may have been skipped. Step back until the screens
                # overlap again, so items stay complete AND in order (PITFALLS#scroll-overshoot).
                boxes = (
                    self._recover_gap(
                        lambda b, prev=last_keys: bool(screen_keys(b) & prev), direction, amount, settle, at
                    )
                    or boxes
                )
                keys = screen_keys(boxes)
            last_keys = keys or last_keys
            new = ingest(boxes)
            if on_progress:
                on_progress(i, len(items), new)
            stale = 0 if new else stale + 1
            if stale >= end_after:
                return {"items": items, "stop": "reached-end", "scrolls": i}
            if not new:
                self.clock.sleep(0.8)  # extra grace for a slow lazy-load
        return {"items": items, "stop": "max-scrolls", "scrolls": max_scrolls}

    def _recover_gap(
        self,
        overlaps: Callable[[list[Box]], bool],
        direction: Direction,
        amount: float,
        settle: float,
        at: At,
        tries: int = 4,
    ) -> list[Box] | None:
        back: Direction = _OPPOSITE[direction]
        for _ in range(tries):
            res = self.scroll_screen(back, amount / 2, settle, at)
            if overlaps(res["boxes"]):
                return res["boxes"]
        return None

    # --- waiting ------------------------------------------------------------

    def wait_stable(self, timeout: float = 6.0, interval: float = 0.5, settle: int = 2) -> bool:
        """True once `settle` consecutive reads are identical; False if `timeout` passes first."""
        deadline = self.clock.now() + timeout
        previous, same = self._text_set(self.screen()), 0
        while self.clock.now() < deadline:
            self.clock.sleep(interval)
            current = self._text_set(self.screen())
            same = same + 1 if current == previous else 0
            if same >= settle:
                return True
            previous = current
        return False

    def wait_for_text(
        self, query: str, timeout: float = 10.0, exact: bool = False, interval: float = 0.5
    ) -> Box | None:
        """The first box matching `query` once it appears, or None after `timeout`."""
        deadline = self.clock.now() + timeout
        while True:
            hits = self.find_text(query, exact)
            if hits:
                return hits[0]
            if self.clock.now() >= deadline:
                return None
            self.clock.sleep(interval)

    def wait_for_app(self, app_id: str, timeout: float = 10.0, interval: float = 0.3) -> bool:
        deadline = self.clock.now() + timeout
        while True:
            if self.current_app() == app_id:
                return True
            if self.clock.now() >= deadline:
                return False
            self.clock.sleep(interval)

    # --- tree ---------------------------------------------------------------

    def ui(self) -> list[Box]:
        """The accessibility tree as nodes, where the device has one."""
        return self.send("tree")

    def find_nodes(
        self, query: str | None = None, exact: bool = False, clickable_only: bool = False, **selector: Any
    ) -> list[Box]:
        """Tree elements as boxes. `query` matches text, content-desc or resource-id; extra
        keywords are selector keys (resource_id=…, content_desc=…, within={…})."""
        sel: dict[str, Any] = dict(selector)
        if query is not None:
            sel["text" if exact else "query"] = query
        if clickable_only:
            sel["clickable"] = True
        return self.send("ui.find", selector=sel)

    def tap_ui(
        self, target: str | dict[str, Any], index: int = 0, exact: bool = False, clickable_only: bool = False
    ) -> Box:
        """Tap a tree element by label or selector dict. Sees what screen() cannot: icons with a
        content-description, fields by resource-id. Taps the clickable ancestor when the matched
        node itself is not clickable."""
        if isinstance(target, dict):
            sel = dict(target)
            if clickable_only:
                sel["clickable"] = True
            hits = self.send("ui.find", selector=sel)
        else:
            hits = self.find_nodes(target, exact=exact, clickable_only=clickable_only)
        if len(hits) <= index:
            visible = self.screen_text()
            raise NotFound(
                f"no tree element matches {target!r} (index {index}); visible: {visible[:15]}",
                details={"selector": target, "visible": visible[:40]},
            )
        hit = hits[index]
        point = hit.get("clickable_ancestor") if not hit.get("clickable") else None
        self.tap(*(point["x"], point["y"]) if point else (hit["x"], hit["y"]))
        return hit

    # --- clipboard, notifications -------------------------------------------

    def clipboard(self) -> str:
        return self.send("clipboard.get")

    def set_clipboard(self, text: str) -> None:
        self.send("clipboard.set", text=text)

    def notifications(self, limit: int = 50) -> list[Box]:
        return self.send("notifications.list", limit=limit)

    # --- humans -------------------------------------------------------------

    def note(self, text: str) -> None:
        """A human-readable line on the run timeline (dashboard in remote mode, stderr locally)."""
        self.notes.append(text)
        print(f"[not] {text}", file=sys.stderr)

    def request_human(self, reason: str, timeout: float = 600.0) -> None:
        """Hand the phone to a person (a PIN, a 2FA code, anything you must not type) and wait
        until they hand it back. Raises NeedsUser if nobody can be asked."""
        if not self.human("human", reason, timeout):
            raise NeedsUser(f"kullanıcı devralmayı iptal etti: {reason}")

    def request_approval(self, summary: str, timeout: float = 600.0) -> None:
        """Ask a person to approve an outward-facing step before taking it. Raises ApprovalDenied."""
        if not self.human("approval", summary, timeout):
            raise ApprovalDenied(f"onay verilmedi: {summary}")


# --- the default phone ------------------------------------------------------

_default: Phone | None = None


def connect(uri: str | None = None, **phone_kw: Any) -> Phone:
    """A new Phone for `uri` (or the configured default). Does not change the default phone."""
    return Phone(_connect.connect(uri), **phone_kw)


def use(target: Phone | Backend | str | None = None) -> Phone:
    """Make `target` the phone the module-level helpers drive, and return it."""
    global _default
    if isinstance(target, Phone):
        _default = target
    elif isinstance(target, Backend):
        _default = Phone(target)
    else:
        _default = connect(target)
    return _default


def phone() -> Phone:
    """The default phone, connected on first use."""
    return _default if _default is not None else use()


def send(op: str, /, **kw: Any) -> Any:
    return phone().send(op, **kw)


def supports(op: str) -> bool:
    return phone().supports(op)


def ops() -> list[str]:
    return phone().ops()


def ensure_device() -> Box:
    return phone().ensure_device()


def connection_state() -> str:
    return phone().connection_state()


def connection_detail() -> str:
    return phone().connection_detail()


def device_info() -> Box:
    return phone().device_info()


def bounds() -> Box:
    return phone().bounds()


def screen(min_confidence: float = 0.3) -> list[Box]:
    return phone().screen(min_confidence)


def screen_text(min_confidence: float = 0.3) -> list[str]:
    return phone().screen_text(min_confidence)


def screenshot(path: str | None = None, max_side: int | None = None) -> str:
    return phone().screenshot(path, max_side)


def find_text(query: str, exact: bool = False) -> list[Box]:
    return phone().find_text(query, exact)


def tap(x: int, y: int) -> None:
    phone().tap(x, y)


def long_press(x: int, y: int, duration: float = 0.8) -> None:
    phone().long_press(x, y, duration)


def drag(x1: int, y1: int, x2: int, y2: int, duration: float = 0.35, steps: int = 14) -> None:
    phone().drag(x1, y1, x2, y2, duration, steps)


def tap_text(query: str, index: int = 0, exact: bool = False) -> Box:
    return phone().tap_text(query, index, exact)


def tap_image_point(x: float, y: float, image_size: tuple[int, int]) -> tuple[int, int]:
    return phone().tap_image_point(x, y, image_size)


def type_text(text: str, mode: str = "auto", delay: float = 0.03) -> Box:
    return phone().type_text(text, mode, delay)


def clear_text() -> None:
    phone().clear_text()


def press(combo: str) -> None:
    phone().press(combo)


def home() -> None:
    phone().home()


def back() -> None:
    phone().back()


def recents() -> None:
    phone().recents()


def notifications_panel() -> None:
    phone().notifications_panel()


def open_app(name: str, fresh: bool = False) -> str:
    return phone().open_app(name, fresh)


def current_app() -> str | None:
    return phone().current_app()


def list_apps(include_system: bool = False) -> list[Box]:
    return phone().list_apps(include_system)


def stop_app(app_id: str) -> None:
    phone().stop_app(app_id)


def swipe(direction: Direction, distance: float = 0.4, at: At = None) -> None:
    phone().swipe(direction, distance, at)


def scroll(direction: Direction = "down", amount: float = 0.3, at: At = None) -> None:
    phone().scroll(direction, amount, at)


def scroll_screen(
    direction: Direction = "down", amount: float = 0.6, settle: float = 2.5, at: At = None
) -> dict[str, Any]:
    return phone().scroll_screen(direction, amount, settle, at)


def scroll_until(
    done: Callable[[list[Box]], Any],
    direction: Direction = "down",
    amount: float = 0.6,
    max_scrolls: int = 60,
    settle: float = 2.5,
    at: At = None,
) -> Any:
    return phone().scroll_until(done, direction, amount, max_scrolls, settle, at)


def scroll_collect(
    extract: Callable[[list[Box]], list[Any]] | None = None,
    key: Callable[[Any], Hashable] | None = None,
    direction: Direction = "down",
    amount: float = 0.6,
    max_scrolls: int = 400,
    end_after: int = 3,
    settle: float = 2.5,
    on_progress: Callable[[int, int, int], None] | None = None,
    at: At = None,
) -> dict[str, Any]:
    return phone().scroll_collect(
        extract, key, direction, amount, max_scrolls, end_after, settle, on_progress, at
    )


def wait_stable(timeout: float = 6.0, interval: float = 0.5, settle: int = 2) -> bool:
    return phone().wait_stable(timeout, interval, settle)


def wait_for_text(
    query: str, timeout: float = 10.0, exact: bool = False, interval: float = 0.5
) -> Box | None:
    return phone().wait_for_text(query, timeout, exact, interval)


def wait_for_app(app_id: str, timeout: float = 10.0, interval: float = 0.3) -> bool:
    return phone().wait_for_app(app_id, timeout, interval)


def ui() -> list[Box]:
    return phone().ui()


def find_nodes(
    query: str | None = None, exact: bool = False, clickable_only: bool = False, **selector: Any
) -> list[Box]:
    return phone().find_nodes(query, exact, clickable_only, **selector)


def tap_ui(
    target: str | dict[str, Any], index: int = 0, exact: bool = False, clickable_only: bool = False
) -> Box:
    return phone().tap_ui(target, index, exact, clickable_only)


def clipboard() -> str:
    return phone().clipboard()


def set_clipboard(text: str) -> None:
    phone().set_clipboard(text)


def notifications(limit: int = 50) -> list[Box]:
    return phone().notifications(limit)


def note(text: str) -> None:
    phone().note(text)


def request_human(reason: str, timeout: float = 600.0) -> None:
    phone().request_human(reason, timeout)


def request_approval(summary: str, timeout: float = 600.0) -> None:
    phone().request_approval(summary, timeout)


__all__ = [
    "ApprovalDenied",
    "NeedsUser",
    "NotFound",
    "Phone",
    "back",
    "bounds",
    "clear_text",
    "clipboard",
    "connect",
    "connection_detail",
    "connection_state",
    "current_app",
    "device_info",
    "drag",
    "ensure_device",
    "find_nodes",
    "find_text",
    "home",
    "list_apps",
    "long_press",
    "note",
    "notifications",
    "notifications_panel",
    "open_app",
    "ops",
    "phone",
    "press",
    "recents",
    "request_approval",
    "request_human",
    "screen",
    "screen_text",
    "screenshot",
    "scroll",
    "scroll_collect",
    "scroll_screen",
    "scroll_until",
    "send",
    "set_clipboard",
    "stop_app",
    "supports",
    "swipe",
    "tap",
    "tap_image_point",
    "tap_text",
    "tap_ui",
    "type_text",
    "ui",
    "use",
    "wait_for_app",
    "wait_for_text",
    "wait_stable",
]
