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


def test_typing_without_a_focused_field_is_an_error_not_silence(test_screen: Phone) -> None:
    from mphone_protocol import NotFound

    p = test_screen
    p.press("back")  # hide any keyboard; nothing is focused on a freshly opened screen
    with pytest.raises(NotFound) as e:
        p.type_text("Çağrı")
    assert e.value.user_action


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


def test_doctor_with_write_test() -> None:
    from mphone_cli.doctor import android_steps

    steps = android_steps("", write_test=True)
    failed = [s for s in steps if not s.ok]
    assert not failed, failed


def test_zz_locked_phone_refuses_and_sends_no_touch(phone: Phone) -> None:
    """Runs LAST (name + position): it changes lock settings, then must leave the phone unlocked."""
    adb = ["adb", "shell"]
    run = lambda *a: subprocess.run([*adb, *a], capture_output=True, text=True, check=False)  # noqa: E731
    before_timeout = run("settings", "get", "secure", "lock_screen_lock_after_timeout").stdout.strip()
    before_disabled = run("settings", "get", "secure", "lockscreen.disabled").stdout.strip()
    # Emulator images ship with the lock screen disabled (PITFALLS#android-emulator-lockscreen-disabled).
    run("locksettings", "set-disabled", "false")
    run("settings", "put", "secure", "lockscreen.disabled", "0")
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
            pytest.skip("this emulator never shows a keyguard; verify lock detection on a real phone")
        phone.backend._gate_at = 0.0  # pyright: ignore[reportAttributeAccessIssue]
        assert phone.connection_state() == "locked"
        with pytest.raises(DeviceLocked):
            phone.tap(540, 1200)
        with pytest.raises(DeviceLocked):
            phone.type_text("1234")
    finally:
        run("locksettings", "clear", "--old", "1234")
        for key, value in (
            ("lock_screen_lock_after_timeout", before_timeout),
            ("lockscreen.disabled", before_disabled),
        ):
            if value in ("null", ""):
                run("settings", "delete", "secure", key)
            else:
                run("settings", "put", "secure", key, value)
        for _ in range(10):  # a swipe keyguard can outlive the PIN: dismiss until it is gone
            run("input", "keyevent", "KEYCODE_WAKEUP")
            run("wm", "dismiss-keyguard")
            run("input", "keyevent", "82")
            time.sleep(1)
            if "isKeyguardShowing=false" in run("dumpsys", "window").stdout:
                break
        else:
            pytest.fail(
                "could not unlock the emulator after the lock test; later tests would see a locked phone"
            )
