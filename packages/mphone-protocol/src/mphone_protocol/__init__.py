"""Op vocabulary, envelopes and error codes: the single contract every device speaks.

Everything here is generated from schema/ops.v1.json (tools/gen_protocol.py) except this
re-export module and `result_schema()`. Plan.md §7, ADR-0003.
"""

from typing import Any

from ._generated import models
from ._generated.errors import (
    ERROR_CLASSES,
    ERROR_DESCRIPTIONS_TR,
    ApprovalDenied,
    ApprovalRequired,
    DeviceAsleep,
    DeviceLocked,
    DeviceOffline,
    DeviceUnauthorized,
    InternalError,
    InvalidArgument,
    LeaseConflict,
    LeaseExpired,
    LeasePaused,
    LeaseRequired,
    MphoneError,
    NeedsUser,
    NotFound,
    PolicyDenied,
    RateLimited,
    Timeout,
    TreeUnavailable,
    Unsupported,
)
from ._generated.models import (
    Bounds,
    Box,
    Capture,
    DeviceInfo,
    ErrorCode,
    ErrorInfo,
    Node,
    OpRequest,
    OpResult,
    Selector,
)
from ._generated.ops import OP_NAMES, OP_SPECS, PROTOCOL_VERSION, OpSpec, SideEffect
from ._generated.schema import SCHEMA

__version__ = "0.1.0"


def result_schema(op: str) -> dict[str, Any]:
    """A standalone JSON Schema for one op's result, with the shared $defs attached."""
    return {"$schema": SCHEMA["$schema"], "$defs": SCHEMA["$defs"], **OP_SPECS[op].result_schema}


__all__ = [
    "ERROR_CLASSES",
    "ERROR_DESCRIPTIONS_TR",
    "OP_NAMES",
    "OP_SPECS",
    "PROTOCOL_VERSION",
    "SCHEMA",
    "ApprovalDenied",
    "ApprovalRequired",
    "Bounds",
    "Box",
    "Capture",
    "DeviceAsleep",
    "DeviceInfo",
    "DeviceLocked",
    "DeviceOffline",
    "DeviceUnauthorized",
    "ErrorCode",
    "ErrorInfo",
    "InternalError",
    "InvalidArgument",
    "LeaseConflict",
    "LeaseExpired",
    "LeasePaused",
    "LeaseRequired",
    "MphoneError",
    "NeedsUser",
    "Node",
    "NotFound",
    "OpRequest",
    "OpResult",
    "OpSpec",
    "PolicyDenied",
    "RateLimited",
    "Selector",
    "SideEffect",
    "Timeout",
    "TreeUnavailable",
    "Unsupported",
    "models",
    "result_schema",
]
