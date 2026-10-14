"""Every module-level helper reaches the default phone (what `mphone run` scripts call)."""

from pathlib import Path

import pytest

from mphone_core import helpers as h
from mphone_core.clock import VirtualClock
from mphone_core.helpers import Phone
from mphone_protocol import ApprovalDenied, NeedsUser


@pytest.fixture
def default_phone() -> Phone:
    from mphone_backends.fake import from_uri

    return h.use(Phone(from_uri("whatsapp_like"), clock=VirtualClock(), human=lambda k, t, s: False))


def test_star_import_exposes_only_helpers() -> None:
    namespace: dict[str, object] = {}
    exec("from mphone_core.helpers import *", namespace)  # noqa: S102
    exported = {k for k in namespace if k != "__builtins__"}
    assert exported == set(h.__all__)
    assert "base64" not in exported and "tap" in exported


def test_every_module_helper(default_phone: Phone, tmp_path: Path) -> None:
    assert h.phone() is default_phone
    assert h.ensure_device()["w"] == 1080
    assert h.connection_state() == "ready"
    assert h.connection_detail()
    assert h.device_info()["platform"] == "fake"
    assert h.bounds()["h"] == 2400
    assert h.supports("nav.back") and "tree" in h.ops()
    assert h.open_app("WhatsApp", fresh=True) == "com.whatsapp.w4b"
    assert h.wait_for_app("com.whatsapp.w4b") and h.current_app() == "com.whatsapp.w4b"
    assert any(a["app_id"] == "com.whatsapp.w4b" for a in h.list_apps())
    assert h.screen() and "Ayşe Yılmaz" in h.screen_text()
    assert h.find_text("ayse yilmaz")
    assert h.wait_for_text("Mehmet") is not None
    assert h.wait_stable(timeout=3) is True
    assert h.screenshot(str(tmp_path / "x.png")).endswith("x.png")
    assert h.ui() and h.find_nodes("Zeynep")
    h.scroll("down", 0.1)
    h.swipe("left")
    h.drag(10, 10, 20, 20)
    h.long_press(540, 500)
    assert h.scroll_screen()["boxes"] is not None
    assert h.scroll_until(lambda boxes: True) is True
    assert h.scroll_collect(max_scrolls=1)["scrolls"] == 1
    h.tap_text("Ayşe Yılmaz")
    h.tap_ui({"resource_id": "entry"})
    assert h.type_text("Selam")["mode_used"] == "keystrokes"
    h.clear_text()
    h.press("back")
    h.tap(10, 10)
    assert h.tap_image_point(10, 10, (1080, 2400)) == (10, 10)
    h.recents()
    h.notifications_panel()
    h.back()
    h.home()
    h.stop_app("com.whatsapp.w4b")
    h.set_clipboard("pano")
    assert h.clipboard() == "pano"
    assert h.notifications(limit=1)
    assert h.send("device.state") == "ready"
    h.note("not")
    with pytest.raises(NeedsUser):
        h.request_human("PIN")
    with pytest.raises(ApprovalDenied):
        h.request_approval("Gönder?")
