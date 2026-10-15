"""The server as a real subprocess over stdio, the way Claude Code / Milyonus Agent launch it."""

import json
import os
import sys

import pytest
from mcp import Client, StdioServerParameters

pytestmark = [pytest.mark.anyio, pytest.mark.slow]


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


async def test_stdio_round_trip() -> None:
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "mphone_mcp.server"],
        env={**os.environ, "MPHONE_DEVICE": "fake:settings_about"},
    )
    async with Client(params) as c:
        tools = {t.name for t in (await c.list_tools()).tools}
        assert {"phone_acquire", "phone_exec", "phone_screen"} <= tools
        r = await c.call_tool("phone_acquire", {"purpose": "stdio test"})
        lease = json.loads(r.content[0].text)["lease_id"]  # pyright: ignore[reportAttributeAccessIssue]
        r = await c.call_tool("phone_open_app", {"lease_id": lease, "name": "Ayarlar"})
        assert "com.android.settings" in r.content[0].text  # pyright: ignore[reportAttributeAccessIssue]
        await c.call_tool("phone_release", {"lease_id": lease})
