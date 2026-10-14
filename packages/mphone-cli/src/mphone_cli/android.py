"""`mphone android …`: list, pair, choose and prepare Android phones (A2.09, A2.14)."""

import hashlib
import sys
import tempfile
import time
import urllib.request
from pathlib import Path
from typing import Any

from mphone_backends.android_adb import parse
from mphone_backends.android_adb.adb import Adb
from mphone_backends.android_adb.backend import AndroidAdb
from mphone_backends.android_adb.text import MPHONE_IME
from mphone_core import config

RELEASE_APK = "https://github.com/ayazelrico/Milyonus-Phone-Control/releases/latest/download/mphone-ime.apk"


def devices(args: Any) -> int:
    adb = Adb()
    rows = parse.parse_devices(adb.run("devices", "-l", pin=False))
    primary = config.get("android.primary")
    if not rows:
        print("Bağlı telefon yok. USB hata ayıklamayı açıp bağlayın ya da `mphone android pair KOD`.")
        return 1
    for r in rows:
        star = " (birincil)" if r.serial == primary else ""
        print(f"{r.serial:28} {r.state:13} {r.transport:9} {r.model or ''}{star}")
    return 0


def pair(args: Any) -> int:
    """Wireless debugging (Android 11+): find the phone's pairing service and pair with the code."""
    adb = Adb()
    target = args.host
    if not target:
        services = [
            s
            for s in parse.parse_mdns(adb.run("mdns", "services", pin=False, check=False))
            if s.kind == "_adb-tls-pairing._tcp"
        ]
        if not services:
            print(
                "Eşleştirme servisi bulunamadı. Telefonda: Kablosuz hata ayıklama → Eşleme koduyla cihaz eşle; "
                "aynı Wi-Fi ağında olun ya da --host IP:PORT verin.",
                file=sys.stderr,
            )
            return 1
        target = services[0].addr
    out = adb.run("pair", target, args.code, pin=False, check=False, timeout=30)
    print(out.strip())
    if "Successfully paired" not in out:
        return 1
    time.sleep(2)
    for s in parse.parse_mdns(adb.run("mdns", "services", pin=False, check=False)):
        if s.kind == "_adb-tls-connect._tcp":
            print(adb.run("connect", s.addr, pin=False, check=False).strip())
    return 0


def use(args: Any) -> int:
    """Make one phone the primary. A primary that is unreachable is an error, never replaced."""
    if args.serial in ("-", "none"):
        config.unset("android.primary")
        print("Birincil telefon kaldırıldı; USB > emülatör > Wi-Fi sırasıyla seçilecek.")
        return 0
    device = AndroidAdb(args.serial)
    device.resolve()
    config.set_value("android.primary", args.serial)
    print(f"Birincil telefon: {args.serial}")
    return 0


def _download(url: str) -> Path:
    target = Path(tempfile.mkdtemp(prefix="mphone-ime-")) / "mphone-ime.apk"
    with urllib.request.urlopen(url, timeout=60) as r:  # noqa: S310 — fixed https URL
        target.write_bytes(r.read())
    with urllib.request.urlopen(url + ".sha256", timeout=60) as r:  # noqa: S310
        expected = r.read().decode().split()[0]
    actual = hashlib.sha256(target.read_bytes()).hexdigest()
    if actual != expected:
        target.unlink()
        raise RuntimeError(f"mphone-ime.apk checksum mismatch: {actual} != {expected}")
    return target


def ime(args: Any) -> int:
    device = AndroidAdb(args.device or "")
    serial = device.resolve()
    if args.action == "status":
        listed = device.send("raw", cmd="ime list -a -s")
        current = device.send("raw", cmd="settings get secure default_input_method").strip()
        print(
            f"{serial}: mphone klavyesi {'yüklü' if MPHONE_IME.ime_id in listed else 'YÜKLÜ DEĞİL'}; etkin klavye: {current}"
        )
        return 0 if MPHONE_IME.ime_id in listed else 1
    if args.action == "uninstall":
        device.send("apps.uninstall", app_id="com.milyonus.mphone.ime")
        print("mphone klavyesi kaldırıldı.")
        return 0
    apk = Path(args.apk) if args.apk else _download(RELEASE_APK)
    device.adb.run("install", "-r", "-g", str(apk), timeout=300)
    device.send("raw", cmd=f"ime enable {MPHONE_IME.ime_id}")
    print(
        f"{serial}: mphone klavyesi kuruldu ve etkinleştirildi. Telefonun kendi klavyesi varsayılan kalır; "
        "mphone yalnızca yazarken geçici olarak geçer."
    )
    return 0


def awake(args: Any) -> int:
    """Keep the screen on for a long task without changing settings, until Ctrl+C."""
    device = AndroidAdb(args.device or "")
    device.send("device.keep_awake", on=True)
    print(f"{device.resolve()} uyanık tutuluyor; bitirmek için Ctrl+C.")
    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        device.send("device.keep_awake", on=False)
        return 0
