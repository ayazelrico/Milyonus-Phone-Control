"""The one seam every device sits behind (A1.04, Plan.md §8.1.1).

A backend implements ops as methods named after them: "input.tap" → `_input_tap`,
"screen.stream.start" → `_screen_stream_start`. It defines only the ops it can honour; every
other op is `Unsupported` automatically, so no capability list is ever kept in sync by hand.

`send()` validates the arguments against the generated schema model and passes the slot the
FULL argument set, defaults included. Defaults therefore live in exactly one place (the schema),
and every slot signature must name every schema argument — the contract test checks that.

Middlewares wrap the slot call (trace, audit, policy, rate limit). Each receives the call and a
`next` callable, and may inspect, refuse, or time it.
"""

import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, ClassVar, Literal

from pydantic import ValidationError

from mphone_protocol import OP_NAMES, OP_SPECS, PROTOCOL_VERSION, InvalidArgument, MphoneError, Unsupported

Platform = Literal["android", "ios", "fake"]


@dataclass
class OpCall:
    """One op on its way to a slot. `meta` carries task/step/trace for middlewares."""

    op: str
    kw: dict[str, Any]
    backend: "Backend"
    meta: dict[str, Any] = field(default_factory=dict[str, Any])


Next = Callable[[OpCall], Any]
Middleware = Callable[[OpCall, Next], Any]


def slot_name(op: str) -> str:
    return "_" + op.replace(".", "_")


class Backend:
    """Base of every device backend. Subclasses set `name` and `platform` and define slots."""

    name: ClassVar[str] = "backend"
    platform: ClassVar[Platform] = "fake"
    protocol_version: ClassVar[str] = PROTOCOL_VERSION

    def __init__(self) -> None:
        self.middlewares: list[Middleware] = []

    # --- capabilities -------------------------------------------------------

    def supports(self, op: str) -> bool:
        return op in OP_SPECS and callable(getattr(self, slot_name(op), None))

    def ops(self) -> list[str]:
        """Every op this backend implements, in vocabulary order. Internal helpers that happen
        to start with an underscore can never masquerade as ops."""
        return [op for op in OP_NAMES if self.supports(op)]

    # --- dispatch -----------------------------------------------------------

    def send(self, op: str, /, **kw: Any) -> Any:
        spec = OP_SPECS.get(op)
        if spec is None:
            raise InvalidArgument(f"unknown op {op!r}", details={"known": list(OP_NAMES)})
        if not self.supports(op):
            raise Unsupported(f"{self.name} cannot {op!r}", details={"op": op, "backend": self.name})
        try:
            args = spec.args_model.model_validate(kw)
        except ValidationError as e:
            first = e.errors()[0]
            where = ".".join(str(part) for part in first["loc"]) or "(arguments)"
            raise InvalidArgument(
                f"bad arguments for {op!r}: {where}: {first['msg']}"
                + (f" (+{e.error_count() - 1} more)" if e.error_count() > 1 else ""),
                details={"errors": e.errors(include_url=False, include_context=False)},
            ) from None
        # by_alias: nested models (Selector) keep wire names such as "class".
        call = OpCall(op=op, kw=args.model_dump(by_alias=True), backend=self)
        return self._chain(0)(call)

    def _chain(self, index: int) -> Next:
        if index == len(self.middlewares):
            return self._invoke
        middleware = self.middlewares[index]
        nxt = self._chain(index + 1)
        return lambda call: middleware(call, nxt)

    def _invoke(self, call: OpCall) -> Any:
        return getattr(self, slot_name(call.op))(**call.kw)

    def use(self, middleware: Middleware) -> None:
        """Append a middleware; the first added is the outermost."""
        self.middlewares.append(middleware)

    # --- lifecycle ----------------------------------------------------------

    def close(self) -> None:
        """Release whatever the backend holds (subprocesses, sockets). Idempotent."""

    def __enter__(self) -> "Backend":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()


@dataclass
class TraceEntry:
    op: str
    duration_ms: int
    ok: bool
    error_code: str | None = None
    error: str | None = None


class TraceMiddleware:
    """Records every op, its duration and outcome. Kept bounded so a long run cannot grow it
    without limit (the reference harness capped its helper trace the same way)."""

    def __init__(self, limit: int = 500) -> None:
        self.limit = limit
        self.entries: list[TraceEntry] = []
        self.total = 0

    def __call__(self, call: OpCall, nxt: Next) -> Any:
        self.total += 1
        start = time.monotonic()
        entry = TraceEntry(op=call.op, duration_ms=0, ok=True)
        try:
            return nxt(call)
        except MphoneError as e:
            entry.ok, entry.error_code, entry.error = False, e.code, e.message[:300]
            raise
        except Exception as e:
            entry.ok, entry.error_code, entry.error = False, "INTERNAL", str(e)[:300]
            raise
        finally:
            entry.duration_ms = round((time.monotonic() - start) * 1000)
            if len(self.entries) < self.limit:
                self.entries.append(entry)
