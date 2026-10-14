"""Key names → Android keycodes (A2.07). Single keys only: `input keyevent` has no chords, so a
combo like "cmd+space" is Unsupported rather than faked."""

from mphone_protocol import InvalidArgument, Unsupported

KEYCODES: dict[str, str] = {
    "enter": "KEYCODE_ENTER",
    "return": "KEYCODE_ENTER",
    "back": "KEYCODE_BACK",
    "home": "KEYCODE_HOME",
    "recents": "KEYCODE_APP_SWITCH",
    "tab": "KEYCODE_TAB",
    "del": "KEYCODE_DEL",
    "backspace": "KEYCODE_DEL",
    "delete": "KEYCODE_FORWARD_DEL",
    "space": "KEYCODE_SPACE",
    "escape": "KEYCODE_ESCAPE",
    "esc": "KEYCODE_ESCAPE",
    "menu": "KEYCODE_MENU",
    "search": "KEYCODE_SEARCH",
    "up": "KEYCODE_DPAD_UP",
    "down": "KEYCODE_DPAD_DOWN",
    "left": "KEYCODE_DPAD_LEFT",
    "right": "KEYCODE_DPAD_RIGHT",
    "volume_up": "KEYCODE_VOLUME_UP",
    "volume_down": "KEYCODE_VOLUME_DOWN",
    "power": "KEYCODE_POWER",
    "wakeup": "KEYCODE_WAKEUP",
    "sleep": "KEYCODE_SLEEP",
    "camera": "KEYCODE_CAMERA",
    "move_home": "KEYCODE_MOVE_HOME",
    "move_end": "KEYCODE_MOVE_END",
    "+": "KEYCODE_PLUS",
    "plus": "KEYCODE_PLUS",
}


def keycode(combo: str) -> str:
    key = combo.strip().lower()
    if key in KEYCODES:
        return KEYCODES[key]
    if "+" in key:
        raise Unsupported(f"Android over adb cannot press chords like {combo!r}; send the keys one by one")
    if key.upper().startswith("KEYCODE_"):
        return key.upper()
    if len(key) == 1 and key.isalnum() and key.isascii():
        return f"KEYCODE_{key.upper()}"
    raise InvalidArgument(f"unknown key {combo!r}; known: {', '.join(sorted(KEYCODES))}")
