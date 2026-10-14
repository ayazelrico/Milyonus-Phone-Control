"""The interpreter a `mphone run` script executes in (spawned by runner.run_script, A3.01).

Helpers are pre-imported, the agent workspace is loaded, every op is audited. Errors print the
one thing the user must do and map to an exit code:
    0 ok · 1 script error · 2 device/prerequisite (locked, offline, needs user…) · 3 policy/approval
"""

import os
import sys
import traceback
from pathlib import Path

from mphone_core import config, helpers, workspace
from mphone_core.audit import AuditMiddleware
from mphone_protocol import MphoneError

PREREQUISITE = {
    "DEVICE_OFFLINE",
    "DEVICE_LOCKED",
    "DEVICE_ASLEEP",
    "DEVICE_UNAUTHORIZED",
    "NEEDS_USER",
    "LEASE_REQUIRED",
    "LEASE_CONFLICT",
    "LEASE_EXPIRED",
    "LEASE_PAUSED",
    "UNSUPPORTED",
}
POLICY = {"POLICY_DENIED", "APPROVAL_REQUIRED", "APPROVAL_DENIED"}


def exit_code_for(error: MphoneError) -> int:
    if error.code in POLICY:
        return 3
    if error.code in PREREQUISITE:
        return 2
    return 1


def main() -> int:
    code = sys.stdin.read()
    run_dir = Path(os.environ["MPHONE_RUN_DIR"])
    phone = helpers.connect(os.environ.get("MPHONE_DEVICE") or None)
    phone.backend.use(
        AuditMiddleware(
            config.subdir("audit"),
            os.environ.get("MPHONE_RUN_ID"),
            os.environ.get("MPHONE_TASK"),
            trace_file=run_dir / "ops.jsonl",
        )
    )
    helpers.use(phone)
    namespace: dict[str, object] = {"__name__": "__main__"}
    for name in helpers.__all__:
        namespace[name] = getattr(helpers, name)
    workspace.load_into(namespace)
    try:
        exec(compile(code, "<mphone script>", "exec"), namespace)  # noqa: S102 — the agent's script, sandboxed by the runner
    except MphoneError as e:
        print(f"✗ [{e.code}] {e.message}", file=sys.stderr)
        if e.user_action:
            print(f"  → {e.user_action}", file=sys.stderr)
        if e.details.get("visible"):
            print(f"  görünen: {e.details['visible'][:20]}", file=sys.stderr)
        return exit_code_for(e)
    except SystemExit as e:
        return int(e.code or 0) if isinstance(e.code, int | type(None)) else 1
    except BaseException:
        lines = traceback.format_exc().splitlines()
        print("\n".join(lines[-20:]), file=sys.stderr)
        return 1
    finally:
        phone.backend.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
