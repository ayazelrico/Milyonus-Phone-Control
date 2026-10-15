"""AndroidAdb behaviour with a scripted adb (no device): choosing, gating, input, text, tree."""

import base64
import re
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import pytest

from mphone_backends.android_adb.adb import Adb
from mphone_backends.android_adb.backend import AndroidAdb, PrimaryUnreachable
from mphone_core import config, ocr
from mphone_core.helpers import Phone
from mphone_protocol import DeviceLocked, DeviceOffline, DeviceUnauthorized, NeedsUser, Unsupported

FIX = Path(__file__).resolve().parents[2] / "fixtures" / "android" / "emulator_api34"
AWAKE = "  mWakefulness=Awake\n---\n    isKeyguardShowing=false\n---\n"
LOCKED = "  mWakefulness=Awake\n---\n    isKeyguardShowing=true\n---\n"
ASLEEP = "  mWakefulness=Dozing\n---\n    isKeyguardShowing=false\n---\n"
LAT = "com.google.android.inputmethod.latin/com.android.inputmethod.latin.LatinIME"


def fx(name: str) -> str:
    return (FIX / f"{name}.out").read_text(encoding="utf-8")


class ScriptedAdb(Adb):
    """Answers by matching the command against rules; records every call."""

    def __init__(self, devices: str = "", **state: Any) -> None:
        super().__init__(binary="/fake/adb")
        self.devices = devices or fx("devices_l")
        self.power = AWAKE
        self.imes = f"{LAT}\ncom.milyonus.mphone.ime/.MphoneIme\n"
        self.current_ime = LAT
        self.tree = fx("uia_testfields")
        self.ime_results: list[int] = []
        self.calls: list[str] = []
        self.__dict__.update(state)

    def run_bytes(self, *args: str, timeout: float = 60, check: bool = True, pin: bool = True) -> bytes:
        cmd = " ".join(args)
        self.calls.append(cmd)
        return self.answer(cmd).encode()

    def answer(self, cmd: str) -> str:
        if cmd == "devices -l":
            return self.devices
        if cmd.startswith("mdns services"):
            return "List of discovered mdns services\n"
        if "mWakefulness" in cmd:
            return self.power
        if cmd.endswith("input KEYCODE_WAKEUP") or "KEYCODE_WAKEUP" in cmd:
            self.power = AWAKE if self.power == ASLEEP else self.power
            return ""
        if "ime list -a -s" in cmd:
            return self.imes
        if "default_input_method" in cmd:
            return self.current_ime + "\n"
        if m := re.search(r"ime set (\S+)", cmd):
            self.current_ime = m.group(1).strip("'")
            return ""
        if "uiautomator dump" in cmd:
            return self.tree
        if "am broadcast" in cmd:
            code = self.ime_results.pop(0) if self.ime_results else 1
            return f"Broadcasting: Intent {{ act=x }}\nBroadcast completed: result={code}\n"
        rules = {
            "wm size": fx("wm_size"),
            "wm density": fx("wm_density"),
            "mCurrentOrientation": "    mCurrentOrientation=0\n",
            "pm list packages": fx("pm_list_all"),
            "resolve-activity": fx("resolve_settings"),
            "ResumedActivity": fx("activity_settings"),
            "input 2>&1": fx("input_help"),
        }
        for key, value in rules.items():
            if key in cmd:
                return value
        return ""


def make(adb: ScriptedAdb, target: str = "") -> AndroidAdb:
    return AndroidAdb(target, adb=adb)


def inputs(adb: ScriptedAdb) -> list[str]:
    return [
        c
        for c in adb.calls
        if re.search(r"\binput (tap|swipe|text|keyevent|motionevent)", c) and "KEYCODE_WAKEUP" not in c
    ]


# --- choosing the phone ------------------------------------------------------------------------

USB_WIFI_EMU = (
    "List of devices attached\n"
    "192.168.1.20:41235     device product:a54 model:SM_A546E transport_id:4\n"
    "emulator-5554          device product:sdk model:sdk_gphone64 transport_id:1\n"
    "R58N123ABC             device usb:1-1 product:a54 model:SM_A546E transport_id:3\n"
)


def test_usb_beats_emulator_beats_wifi() -> None:
    assert make(ScriptedAdb(USB_WIFI_EMU)).resolve() == "R58N123ABC"
    no_usb = "\n".join(line for line in USB_WIFI_EMU.splitlines() if "usb:" not in line)
    assert make(ScriptedAdb(no_usb)).resolve() == "emulator-5554"


def test_explicit_serial_is_never_substituted() -> None:
    with pytest.raises(DeviceOffline, match="not connected"):
        make(ScriptedAdb(USB_WIFI_EMU), "ZZZ999").resolve()


def test_unreachable_primary_is_an_error_not_another_phone() -> None:
    config.set_value("android.primary", "GONE123")
    adb = ScriptedAdb(USB_WIFI_EMU)
    with pytest.raises(PrimaryUnreachable) as e:
        make(adb).resolve()
    assert "no other phone was used" in e.value.message
    assert adb.serial is None  # nothing got pinned


def test_unauthorized_only() -> None:
    adb = ScriptedAdb("List of devices attached\nR58N123ABC unauthorized usb:1-1 transport_id:3\n")
    with pytest.raises(DeviceUnauthorized) as e:
        make(adb).resolve()
    assert e.value.user_action and "İzin ver" in e.value.user_action
    assert (
        make(ScriptedAdb("List of devices attached\nR58 unauthorized usb:1 transport_id:3\n")).send(
            "device.state"
        )
        == "unauthorized"
    )


def test_no_phone() -> None:
    with pytest.raises(DeviceOffline):
        make(ScriptedAdb("List of devices attached\n\n")).resolve()


def test_commands_are_pinned_after_resolve() -> None:
    adb = ScriptedAdb()
    make(adb).send("input.tap", x=1, y=2)
    assert adb.serial == "emulator-5554"
    assert adb.argv("shell", "x")[:3] == ["/fake/adb", "-s", "emulator-5554"]


# --- the gate ------------------------------------------------------------------------------------


def test_locked_phone_gets_no_touch() -> None:
    adb = ScriptedAdb(power=LOCKED)
    d = make(adb)
    for op, kw in [
        ("input.tap", {"x": 5, "y": 5}),
        ("input.text", {"s": "1234"}),
        ("nav.home", {}),
        ("input.scroll", {"x": 5, "y": 900, "dy": 300}),
        ("apps.launch", {"name": "Ayarlar"}),
    ]:
        with pytest.raises(DeviceLocked):
            d.send(op, **kw)
    assert inputs(adb) == []
    assert d.send("device.state") == "locked"


def test_asleep_is_woken_then_driven() -> None:
    adb = ScriptedAdb(power=ASLEEP)
    make(adb).send("input.tap", x=10, y=20)
    assert any("KEYCODE_WAKEUP" in c for c in adb.calls)
    assert inputs(adb) == ["shell input tap 10 20"]


def test_require_returns_bounds() -> None:
    assert make(ScriptedAdb()).send("device.require") == {"w": 1080, "h": 2400, "scale": 2.625, "rotation": 0}


# --- input -----------------------------------------------------------------------------------------


def test_scroll_has_no_momentum_and_moves_the_finger_against_the_content() -> None:
    adb = ScriptedAdb()
    make(adb).send("input.scroll", x=540, y=1200, dy=600, steps=3)
    (cmd,) = inputs(adb)
    assert cmd.startswith("shell input motionevent DOWN 540 1500")  # finger starts low…
    assert cmd.endswith("input motionevent MOVE 540 900 && input motionevent UP 540 900")  # …rests, lifts
    assert cmd.count("MOVE") == 5  # 3 steps + 2 stationary samples so the list cannot fling


def test_drag_keeps_its_duration() -> None:
    adb = ScriptedAdb()
    make(adb).send("input.drag", x1=500, y1=1800, x2=500, y2=600, duration=0.15)
    assert inputs(adb) == ["shell input swipe 500 1800 500 600 150"]


def test_keys_and_chords() -> None:
    adb = ScriptedAdb()
    d = make(adb)
    d.send("input.keys", combo="enter")
    assert inputs(adb) == ["shell input keyevent KEYCODE_ENTER"]
    with pytest.raises(Unsupported):
        d.send("input.keys", combo="ctrl+a")


def test_ascii_text_uses_input_text() -> None:
    adb = ScriptedAdb()
    assert make(adb).send("input.text", s="hello world")["mode_used"] == "keystrokes"
    assert "shell input text hello%sworld" in adb.calls


def test_turkish_text_switches_to_the_ime_and_back() -> None:
    adb = ScriptedAdb()
    text = "Çağrı ışığı söndü; İğdır'a gidiyoruz! 🚀"
    assert make(adb).send("input.text", s=text)["mode_used"] == "ime"
    sets = [c for c in adb.calls if "ime set" in c]
    assert "com.milyonus.mphone.ime/.MphoneIme" in sets[0] and LAT in sets[-1]
    broadcast = next(c for c in adb.calls if "INPUT_B64" in c)
    assert base64.b64decode(broadcast.split()[-1]).decode("utf-8") == text
    assert adb.current_ime == LAT  # the person's keyboard is back


def test_ime_not_listening_yet_is_retried(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("time.sleep", lambda s: None)
    adb = ScriptedAdb(ime_results=[0, 0, 1])  # the IME service is created after `ime set`
    assert make(adb).send("input.text", s="Şule")["mode_used"] == "ime"
    assert sum("INPUT_B64" in c for c in adb.calls) == 3


def test_early_no_field_after_a_switch_is_retried(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("time.sleep", lambda s: None)
    adb = ScriptedAdb(ime_results=[2, 1])  # the new IME had not bound to the field yet
    assert make(adb).send("input.text", s="Şule")["mode_used"] == "ime"


def test_ime_reports_no_focused_field(monkeypatch: pytest.MonkeyPatch) -> None:
    from mphone_protocol import NotFound

    clock = iter(range(0, 1000))
    monkeypatch.setattr("time.monotonic", lambda: float(next(clock)))
    monkeypatch.setattr("time.sleep", lambda s: None)
    adb = ScriptedAdb(ime_results=[2] * 50)
    with pytest.raises(NotFound) as e:
        make(adb).send("input.text", s="Şule")
    assert e.value.user_action and "dokunun" in e.value.user_action
    assert adb.current_ime == LAT  # keyboard restored even on failure


def test_turkish_without_ime_asks_for_install() -> None:
    adb = ScriptedAdb(imes=f"{LAT}\n")
    with pytest.raises(NeedsUser) as e:
        make(adb).send("input.text", s="Şule")
    assert e.value.user_action and "mphone android ime install" in e.value.user_action
    assert not any("broadcast" in c for c in adb.calls)


def test_paste_and_non_ascii_keystrokes_are_unsupported() -> None:
    d = make(ScriptedAdb())
    with pytest.raises(Unsupported):
        d.send("input.text", s="x", mode="paste")
    with pytest.raises(Unsupported):
        d.send("input.text", s="ç", mode="keystrokes")


# --- tree and text ------------------------------------------------------------------------------


def test_tree_dumps_to_a_file_never_dev_tty() -> None:
    adb = ScriptedAdb()
    boxes = make(adb).send("screen.text")
    assert any(b["text"] == "Gönder" for b in boxes)
    dump = next(c for c in adb.calls if "uiautomator dump" in c)
    assert "/dev/tty" not in dump and "/sdcard/mphone_ui.xml" in dump


class StubOcr:
    name = "stub"

    def available(self) -> bool:
        return True

    def recognize(self, png: bytes, langs: Sequence[str] = ("tr", "en")) -> list[dict[str, Any]]:
        return [ocr.box("Oynatılıyor", 0.9, 10, 10, 200, 40)]


def test_idle_state_falls_back_to_pixels_and_backs_off(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    adb = ScriptedAdb(tree="ERROR: could not get idle state.\n")
    d = make(adb)
    monkeypatch.setattr(ocr, "_FACTORIES", {"rapidocr": StubOcr})
    monkeypatch.setattr(ocr, "_load_entry_points", lambda: None)  # keep real engines out
    png = tmp_path / "x.png"
    from PIL import Image

    Image.new("RGB", (1080, 2400), "white").save(png)
    monkeypatch.setattr(d.adb, "shell_bytes", lambda cmd, timeout=60: png.read_bytes())
    boxes = d.send("screen.text")
    assert boxes[0]["source"] == "pixels"
    dumps = sum("uiautomator dump" in c for c in adb.calls)
    d.send("screen.text")
    assert sum("uiautomator dump" in c for c in adb.calls) == dumps  # backed off: no second dump


def test_tap_ui_by_resource_id() -> None:
    adb = ScriptedAdb()
    p = Phone(make(adb))
    hit = p.tap_ui({"resource_id": "mphone_send"})
    assert hit["text"] == "Gönder"
    assert inputs(adb) == [f"shell input tap {hit['x']} {hit['y']}"]


# --- apps --------------------------------------------------------------------------------------------


def test_launch_by_turkish_name() -> None:
    adb = ScriptedAdb()
    assert make(adb).send("apps.launch", name="ayarlar") == {"app_id": "com.android.settings"}
    assert any("am start -W -n com.android.settings/.Settings" in c for c in adb.calls)
    assert make(ScriptedAdb()).send("apps.current") == {"app_id": "com.android.settings"}


def test_unknown_app_lists_what_is_installed() -> None:
    from mphone_protocol import NotFound

    with pytest.raises(NotFound):
        make(ScriptedAdb()).send("apps.launch", name="Instagram")


def test_clipboard_is_honestly_unsupported() -> None:
    d = make(ScriptedAdb())
    assert not d.supports("clipboard.get")
    assert not d.supports("screen.stream.start")


def test_no_platform_names_leak_into_helpers() -> None:
    """CLAUDE.md §2: helpers.py never names a platform; platform knowledge lives in backends."""
    from mphone_core import helpers

    text = Path(helpers.__file__).read_text(encoding="utf-8")
    assert not re.search(r"\b(adb|uiautomator|Quartz|android_adb)\b", text)
