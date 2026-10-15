"""Connected nodes and in-flight ops (A5.13, Plan.md §8.4.5).

One gateway instance holds each node's WebSocket; an op is a message to the node plus a future
resolved by its response. When a node drops, every op waiting on it fails at once with
DEVICE_OFFLINE — never a hang, never another device (CLAUDE.md §6.2). Multi-instance routing over
Redis comes with A9.03; until then one instance owns all nodes.
"""

import asyncio
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Protocol

from mphone_protocol import DeviceOffline, ErrorInfo, MphoneError, Timeout


class NodeSocket(Protocol):
    async def send_json(self, data: Any) -> None: ...


@dataclass
class NodeConnection:
    node_id: str
    socket: NodeSocket
    pending: dict[str, asyncio.Future[dict[str, Any]]] = field(
        default_factory=dict[str, "asyncio.Future[dict[str, Any]]"]
    )


class Hub:
    def __init__(self) -> None:
        self.nodes: dict[str, NodeConnection] = {}

    def attach(self, node_id: str, socket: NodeSocket) -> NodeConnection:
        old = self.nodes.get(node_id)
        if old is not None:
            self._fail_pending(old, "the node reconnected")
        conn = NodeConnection(node_id, socket)
        self.nodes[node_id] = conn
        return conn

    def detach(self, conn: NodeConnection) -> None:
        if self.nodes.get(conn.node_id) is conn:
            del self.nodes[conn.node_id]
        self._fail_pending(conn, "the node disconnected")

    @staticmethod
    def _fail_pending(conn: NodeConnection, why: str) -> None:
        for future in conn.pending.values():
            if not future.done():
                future.set_exception(
                    DeviceOffline(
                        f"{why} while an op was running",
                        user_action="Node bağlantısını kontrol edin; başka cihaza geçilmedi.",
                    )
                )
        conn.pending.clear()

    def resolve(self, conn: NodeConnection, message: dict[str, Any]) -> None:
        future = conn.pending.pop(str(message.get("req")), None)
        if future is not None and not future.done():
            future.set_result(message)

    def online(self, node_id: str) -> bool:
        return node_id in self.nodes

    async def call(
        self, node_id: str, local_id: str, op: str, kw: dict[str, Any], timeout_s: float
    ) -> tuple[Any, int]:
        """Run an op on a node's phone; returns (result, duration_ms) or raises the protocol error."""
        conn = self.nodes.get(node_id)
        if conn is None:
            raise DeviceOffline(
                "the phone's node is not connected",
                user_action="Node'un çalıştığını ve internete bağlı olduğunu kontrol edin.",
            )
        req = f"req_{uuid.uuid4().hex[:12]}"
        future: asyncio.Future[dict[str, Any]] = asyncio.get_running_loop().create_future()
        conn.pending[req] = future
        start = time.monotonic()
        await conn.socket.send_json(
            {
                "t": "op.request",
                "req": req,
                "local_id": local_id,
                "op": op,
                "kw": kw,
                "deadline_ms": int(timeout_s * 1000),
            }
        )
        try:
            message = await asyncio.wait_for(future, timeout_s)
        except TimeoutError:
            conn.pending.pop(req, None)
            raise Timeout(f"{op} took longer than {timeout_s:g}s on the node") from None
        duration = round((time.monotonic() - start) * 1000)
        if not message.get("ok"):
            raise MphoneError.from_info(
                ErrorInfo.model_validate(
                    message.get("error")
                    or {
                        "code": "INTERNAL",
                        "message": "the node reported a failure without details",
                        "retryable": False,
                    }
                )
            )
        return message.get("result"), duration
