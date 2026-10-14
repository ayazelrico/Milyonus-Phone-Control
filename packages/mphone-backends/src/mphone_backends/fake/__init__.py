"""The fake phone: deterministic, scenario-driven, every op implemented (A1.12).

connect("fake:settings_about")             # a packaged scenario
connect("fake:/path/to/my_scenario.yaml")  # any file
"""

import os
from pathlib import Path
from typing import Any

import yaml

from mphone_protocol import InvalidArgument

from .backend import FakeBackend

SCENARIO_DIR = Path(__file__).parent / "scenarios"


def scenario_names() -> list[str]:
    return sorted(p.stem for p in SCENARIO_DIR.glob("*.yaml"))


def load_scenario(name_or_path: str) -> tuple[dict[str, Any], str]:
    candidates = [Path(name_or_path)]
    extra = os.environ.get("MPHONE_FAKE_SCENARIOS")
    if extra:
        candidates += [Path(d) / f"{name_or_path}.yaml" for d in extra.split(os.pathsep)]
    candidates.append(SCENARIO_DIR / f"{name_or_path}.yaml")
    for path in candidates:
        if path.suffix in (".yaml", ".yml") and path.is_file():
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
            if not isinstance(data, dict) or "screens" not in data:
                raise InvalidArgument(f"{path} is not a fake scenario (needs a 'screens' mapping)")
            return data, str(path)  # pyright: ignore[reportUnknownVariableType]
    raise InvalidArgument(f"no fake scenario {name_or_path!r}; packaged: {', '.join(scenario_names())}")


def from_uri(rest: str) -> FakeBackend:
    scenario, source = load_scenario(rest or "settings_about")
    return FakeBackend(scenario, source)


__all__ = ["FakeBackend", "from_uri", "load_scenario", "scenario_names"]
