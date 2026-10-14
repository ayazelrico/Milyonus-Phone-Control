"""Backend dispatch, validation, middleware (A1.04)."""

from typing import Any

import pytest

from mphone_core.transport import Backend, OpCall, TraceMiddleware
from mphone_protocol import OP_NAMES, DeviceLocked, InvalidArgument, Unsupported


class TapOnly(Backend):
    name = "tap-only"

    def __init__(self) -> None:
        super().__init__()
        self.taps: list[tuple[int, int]] = []

    def _input_tap(self, x: int, y: int) -> None:
        self.taps.append((x, y))

    def _input_press(self, x: int, y: int, duration: float) -> float:
        return duration

    def _helper_not_an_op(self) -> None: ...


def test_undefined_slot_is_unsupported() -> None:
    with pytest.raises(Unsupported) as e:
        TapOnly().send("nav.back")
    assert e.value.code == "UNSUPPORTED"
    assert not e.value.retryable


def test_ops_lists_only_vocabulary() -> None:
    b = TapOnly()
    assert b.ops() == ["input.tap", "input.press"]
    assert b.supports("input.tap")
    assert not b.supports("helper.not_an_op")
    assert set(b.ops()) <= set(OP_NAMES)


def test_unknown_op_is_invalid_argument() -> None:
    with pytest.raises(InvalidArgument):
        TapOnly().send("input.teleport")


@pytest.mark.parametrize("kw", [{"x": 1}, {"x": -1, "y": 2}, {"x": 1, "y": 2, "z": 3}, {"x": "a", "y": 2}])
def test_bad_arguments_never_reach_the_slot(kw: dict[str, Any]) -> None:
    b = TapOnly()
    with pytest.raises(InvalidArgument):
        b.send("input.tap", **kw)
    assert b.taps == []


def test_invalid_argument_names_the_field() -> None:
    with pytest.raises(InvalidArgument, match=r"input.tap'?: y: Field required"):
        TapOnly().send("input.tap", x=1)


def test_schema_defaults_are_filled_in() -> None:
    assert TapOnly().send("input.press", x=1, y=2) == 0.8


def test_middleware_order_and_refusal() -> None:
    b = TapOnly()
    seen: list[str] = []

    def outer(call: OpCall, nxt: Any) -> Any:
        seen.append("outer:" + call.op)
        return nxt(call)

    def refuse_taps(call: OpCall, nxt: Any) -> Any:
        seen.append("inner")
        if call.kw["x"] > 100:
            raise DeviceLocked("locked")
        return nxt(call)

    b.use(outer)
    b.use(refuse_taps)
    b.send("input.tap", x=5, y=5)
    with pytest.raises(DeviceLocked):
        b.send("input.tap", x=500, y=5)
    assert seen == ["outer:input.tap", "inner", "outer:input.tap", "inner"]
    assert b.taps == [(5, 5)]


def test_trace_middleware_records_outcomes() -> None:
    b = TapOnly()
    trace = TraceMiddleware(limit=2)
    b.use(trace)
    b.send("input.tap", x=1, y=1)
    with pytest.raises(Unsupported):
        b.send("nav.home")  # unsupported is decided before middlewares run
    b.send("input.tap", x=2, y=2)
    b.send("input.tap", x=3, y=3)
    assert trace.total == 3
    assert len(trace.entries) == 2  # bounded
    assert all(e.ok for e in trace.entries)
