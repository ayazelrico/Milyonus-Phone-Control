"""Config, device URI resolution and the agent workspace (A1.05, A1.10)."""

from pathlib import Path

import pytest

from mphone_backends.fake import FakeBackend
from mphone_core import config, workspace
from mphone_core.connect import connect, resolve_uri, split
from mphone_protocol import DeviceOffline, InvalidArgument


def test_config_sources_env_beats_file_beats_default(monkeypatch: pytest.MonkeyPatch) -> None:
    assert config.lookup("ocr.engine") == ("auto", "default")
    config.set_value("ocr.engine", "rapidocr")
    value, source = config.lookup("ocr.engine")
    assert value == "rapidocr" and source.startswith("file:")
    monkeypatch.setenv("MPHONE_OCR_ENGINE", "vision")
    assert config.lookup("ocr.engine") == ("vision", "env:MPHONE_OCR_ENGINE")


def test_config_roundtrip_and_types() -> None:
    config.set_value("android.unicode_ime", "hayır")
    config.set_value("default_device", 'fake:"quoted"')
    assert config.get("android.unicode_ime") is False
    assert config.get("default_device") == 'fake:"quoted"'
    config.unset("default_device")
    assert config.get("default_device") is None
    with pytest.raises(config.ConfigError):
        config.set_value("android.unicode_ime", "maybe")
    with pytest.raises(config.ConfigError):
        config.lookup("no.such.key")


def test_split() -> None:
    assert split("fake:settings_about") == ("fake", "settings_about")
    assert split("android:R58N123") == ("android", "R58N123")
    assert split("gw://dev_1?lease=lse_1") == ("gw", "dev_1?lease=lse_1")
    with pytest.raises(InvalidArgument):
        split("nonsense")


def test_no_device_is_an_error_never_a_guess() -> None:
    with pytest.raises(DeviceOffline) as e:
        resolve_uri()
    assert e.value.user_action and "default_device" in e.value.user_action


def test_resolution_order(monkeypatch: pytest.MonkeyPatch) -> None:
    config.set_value("default_device", "fake:notes_turkish")
    assert resolve_uri()[0] == "fake:notes_turkish"
    monkeypatch.setenv("MPHONE_DEVICE", "fake:long_list_120")
    assert resolve_uri() == ("fake:long_list_120", "env:MPHONE_DEVICE")
    assert resolve_uri("fake:settings_about") == ("fake:settings_about", "argument")


def test_connect_uses_entry_points_and_rejects_unknown_schemes() -> None:
    assert isinstance(connect("fake:settings_about"), FakeBackend)
    android = connect("android:R58N123")  # P2: registered; construction touches no device
    assert type(android).__name__ == "AndroidAdb"
    with pytest.raises(InvalidArgument, match="no backend for 'ios-wda'"):
        connect("ios-wda:00008110")  # P8: until then a clear error, no fallback
    with pytest.raises(InvalidArgument, match="no fake scenario"):
        connect("fake:does_not_exist")


def test_workspace_seeds_once_and_never_overwrites(isolated_home: Path) -> None:
    target = workspace.ensure()
    assert target == isolated_home / "agent-workspace" / "agent_helpers.py"
    target.write_text("def tap(x, y):\n    return 'mine'\n\ndef extra():\n    return 1\n", encoding="utf-8")
    workspace.ensure()
    assert "mine" in target.read_text(encoding="utf-8")
    namespace = {"tap": print}
    with pytest.warns(UserWarning, match="overrides core helper 'tap'"):
        defined = workspace.load_into(namespace)
    assert set(defined) == {"tap", "extra"}
    assert namespace["extra"]() == 1  # pyright: ignore[reportCallIssue]


def test_workspace_path_override(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MPHONE_AGENT_WORKSPACE", str(tmp_path / "ws"))
    assert workspace.ensure() == tmp_path / "ws" / "agent_helpers.py"
    namespace: dict[str, object] = {}
    assert "visible_texts" in workspace.load_into(namespace)
