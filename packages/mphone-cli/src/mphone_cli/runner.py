"""Run an agent script against a phone in a fresh interpreter (A3.01; CLI `mphone run` and MCP
`phone_exec` both use this).

  - the child gets the parent's environment minus secrets (*_API_KEY, *_TOKEN, *_SECRET,
    *_PASSWORD), as the reference harness did for its agent plugin;
  - the device is locked for this machine while the script runs (LocalLease);
  - a timeout kills the whole process group; output keeps its last 50 KB;
  - everything lands in <home>/runs/<run_id>/: script, ops trace, result.
"""

import json
import os
import re
import signal
import subprocess
import sys
import time
import uuid
from dataclasses import asdict, dataclass, field

from mphone_core import config
from mphone_core.connect import resolve_uri
from mphone_core.locallease import LocalLease

OUTPUT_CAP, STDERR_CAP = 50_000, 8_000
DEFAULT_TIMEOUT, MIN_TIMEOUT, MAX_TIMEOUT = 300, 5, 1800
SECRET_SUFFIXES = ("_API_KEY", "_TOKEN", "_SECRET", "_PASSWORD", "_PASSWD")
TIMEOUT_EXIT = 124


@dataclass
class RunResult:
    run_id: str
    exit_code: int
    stdout: str
    stderr: str
    duration_s: float
    timed_out: bool = False
    device: str = ""
    warnings: list[str] = field(default_factory=list[str])
    images: list[str] = field(default_factory=list[str])

    @property
    def ok(self) -> bool:
        return self.exit_code == 0


def scrubbed_env(base: dict[str, str]) -> dict[str, str]:
    return {k: v for k, v in base.items() if not k.upper().endswith(SECRET_SUFFIXES)}


def lint(code: str) -> list[str]:
    """Advice, not errors: the # task: / # step: header makes runs readable later (SKILL.md)."""
    head = "\n".join(code.splitlines()[:5])
    warnings: list[str] = []
    if not re.search(r"^#\s*task:", head, re.MULTILINE):
        warnings.append("script has no '# task:' line (the user's request, same for every script of a task)")
    if not re.search(r"^#\s*step:", head, re.MULTILINE):
        warnings.append("script has no '# step:' line (what this script does)")
    return warnings


def _tail(text: str, cap: int) -> str:
    return text if len(text) <= cap else f"[… {len(text) - cap} karakter kesildi …]\n" + text[-cap:]


def _images(stdout: str, since: float) -> list[str]:
    """Image paths the script printed (screenshot() prints its path) that were written during it."""
    found: list[str] = []
    for line in stdout.splitlines():
        line = line.strip()
        is_image = line.lower().endswith((".png", ".jpg", ".jpeg")) and os.path.isfile(line)
        if is_image and os.path.getmtime(line) >= since - 1 and line not in found:
            found.append(line)
    return found


def run_script(
    code: str,
    device: str | None = None,
    timeout: float = DEFAULT_TIMEOUT,
    owner: str = "mphone run",
    lock: bool = True,
    allow: list[str] | None = None,
    trust_level: str = "standard",
    extra_env: dict[str, str] | None = None,
) -> RunResult:
    timeout = max(MIN_TIMEOUT, min(MAX_TIMEOUT, timeout))
    uri, _ = resolve_uri(device)
    run_id = f"run_{time.strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
    run_dir = config.subdir("runs") / run_id
    run_dir.mkdir(parents=True)
    (run_dir / "script.py").write_text(code, encoding="utf-8")
    task = next((m.group(1).strip() for m in re.finditer(r"^#\s*task:(.*)$", code, re.MULTILINE)), "")
    env = scrubbed_env(dict(os.environ))
    env.update(
        MPHONE_DEVICE=uri,
        MPHONE_RUN_ID=run_id,
        MPHONE_RUN_DIR=str(run_dir),
        MPHONE_TASK=task,
        PYTHONIOENCODING="utf-8",
        MPHONE_ALLOW=",".join(allow or []),
        MPHONE_TRUST=trust_level,
    )
    env.update(extra_env or {})  # e.g. a lease credential: scoped to one lease, unlike the agent's key
    lease = LocalLease(uri, owner=owner, purpose=task) if lock else None
    start, wall = time.monotonic(), time.time()
    timed_out = False
    if lease is not None:
        lease.acquire()
    try:
        proc = subprocess.Popen(
            [sys.executable, "-I", "-m", "mphone_cli.child"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            start_new_session=not sys.platform.startswith("win"),
        )
        try:
            out, err = proc.communicate(code.encode("utf-8"), timeout=timeout)
        except subprocess.TimeoutExpired:
            timed_out = True
            if sys.platform.startswith("win"):
                proc.kill()
            else:
                os.killpg(proc.pid, signal.SIGKILL)
            out, err = proc.communicate()
    finally:
        if lease is not None:
            lease.release()
    stdout = out.decode("utf-8", "replace")
    stderr = err.decode("utf-8", "replace")
    if timed_out:
        stderr += f"\n✗ [TIMEOUT] script exceeded {timeout:g}s and was stopped\n"
    result = RunResult(
        run_id=run_id,
        exit_code=TIMEOUT_EXIT if timed_out else proc.returncode,
        stdout=_tail(stdout, OUTPUT_CAP),
        stderr=_tail(stderr, STDERR_CAP),
        duration_s=round(time.monotonic() - start, 2),
        timed_out=timed_out,
        device=uri,
        warnings=lint(code),
        images=_images(stdout, wall),
    )
    (run_dir / "result.json").write_text(
        json.dumps(asdict(result), ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return result
