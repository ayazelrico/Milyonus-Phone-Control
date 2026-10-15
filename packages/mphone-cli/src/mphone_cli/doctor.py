"""`mphone doctor android`: walk the connection ladder and name the ONE thing to fix (A2.13).

Each rung depends on the ones before it, so the first failure stops the walk: "adb is missing"
is the useful answer, not twelve red lines that all follow from it.
"""

import json
import sys
from collections.abc import Callable
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from mphone_protocol import MphoneError


@dataclass
class Step:
    name: str
    ok: bool
    detail: str = ""
    hint: str = ""
    fatal: bool = True


def _run(name: str, fn: Callable[[], str], hint: str = "", fatal: bool = True) -> Step:
    try:
        return Step(name, True, fn())
    except MphoneError as e:
        return Step(name, False, e.message, e.user_action or hint, fatal)
    except Exception as e:  # doctor reports, it never crashes
        return Step(name, False, f"{type(e).__name__}: {e}", hint, fatal)


def android_steps(target: str = "", write_test: bool = False) -> list[Step]:
    from mphone_backends.android_adb.adb import find_adb
    from mphone_backends.android_adb.backend import AndroidAdb
    from mphone_backends.android_adb.text import KNOWN_IMES

    device = AndroidAdb(target)
    steps: list[Step] = []

    def check(step: Step) -> bool:
        steps.append(step)
        return step.ok or not step.fatal

    if not check(
        _run("adb kurulu", lambda: f"{find_adb()} ({device.adb.run('version', pin=False).splitlines()[0]})")
    ):
        return steps
    if not check(_run("telefon seçildi", lambda: f"{device.resolve()}")):
        return steps
    if not check(_run("uyanık ve kilitsiz", lambda: str(device.send("device.require")))):
        return steps

    def capture() -> str:
        cap = device.send("screen.capture")
        Path(cap["path"]).unlink(missing_ok=True)
        return f"{cap['w']}x{cap['h']}" + (" (FLAG_SECURE: siyah)" if cap["secure"] else "")

    if not check(_run("ekran görüntüsü", capture)):
        return steps
    check(
        _run(
            "erişilebilirlik ağacı",
            lambda: f"{len(device.send('tree'))} düğüm",
            hint="Animasyonlu bir ekrandaysanız ana ekrana dönüp tekrar deneyin (PITFALLS#android-idle-state).",
            fatal=False,
        )
    )

    def ime() -> str:
        found = device.send("raw", cmd="ime list -a -s")
        for candidate in KNOWN_IMES:
            if candidate.ime_id in found:
                return candidate.name
        raise RuntimeError("Türkçe/emoji yazmak için klavye yüklü değil")

    check(_run("Unicode klavye (Türkçe yazım)", ime, hint="`mphone android ime install`", fatal=False))

    if write_test:

        def turkish() -> str:
            text = "Çağrı ışığı söndü; İğdır"
            device.send("apps.launch", name="com.milyonus.mphone.ime", fresh=True)
            field = device.send("ui.find", selector={"resource_id": "mphone_text"})
            if not field:
                visible = [b["text"] for b in device.send("screen.text")][:25]
                current = device.send("apps.current")
                raise RuntimeError(
                    f"test ekranı açılmadı (mphone IME debug APK gerekli); önde: {current}; görünen: {visible}"
                )
            device.send("input.tap", x=field[0]["x"], y=field[0]["y"])
            device.send("input.text", s=text)
            got = device.send("ui.find", selector={"resource_id": "mphone_text"})[0]["text"]
            if got != text:
                raise RuntimeError(f"yazılan {text!r}, okunan {got!r}")
            return "Türkçe metin yazıldı ve geri okundu"

        check(_run("Türkçe yazım testi", turkish, fatal=False))
    device.close()
    return steps


def report(steps: list[Step], as_json: bool) -> int:
    if as_json:
        print(json.dumps([asdict(s) for s in steps], ensure_ascii=False, indent=2))
    else:
        for s in steps:
            mark = "✓" if s.ok else ("✗" if s.fatal else "!")
            print(f"{mark} {s.name}: {s.detail}")
            if not s.ok and s.hint:
                print(f"    → {s.hint}")
    failed = [s for s in steps if not s.ok and s.fatal]
    if not as_json:
        print("\nHazır." if not failed else f"\nDüzeltilmesi gereken: {failed[0].name}", file=sys.stderr)
    return 1 if failed else 0


def main(args: Any) -> int:
    if args.platform != "android":
        print(f"doctor {args.platform}: P4 ile gelecek", file=sys.stderr)
        return 2
    return report(android_steps(args.device or "", args.write_test), args.json)
