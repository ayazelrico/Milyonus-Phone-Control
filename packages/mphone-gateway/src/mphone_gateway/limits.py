"""Rate limits (A5.14, Plan.md §8.4.5): a sliding one-second window per agent and per device.

An agent stuck in a loop must not hammer a phone. In-process for the single-instance gateway;
moves to Redis with multi-instance routing (A9.03).
"""

import time
from collections import deque

from mphone_protocol import RateLimited


class SlidingWindow:
    def __init__(self, per_second: int) -> None:
        self.per_second = per_second
        self.hits: dict[str, deque[float]] = {}

    def check(self, key: str, what: str) -> None:
        now = time.monotonic()
        window = self.hits.setdefault(key, deque())
        while window and now - window[0] >= 1.0:
            window.popleft()
        if len(window) >= self.per_second:
            retry_ms = max(1, round((1.0 - (now - window[0])) * 1000))
            raise RateLimited(
                f"{what} is over {self.per_second} ops/s",
                details={"retry_after_ms": retry_ms},
                user_action=f"{retry_ms} ms bekleyip tekrar deneyin.",
            )
        window.append(now)
