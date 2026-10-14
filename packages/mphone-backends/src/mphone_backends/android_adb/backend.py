"""Android over adb (P2, Plan.md §8.2.1). See docs/PITFALLS.md#android-* before changing anything.

The phone is chosen once and pinned (`-s SERIAL`); a named or primary phone that cannot be
reached is an error, never a reason to drive another one (CLAUDE.md §6.2).
"""

import base64
import hashlib
import io
import logging
import os
import shlex
import tempfile
import threading
import time
from pathlib import Path
from typing import Any

from PIL import Image

from mphone_core import config, ocr
from mphone_core import tree as treeutil
from mphone_core.textnorm import match
from mphone_core.transport import Backend
from mphone_protocol import (
    DeviceAsleep,
    DeviceLocked,
    DeviceOffline,
    DeviceUnauthorized,
    InternalError,
    InvalidArgument,
    NeedsUser,
    NotFound,
    TreeUnavailable,
    Unsupported,
)

from . import parse
from .adb import UNAUTHORIZED_HINT, Adb
from .apps import ALIASES, label_for
from .keys import keycode
from .text import (
    KNOWN_IMES,
    MPHONE_IME,
    RESULT_DONE,
    RESULT_NO_FIELD,
    Ime,
    ascii_safe,
    broadcast_command,
    broadcast_result,
    clear_command,
    input_text_command,
)

Dict = dict[str, Any]
log = logging.getLogger(__name__)
LOCKED_ACTION = "Telefonun kilidini açın; PIN asla otomatik yazılmaz. Sonra aynı adımdan devam edin."
UI_DUMP = "/sdcard/mphone_ui.xml"
GATE_TTL = 2.0
TREE_BACKOFF = 10.0
IME_BIND_TIMEOUT = 5.0


class PrimaryUnreachable(DeviceOffline):
    """The saved primary phone is not reachable. Deliberately NOT replaced by another phone."""


class AndroidAdb(Backend):
    name = "android_adb"
    platform = "android"

    def __init__(self, target: str = "", adb: Adb | None = None) -> None:
        super().__init__()
        self.target = target
        self.adb = adb or Adb()
        self._resolved = False
        self._gate_at = 0.0
        self._tree_busy_until = 0.0
        self._motionevent: bool | None = None
        self._bounds: tuple[float, Dict] | None = None
        self._awake_thread: threading.Thread | None = None
        self._awake_stop = threading.Event()

    # --- choosing the phone ---------------------------------------------------------------

    def _devices(self) -> list[parse.DeviceRow]:
        return parse.parse_devices(self.adb.run("devices", "-l", pin=False))

    def _connect_mdns(self, name: str | None = None) -> None:
        services = parse.parse_mdns(self.adb.run("mdns", "services", pin=False, check=False))
        for service in services:
            if service.kind != "_adb-tls-connect._tcp":
                continue
            if name is not None and match(name, service.name) is None:
                continue
            self.adb.run("connect", service.addr, pin=False, check=False, timeout=15)

    def _pick(self, rows: list[parse.DeviceRow], serial: str) -> str:
        row = next((r for r in rows if r.serial == serial), None)
        if row is None:
            raise DeviceOffline(
                f"phone {serial} is not connected",
                user_action="Telefonu bağlayın; başka bir telefona geçilmedi.",
            )
        if row.state == "unauthorized":
            raise DeviceUnauthorized(
                f"phone {serial} has not authorised this computer", user_action=UNAUTHORIZED_HINT
            )
        if row.state != "device":
            raise DeviceOffline(
                f"phone {serial} is {row.state}",
                user_action="Kabloyu çıkarıp takın veya telefonu yeniden başlatın.",
            )
        return serial

    def resolve(self) -> str:
        """Pin one phone. Explicit serial > saved primary > USB > emulator > Wi-Fi > mDNS."""
        if self._resolved and self.adb.serial:
            return self.adb.serial
        target = self.target
        rows = self._devices()
        if target and target not in ("usb", "auto") and not target.startswith("wifi:"):
            serial = self._pick(rows, target)
        elif target.startswith("wifi:"):
            name = target[len("wifi:") :]
            self._connect_mdns(name)
            rows = self._devices()
            wifi = [r for r in rows if r.transport == "wifi" and match(name, r.model or r.serial) is not None]
            if not wifi:
                raise DeviceOffline(
                    f"no Wi-Fi phone named {name!r} answered",
                    user_action="Kablosuz hata ayıklamanın açık olduğunu ve aynı ağda olduğunuzu kontrol edin.",
                )
            serial = self._pick(rows, wifi[0].serial)
        elif primary := config.get("android.primary"):
            if not any(r.serial == primary for r in rows):
                self._connect_mdns()
                rows = self._devices()
            if not any(r.serial == primary and r.state == "device" for r in rows):
                raise PrimaryUnreachable(
                    f"the primary Android phone {primary!r} is unreachable; no other phone was used",
                    user_action="Birincil telefonu bağlayın veya `mphone config unset android.primary`.",
                )
            serial = self._pick(rows, str(primary))
        else:
            order = {"usb": 0, "emulator": 1, "wifi": 2}
            ready = sorted((r for r in rows if r.state == "device"), key=lambda r: order.get(r.transport, 3))
            if target == "usb":
                ready = [r for r in ready if r.transport == "usb"]
            if not ready:
                if any(r.state == "unauthorized" for r in rows):
                    raise DeviceUnauthorized(
                        "a phone is connected but has not authorised this computer",
                        user_action=UNAUTHORIZED_HINT,
                    )
                self._connect_mdns()
                ready = [r for r in self._devices() if r.state == "device"]
            if not ready:
                raise DeviceOffline(
                    "no Android phone is connected",
                    user_action="Telefonu USB ile bağlayıp USB hata ayıklamayı açın veya `mphone android pair KOD` ile Wi-Fi'dan eşleyin.",
                )
            serial = ready[0].serial
        self.adb.serial = serial
        self._resolved = True
        return serial

    def _sh(self, cmd: str, timeout: float = 60, check: bool = True) -> str:
        self.resolve()
        return self.adb.shell(cmd, timeout=timeout, check=check)

    # --- awake and unlocked? ------------------------------------------------------------------

    def _power_state(self) -> tuple[str | None, bool | None]:
        out = self._sh(
            "dumpsys power | grep -E 'mWakefulness='; echo ---; "
            "dumpsys window | grep -E 'isKeyguardShowing|mShowingLockscreen'; echo ---; "
            "dumpsys window policy | grep -A1 KeyguardServiceDelegate",
            check=False,
        )
        power, _, rest = out.partition("---")
        window, _, policy = rest.partition("---")
        return parse.parse_wakefulness(power), parse.parse_keyguard_showing(window, policy)

    def _gate(self) -> None:
        """Refuse input unless the phone is awake and unlocked (PITFALLS#android-locked-taps).
        Waking is harmless and done here; unlocking is the user's. Cached for 2 s."""
        if time.monotonic() - self._gate_at < GATE_TTL:
            return
        wakefulness, locked = self._power_state()
        if not parse.is_awake(wakefulness):
            self._sh("input keyevent KEYCODE_WAKEUP")
            time.sleep(0.6)
            wakefulness, locked = self._power_state()
            if not parse.is_awake(wakefulness):
                raise DeviceAsleep(
                    f"the screen did not wake ({wakefulness})",
                    user_action="Güç düğmesine basarak ekranı açın.",
                )
        if locked:
            raise DeviceLocked("the phone is locked", user_action=LOCKED_ACTION)
        self._gate_at = time.monotonic()

    # --- device ops -------------------------------------------------------------------------

    def _device_state(self) -> str:
        try:
            serial = self.resolve()
        except DeviceUnauthorized:
            return "unauthorized"
        except DeviceOffline:
            return "offline"
        row = next((r for r in self._devices() if r.serial == serial), None)
        if row is None:
            return "offline"
        if row.state == "unauthorized":
            return "unauthorized"
        if row.state != "device":
            return "offline"
        wakefulness, locked = self._power_state()
        if locked:
            return "locked"
        return "ready" if parse.is_awake(wakefulness) else "asleep"

    def _device_require(self) -> Dict:
        self.resolve()
        self._gate_at = 0.0
        self._gate()
        return self._screen_bounds()

    def _device_detail(self) -> str:
        state = self._device_state()
        serial = self.adb.serial or "?"
        return {
            "ready": f"Android {serial} is ready",
            "locked": f"Android {serial} is locked: {LOCKED_ACTION}",
            "asleep": f"Android {serial} screen is off",
            "unauthorized": f"Android {serial}: {UNAUTHORIZED_HINT}",
            "offline": "no Android phone is reachable",
        }.get(state, state)

    def _device_info(self) -> Dict:
        props = self._sh(
            "for p in ro.build.version.release ro.product.model ro.product.manufacturer ro.serialno "
            'persist.sys.locale ro.product.locale persist.sys.timezone; do echo "$p=$(getprop $p)"; done'
        )
        values = dict(line.split("=", 1) for line in props.splitlines() if "=" in line)
        level, charging = parse.parse_battery(self._sh("dumpsys battery", check=False))
        serial = values.get("ro.serialno") or self.adb.serial or ""
        return {
            "platform": "android",
            "os_version": values.get("ro.build.version.release", ""),
            "model": values.get("ro.product.model", ""),
            "manufacturer": values.get("ro.product.manufacturer") or None,
            "serial_hash": hashlib.sha256(serial.encode()).hexdigest()[:12] if serial else None,
            "battery": level,
            "charging": charging,
            "locale": values.get("persist.sys.locale") or values.get("ro.product.locale") or None,
            "timezone": values.get("persist.sys.timezone") or None,
        }

    def _device_wake(self) -> None:
        self._sh("input keyevent KEYCODE_WAKEUP")
        self._gate_at = 0.0

    def _device_keep_awake(self, on: bool) -> None:
        """Wake the screen every 20 s without changing any setting (PITFALLS#android-screen-timeout)."""
        if not on:
            self._awake_stop.set()
            self._awake_thread = None
            return
        if self._awake_thread is not None:
            return
        self._awake_stop.clear()

        def loop() -> None:
            while not self._awake_stop.wait(20):
                try:
                    self._sh("input keyevent KEYCODE_WAKEUP", check=False)
                except Exception as e:  # a missed poke must not kill the thread
                    log.warning("keep-awake poke failed: %s", e)

        self._awake_thread = threading.Thread(target=loop, name="mphone-keep-awake", daemon=True)
        self._awake_thread.start()

    def close(self) -> None:
        self._awake_stop.set()

    # --- screen -----------------------------------------------------------------------------

    def _screen_bounds(self) -> Dict:
        if self._bounds and time.monotonic() - self._bounds[0] < GATE_TTL:
            return self._bounds[1]
        size = parse.parse_wm_size(self._sh("wm size"))
        density = parse.parse_wm_density(self._sh("wm density")) or 160
        rotation = parse.parse_rotation(
            self._sh("dumpsys display | grep -m1 mCurrentOrientation", check=False)
        )
        if size is None:
            raise InternalError("could not read the screen size (`wm size`)")
        w, h = size
        if rotation in (90, 270):
            w, h = h, w
        bounds = {"w": w, "h": h, "scale": round(density / 160, 3), "rotation": rotation}
        self._bounds = (time.monotonic(), bounds)
        return bounds

    def _screen_capture(self, format: str, quality: int, max_side: int | None, path: str | None) -> Dict:
        self.resolve()
        png = self.adb.shell_bytes("screencap -p", timeout=60)
        if not png.startswith(b"\x89PNG"):
            raise InternalError(f"screencap returned no PNG: {png[:120]!r}")
        image = Image.open(io.BytesIO(png))
        secure = image.convert("L").getextrema() == (0, 0)  # FLAG_SECURE blacks the frame out
        data = png
        if max_side and max(image.size) > max_side:
            ratio = max_side / max(image.size)
            image = image.resize((round(image.width * ratio), round(image.height * ratio)))
        if format == "jpeg" or image.size != Image.open(io.BytesIO(png)).size:
            buf = io.BytesIO()
            if format == "jpeg":
                image.convert("RGB").save(buf, format="JPEG", quality=quality)
            else:
                image.save(buf, format="PNG")
            data = buf.getvalue()
        if path is None:
            fd, path = tempfile.mkstemp(prefix="mphone-android-", suffix=f".{format}")
            os.close(fd)
        Path(path).write_bytes(data)
        return {
            "w": image.width,
            "h": image.height,
            "format": format,
            "path": path,
            "data_b64": None,
            "artifact_id": None,
            "secure": secure,
        }

    def _tree(self, compressed: bool) -> list[Dict]:
        if time.monotonic() < self._tree_busy_until:
            raise TreeUnavailable(
                "the tree was unavailable moments ago (screen not idle); reading pixels instead"
            )
        flag = "--compressed " if compressed else ""
        out = self._sh(
            f"uiautomator dump {flag}{UI_DUMP} 2>&1; cat {UI_DUMP} 2>/dev/null; rm -f {UI_DUMP}",
            timeout=45,
            check=False,
        )
        lowered = out.lower()
        if "could not get idle state" in lowered or "null root node" in lowered or "<hierarchy" not in out:
            self._tree_busy_until = time.monotonic() + TREE_BACKOFF
            raise TreeUnavailable(
                "uiautomator could not read this screen (it never goes idle, e.g. video or animation)",
                details={"output": out.strip()[:300]},
            )
        nodes, _ = parse.parse_uiautomator(out)
        return nodes

    def _screen_text(self, min_confidence: float) -> list[Dict]:
        try:
            nodes = self._tree(True)
        except TreeUnavailable:
            return self._screen_text_pixels(min_confidence, ["tr", "en"])
        return [b for b in treeutil.nodes_to_boxes(nodes) if b["confidence"] >= min_confidence]

    def _screen_text_pixels(self, min_confidence: float, langs: list[str]) -> list[Dict]:
        engine = ocr.get_engine(str(config.get("ocr.engine") or "auto"))
        cap = self._screen_capture("png", 85, None, None)
        try:
            png = Path(cap["path"]).read_bytes()
        finally:
            Path(cap["path"]).unlink(missing_ok=True)
        return [b for b in engine.recognize(png, langs) if b["confidence"] >= min_confidence]

    def _ui_find(self, selector: Dict) -> list[Dict]:
        return treeutil.select(self._tree(True), selector)

    # --- input -------------------------------------------------------------------------------

    def _input_tap(self, x: int, y: int) -> None:
        self._gate()
        self._sh(f"input tap {x} {y}")

    def _input_press(self, x: int, y: int, duration: float) -> None:
        self._gate()
        self._sh(f"input swipe {x} {y} {x} {y} {round(duration * 1000)}")

    def _input_drag(self, x1: int, y1: int, x2: int, y2: int, duration: float, steps: int) -> None:
        """Finger motion with its real duration: a short one is a flick and the content coasts."""
        self._gate()
        self._sh(f"input swipe {x1} {y1} {x2} {y2} {max(1, round(duration * 1000))}")

    def _has_motionevent(self) -> bool:
        if self._motionevent is None:
            self._motionevent = "motionevent" in self._sh("input 2>&1", check=False)
        return self._motionevent

    def _input_scroll(self, x: int, y: int, dy: int, dx: int, steps: int) -> None:
        """Content-space scroll with no momentum (PITFALLS#android-scroll-vs-swipe): the finger
        moves opposite to the content, then rests before lifting so the list does not fling."""
        self._gate()
        b = self._screen_bounds()
        clamp = lambda v, hi: max(1, min(hi - 2, v))  # noqa: E731
        x1, y1 = clamp(x + dx // 2, b["w"]), clamp(y + dy // 2, b["h"])
        x2, y2 = clamp(x - dx // 2, b["w"]), clamp(y - dy // 2, b["h"])
        if not self._has_motionevent():
            self._sh(f"input swipe {x1} {y1} {x2} {y2} {300 + 60 * steps}")
            return
        moves = " && ".join(
            f"input motionevent MOVE {round(x1 + (x2 - x1) * i / steps)} {round(y1 + (y2 - y1) * i / steps)}"
            for i in range(1, steps + 1)
        )
        # Rest at the end with stationary MOVEs before UP: the velocity tracker then sees zero
        # speed and the list cannot fling (API 34 flung once after a plain sleep, skipping 2 rows).
        hold = f"input motionevent MOVE {x2} {y2} && sleep 0.1 && input motionevent MOVE {x2} {y2}"
        self._sh(
            f"input motionevent DOWN {x1} {y1} && {moves} && sleep 0.1 && {hold} && input motionevent UP {x2} {y2}"
        )

    def _input_keys(self, combo: str) -> None:
        self._gate()
        self._sh(f"input keyevent {keycode(combo)}")

    def _installed_ime(self) -> Ime | None:
        available = self._sh("ime list -a -s", check=False)
        for ime in KNOWN_IMES:
            if ime.ime_id in available:
                return ime
        return None

    def _with_ime(self, command: str) -> None:
        """Switch to our IME for one command and switch back, so the person's keyboard returns.

        The mphone IME answers the ordered broadcast: 0 = nobody listened yet (the service is
        created asynchronously after `ime set`, PITFALLS#android-ime-first-bind), 1 = done,
        2 = no focused field. Retry on 0; never report success for text that went nowhere.
        """
        ime = self._installed_ime()
        if ime is None:
            raise NeedsUser(
                "non-ASCII text needs the mphone keyboard on the phone",
                user_action="Bir kez çalıştırın: `mphone android ime install`",
            )
        previous = self._sh("settings get secure default_input_method", check=False).strip()
        if previous != ime.ime_id:
            self._sh(f"ime enable {ime.ime_id} && ime set {ime.ime_id}")
        try:
            if ime is not MPHONE_IME:  # third-party IME: no result codes, so wait and send once
                time.sleep(1.0)
                self._sh(command)
                return
            deadline = time.monotonic() + IME_BIND_TIMEOUT
            while True:
                code = broadcast_result(self._sh(command))
                if code == RESULT_DONE:
                    return
                if code == RESULT_NO_FIELD:
                    raise NotFound(
                        "no text field is focused, so the text went nowhere",
                        user_action="Önce metin alanına dokunun (tap_text / tap_ui), sonra yazın.",
                    )
                if time.monotonic() >= deadline:
                    raise InternalError(
                        f"the mphone keyboard did not answer within {IME_BIND_TIMEOUT:g}s (result={code})"
                    )
                time.sleep(0.3)
        finally:
            if previous and previous != ime.ime_id and previous != "null":
                self._sh(f"ime set {shlex.quote(previous)}", check=False)

    def _input_text(self, s: str, mode: str, delay: float) -> Dict:
        self._gate()
        if mode == "paste":
            raise Unsupported("adb has no paste path on Android; use mode='auto' or 'ime'")
        if mode == "keystrokes" or (mode == "auto" and ascii_safe(s)):
            if not ascii_safe(s):
                raise Unsupported("adb keystrokes are ASCII-only; use mode='auto' or 'ime' for this text")
            self._sh(input_text_command(s))
            return {"mode_used": "keystrokes"}
        ime = self._installed_ime()
        if ime is None:
            raise NeedsUser(
                "non-ASCII text needs the mphone keyboard on the phone",
                user_action="Bir kez çalıştırın: `mphone android ime install`",
            )
        self._with_ime(broadcast_command(ime, s))
        return {"mode_used": "ime"}

    def _input_clear(self) -> None:
        self._gate()
        ime = self._installed_ime()
        if ime is not None:
            self._with_ime(clear_command(ime))
            return
        focused = [n for n in self._tree(True) if n.get("focused") and n.get("editable")]
        count = len(focused[0]["text"]) if focused else 0
        if count:
            self._sh("input keyevent KEYCODE_MOVE_END && input keyevent " + " ".join(["KEYCODE_DEL"] * count))

    # --- navigation ----------------------------------------------------------------------------

    def _nav_home(self) -> None:
        self._gate()
        self._sh("input keyevent KEYCODE_HOME")

    def _nav_back(self) -> None:
        self._gate()
        self._sh("input keyevent KEYCODE_BACK")

    def _nav_recents(self) -> None:
        self._gate()
        self._sh("input keyevent KEYCODE_APP_SWITCH")

    def _nav_notifications(self) -> None:
        self._gate()
        self._sh("cmd statusbar expand-notifications")

    # --- apps ----------------------------------------------------------------------------------

    def _packages(self, include_system: bool = True) -> list[str]:
        return parse.parse_packages(self._sh("pm list packages" + ("" if include_system else " -3")))

    def _resolve_app(self, name: str) -> str:
        installed = self._packages()
        if name in installed:
            return name
        scored: list[tuple[int, str]] = []
        for pkg in installed:
            labels = [label for label, ids in ALIASES.items() if pkg in ids]
            best = min((s for label in labels if (s := match(name, label)) is not None), default=None)
            if best is None and match(name, pkg) is not None:
                best = 5
            if best is not None:
                scored.append((best, pkg))
        if not scored:
            third_party = self._packages(include_system=False)
            raise NotFound(
                f"no installed app matches {name!r}",
                details={"query": name, "installed": sorted(label_for(p) or p for p in third_party)[:80]},
            )
        scored.sort()
        return scored[0][1]

    def _apps_launch(self, name: str, fresh: bool) -> Dict:
        self._gate()
        pkg = self._resolve_app(name)
        if fresh:
            self._sh(f"am force-stop {shlex.quote(pkg)}")
        component = parse.parse_resolved_component(
            self._sh(
                f"cmd package resolve-activity --brief -c android.intent.category.LAUNCHER {shlex.quote(pkg)}",
                check=False,
            )
        )
        if component:
            self._sh(f"am start -W -n {shlex.quote(component)}", timeout=60)
        else:
            self._sh(f"monkey -p {shlex.quote(pkg)} -c android.intent.category.LAUNCHER 1", check=False)
        return {"app_id": pkg}

    def _apps_current(self) -> Dict | None:
        pkg = parse.parse_resumed_package(
            self._sh("dumpsys activity activities | grep -E 'ResumedActivity'", check=False)
        )
        return {"app_id": pkg} if pkg else None

    def _apps_list(self, include_system: bool) -> list[Dict]:
        system = set(self._packages()) - set(self._packages(include_system=False))
        pkgs = self._packages(include_system)
        return [{"app_id": p, "label": label_for(p), "system": p in system} for p in sorted(pkgs)]

    def _apps_stop(self, app_id: str) -> None:
        self._sh(f"am force-stop {shlex.quote(app_id)}")

    def _apps_install(self, artifact_id: str | None, url: str | None, path: str | None) -> Dict:
        if path is None:
            raise InvalidArgument("on a local Android, apps.install takes path=…")
        before = set(self._packages())
        out = self.adb.run("install", "-r", "-g", path, timeout=300)
        if "Success" not in out:
            raise InternalError(f"adb install failed: {out.strip()[:300]}")
        new = set(self._packages()) - before
        if len(new) == 1:
            return {"app_id": new.pop()}
        stem = Path(path).stem
        if stem in before:
            return {"app_id": stem}
        raise InternalError(
            "installed, but could not tell which package it was (reinstall of an existing app?)"
        )

    def _apps_uninstall(self, app_id: str) -> None:
        out = self.adb.run("uninstall", app_id, check=False)
        if "Success" not in out:
            raise NotFound(f"could not uninstall {app_id}: {out.strip()[:200]}")

    # --- misc ------------------------------------------------------------------------------------

    def _notifications_list(self, limit: int) -> list[Dict]:
        return parse.parse_notifications(self._sh("dumpsys notification --noredact", check=False), limit)

    def _focus_probe(self) -> list[bool]:
        return [True]

    def _focus_diff(self, before: Any, after: Any) -> Dict:
        return {"raised": False, "stole_focus": False}  # adb touches nothing on this computer

    def _files_push(self, dest: str, artifact_id: str | None, path: str | None) -> None:
        if path is None:
            raise InvalidArgument("on a local Android, files.push takes path=…")
        self.resolve()
        self.adb.run("push", path, dest, timeout=300)

    def _files_pull(self, path: str) -> Dict:
        self.resolve()
        fd, local = tempfile.mkstemp(prefix="mphone-pull-")
        os.close(fd)
        self.adb.run("pull", path, local, timeout=300)
        return {"artifact_id": None, "local_path": local}

    def _raw(self, cmd: str, binary: bool, timeout: float) -> Any:
        self.resolve()
        if binary:
            return base64.b64encode(self.adb.shell_bytes(cmd, timeout=timeout)).decode()
        return self.adb.shell(cmd, timeout=timeout, check=False)


def from_uri(rest: str) -> AndroidAdb:
    """android: | android:usb | android:SERIAL | android:wifi:NAME"""
    return AndroidAdb(rest)
