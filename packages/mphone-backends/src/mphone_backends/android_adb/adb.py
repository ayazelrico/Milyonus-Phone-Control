"""Running adb: finding the binary, pinning the serial, and turning failures into protocol errors
(A2.01, Plan.md §8.2.1).

Every device-side command carries `-s SERIAL`: over Wi-Fi adb can list one phone twice (ip:port
and its mDNS name), and an unpinned command then fails with "more than one device"
(PITFALLS#android-duplicate-wifi-device).
"""

import os
import shutil
import subprocess
from pathlib import Path

from mphone_core import config
from mphone_protocol import (
    DeviceOffline,
    DeviceUnauthorized,
    InternalError,
    MphoneError,
    NeedsUser,
    Timeout,
)

INSTALL_HINT = (
    "adb kurun: macOS `brew install android-platform-tools`, Debian/Ubuntu `sudo apt install adb`, "
    "Windows `winget install Google.PlatformTools`; ya da `mphone config set android.adb_path YOL`."
)
UNAUTHORIZED_HINT = (
    "Telefonun kilidini açıp 'USB hata ayıklamaya izin verilsin mi?' sorusunda 'Bu bilgisayardan her zaman "
    "izin ver'i işaretleyin ve İzin ver'e dokunun. Soru çıkmazsa kabloyu çıkarıp takın."
)


def candidates() -> list[Path]:
    home = Path.home()
    sdk_roots = [os.environ.get(v) for v in ("ANDROID_HOME", "ANDROID_SDK_ROOT")]
    paths = [Path(r) / "platform-tools" / "adb" for r in sdk_roots if r]
    paths += [
        Path("/opt/homebrew/bin/adb"),
        Path("/usr/local/bin/adb"),
        home / "Library/Android/sdk/platform-tools/adb",
        home / "Android/Sdk/platform-tools/adb",
    ]
    local = os.environ.get("LOCALAPPDATA")
    if local:
        paths.append(Path(local) / "Android/Sdk/platform-tools/adb.exe")
    return paths


def find_adb() -> str:
    configured = config.get("android.adb_path")
    if configured:
        if Path(configured).is_file():
            return str(configured)
        raise NeedsUser(
            f"android.adb_path points to {configured}, which does not exist", user_action=INSTALL_HINT
        )
    found = shutil.which("adb")
    if found:
        return found
    for path in candidates():
        if path.is_file():
            return str(path)
    raise NeedsUser("adb is not installed", user_action=INSTALL_HINT)


def classify(message: str, serial: str | None) -> MphoneError | None:
    """Map adb's own failure text to a protocol error, or None when it is not an adb-level failure."""
    text = message.lower()
    who = f"telefon {serial}" if serial else "telefon"
    if "unauthorized" in text:
        return DeviceUnauthorized(f"{who} has not authorised this computer", user_action=UNAUTHORIZED_HINT)
    if "device offline" in text or "error: offline" in text:
        return DeviceOffline(
            f"{who} is offline", user_action="Kabloyu çıkarıp takın veya `adb reconnect` deneyin."
        )
    if "not found" in text and ("device" in text or "emulator" in text):
        return DeviceOffline(
            f"{who} is not connected",
            user_action="Telefonu bağlayın ve USB hata ayıklamanın açık olduğunu kontrol edin.",
        )
    if "no devices/emulators found" in text:
        return DeviceOffline(
            "no phone is connected",
            user_action="Telefonu USB ile bağlayın veya `mphone android pair KOD` ile Wi-Fi'dan eşleyin.",
        )
    if "more than one device" in text:
        return InternalError(
            "adb saw several devices for an unpinned command; this is an mphone bug (serial not pinned)"
        )
    if "cannot connect to daemon" in text or ("daemon not running" in text and "failed" in text):
        return DeviceOffline(
            "the adb server could not start", user_action="`adb kill-server` ve tekrar deneyin."
        )
    return None


class Adb:
    """One adb binary, optionally pinned to one device."""

    def __init__(self, serial: str | None = None, binary: str | None = None) -> None:
        self.serial = serial
        self._binary = binary

    @property
    def binary(self) -> str:
        if self._binary is None:
            self._binary = find_adb()
        return self._binary

    def argv(self, *args: str, pin: bool = True) -> list[str]:
        prefix = [self.binary]
        if pin and self.serial:
            prefix += ["-s", self.serial]
        return [*prefix, *args]

    def run_bytes(self, *args: str, timeout: float = 60, check: bool = True, pin: bool = True) -> bytes:
        argv = self.argv(*args, pin=pin)
        try:
            proc = subprocess.run(argv, capture_output=True, timeout=timeout, check=False)
        except subprocess.TimeoutExpired:
            raise Timeout(f"adb {' '.join(args[:3])} took longer than {timeout:g}s") from None
        except FileNotFoundError:
            raise NeedsUser("adb is not installed", user_action=INSTALL_HINT) from None
        if proc.returncode != 0 or not proc.stdout:
            err = proc.stderr.decode("utf-8", "replace") + proc.stdout[:2000].decode("utf-8", "replace")
            mapped = classify(err, self.serial)
            if mapped is not None:
                raise mapped
            if check and proc.returncode != 0:
                raise InternalError(
                    f"adb {' '.join(args[:4])} exited {proc.returncode}: {err.strip()[:500]}",
                    details={"argv": argv[1:], "code": proc.returncode},
                )
        return proc.stdout

    def run(self, *args: str, timeout: float = 60, check: bool = True, pin: bool = True) -> str:
        return self.run_bytes(*args, timeout=timeout, check=check, pin=pin).decode("utf-8", "replace")

    def shell(self, cmd: str, timeout: float = 60, check: bool = True) -> str:
        """Run one command string through the device shell. Quote user data with shlex.quote."""
        return self.run("shell", cmd, timeout=timeout, check=check).replace("\r\n", "\n")

    def shell_bytes(self, cmd: str, timeout: float = 60) -> bytes:
        return self.run_bytes("exec-out", cmd, timeout=timeout)
