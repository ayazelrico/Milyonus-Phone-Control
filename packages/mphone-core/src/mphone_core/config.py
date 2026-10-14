"""Settings: ~/.mphone/config.toml, overridden by MPHONE_<SECTION>_<KEY> (A1.10, Plan.md §8.1.5).

Every value can report where it came from (`env:…`, `file:…`, `default`) so `mphone config`
and `doctor` can explain a surprising setting instead of just printing it.

The home directory is MPHONE_HOME, else ~/.mphone, on every OS. It holds config.toml and the
cache/, runs/, audit/, locks/ and agent-workspace/ directories.
"""

import os
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

Scalar = str | int | float | bool


@dataclass(frozen=True)
class Key:
    name: str
    kind: type
    default: Scalar | None
    help: str


KNOWN_KEYS: dict[str, Key] = {
    k.name: k
    for k in [
        Key("default_device", str, None, "Device URI used when none is given (android:SERIAL, fake:NAME, …)"),
        Key("android.primary", str, None, "Saved primary Android phone; never substituted when unreachable"),
        Key("android.adb_path", str, None, "adb binary; found on PATH and known install paths when unset"),
        Key("android.unicode_ime", bool, True, "Type non-ASCII text through an IME (ADR-0009)"),
        Key("ios.background_events", bool, True, "Post iPhone Mirroring events without taking focus"),
        Key("ocr.engine", str, "auto", "OCR engine: auto, vision, rapidocr, null"),
        Key("gateway.url", str, None, "Gateway base URL for remote devices"),
        Key("gateway.api_key_ref", str, None, "Keychain reference of the API key (never the key itself)"),
        Key("policy.file", str, None, "Local policy YAML; defaults to <home>/policy.yaml"),
        Key("audit.dir", str, None, "Local audit directory; defaults to <home>/audit"),
        Key("workspace.dir", str, None, "Agent workspace; defaults to <home>/agent-workspace"),
    ]
}


class ConfigError(ValueError):
    pass


def home() -> Path:
    return Path(os.environ.get("MPHONE_HOME") or Path.home() / ".mphone")


def config_path() -> Path:
    return home() / "config.toml"


def subdir(name: str) -> Path:
    """A directory under the home, created on first use."""
    path = home() / name
    path.mkdir(parents=True, exist_ok=True)
    return path


def env_name(key: str) -> str:
    return "MPHONE_" + key.replace(".", "_").upper()


def _read_file() -> dict[str, Any]:
    path = config_path()
    if not path.is_file():
        return {}
    try:
        return tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as e:
        raise ConfigError(f"{path} is not valid TOML: {e}") from None


def _dig(data: dict[str, Any], key: str) -> Any:
    node: Any = data
    for part in key.split("."):
        if not isinstance(node, dict) or part not in node:
            return None
        node = node[part]  # pyright: ignore[reportUnknownVariableType]
    return node  # pyright: ignore[reportUnknownVariableType]


def coerce(key: str, raw: str) -> Scalar:
    kind = KNOWN_KEYS[key].kind
    if kind is bool:
        lowered = raw.strip().lower()
        if lowered in ("1", "true", "yes", "on", "evet"):
            return True
        if lowered in ("0", "false", "no", "off", "hayır", "hayir"):
            return False
        raise ConfigError(f"{key} expects true/false, got {raw!r}")
    if kind is int:
        return int(raw)
    if kind is float:
        return float(raw)
    return raw


def lookup(key: str) -> tuple[Scalar | None, str]:
    """(value, source) for a known key. Environment beats file beats default."""
    if key not in KNOWN_KEYS:
        raise ConfigError(f"unknown setting {key!r}; known: {', '.join(sorted(KNOWN_KEYS))}")
    env = env_name(key)
    if env in os.environ:
        return coerce(key, os.environ[env]), f"env:{env}"
    value = _dig(_read_file(), key)
    if value is not None:
        return value, f"file:{config_path()}"
    return KNOWN_KEYS[key].default, "default"


def get(key: str) -> Any:
    return lookup(key)[0]


def _dump(data: dict[str, Any]) -> str:
    """Minimal TOML writer for our shape: top-level scalars and one level of sections."""

    def scalar(v: Any) -> str:
        if isinstance(v, bool):
            return "true" if v else "false"
        if isinstance(v, int | float):
            return repr(v)
        escaped = str(v).replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'

    top = [f"{k} = {scalar(v)}" for k, v in sorted(data.items()) if not isinstance(v, dict)]
    out = "\n".join(top) + ("\n" if top else "")
    for section, values in sorted(data.items()):
        if isinstance(values, dict):
            body = "\n".join(f"{k} = {scalar(v)}" for k, v in sorted(values.items()))  # pyright: ignore[reportUnknownVariableType, reportUnknownArgumentType]
            out += f"\n[{section}]\n{body}\n"
    return out.lstrip("\n")


def set_value(key: str, raw: str) -> Scalar:
    if key not in KNOWN_KEYS:
        raise ConfigError(f"unknown setting {key!r}; known: {', '.join(sorted(KNOWN_KEYS))}")
    value = coerce(key, raw)
    data = _read_file()
    parts = key.split(".")
    node = data
    for part in parts[:-1]:
        node = node.setdefault(part, {})
    node[parts[-1]] = value
    config_path().parent.mkdir(parents=True, exist_ok=True)
    config_path().write_text(_dump(data), encoding="utf-8")
    return value


def unset(key: str) -> None:
    data = _read_file()
    parts = key.split(".")
    node: Any = data
    for part in parts[:-1]:
        node = node.get(part, {})
    if isinstance(node, dict):
        node.pop(parts[-1], None)  # pyright: ignore[reportUnknownMemberType]
    config_path().parent.mkdir(parents=True, exist_ok=True)
    config_path().write_text(_dump(data), encoding="utf-8")
