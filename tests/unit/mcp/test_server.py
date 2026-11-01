"""The MCP server as an agent uses it (A3.05), against fake phones, in-process."""

import json
from collections.abc import AsyncIterator
from typing import Any

import pytest
from mcp import Client

from mphone_mcp.server import SCREEN_LABEL, State, build_server

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
async def client() -> AsyncIterator[tuple[Client, State]]:
    state = State()
    async with Client(build_server(state)) as c:
        yield c, state
    state.release_all()


def text(result: Any) -> str:
    return "\n".join(getattr(part, "text", "") for part in result.content)


async def acquire(c: Client, device: str = "fake:whatsapp_like") -> str:
    r = await c.call_tool("phone_acquire", {"purpose": "test", "device": device})
    assert not r.is_error, text(r)
    return json.loads(text(r))["lease_id"]


async def test_lists_tools_with_consent_rules(client: tuple[Client, State]) -> None:
    c, _ = client
    tools = {t.name: t for t in (await c.list_tools()).tools}
    assert len(tools) == 15
    for name in ("phone_exec", "phone_tap", "phone_type"):
        assert "PIN" in (tools[name].description or "") and "allow" in (tools[name].description or "")


async def test_device_list_includes_fake_phones(client: tuple[Client, State]) -> None:
    c, _ = client
    data = json.loads(text(await c.call_tool("phone_list_devices", {})))
    assert "fake:whatsapp_like" in data["fake"]


async def test_agent_flow_with_approval(client: tuple[Client, State]) -> None:
    c, _ = client
    lease = await acquire(c)
    r = await c.call_tool("phone_open_app", {"lease_id": lease, "name": "WhatsApp"})
    assert "com.whatsapp.w4b" in text(r)
    screen = text(await c.call_tool("phone_screen", {"lease_id": lease}))
    assert screen.startswith(SCREEN_LABEL) and "'Ayşe Yılmaz'" in screen
    await c.call_tool("phone_tap", {"lease_id": lease, "text": "ayse yilmaz"})
    await c.call_tool("phone_tap", {"lease_id": lease, "text": "Mesaj"})
    r = await c.call_tool("phone_type", {"lease_id": lease, "text": "Siparişiniz yarın kargoda 📦"})
    assert not r.is_error and "27 karakter" in text(r)

    send = next(
        line
        for line in text(await c.call_tool("phone_screen", {"lease_id": lease})).splitlines()
        if "Gönder" in line
    )
    x, y = (int(v) for v in send.split("@ (")[1].split(")")[0].split(","))
    blocked = await c.call_tool("phone_tap", {"lease_id": lease, "x": x, "y": y})
    assert blocked.is_error and "APPROVAL_REQUIRED" in text(blocked) and "outward-send" in text(blocked)
    assert "Gönderildi" not in text(await c.call_tool("phone_screen", {"lease_id": lease}))

    ok = await c.call_tool("phone_tap", {"lease_id": lease, "x": x, "y": y, "allow": ["outward-send"]})
    assert not ok.is_error
    assert "görünüyor" in text(await c.call_tool("phone_wait_for", {"lease_id": lease, "text": "Gönderildi"}))
    # the approval was for that one call only
    again = await c.call_tool("phone_tap", {"lease_id": lease, "x": x, "y": y})
    assert again.is_error or "Gönderildi" in text(await c.call_tool("phone_screen", {"lease_id": lease}))
    assert not (await c.call_tool("phone_release", {"lease_id": lease})).is_error


async def test_errors_tell_the_agent_what_to_do(client: tuple[Client, State]) -> None:
    c, _ = client
    lease = await acquire(c)
    r = await c.call_tool("phone_tap", {"lease_id": lease, "text": "Bluetooth"})
    assert r.is_error and "NOT_FOUND" in text(r) and "görünen:" in text(r)
    locked = await c.call_tool("phone_acquire", {"purpose": "x", "device": "fake:locked_phone"})
    assert locked.is_error and "DEVICE_LOCKED" in text(locked) and "PIN" in text(locked)
    missing = await c.call_tool("phone_screen", {"lease_id": "lse_nope"})
    assert missing.is_error and "LEASE_REQUIRED" in text(missing)


async def test_one_phone_one_lease(client: tuple[Client, State]) -> None:
    c, _ = client
    await acquire(c)
    second = await c.call_tool("phone_acquire", {"purpose": "ikinci görev", "device": "fake:whatsapp_like"})
    assert second.is_error and "LEASE_CONFLICT" in text(second)


async def test_exec_returns_output_and_screenshots(client: tuple[Client, State]) -> None:
    c, _ = client
    lease = await acquire(c, "fake:settings_about")
    code = "# task: sürüm\n# step: oku\nopen_app('Ayarlar'); print(current_app()); screenshot()"
    r = await c.call_tool("phone_exec", {"lease_id": lease, "code": code})
    assert not r.is_error, text(r)
    assert "exit_code=0" in text(r) and "com.android.settings" in text(r)
    images = [p for p in r.content if getattr(p, "type", "") == "image"]
    assert len(images) == 1 and getattr(images[0], "mime_type", None) == "image/jpeg"


async def test_exec_failure_is_an_error_with_the_reason(client: tuple[Client, State]) -> None:
    c, _ = client
    lease = await acquire(c)
    code = "# task: t\n# step: s\nopen_app('WhatsApp'); tap_ui('Ayarlar')\nb = find_nodes(query='PIN')[0]; tap(b['x'], b['y']); type_text('123456')"
    r = await c.call_tool("phone_exec", {"lease_id": lease, "code": code})
    assert r.is_error and "POLICY_DENIED" in text(r) and "exit_code=3" in text(r)


async def test_screenshot_is_a_jpeg(client: tuple[Client, State]) -> None:
    c, _ = client
    lease = await acquire(c)
    r = await c.call_tool("phone_screenshot", {"lease_id": lease, "max_side": 800})
    assert "1080x2400" in text(r)
    assert [getattr(p, "mime_type", None) for p in r.content if getattr(p, "type", "") == "image"] == [
        "image/jpeg"
    ]


async def test_resources_and_prompt(client: tuple[Client, State]) -> None:
    c, _ = client
    skill = await c.read_resource("mphone://skill")
    assert "Rıza" in skill.contents[0].text  # pyright: ignore[reportAttributeAccessIssue]
    proto = await c.read_resource("mphone://protocol")
    assert "input.tap" in json.loads(proto.contents[0].text)["x-ops"]  # pyright: ignore[reportAttributeAccessIssue]
    prompt = await c.get_prompt("phone_task", {"task": "Ayarlar'dan Android sürümünü oku"})
    assert "Android sürümünü oku" in prompt.messages[0].content.text  # pyright: ignore[reportAttributeAccessIssue]
