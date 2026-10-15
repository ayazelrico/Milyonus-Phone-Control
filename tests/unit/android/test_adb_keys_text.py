"""adb runner, keycodes and text paths (A2.01, A2.07, A2.08) — no device needed."""

import base64
import shlex
import shutil
import subprocess
from pathlib import Path

import pytest

from mphone_backends.android_adb import adb as adbmod
from mphone_backends.android_adb.adb import Adb, classify, find_adb
from mphone_backends.android_adb.keys import keycode
from mphone_backends.android_adb.text import (
    ADB_KEYBOARD,
    MPHONE_IME,
    ascii_safe,
    broadcast_command,
    input_text_command,
)
from mphone_core import config
from mphone_protocol import (
    DeviceOffline,
    DeviceUnauthorized,
    InternalError,
    InvalidArgument,
    NeedsUser,
    Timeout,
    Unsupported,
)


@pytest.mark.parametrize(
    ("message", "expected"),
    [
        ("error: device unauthorized.\nThis adb server's $ADB_VENDOR_KEYS is not set", DeviceUnauthorized),
        ("adb: device unauthorized", DeviceUnauthorized),
        ("error: device offline", DeviceOffline),
        ("adb: device 'does-not-exist' not found", DeviceOffline),
        ("error: device 'R58N' not found", DeviceOffline),
        ("adb: no devices/emulators found", DeviceOffline),
        ("error: more than one device/emulator", InternalError),
        ("/system/bin/sh: this-command-does-not-exist: inaccessible or not found", None),
        ("Error: Unknown option", None),
    ],
)
def test_classify(message: str, expected: type | None) -> None:
    got = classify(message, "R58N")
    assert (type(got) if got else None) is expected


def test_unauthorized_tells_the_user_what_to_tap() -> None:
    err = classify("error: device unauthorized.", None)
    assert err is not None and err.user_action and "İzin ver" in err.user_action


def test_find_adb_prefers_config_then_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fake = tmp_path / "adb"
    fake.write_text("#!/bin/sh\n", encoding="utf-8")
    config.set_value("android.adb_path", str(fake))
    assert find_adb() == str(fake)
    config.set_value("android.adb_path", str(tmp_path / "missing"))
    with pytest.raises(NeedsUser):
        find_adb()
    config.unset("android.adb_path")
    monkeypatch.setattr(shutil, "which", lambda name: None)
    monkeypatch.setattr(adbmod, "candidates", lambda: [tmp_path / "nope"])
    with pytest.raises(NeedsUser) as e:
        find_adb()
    assert e.value.user_action and "brew install android-platform-tools" in e.value.user_action


def test_every_command_is_pinned() -> None:
    a = Adb("emulator-5554", binary="/x/adb")
    assert a.argv("shell", "true") == ["/x/adb", "-s", "emulator-5554", "shell", "true"]
    assert a.argv("devices", "-l", pin=False) == ["/x/adb", "devices", "-l"]


def test_run_maps_failures(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(argv: list[str], **kw: object) -> subprocess.CompletedProcess[bytes]:
        if "boom" in argv:
            return subprocess.CompletedProcess(argv, 1, b"", b"error: device unauthorized.")
        if "slow" in argv:
            raise subprocess.TimeoutExpired(argv, 1)
        if "fail" in argv:
            return subprocess.CompletedProcess(argv, 3, b"", b"weird failure")
        return subprocess.CompletedProcess(argv, 0, b"ok\r\n", b"")

    monkeypatch.setattr(subprocess, "run", fake_run)
    a = Adb("S1", binary="/x/adb")
    assert a.shell("echo") == "ok\n"
    with pytest.raises(DeviceUnauthorized):
        a.run("boom")
    with pytest.raises(Timeout):
        a.run("slow", timeout=1)
    with pytest.raises(InternalError, match="exited 3"):
        a.run("fail")
    assert a.run("fail", check=False) == ""


@pytest.mark.parametrize(
    ("combo", "code"),
    [
        ("enter", "KEYCODE_ENTER"),
        ("Back", "KEYCODE_BACK"),
        ("tab", "KEYCODE_TAB"),
        ("del", "KEYCODE_DEL"),
        ("a", "KEYCODE_A"),
        ("7", "KEYCODE_7"),
        ("KEYCODE_MEDIA_PLAY", "KEYCODE_MEDIA_PLAY"),
    ],
)
def test_keycodes(combo: str, code: str) -> None:
    assert keycode(combo) == code


def test_chords_are_unsupported_not_faked() -> None:
    with pytest.raises(Unsupported):
        keycode("cmd+space")
    with pytest.raises(InvalidArgument):
        keycode("hyperjump")
    assert keycode("+") == "KEYCODE_PLUS"  # a lone "+" is a key, not a chord


@pytest.mark.parametrize(
    ("text", "safe"),
    [
        ("hello world", True),
        ("a&b;c'd", True),
        ("Çağrı", False),
        ("emoji 🚀", False),
        ("line\nbreak", False),
        ("100%s", False),
        ("", False),
        ("İ", False),
    ],
)
def test_ascii_safe(text: str, safe: bool) -> None:
    assert ascii_safe(text) is safe


def test_input_text_command_survives_the_device_shell() -> None:
    cmd = input_text_command("a&b c'd")
    assert shlex.split(cmd) == ["input", "text", "a&b%sc'd"]


def test_broadcast_carries_utf8_base64() -> None:
    text = "Çağrı ışığı söndü; İğdır'a gidiyoruz! 🚀"
    for ime in (MPHONE_IME, ADB_KEYBOARD):
        parts = broadcast_command(ime, text).split()
        assert parts[:3] == ["am", "broadcast", "-a"] and parts[3] == ime.input_action
        assert base64.b64decode(parts[-1]).decode("utf-8") == text
