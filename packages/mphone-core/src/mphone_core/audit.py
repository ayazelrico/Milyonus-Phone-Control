"""Local trace and audit (A3.02, Plan.md §10).

Every op is recorded with what it did and how it ended, but never with what was typed: sensitive
arguments (schema `x-sensitive-args`, e.g. input.text's `s`) become {len, sha256}. A PIN typed by
mistake must not end up on disk in plain text.
"""

import hashlib
import json
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from mphone_protocol import OP_SPECS, MphoneError

from .transport import Next, OpCall


def mask(op: str, kw: dict[str, Any]) -> dict[str, Any]:
    spec = OP_SPECS.get(op)
    sensitive: set[str] = set(spec.sensitive_args) if spec else set()
    out: dict[str, Any] = {}
    for key, value in kw.items():
        if key in sensitive and isinstance(value, str):
            out[key] = {"len": len(value), "sha256": hashlib.sha256(value.encode()).hexdigest()[:16]}
        else:
            out[key] = value
    return out


class AuditMiddleware:
    """Appends one JSON line per op to <dir>/YYYY-MM-DD.jsonl (and to an optional run trace)."""

    def __init__(
        self,
        directory: Path,
        run_id: str | None = None,
        task: str | None = None,
        trace_file: Path | None = None,
    ) -> None:
        self.directory = directory
        self.run_id = run_id
        self.task = task
        self.trace_file = trace_file
        directory.mkdir(parents=True, exist_ok=True)

    def __call__(self, call: OpCall, nxt: Next) -> Any:
        start = time.monotonic()
        record: dict[str, Any] = {
            "ts": datetime.now(UTC).isoformat(timespec="milliseconds"),
            "run_id": self.run_id,
            "task": self.task,
            "backend": call.backend.name,
            "op": call.op,
            "kw": mask(call.op, call.kw),
        }
        try:
            result = nxt(call)
            record["ok"] = True
            return result
        except MphoneError as e:
            record.update(ok=False, error_code=e.code, error=e.message[:300])
            raise
        except Exception as e:
            record.update(ok=False, error_code="INTERNAL", error=f"{type(e).__name__}: {e}"[:300])
            raise
        finally:
            record["duration_ms"] = round((time.monotonic() - start) * 1000)
            line = json.dumps(record, ensure_ascii=False, default=str) + "\n"
            day = self.directory / f"{datetime.now(UTC):%Y-%m-%d}.jsonl"
            with day.open("a", encoding="utf-8") as f:
                f.write(line)
            if self.trace_file is not None:
                with self.trace_file.open("a", encoding="utf-8") as f:
                    f.write(line)
