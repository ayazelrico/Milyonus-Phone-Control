"""The node daemon (A5.06–A5.07, Plan.md §8.3): phones on this machine, served to a gateway.

It dials OUT to the gateway (ADR-0004: no inbound port), says hello with its phones, then runs
op requests: one at a time per phone, phones in parallel. It never runs scripts — only protocol
ops — and refuses `raw` unless explicitly allowed. A dropped connection is retried with backoff.
"""

import asyncio
import base64
import contextlib
import json
import logging
import random
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

import websockets

from mphone_core.connect import connect
from mphone_core.transport import Backend
from mphone_protocol import PROTOCOL_VERSION, InternalError, MphoneError, PolicyDenied

from . import __version__

log = logging.getLogger("mphone.node")
Discover = Callable[[], list[str]]


class PhoneSlot:
    def __init__(self, local_id: str, backend: Backend) -> None:
        self.local_id = local_id
        self.backend = backend
        self.lock = asyncio.Lock()  # one op at a time on a phone

    def describe(self) -> dict[str, Any]:
        state = "offline"
        with contextlib.suppress(MphoneError):
            state = self.backend.send("device.state")
        info: dict[str, Any] = {}
        with contextlib.suppress(MphoneError):
            info = self.backend.send("device.info")
        return {
            "local_id": self.local_id,
            "platform": self.backend.platform,
            "model": info.get("model"),
            "os_version": info.get("os_version"),
            "state": state,
            "transport": None,
            "ops": self.backend.ops(),
        }


class NodeDaemon:
    def __init__(
        self,
        gateway: str,
        node_id: str,
        secret: str,
        devices: Discover,
        allow_raw: bool = False,
        rediscover_s: float = 5.0,
    ) -> None:
        self.url = (
            gateway.rstrip("/").replace("http://", "ws://").replace("https://", "wss://")
            + f"/v1/nodes/connect?node_id={node_id}"
        )
        self.secret = secret
        self.discover = devices
        self.allow_raw = allow_raw
        self.rediscover_s = rediscover_s
        self.slots: dict[str, PhoneSlot] = {}
        self.stopping = asyncio.Event()

    def _refresh(self) -> tuple[list[dict[str, Any]], list[str]]:
        wanted = set(self.discover())
        gone = [lid for lid in self.slots if lid not in wanted]
        for lid in gone:
            self.slots.pop(lid).backend.close()
        for lid in wanted - set(self.slots):
            try:
                self.slots[lid] = PhoneSlot(lid, connect(lid))
            except MphoneError as e:
                log.warning("cannot open %s: %s", lid, e)
        return [slot.describe() for slot in self.slots.values()], gone

    async def _run_op(self, ws: Any, msg: dict[str, Any]) -> None:
        reply: dict[str, Any] = {"t": "op.response", "req": msg["req"]}
        start = time.monotonic()
        slot = self.slots.get(msg["local_id"])
        try:
            if slot is None:
                raise InternalError(f"this node has no phone {msg['local_id']!r}")
            if msg["op"] == "raw" and not self.allow_raw:
                raise PolicyDenied("this node does not run raw commands (node.allow_raw=false)")
            kw = dict(msg.get("kw") or {})
            if msg["op"] == "screen.capture":
                kw["path"] = None  # a path on this machine means nothing to the caller
            async with slot.lock:
                result = await asyncio.to_thread(slot.backend.send, msg["op"], **kw)
            if msg["op"] == "screen.capture" and isinstance(result, dict) and result.get("path"):
                path = Path(str(result["path"]))  # pyright: ignore[reportUnknownArgumentType]
                result = {**result, "path": None, "data_b64": base64.b64encode(path.read_bytes()).decode()}
                path.unlink(missing_ok=True)
            reply.update(ok=True, result=result)
        except MphoneError as e:
            reply.update(ok=False, error=e.to_info().model_dump())
        except Exception as e:  # the node reports, it never dies on one op
            reply.update(
                ok=False,
                error={"code": "INTERNAL", "message": f"{type(e).__name__}: {e}", "retryable": False},
            )
        reply["duration_ms"] = round((time.monotonic() - start) * 1000)
        await ws.send(json.dumps(reply, default=str))

    async def _session(self) -> None:
        async with websockets.connect(
            self.url, additional_headers={"Authorization": f"Bearer {self.secret}"}, max_size=64 * 1024 * 1024
        ) as ws:
            devices, _ = await asyncio.to_thread(self._refresh)
            await ws.send(
                json.dumps(
                    {"t": "hello", "version": __version__, "protocol": PROTOCOL_VERSION, "devices": devices}
                )
            )
            known = {d["local_id"] for d in devices}

            async def watch() -> None:
                nonlocal known
                while True:
                    await asyncio.sleep(self.rediscover_s)
                    current, gone = await asyncio.to_thread(self._refresh)
                    for lid in gone:
                        await ws.send(json.dumps({"t": "device.gone", "local_id": lid}))
                    for d in current:
                        if d["local_id"] not in known:
                            await ws.send(json.dumps({"t": "device.update", "device": d}))
                    known = {d["local_id"] for d in current}

            watcher = asyncio.create_task(watch())
            tasks: set[asyncio.Task[None]] = set()
            try:
                async for raw in ws:
                    msg = json.loads(raw)
                    if msg.get("t") == "op.request":
                        task = asyncio.create_task(self._run_op(ws, msg))
                        tasks.add(task)
                        task.add_done_callback(tasks.discard)
            finally:
                watcher.cancel()

    async def run(self) -> None:
        delay = 1.0
        while not self.stopping.is_set():
            try:
                await self._session()
                delay = 1.0
            except (OSError, websockets.WebSocketException) as e:
                log.warning("gateway connection lost (%s); retrying in %.0fs", e, delay)
            if self.stopping.is_set():
                break
            await asyncio.sleep(delay + random.uniform(0, delay / 2))  # noqa: S311 — jitter, not crypto
            delay = min(delay * 2, 30.0)
