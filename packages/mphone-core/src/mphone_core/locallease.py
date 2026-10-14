"""Local lease: one process drives a device at a time on this machine (A3.03, Plan.md §6.2 Mode A).

An OS file lock under <home>/locks/: it disappears with the process that held it, so a crashed
agent can never leave a phone locked forever. The lock file carries who holds it, so the second
agent's error can name the first.
"""

import hashlib
import json
import os
import sys
import time
from typing import IO, Any

from mphone_protocol import LeaseConflict

from . import config


def key_for(uri: str) -> str:
    safe = "".join(c if c.isalnum() or c in "-_." else "_" for c in uri)[:60]
    return f"{safe}-{hashlib.sha256(uri.encode()).hexdigest()[:8]}"


def _try_lock(f: IO[str]) -> bool:
    if sys.platform.startswith("win"):
        import msvcrt

        try:
            msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)  # pyright: ignore[reportAttributeAccessIssue, reportUnknownMemberType]
        except OSError:
            return False
        return True
    import fcntl

    try:
        fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        return False
    return True


class LocalLease:
    def __init__(self, uri: str, owner: str = "mphone", purpose: str = "") -> None:
        self.uri = uri
        self.owner = owner
        self.purpose = purpose
        self.path = config.subdir("locks") / f"{key_for(uri)}.lock"
        self._file: IO[str] | None = None

    def holder(self) -> dict[str, Any] | None:
        try:
            return json.loads(self.path.read_text(encoding="utf-8") or "null")
        except (OSError, ValueError):
            return None

    def acquire(self) -> "LocalLease":
        f = self.path.open("a+", encoding="utf-8")
        if not _try_lock(f):
            f.close()
            held = self.holder() or {}
            raise LeaseConflict(
                f"{self.uri} is in use by {held.get('owner', 'another process')} "
                f"(pid {held.get('pid', '?')}, {held.get('purpose') or 'no purpose given'})",
                user_action="Diğer görev bitene kadar bekleyin veya başka bir cihaz seçin.",
                details={"holder": held},
            )
        f.seek(0)
        f.truncate()
        f.write(
            json.dumps(
                {
                    "owner": self.owner,
                    "pid": os.getpid(),
                    "purpose": self.purpose,
                    "since": time.time(),
                    "uri": self.uri,
                }
            )
        )
        f.flush()
        self._file = f
        return self

    def release(self) -> None:
        if self._file is not None:
            self._file.seek(0)
            self._file.truncate()
            self._file.close()  # closing drops the OS lock
            self._file = None

    def __enter__(self) -> "LocalLease":
        return self.acquire()

    def __exit__(self, *exc: object) -> None:
        self.release()
