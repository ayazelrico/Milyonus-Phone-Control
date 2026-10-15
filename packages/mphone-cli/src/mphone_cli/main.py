"""The `mphone` command: run, mcp, skill, doctor, android (A2.13, A2.14, A3.01, A3.05, A3.08)."""

import argparse
import sys
from pathlib import Path

from mphone_cli import __version__
from mphone_protocol import MphoneError


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="mphone", description="Milyonus Phone Control")
    p.add_argument("-V", "--version", action="version", version=f"mphone {__version__}")
    sub = p.add_subparsers(dest="command")

    sub.add_parser("version", help="sürümü yazdır")

    r = sub.add_parser(
        "run", help="telefonda Python script çalıştır (helper'lar yüklü); stdin, dosya veya -c"
    )
    r.add_argument("file", nargs="?", help="script dosyası (yoksa stdin)")
    r.add_argument("-c", "--code", help="script metni")
    r.add_argument("--device", help="cihaz URI'si (fake:settings_about, android:SERİ, …)")
    r.add_argument("--timeout", type=float, default=300, help="saniye (5–1800, varsayılan 300)")
    r.add_argument(
        "--allow",
        action="append",
        default=[],
        metavar="KURAL",
        help="kullanıcının AÇIKÇA onayladığı politika kuralı (ör. outward-send); tekrarlanabilir",
    )
    r.add_argument("--trust", default="standard", choices=["low", "standard", "high"])

    sub.add_parser("mcp", help="MCP sunucusunu stdio üzerinde başlat (agent'lar için)")
    sub.add_parser("skill", help="agent yönergesini (SKILL.md) yazdır")

    d = sub.add_parser("doctor", help="bağlantı zincirini teşhis et")
    d.add_argument("platform", nargs="?", default="android", choices=["android", "ios"])
    d.add_argument("--device", help="seri numarası, usb veya wifi:AD")
    d.add_argument("--write-test", action="store_true", help="Türkçe yazımı test ekranında dene")
    d.add_argument("--json", action="store_true")

    a = sub.add_parser("android", help="Android telefonları yönet")
    asub = a.add_subparsers(dest="android_command", required=True)
    asub.add_parser("devices", help="bağlı telefonlar")
    pr = asub.add_parser("pair", help="Wi-Fi eşleştirme (Android 11+)")
    pr.add_argument("code")
    pr.add_argument("--host", help="IP:PORT (bulunamazsa)")
    us = asub.add_parser("use", help="birincil telefonu seç ('-' kaldırır)")
    us.add_argument("serial")
    im = asub.add_parser("ime", help="Türkçe/emoji için mphone klavyesi")
    im.add_argument("action", choices=["install", "status", "uninstall"])
    im.add_argument("--apk", help="yerel APK (varsayılan: son sürüm)")
    im.add_argument("--device")
    aw = asub.add_parser("awake", help="ekranı ayar değiştirmeden uyanık tut")
    aw.add_argument("--device")
    return p


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):  # Windows consoles/pipes default to cp1252: Turkish needs UTF-8
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="replace")
    args = build_parser().parse_args(sys.argv[1:] if argv is None else argv)
    try:
        if args.command in (None, "version"):
            print(f"mphone {__version__}")
            return 0
        if args.command == "run":
            from mphone_cli.runner import run_script

            if args.code is not None:
                code = args.code
            elif args.file:
                code = Path(args.file).read_text(encoding="utf-8")
            else:
                code = sys.stdin.read()
            result = run_script(code, args.device, args.timeout, allow=args.allow, trust_level=args.trust)
            sys.stdout.write(result.stdout)
            sys.stderr.write(
                result.stderr if result.stderr.endswith("\n") or not result.stderr else result.stderr + "\n"
            )
            for warning in result.warnings:
                print(f"! {warning}", file=sys.stderr)
            return result.exit_code
        if args.command in ("mcp", "skill"):
            try:
                from mphone_mcp import server
            except ImportError:
                print("mphone-mcp kurulu değil: `uv tool install mphone-mcp`", file=sys.stderr)
                return 2
            if args.command == "skill":
                sys.stdout.write(server.skill_text())
                return 0
            server.main()
            return 0
        if args.command == "doctor":
            from mphone_cli import doctor

            return doctor.main(args)
        if args.command == "android":
            from mphone_cli import android

            return getattr(android, args.android_command)(args)
    except MphoneError as e:
        print(f"✗ {e.message}", file=sys.stderr)
        if e.user_action:
            print(f"  → {e.user_action}", file=sys.stderr)
        return 2
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
