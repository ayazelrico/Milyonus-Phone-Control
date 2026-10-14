"""The P2 exit criteria on a real Android (Phases.md P2)."""

import subprocess
import time

import pytest

from mphone_core.helpers import Phone
from mphone_protocol import DeviceLocked

pytestmark = pytest.mark.emulator

TURKISH = "Çağrı ışığı söndü; İğdır'a gidiyoruz! 🚀"


def field_text(p: Phone, resource_id: str) -> str:
    return p.find_nodes(resource_id=resource_id)[0]["text"]


def test_settings_by_turkish_name(phone: Phone) -> None:
    app = phone.open_app("ayarlar")
    assert app == "com.android.settings"
    assert phone.wait_for_app(app)
    assert phone.screen_text()


def test_turkish_text_round_trip(test_screen: Phone) -> None:
    p = test_screen
    p.tap_ui({"resource_id": "mphone_text"})
    assert p.type_text(TURKISH)["mode_used"] == "ime"
    assert field_text(p, "mphone_text") == TURKISH
    p.clear_text()
    time.sleep(0.5)
    assert field_text(p, "mphone_text") in ("", "Metin")  # an empty field reports its hint
    p.type_text("hello world")  # ASCII path: input text
    assert field_text(p, "mphone_text") == "hello world"


def test_send_button_echoes(test_screen: Phone) -> None:
    p = test_screen
    p.tap_ui({"resource_id": "mphone_text"})
    p.type_text("Şule Öztürk")
    p.tap_ui("Gönder")
    assert p.wait_for_text("Gönderildi: Şule Öztürk", timeout=5) is not None


def test_password_field_is_flagged(test_screen: Phone) -> None:
    pin = test_screen.find_nodes(resource_id="mphone_password")[0]
    assert pin["password"] is True and pin["editable"] is True


def test_scroll_collect_walks_200_rows_in_order(test_screen: Phone) -> None:
    res = test_screen.scroll_collect(
        extract=lambda boxes: [b["text"] for b in boxes if b["text"].startswith("Öğe ")],
        amount=0.4,
        settle=1.5,
    )
    assert res["stop"] == "reached-end"
    assert res["items"] == [f"Öğe {i}" for i in range(1, 201)]


def test_screenshot_matches_bounds(phone: Phone) -> None:
    from PIL import Image

    path = phone.screenshot()
    b = phone.bounds()
    with Image.open(path) as img:
        assert img.size == (b["w"], b["h"])


def test_locked_phone_refuses_and_sends_no_touch(phone: Phone) -> None:
    adb = ["adb", "shell"]
    run = lambda *a: subprocess.run([*adb, *a], capture_output=True, text=True, check=False)  # noqa: E731
    before = run("settings", "get", "secure", "lock_screen_lock_after_timeout").stdout.strip()
    run("locksettings", "set-disabled", "false")
    run("settings", "put", "secure", "lock_screen_lock_after_timeout", "0")
    run("locksettings", "set-pin", "1234")
    try:
        run("input", "keyevent", "KEYCODE_SLEEP")
        time.sleep(7)
        run("input", "keyevent", "KEYCODE_WAKEUP")
        for _ in range(10):
            if "isKeyguardShowing=true" in run("dumpsys", "window").stdout:
                break
            time.sleep(1)
        else:
            pytest.fail("the emulator never showed a keyguard; the lock test cannot run")
        phone.backend._gate_at = 0.0  # pyright: ignore[reportAttributeAccessIssue]
        assert phone.connection_state() == "locked"
        with pytest.raises(DeviceLocked):
            phone.tap(540, 1200)
        with pytest.raises(DeviceLocked):
            phone.type_text("1234")
    finally:
        run("locksettings", "clear", "--old", "1234")
        if before in ("null", ""):
            run("settings", "delete", "secure", "lock_screen_lock_after_timeout")
        else:
            run("settings", "put", "secure", "lock_screen_lock_after_timeout", before)
        run("input", "keyevent", "KEYCODE_WAKEUP")
        run("wm", "dismiss-keyguard")


def test_doctor_with_write_test() -> None:
    from mphone_cli.doctor import android_steps

    steps = android_steps("", write_test=True)
    failed = [s for s in steps if not s.ok]
    assert not failed, failed
