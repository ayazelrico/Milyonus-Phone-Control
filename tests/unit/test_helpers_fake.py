"""Every helper against the fake phone (A1.07–A1.09, P1 exit criteria)."""

import sys
from pathlib import Path

import pytest
from PIL import Image

from mphone_backends.fake import FakeBackend
from mphone_core import helpers
from mphone_core.clock import VirtualClock
from mphone_core.helpers import Phone
from mphone_protocol import (
    ApprovalDenied,
    DeviceLocked,
    InvalidArgument,
    NeedsUser,
    NotFound,
    TreeUnavailable,
    Unsupported,
)

from ..conftest import FakePhone


def fake(p: Phone) -> FakeBackend:
    assert isinstance(p.backend, FakeBackend)
    return p.backend


def open_settings(p: Phone) -> None:
    assert p.open_app("Ayarlar") == "com.android.settings"
    assert p.wait_for_app("com.android.settings")


# --- reading the screen -------------------------------------------------------


def test_screen_boxes_are_tap_ready_and_sourced(fake_phone: FakePhone) -> None:
    p = fake_phone("settings_about")
    open_settings(p)
    boxes = p.screen()
    title = next(b for b in boxes if b["text"] == "Ayarlar")
    assert title["source"] == "tree"
    assert (title["x"], title["y"]) == (540, 220)
    assert boxes == sorted(boxes, key=lambda b: (b["y"], b["x"]))


def test_rows_report_their_clickable_ancestor(fake_phone: FakePhone) -> None:
    p = fake_phone("settings_about")
    open_settings(p)
    row = next(b for b in p.screen() if b["text"] == "Pil")
    assert row["clickable"] is False
    assert row["clickable_ancestor"] == {"x": row["x"], "y": row["y"]}


def test_find_text_is_turkish_aware_and_ranked(fake_phone: FakePhone) -> None:
    p = fake_phone("settings_about")
    open_settings(p)
    assert [b["text"] for b in p.find_text("AĞ VE İNTERNET")] == ["Ağ ve internet"]
    assert p.find_text("bagli cihazlar")[0]["text"] == "Bağlı cihazlar"
    assert p.find_text("Ayarlar", exact=True)[0]["text"] == "Ayarlar"


def test_tree_unavailable_screen_falls_back_to_pixels(fake_phone: FakePhone) -> None:
    p = fake_phone("settings_about")
    p.open_app("chrome")
    boxes = p.screen()
    assert boxes and {b["source"] for b in boxes} == {"pixels"}
    with pytest.raises(TreeUnavailable):
        p.ui()


def test_screenshot_writes_a_png_and_prints_its_path(
    fake_phone: FakePhone, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    p = fake_phone("settings_about")
    out = p.screenshot(str(tmp_path / "s.png"), max_side=1200)
    assert capsys.readouterr().out.strip() == out
    with Image.open(out) as img:
        assert img.size == (540, 1200)


def test_tap_image_point_scales_a_resized_screenshot(fake_phone: FakePhone) -> None:
    p = fake_phone("settings_about")
    assert p.tap_image_point(100, 280, image_size=(540, 1200)) == (200, 560)
    assert p.current_app() == "com.android.settings"  # that point is the settings icon


# --- acting -------------------------------------------------------------------


def test_tap_text_not_found_lists_what_is_visible(fake_phone: FakePhone) -> None:
    p = fake_phone("settings_about")
    open_settings(p)
    with pytest.raises(NotFound) as e:
        p.tap_text("Bluetooth")
    assert "Ağ ve internet" in e.value.details["visible"]
    assert "Ağ ve internet" in str(e.value)


def test_tap_on_empty_space_changes_nothing(fake_phone: FakePhone) -> None:
    p = fake_phone("settings_about")
    open_settings(p)
    before = p.screen_text()
    p.tap(1070, 2390)
    assert p.screen_text()[1:] == before[1:]  # [0] is the ticking clock


def test_turkish_typing_into_a_focused_field(fake_phone: FakePhone) -> None:
    p = fake_phone("notes_turkish")
    p.open_app("notlar")
    p.tap_text("Yeni not")
    p.tap_ui({"resource_id": "title"})
    text = "Çağrı ışığı söndü; İğdır'a gidiyoruz! 🚀"
    assert p.type_text(text)["mode_used"] == "ime"
    assert fake(p).value("note_title") == text
    assert p.wait_for_text("Çağrı ışığı söndü") is not None


def test_password_fields_are_masked_on_screen(fake_phone: FakePhone) -> None:
    p = fake_phone("whatsapp_like")
    p.open_app("WhatsApp")
    p.tap_ui("Ayarlar")
    field = p.find_nodes(query="PIN")[0]
    assert field["password"] is True
    p.tap(field["x"], field["y"])
    p.type_text("123456")
    assert "123456" not in " ".join(p.screen_text())
    assert p.find_text("••••••")


def test_typing_without_focus_goes_nowhere(fake_phone: FakePhone) -> None:
    p = fake_phone("notes_turkish")
    p.open_app("Notes")
    p.tap_text("Yeni not")
    p.type_text("kaybolacak")
    assert fake(p).lost_text == ["kaybolacak"]
    assert p.find_text("kaybolacak") == []


def test_clear_and_keys(fake_phone: FakePhone) -> None:
    p = fake_phone("notes_turkish")
    p.open_app("Notlar")
    p.tap_text("Yeni not")
    p.press("tab")
    p.type_text("abc")
    p.press("del")
    assert fake(p).value("note_title") == "ab"
    p.clear_text()
    assert fake(p).value("note_title") == ""
    p.press("enter")
    assert p.find_text("Henüz not yok")
    with pytest.raises(InvalidArgument):
        p.press("hyperjump")


def test_tap_ui_by_content_desc_hits_icon(fake_phone: FakePhone) -> None:
    p = fake_phone("whatsapp_like")
    p.tap_ui("WhatsApp Business")
    assert p.current_app() == "com.whatsapp.w4b"
    p.tap_ui({"resource_id": "menuitem_search"})
    assert p.find_nodes(resource_id="com.whatsapp.w4b:id/search_input")


def test_navigation_and_apps(fake_phone: FakePhone) -> None:
    p = fake_phone("settings_about")
    open_settings(p)
    p.home()
    assert p.current_app() == "com.fake.launcher"
    open_settings(p)
    p.back()
    assert p.current_app() == "com.fake.launcher"
    assert [a["app_id"] for a in p.list_apps()] == ["com.android.chrome"]
    assert len(p.list_apps(include_system=True)) == 3
    with pytest.raises(NotFound) as e:
        p.open_app("Instagram")
    assert "Ayarlar" in e.value.details["installed"]
    open_settings(p)
    p.stop_app("com.android.settings")
    assert p.current_app() == "com.fake.launcher"


# --- scrolling ----------------------------------------------------------------


def test_scroll_collect_gathers_all_120_without_duplicates(fake_phone: FakePhone) -> None:
    p = fake_phone("long_list_120")
    progress: list[tuple[int, int, int]] = []
    res = p.scroll_collect(
        extract=lambda boxes: [b["text"] for b in boxes if b["text"].startswith("Öğe")],
        on_progress=lambda i, total, new: progress.append((i, total, new)),
    )
    assert res["stop"] == "reached-end"
    assert res["items"] == [f"Öğe {i}" for i in range(1, 121)]
    assert progress[-1][1] == 120


def test_scroll_collect_recovers_rows_skipped_by_a_fling(fake_phone: FakePhone) -> None:
    p = fake_phone("long_list_120")
    p.open_app("Fırlayan")
    res = p.scroll_collect(extract=lambda boxes: [b["text"] for b in boxes if b["text"].startswith("Satır")])
    assert res["stop"] == "reached-end"
    assert res["items"] == [f"Satır {i}" for i in range(1, 121)]  # complete and in order


def test_scroll_collect_respects_max_scrolls(fake_phone: FakePhone) -> None:
    res = fake_phone("long_list_120").scroll_collect(max_scrolls=3)
    assert res["stop"] == "max-scrolls"
    assert res["scrolls"] == 3


def test_ticking_clock_does_not_count_as_movement(fake_phone: FakePhone) -> None:
    p = fake_phone("long_list_120")
    p.scroll_collect()  # reach the end
    res = p.scroll_screen()
    assert res["moved"] is False  # the status-bar clock changed, the content did not


def test_scroll_until_finds_and_stops(fake_phone: FakePhone) -> None:
    p = fake_phone("settings_about")
    open_settings(p)
    hit = p.scroll_until(lambda boxes: next((b for b in boxes if b["text"] == "Telefon hakkında"), None))
    assert hit is not None
    p.tap(hit["x"], hit["y"])
    assert p.wait_for_text("Android sürümü") is not None
    assert p.scroll_until(lambda boxes: None, max_scrolls=10) is None


def test_scroll_moves_exactly_swipe_flicks_further(fake_phone: FakePhone) -> None:
    a, b = fake_phone("long_list_120"), fake_phone("long_list_120")
    a.scroll("down", amount=0.25)
    b.swipe("up", distance=0.25)
    assert fake(a).offsets["list"] == 600
    assert fake(b).offsets["list"] > 600


def test_invalid_direction(fake_phone: FakePhone) -> None:
    with pytest.raises(InvalidArgument):
        fake_phone("long_list_120").scroll("sideways")  # pyright: ignore[reportArgumentType]


# --- waiting ------------------------------------------------------------------


def test_waits_time_out_on_the_virtual_clock(fake_phone: FakePhone) -> None:
    p = fake_phone("settings_about")
    assert p.wait_for_text("Yok böyle bir şey", timeout=3) is None
    assert not p.wait_for_app("com.whatsapp", timeout=2)
    assert isinstance(p.clock, VirtualClock) and p.clock.slept >= 5
    assert p.wait_stable() is False  # the status-bar clock ticks on every read
    q = fake_phone("notes_turkish")
    assert q.wait_stable() is True


# --- device state and safety ---------------------------------------------------


def test_locked_phone_refuses_all_input_and_sends_no_touch(fake_phone: FakePhone) -> None:
    p = fake_phone("locked_phone")
    assert p.connection_state() == "locked"
    with pytest.raises(DeviceLocked) as e:
        p.ensure_device()
    assert e.value.user_action and "PIN" in e.value.user_action
    for action in (
        lambda: p.tap(200, 560),
        lambda: p.type_text("1234"),
        p.home,
        lambda: p.open_app("Ayarlar"),
    ):
        with pytest.raises(DeviceLocked):
            action()
    assert p.current_app() == "com.fake.launcher"
    assert p.screenshot()  # looking is still allowed
    fake(p).unlock()
    assert p.ensure_device()["w"] == 1080


def test_request_human_and_approval(fake_phone: FakePhone) -> None:
    p = fake_phone("settings_about")
    with pytest.raises(NeedsUser):
        p.request_human("2FA kodunu girin")
    with pytest.raises(ApprovalDenied):
        p.request_approval("Mesaj gönderilsin mi?")
    p.human = lambda kind, text, timeout: True
    p.request_human("2FA kodunu girin")
    p.request_approval("Mesaj gönderilsin mi?")


def test_tty_handler_without_terminal_raises_needs_user(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys.stdin, "isatty", lambda: False)
    p = Phone(FakeBackend({"screens": {"s": {}}}), clock=VirtualClock())
    with pytest.raises(NeedsUser) as e:
        p.request_human("PIN girin")
    assert e.value.user_action == "PIN girin"


def test_misc_ops(fake_phone: FakePhone, capsys: pytest.CaptureFixture[str]) -> None:
    p = fake_phone("whatsapp_like")
    p.set_clipboard("merhaba")
    assert p.clipboard() == "merhaba"
    assert p.notifications()[0]["title"] == "Ayşe Yılmaz"
    assert p.device_info()["locale"] == "tr-TR"
    p.note("Sohbet bulundu")
    assert "Sohbet bulundu" in capsys.readouterr().err
    assert "nav.back" in p.ops()


# --- module-level default phone -------------------------------------------------


def test_module_functions_drive_the_default_phone(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MPHONE_DEVICE", "fake:settings_about")
    assert helpers.open_app("Ayarlar") == "com.android.settings"
    assert helpers.current_app() == "com.android.settings"
    other = helpers.connect("fake:notes_turkish")
    assert other.backend is not helpers.phone().backend
    helpers.use(other)
    assert helpers.open_app("Notlar") == "com.fake.notes"


def test_unsupported_is_honest() -> None:
    class NoBack(FakeBackend):
        _nav_back = None  # pyright: ignore[reportAssignmentType]

    p = Phone(NoBack({"screens": {"s": {}}}), clock=VirtualClock())
    assert not p.supports("nav.back")
    with pytest.raises(Unsupported):
        p.back()
