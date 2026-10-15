"""Parsers for what adb and the Android shell print (A2.02–A2.12).

Every parser here is tested against REAL output captured from emulators
(tools/android/capture_fixtures.sh → tests/fixtures/android/). Formats differ between Android
versions; where they do, the difference is named next to the code that handles it.
"""

import re
from dataclasses import dataclass
from typing import Any
from xml.etree.ElementTree import Element

from defusedxml.ElementTree import fromstring

Dict = dict[str, Any]


# --- adb devices -l / adb mdns services ------------------------------------------------------


@dataclass(frozen=True)
class DeviceRow:
    serial: str
    state: str  # device | unauthorized | offline | recovery | sideload | bootloader | …
    transport: str  # usb | wifi | emulator
    model: str | None = None
    product: str | None = None


def transport_of(serial: str, props: dict[str, str]) -> str:
    if serial.startswith("emulator-"):
        return "emulator"
    if "usb" in props:
        return "usb"
    if ":" in serial or "._adb-tls-connect." in serial or serial.startswith("adb-"):
        return "wifi"
    return "usb"


def parse_devices(out: str) -> list[DeviceRow]:
    """`adb devices -l`: "SERIAL  STATE key:value …" after the header line."""
    rows: list[DeviceRow] = []
    for line in out.splitlines():
        line = line.strip()
        if not line or line.startswith("List of devices") or line.startswith("*"):
            continue
        parts = line.split()
        if len(parts) < 2:
            continue
        serial, state = parts[0], parts[1]
        props = dict(p.split(":", 1) for p in parts[2:] if ":" in p)
        rows.append(
            DeviceRow(serial, state, transport_of(serial, props), props.get("model"), props.get("product"))
        )
    return rows


@dataclass(frozen=True)
class MdnsService:
    name: str
    kind: str  # _adb._tcp | _adb-tls-connect._tcp | _adb-tls-pairing._tcp
    addr: str


def parse_mdns(out: str) -> list[MdnsService]:
    """`adb mdns services`: "NAME<TAB>_TYPE._tcp<TAB>IP:PORT" after the header."""
    services: list[MdnsService] = []
    for line in out.splitlines():
        parts = line.split()
        if len(parts) == 3 and parts[1].startswith("_adb") and ":" in parts[2]:
            services.append(MdnsService(parts[0], parts[1].rstrip("."), parts[2]))
    return services


# --- power, keyguard ------------------------------------------------------------------------


def parse_wakefulness(out: str) -> str | None:
    """`dumpsys power`: mWakefulness=Awake|Asleep|Dozing|Dreaming.

    Android 14 reports a screen turned off with KEYCODE_SLEEP as "Dozing", not "Asleep"
    (captured on API 34); only "Awake" means input reaches the screen.
    """
    m = re.search(r"mWakefulness=(\w+)", out)
    return m.group(1) if m else None


def is_awake(wakefulness: str | None) -> bool:
    return wakefulness == "Awake"


def parse_keyguard_showing(window: str, policy: str = "") -> bool | None:
    """Whether the lock screen is up, from `dumpsys window` (isKeyguardShowing=…) and
    `dumpsys window policy` (KeyguardServiceDelegate showing=…). None when neither says."""
    for pattern in (r"isKeyguardShowing=(true|false)", r"mShowingLockscreen=(true|false)"):
        m = re.search(pattern, window)
        if m and m.group(1) == "true":
            return True
    m = re.search(r"KeyguardServiceDelegate\s+showing=(true|false)", policy)
    if m and m.group(1) == "true":
        return True
    if "isKeyguardShowing=false" in window or m:
        return False
    return None


# --- geometry ------------------------------------------------------------------------------


def _size(out: str, kind: str) -> str | None:
    override = re.search(rf"Override {kind}:\s*(\S+)", out)
    physical = re.search(rf"Physical {kind}:\s*(\S+)", out)
    chosen = override or physical
    return chosen.group(1) if chosen else None


def parse_wm_size(out: str) -> tuple[int, int] | None:
    """`wm size`: an override (set by `wm size WxH`) wins over the physical size, because that
    is what screencap and input use."""
    value = _size(out, "size")
    if not value or "x" not in value:
        return None
    w, h = value.split("x", 1)
    return int(w), int(h)


def parse_wm_density(out: str) -> int | None:
    value = _size(out, "density")
    return int(value) if value and value.isdigit() else None


def parse_rotation(display: str) -> int:
    """`dumpsys display`: mCurrentOrientation=0..3 → degrees. (`dumpsys input` SurfaceOrientation
    is missing on API 34.)"""
    m = re.search(r"mCurrentOrientation=(\d)", display)
    return int(m.group(1)) * 90 if m else 0


# --- activities, packages ----------------------------------------------------------------------

_RESUMED = re.compile(
    r"(?:topResumedActivity|mResumedActivity|ResumedActivity)[=:]\s*ActivityRecord\{\S+ u\d+ ([\w.]+)/"
)


def parse_resumed_package(out: str) -> str | None:
    """`dumpsys activity activities`: API 30 prints mResumedActivity, API 34 topResumedActivity;
    both print "ResumedActivity: ActivityRecord{… u0 PACKAGE/.Activity tN}"."""
    m = _RESUMED.search(out)
    return m.group(1) if m else None


def parse_packages(out: str) -> list[str]:
    """`pm list packages [-f]`: "package:ID" or "package:/path/base.apk=ID"."""
    found: list[str] = []
    for line in out.splitlines():
        line = line.strip()
        if not line.startswith("package:"):
            continue
        rest = line[len("package:") :]
        found.append(rest.rsplit("=", 1)[1] if "=" in rest else rest)
    return found


def parse_resolved_component(out: str) -> str | None:
    """`cmd package resolve-activity --brief …`: the last line is PACKAGE/ACTIVITY."""
    for line in reversed(out.splitlines()):
        line = line.strip()
        if "/" in line and " " not in line:
            return line
    return None


def parse_launchable(out: str) -> list[str]:
    """`cmd package query-activities --brief -a MAIN -c LAUNCHER`: component lines."""
    return [line.strip() for line in out.splitlines() if re.fullmatch(r"\s*[\w.]+/[\w.$]+\s*", line)]


# --- battery, notifications, props ---------------------------------------------------------------


def parse_battery(out: str) -> tuple[int | None, bool | None]:
    level = re.search(r"^\s*level:\s*(\d+)", out, re.MULTILINE)
    powered = [
        re.search(rf"^\s*{k} powered:\s*(true|false)", out, re.MULTILINE)
        for k in ("AC", "USB", "Wireless", "Dock")
    ]
    charging = any(m and m.group(1) == "true" for m in powered) if any(powered) else None
    return (int(level.group(1)) if level else None), charging


def parse_notifications(out: str, limit: int = 50) -> list[Dict]:
    """`dumpsys notification --noredact`: one NotificationRecord(… pkg=ID …) per notification,
    then extras with android.title=String (…) / android.text=String (…)."""
    records: list[Dict] = []
    for block in re.split(r"\n\s*NotificationRecord\(", "\n" + out)[1:]:
        pkg = re.search(r"pkg=([\w.]+)", block)
        if not pkg:
            continue
        title = re.search(r"android\.title=\w+ \((.*)\)\s*$", block, re.MULTILINE)
        text = re.search(r"android\.text=\w+ \((.*)\)\s*$", block, re.MULTILINE)
        records.append(
            {
                "app_id": pkg.group(1),
                "title": title.group(1) if title else None,
                "text": text.group(1) if text else None,
                "posted_at": None,
            }
        )
        if len(records) >= limit:
            break
    return records


# --- uiautomator ----------------------------------------------------------------------------------

_BOUNDS = re.compile(r"\[(-?\d+),(-?\d+)\]\[(-?\d+),(-?\d+)\]")
EDITABLE_CLASSES = ("EditText", "AutoCompleteTextView", "SearchView$SearchAutoComplete")


class TreeParseError(ValueError):
    pass


def extract_xml(out: str) -> str:
    """The XML part of a dump. `uiautomator dump FILE && cat FILE` prints a status line first;
    `uiautomator dump /dev/tty` prints ONLY the status line under a non-interactive adb shell."""
    start = out.find("<?xml")
    if start < 0:
        start = out.find("<hierarchy")
    if start < 0:
        raise TreeParseError(f"no hierarchy in uiautomator output: {out.strip()[:200]!r}")
    end = out.rfind("</hierarchy>")
    return out[start : end + len("</hierarchy>")] if end >= 0 else out[start:]


def _flag(el: Element, name: str) -> bool:
    return el.get(name) == "true"


def parse_uiautomator(out: str) -> tuple[list[Dict], int]:
    """(nodes, rotation degrees) from a uiautomator dump, as protocol Node dicts."""
    root = fromstring(extract_xml(out))
    rotation = int(root.get("rotation", "0") or 0) * 90
    nodes: list[Dict] = []

    def walk(el: Element, path: str, parent: str | None) -> None:
        m = _BOUNDS.match(el.get("bounds", ""))
        left, top, right, bottom = (int(v) for v in m.groups()) if m else (0, 0, 0, 0)
        cls = el.get("class") or None
        nodes.append(
            {
                "node_id": path,
                "parent_id": parent,
                "text": el.get("text", ""),
                "content_desc": el.get("content-desc") or None,
                "resource_id": el.get("resource-id") or None,
                "class": cls,
                "package": el.get("package") or None,
                "rect": {"left": left, "top": top, "right": right, "bottom": bottom},
                "visible": True,  # uiautomator dumps only visible nodes
                "clickable": _flag(el, "clickable") or _flag(el, "long-clickable"),
                "enabled": el.get("enabled", "true") == "true",
                "focused": _flag(el, "focused"),
                "editable": bool(cls and cls.endswith(EDITABLE_CLASSES)),
                "password": _flag(el, "password"),
                "scrollable": _flag(el, "scrollable"),
                "checked": _flag(el, "checked") if _flag(el, "checkable") else None,
                "selected": _flag(el, "selected"),
            }
        )
        for i, child in enumerate(c for c in el if c.tag == "node"):
            walk(child, f"{path}.{i}", path)

    for i, top_node in enumerate(c for c in root if c.tag == "node"):
        walk(top_node, str(i), None)
    return nodes, rotation
