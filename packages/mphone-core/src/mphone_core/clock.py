"""Time as a dependency, so waiting helpers are testable without real sleeps."""

import time
from typing import Protocol


class Clock(Protocol):
    def now(self) -> float: ...

    def sleep(self, seconds: float) -> None: ...


class RealClock:
    def now(self) -> float:
        return time.monotonic()

    def sleep(self, seconds: float) -> None:
        time.sleep(seconds)


class VirtualClock:
    """Sleeping advances time instantly. Use in tests and against the fake backend."""

    def __init__(self, start: float = 0.0) -> None:
        self.t = start
        self.slept = 0.0

    def now(self) -> float:
        return self.t

    def sleep(self, seconds: float) -> None:
        self.t += max(0.0, seconds)
        self.slept += max(0.0, seconds)
