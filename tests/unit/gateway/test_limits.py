"""Sliding-window rate limits (A5.14)."""

import pytest

from mphone_gateway.limits import SlidingWindow
from mphone_protocol import RateLimited


def test_window_allows_n_per_second_then_says_how_long_to_wait(monkeypatch: pytest.MonkeyPatch) -> None:
    now = [100.0]
    monkeypatch.setattr("time.monotonic", lambda: now[0])
    w = SlidingWindow(3)
    for _ in range(3):
        w.check("agent", "this agent")
    with pytest.raises(RateLimited) as e:
        w.check("agent", "this agent")
    assert e.value.retryable and 0 < e.value.details["retry_after_ms"] <= 1000
    w.check("other", "another agent")  # keys are independent
    now[0] += 1.01
    w.check("agent", "this agent")  # the window slid
