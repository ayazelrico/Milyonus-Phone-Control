"""E2E against a real Android (emulator in CI, A2.15). Skipped when no device is attached.

Needs the mphone IME debug APK (it carries the deterministic test screen):
    MPHONE_IME_APK=apps/android-ime/app/build/outputs/apk/debug/app-debug.apk
"""

import os
import shutil
import subprocess
import time
from collections.abc import Iterator

import pytest

from mphone_backends.android_adb.backend import AndroidAdb
from mphone_core.helpers import Phone

TEST_PKG = "com.milyonus.mphone.ime"


def _attached() -> bool:
    if not shutil.which("adb"):
        return False
    out = subprocess.run(["adb", "devices"], capture_output=True, text=True, check=False).stdout
    return any(line.endswith("\tdevice") for line in out.splitlines())


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    # This hook sees the WHOLE session's items, not just this directory's: scope it, or every
    # unit test in the run is skipped whenever no phone is attached.
    here = os.path.dirname(__file__)
    mine = [item for item in items if str(item.path).startswith(here)]
    if not mine or _attached():
        return
    skip = pytest.mark.skip(reason="no Android device attached")
    for item in mine:
        item.add_marker(skip)


@pytest.fixture(scope="session")
def ime_installed() -> None:
    apk = os.environ.get("MPHONE_IME_APK")
    if not apk:
        pytest.skip("MPHONE_IME_APK not set")
    subprocess.run(["adb", "install", "-r", "-g", apk], check=True, capture_output=True)
    for _ in range(30):  # the IME service scans new packages asynchronously (PITFALLS#android-ime-async)
        listed = subprocess.run(
            ["adb", "shell", "ime", "list", "-a", "-s"], capture_output=True, text=True
        ).stdout
        if f"{TEST_PKG}/" in listed:
            break
        time.sleep(1)
    subprocess.run(
        ["adb", "shell", "ime", "enable", f"{TEST_PKG}/.MphoneIme"], check=True, capture_output=True
    )


@pytest.fixture
def phone(ime_installed: None) -> Iterator[Phone]:
    device = AndroidAdb("")
    p = Phone(device)
    p.ensure_device()
    yield p
    device.close()


@pytest.fixture
def test_screen(phone: Phone) -> Phone:
    phone.open_app(TEST_PKG, fresh=True)
    assert phone.wait_for_text("Gönder", timeout=15) is not None
    return phone
