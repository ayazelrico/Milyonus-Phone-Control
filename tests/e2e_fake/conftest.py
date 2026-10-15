"""A real gateway (uvicorn + SQLite) and a real node daemon (WebSocket) in background threads,
serving fake phones. No Docker: the full remote path over real HTTP and WebSocket (A5.22)."""

import asyncio
import contextlib
import socket
import threading
import time
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

import httpx
import pytest
import uvicorn

from mphone_gateway import auth
from mphone_gateway.app import create_app
from mphone_gateway.db import Database
from mphone_gateway.settings import Settings
from mphone_node.node import NodeDaemon

DEVICES = ["fake:whatsapp_like", "fake:settings_about"]


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class NodeThread:
    def __init__(self, url: str, node_id: str, secret: str) -> None:
        self.loop = asyncio.new_event_loop()
        self.daemon = NodeDaemon(url, node_id, secret, devices=lambda: list(DEVICES), rediscover_s=0.5)
        self.thread = threading.Thread(target=self._run, daemon=True)

    def _run(self) -> None:
        asyncio.set_event_loop(self.loop)
        self.task = self.loop.create_task(self.daemon.run())
        with contextlib.suppress(asyncio.CancelledError):
            self.loop.run_until_complete(self.task)

    def start(self) -> None:
        self.thread.start()

    def stop(self) -> None:
        def cancel() -> None:
            self.daemon.stopping.set()
            self.task.cancel()

        self.loop.call_soon_threadsafe(cancel)
        self.thread.join(timeout=10)


@dataclass
class Stack:
    url: str
    db_url: str
    node: NodeThread

    def admin(self, coro_fn):  # type: ignore[no-untyped-def]
        async def run():  # type: ignore[no-untyped-def]
            db = Database(self.db_url)
            async with db.sessions() as s:
                out = await coro_fn(s)
            await db.dispose()
            return out

        return asyncio.run(run())

    def agent(self, name: str = "agent", **kw) -> str:  # type: ignore[no-untyped-def]
        return self.admin(lambda s: auth.create_agent(s, name, **kw))[1]

    def http(self, key: str) -> httpx.Client:
        return httpx.Client(base_url=self.url, headers={"Authorization": f"Bearer {key}"}, timeout=60)

    def device_id(self, key: str, local: str) -> str:
        for _ in range(100):
            devices = self.http(key).get("/v1/devices").json()
            found = [d for d in devices if d["state"] != "offline" and d.get("model")]
            if len(found) >= len(DEVICES):
                break
            time.sleep(0.1)
        r = self.admin(_device_by_local(local))
        assert r, f"node never registered {local}"
        return r


def _device_by_local(local: str):  # type: ignore[no-untyped-def]
    from sqlalchemy import select

    from mphone_gateway.db import Device

    async def find(s):  # type: ignore[no-untyped-def]
        row = (await s.execute(select(Device).where(Device.local_id == local))).scalar_one_or_none()
        return row.id if row else None

    return find


@pytest.fixture
def stack(tmp_path: Path) -> Iterator[Stack]:
    db_url = f"sqlite+aiosqlite:///{tmp_path / 'gw.db'}"
    port = free_port()
    server = uvicorn.Server(
        uvicorn.Config(
            create_app(Settings(database_url=db_url, op_timeout_s=20)),
            host="127.0.0.1",
            port=port,
            log_level="warning",
            ws="websockets-sansio",
        )
    )
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    url = f"http://127.0.0.1:{port}"
    for _ in range(100):
        try:
            if httpx.get(f"{url}/healthz").status_code == 200:
                break
        except httpx.HTTPError:
            time.sleep(0.05)
    token = Stack(url, db_url, None).admin(lambda s: auth.create_enrollment_token(s))  # type: ignore[arg-type]
    enrolled = httpx.post(f"{url}/v1/nodes/enroll", json={"token": token, "name": "raf-1"}).json()
    node = NodeThread(url, enrolled["node_id"], enrolled["node_secret"])
    node.start()
    st = Stack(url, db_url, node)
    st.enrollment_token = token  # type: ignore[attr-defined]
    for _ in range(100):
        if httpx.get(f"{url}/healthz").json()["nodes_online"] == 1:
            break
        time.sleep(0.05)
    yield st
    node.stop()
    server.should_exit = True
    thread.join(timeout=10)
