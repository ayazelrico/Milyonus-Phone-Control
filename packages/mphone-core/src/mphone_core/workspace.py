"""The agent workspace: helpers an agent writes for itself and keeps across upgrades (A1.10).

Path: MPHONE_AGENT_WORKSPACE, else `workspace.dir` from config, else <home>/agent-workspace.
The directory is seeded from the packaged default only when agent_helpers.py is missing; an
existing file is never touched. Delete it to get a fresh default on the next run.
"""

import shutil
import warnings
from importlib import resources
from pathlib import Path
from typing import Any

from . import config

HELPERS_FILE = "agent_helpers.py"


def path() -> Path:
    import os

    explicit = os.environ.get("MPHONE_AGENT_WORKSPACE") or config.get("workspace.dir")
    return Path(explicit) if explicit else config.home() / "agent-workspace"


def default_source() -> Path:
    return Path(str(resources.files("mphone_core") / "workspace_default" / HELPERS_FILE))


def ensure() -> Path:
    """Create the workspace from the packaged default if it has no helpers file yet."""
    directory = path()
    target = directory / HELPERS_FILE
    if not target.exists():
        directory.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(default_source(), target)
    return target


def load_into(namespace: dict[str, Any]) -> list[str]:
    """Execute the workspace helpers into `namespace`; return the names they defined.

    A workspace name that shadows a core helper wins (the agent asked for it), but it is
    reported, because silently replacing `tap` would be a miserable thing to debug.
    """
    target = ensure()
    scope: dict[str, Any] = {"__name__": "agent_helpers", "__file__": str(target)}
    code = compile(target.read_text(encoding="utf-8"), str(target), "exec")
    exec(code, scope)  # noqa: S102 — the agent's own helpers, by design
    defined = [k for k in scope if not k.startswith("_")]
    for name in defined:
        if name in namespace and namespace[name] is not scope[name]:
            warnings.warn(f"agent workspace overrides core helper {name!r}", stacklevel=2)
        namespace[name] = scope[name]
    return defined
