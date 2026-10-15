"""Parsers against REAL emulator output (tests/fixtures/android, A2.02–A2.12)."""

from pathlib import Path

import pytest

from mphone_backends.android_adb import parse
from mphone_backends.android_adb.adb import classify
from mphone_core.tree import nodes_to_boxes, select
from mphone_protocol import DeviceOffline

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "android"
APIS = ["emulator_api30", "emulator_api34"]


def read(api: str, name: str, ext: str = "out") -> str:
    return (FIXTURES / api / f"{name}.{ext}").read_text(encoding="utf-8")


@pytest.mark.parametrize("api", APIS)
def test_devices(api: str) -> None:
    rows = parse.parse_devices(read(api, "devices_l"))
    assert len(rows) == 1
    assert rows[0].serial == "emulator-5554" and rows[0].state == "device" and rows[0].transport == "emulator"
    assert rows[0].model and rows[0].model.startswith("sdk_gphone")


def test_devices_states_and_transports() -> None:
    out = (
        "List of devices attached\n"
        "R58N123ABC             unauthorized usb:1-1 transport_id:3\n"
        "192.168.1.20:41235     device product:a54 model:SM_A546E device:a54 transport_id:4\n"
        "adb-R58N-xyz._adb-tls-connect._tcp device product:a54 model:SM_A546E transport_id:5\n"
        "* daemon started successfully\n"
    )
    rows = parse.parse_devices(out)
    assert [(r.state, r.transport) for r in rows] == [
        ("unauthorized", "usb"),
        ("device", "wifi"),
        ("device", "wifi"),
    ]


def test_mdns() -> None:
    services = parse.parse_mdns(read("emulator_api30", "mdns_services"))
    assert services and services[0].kind == "_adb._tcp" and ":" in services[0].addr
    # Discovery depends on the network: the API 34 run saw nothing, which must parse to [].
    assert parse.parse_mdns(read("emulator_api34", "mdns_services")) == []


@pytest.mark.parametrize("api", APIS)
def test_wakefulness(api: str) -> None:
    assert parse.parse_wakefulness(read(api, "power_awake")) == "Awake"
    off = parse.parse_wakefulness(read(api, "power_asleep"))
    # A screen turned off with KEYCODE_SLEEP reads "Asleep" or, on Android 14, sometimes "Dozing"
    # (both seen on the same API 34 image in different runs). Only "Awake" is awake.
    assert off in ("Asleep", "Dozing")
    assert not parse.is_awake(off)
    assert not parse.is_awake("Dozing") and not parse.is_awake("Dreaming") and not parse.is_awake(None)


@pytest.mark.parametrize("api", APIS)
def test_keyguard_unlocked(api: str) -> None:
    assert parse.parse_keyguard_showing(read(api, "window_unlocked")) is False


def test_keyguard_locked_variants() -> None:
    assert parse.parse_keyguard_showing("    isKeyguardShowing=true") is True
    assert parse.parse_keyguard_showing("", "    KeyguardServiceDelegate\n      showing=true\n") is True
    assert parse.parse_keyguard_showing("nothing here") is None


@pytest.mark.parametrize("api", APIS)
def test_geometry(api: str) -> None:
    assert parse.parse_wm_size(read(api, "wm_size")) == (1080, 2400)
    assert parse.parse_wm_density(read(api, "wm_density")) == 420
    assert parse.parse_rotation(read(api, "display_rotation")) == 0


def test_wm_size_override_wins() -> None:
    assert parse.parse_wm_size("Physical size: 1080x2400\nOverride size: 720x1600\n") == (720, 1600)


@pytest.mark.parametrize("api", APIS)
def test_resumed_package(api: str) -> None:
    assert parse.parse_resumed_package(read(api, "activity_home")) == "com.google.android.apps.nexuslauncher"
    assert parse.parse_resumed_package(read(api, "activity_settings")) == "com.android.settings"


@pytest.mark.parametrize("api", APIS)
def test_packages_and_components(api: str) -> None:
    assert parse.parse_packages(read(api, "pm_list_3")) == []  # a fresh emulator has no third-party apps
    everything = parse.parse_packages(read(api, "pm_list_all"))
    assert "com.android.settings" in everything and len(everything) > 50
    assert all("/" not in p and "=" not in p for p in everything)
    assert parse.parse_packages("package:/data/app/~~x==/com.whatsapp-1/base.apk=com.whatsapp\n") == [
        "com.whatsapp"
    ]
    assert parse.parse_resolved_component(read(api, "resolve_settings")) == "com.android.settings/.Settings"
    assert "com.android.settings/.Settings" in parse.parse_launchable(read(api, "query_launchers"))


@pytest.mark.parametrize("api", APIS)
def test_battery_and_notifications(api: str) -> None:
    assert parse.parse_battery(read(api, "dumpsys_battery")) == (100, True)
    notes = parse.parse_notifications(read(api, "notifications_noredact"))
    assert notes and all(n["app_id"] for n in notes)


def test_serial_console_notification_api30() -> None:
    notes = parse.parse_notifications(read("emulator_api30", "notifications_noredact"))
    console = next(n for n in notes if n["title"] == "Serial console enabled")
    assert console["app_id"] == "android"
    assert console["text"] == "Performance is impacted. To disable, check bootloader."


@pytest.mark.parametrize("api", APIS)
def test_dev_tty_dump_has_no_xml(api: str) -> None:
    """PITFALLS#android-uiautomator-dev-tty: the popular recipe returns only a status line."""
    out = read(api, "uia_home_tty")
    assert "<hierarchy" not in out
    with pytest.raises(parse.TreeParseError):
        parse.parse_uiautomator(out)


@pytest.mark.parametrize("api", APIS)
def test_uiautomator_home(api: str) -> None:
    nodes, rotation = parse.parse_uiautomator(read(api, "uia_home"))
    assert rotation == 0 and len(nodes) > 10
    assert nodes[0]["parent_id"] is None and all(n["parent_id"] for n in nodes[1:])
    boxes = nodes_to_boxes(nodes)
    assert boxes and all(b["source"] == "tree" for b in boxes)


@pytest.mark.parametrize("api", APIS)
def test_uiautomator_test_screen(api: str) -> None:
    nodes, _ = parse.parse_uiautomator(read(api, "uia_testfields"))
    text = select(nodes, {"resource_id": "mphone_text"})
    pin = select(nodes, {"resource_id": "mphone_password"})
    send = select(nodes, {"text": "Gönder"})
    assert len(text) == 1 and text[0]["editable"] is True
    assert pin[0]["password"] is True and pin[0]["editable"] is True
    assert send and send[0]["clickable"] is True
    rows = [b["text"] for b in nodes_to_boxes(nodes) if b["text"].startswith("Öğe")]
    assert rows[:3] == ["Öğe 1", "Öğe 2", "Öğe 3"]
    # PITFALLS#android-hint-as-text: an empty EditText reports its hint as text.
    assert text[0]["text"] == "Metin"


@pytest.mark.parametrize("api", APIS)
def test_motionevent_is_available(api: str) -> None:
    assert "motionevent" in read(api, "input_help")


@pytest.mark.parametrize("api", APIS)
def test_input_text_cannot_type_turkish(api: str) -> None:
    """PITFALLS#android-ascii-only-text, now with evidence: NullPointerException, non-zero exit."""
    out = read(api, "input_text_turkish") + read(api, "input_text_turkish", "err")
    assert "NullPointerException" in out
    assert read(api, "input_text_turkish", "code").strip() != "0"


@pytest.mark.parametrize("api", APIS)
def test_adb_error_texts(api: str) -> None:
    bad = (FIXTURES / api / "error_bad_serial.err").read_text("utf-8")
    assert isinstance(classify(bad, "does-not-exist"), DeviceOffline)
    unknown = (FIXTURES / api / "error_unknown_command.err").read_text("utf-8")
    assert classify(unknown, None) is None  # a failing device command is not an adb failure
