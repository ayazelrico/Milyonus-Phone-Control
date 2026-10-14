"""Getting text into the focused field (A2.08, ADR-0009, PITFALLS#android-ascii-only-text).

`input text` types ASCII only, through the device shell, with " " spelled "%s". Anything else —
Turkish letters, emoji, newlines, or a literal "%s" — goes through an IME that receives the text
base64-encoded in a broadcast:

  - mphone IME (apps/android-ime, Apache-2.0)          — preferred
  - ADBKeyboard (third party, GPL-2.0, user-installed) — accepted when present
"""

import base64
import shlex
from dataclasses import dataclass


@dataclass(frozen=True)
class Ime:
    name: str
    ime_id: str
    input_action: str
    clear_action: str
    extra: str = "msg"


MPHONE_IME = Ime(
    name="mphone",
    ime_id="com.milyonus.mphone.ime/.MphoneIme",
    input_action="com.milyonus.mphone.ime.INPUT_B64",
    clear_action="com.milyonus.mphone.ime.CLEAR",
)
ADB_KEYBOARD = Ime(
    name="adbkeyboard",
    ime_id="com.android.adbkeyboard/.AdbIME",
    input_action="ADB_INPUT_B64",
    clear_action="ADB_CLEAR_TEXT",
)
KNOWN_IMES = (MPHONE_IME, ADB_KEYBOARD)


def ascii_safe(s: str) -> bool:
    """True when `input text` can type `s` exactly."""
    return s.isascii() and all(c.isprintable() for c in s) and "%s" not in s and s != ""


def input_text_command(s: str) -> str:
    """The device-shell command that types ASCII `s` with `input text`."""
    return "input text " + shlex.quote(s.replace(" ", "%s"))


def broadcast_command(ime: Ime, s: str) -> str:
    payload = base64.b64encode(s.encode("utf-8")).decode("ascii")
    return f"am broadcast -a {ime.input_action} --es {ime.extra} {payload}"


def clear_command(ime: Ime) -> str:
    return f"am broadcast -a {ime.clear_action}"
