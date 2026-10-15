"""Milyonus Agent's view of a remote phone: the same MCP tools, through the gateway (A5.19)."""

import json
import os
from collections.abc import Iterator
from typing import Any

import pytest
from mcp import Client

from mphone_mcp.server import Gateway, State, build_server

from .conftest import Stack

pytestmark = [pytest.mark.anyio, pytest.mark.slow]


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


def text(result: Any) -> str:
    return "\n".join(getattr(p, "text", "") for p in result.content)


@pytest.fixture
def remote(stack: Stack) -> Iterator[tuple[Stack, str, str]]:
    key = stack.agent("milyonus-agent")
    stack.other_key = stack.agent("other")  # type: ignore[attr-defined]  # made here: tests below run inside an event loop
    yield stack, key, stack.device_id(key, "fake:whatsapp_like")


async def test_remote_phone_through_mcp(
    remote: tuple[Stack, str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    stack, key, wa = remote
    monkeypatch.setenv("MILYONUS_API_KEY", "sk-agent-secret")  # must never reach a script
    state = State(Gateway(stack.url, key))
    async with Client(build_server(state)) as c:
        listed = json.loads(text(await c.call_tool("phone_list_devices", {})))
        assert f"gw://{wa}" in {d["uri"] for d in listed["remote"]}
        r = await c.call_tool("phone_acquire", {"purpose": "uzak test", "device": f"gw://{wa}"})
        assert not r.is_error, text(r)
        lease = json.loads(text(r))["lease_id"]
        assert "com.whatsapp.w4b" in text(
            await c.call_tool("phone_open_app", {"lease_id": lease, "name": "WhatsApp"})
        )
        await c.call_tool("phone_tap", {"lease_id": lease, "text": "Ayşe Yılmaz"})
        await c.call_tool("phone_tap", {"lease_id": lease, "text": "Mesaj"})
        assert not (await c.call_tool("phone_type", {"lease_id": lease, "text": "Yarın kargoda"})).is_error
        blocked = await c.call_tool("phone_tap", {"lease_id": lease, "text": "Gönder"})
        assert blocked.is_error and "APPROVAL_REQUIRED" in text(blocked)
        ok = await c.call_tool("phone_tap", {"lease_id": lease, "text": "Gönder", "allow": ["outward-send"]})
        assert not ok.is_error, text(ok)

        code = (
            "# task: t\n# step: s\nimport os\nprint(current_app())\n"
            "print(sorted(k for k in os.environ if 'KEY' in k or 'CREDENTIAL' in k))"
        )
        r = await c.call_tool("phone_exec", {"lease_id": lease, "code": code})
        assert not r.is_error, text(r)
        assert "com.whatsapp.w4b" in text(r)
        assert (
            "MPHONE_LEASE_CREDENTIAL" in text(r)
            and "MILYONUS_API_KEY" not in text(r)
            and "MPHONE_API_KEY" not in text(r)
        )

        released = await c.call_tool("phone_release", {"lease_id": lease})
        assert not released.is_error
    # released at the gateway too: another agent can now take the phone
    other = stack.other_key  # type: ignore[attr-defined]
    assert stack.http(other).post("/v1/leases", json={"device_id": wa}).status_code == 201


def test_lease_credentials_cannot_cross_leases(remote: tuple[Stack, str, str]) -> None:
    stack, key, wa = remote
    st = stack.device_id(key, "fake:settings_about")
    lease_wa = stack.http(key).post("/v1/leases", json={"device_id": wa}).json()["lease_id"]
    lease_st = stack.http(key).post("/v1/leases", json={"device_id": st}).json()["lease_id"]
    cred = stack.http(key).post(f"/v1/leases/{lease_wa}/credential").json()["credential"]
    scoped = stack.http(cred)
    ok = scoped.post(f"/v1/devices/{wa}/ops", json={"op": "device.state", "lease_id": lease_wa})
    assert ok.status_code == 200 and ok.json()["ok"]
    assert (
        scoped.post(f"/v1/devices/{st}/ops", json={"op": "device.state", "lease_id": lease_st}).status_code
        == 403
    )
    assert scoped.post("/v1/leases", json={"device_id": st}).status_code == 403  # no leases:write scope
    assert scoped.post(f"/v1/leases/{lease_wa}/credential").status_code == 403
    os.environ.pop("MPHONE_LEASE_CREDENTIAL", None)
