"""The remote path end to end: agent → gateway → node → phone, over real HTTP and WebSocket (A5.22)."""

import json
import time
from pathlib import Path

import httpx
import pytest

from mphone_backends.remote import RemoteBackend
from mphone_core.clock import VirtualClock
from mphone_core.helpers import Phone
from mphone_protocol import ApprovalRequired, DeviceOffline, LeaseExpired, LeaseRequired, PolicyDenied

from .conftest import Stack

pytestmark = pytest.mark.slow


def lease(stack: Stack, key: str, device: str, purpose: str = "test") -> httpx.Response:
    return stack.http(key).post("/v1/leases", json={"device_id": device, "purpose": purpose})


def remote_phone(
    stack: Stack, key: str, device: str, lease_id: str | None, allow: list[str] | None = None
) -> Phone:
    return Phone(RemoteBackend(device, lease_id, stack.url, key, allow=allow), clock=VirtualClock())


def test_node_registers_its_phones(stack: Stack) -> None:
    key = stack.agent()
    wa = stack.device_id(key, "fake:whatsapp_like")
    device = stack.http(key).get(f"/v1/devices/{wa}").json()
    assert (
        device["state"] == "ready" and "input.tap" in device["ops"] and device["model"] == "Fake Galaxy A54"
    )


def test_drive_a_remote_phone_with_the_same_helpers(stack: Stack, tmp_path: Path) -> None:
    key = stack.agent()
    wa = stack.device_id(key, "fake:whatsapp_like")
    lease_id = lease(stack, key, wa, "Ayşe'ye yanıt").json()["lease_id"]
    p = remote_phone(stack, key, wa, lease_id)
    assert p.ensure_device()["w"] == 1080
    assert p.open_app("WhatsApp") == "com.whatsapp.w4b"
    p.tap_text("ayse yilmaz")
    p.tap_text("Mesaj")
    p.type_text("Siparişiniz yarın kargoda 📦")
    with pytest.raises(ApprovalRequired) as e:
        p.tap_ui({"resource_id": "send"})
    assert e.value.details["rule"] == "outward-send"
    assert not p.find_text("Gönderildi")
    approved = remote_phone(stack, key, wa, lease_id, allow=["outward-send"])
    approved.tap_ui({"resource_id": "send"})
    assert approved.find_text("Gönderildi")
    shot = p.screenshot(str(tmp_path / "remote.png"))
    assert Path(shot).read_bytes().startswith(b"\x89PNG")


def test_one_lease_per_phone(stack: Stack) -> None:
    a, b = stack.agent("a"), stack.agent("b")
    wa = stack.device_id(a, "fake:whatsapp_like")
    assert lease(stack, a, wa).status_code == 201
    conflict = lease(stack, b, wa)
    assert conflict.status_code == 409 and conflict.json()["error"]["code"] == "LEASE_CONFLICT"


def test_ops_need_the_callers_own_lease(stack: Stack) -> None:
    a, b = stack.agent("a"), stack.agent("b")
    wa = stack.device_id(a, "fake:whatsapp_like")
    with pytest.raises(LeaseRequired):
        remote_phone(stack, a, wa, None).tap(1, 1)
    lease_a = lease(stack, a, wa).json()["lease_id"]
    with pytest.raises(LeaseRequired):
        remote_phone(stack, b, wa, lease_a).tap(1, 1)  # someone else's lease
    stack.http(a).delete(f"/v1/leases/{lease_a}")
    with pytest.raises(LeaseExpired):
        remote_phone(stack, a, wa, lease_a).tap(1, 1)  # released


def test_pin_fields_are_refused_remotely_too(stack: Stack) -> None:
    key = stack.agent()
    wa = stack.device_id(key, "fake:whatsapp_like")
    p = remote_phone(stack, key, wa, lease(stack, key, wa).json()["lease_id"], allow=["outward-send"])
    p.open_app("WhatsApp")
    p.tap_ui("Ayarlar")
    pin = p.find_nodes(query="PIN")[0]
    p.tap(pin["x"], pin["y"])
    with pytest.raises(PolicyDenied):
        p.type_text("123456")


def test_audit_records_ops_but_never_typed_text(stack: Stack) -> None:
    key = stack.agent()
    wa = stack.device_id(key, "fake:whatsapp_like")
    p = remote_phone(stack, key, wa, lease(stack, key, wa).json()["lease_id"])
    p.open_app("WhatsApp")
    p.tap_text("Ara")
    p.tap_ui({"resource_id": "search_input"})
    p.type_text("gizli-arama-77")
    rows = stack.http(key).get("/v1/audit", params={"device_id": wa}).json()
    assert {"apps.launch", "input.tap", "input.text"} <= {r["op"] for r in rows}
    assert "gizli-arama-77" not in json.dumps(rows)
    typed = next(r for r in rows if r["op"] == "input.text")
    assert typed["kw"]["s"]["len"] == 14


def test_a_dead_node_is_offline_never_another_phone(stack: Stack) -> None:
    key = stack.agent()
    wa = stack.device_id(key, "fake:whatsapp_like")
    p = remote_phone(stack, key, wa, lease(stack, key, wa).json()["lease_id"])
    p.open_app("WhatsApp")
    stack.node.stop()
    for _ in range(50):
        if httpx.get(f"{stack.url}/healthz").json()["nodes_online"] == 0:
            break
        time.sleep(0.05)
    with pytest.raises(DeviceOffline):
        p.tap(1, 1)
    assert stack.http(key).get(f"/v1/devices/{wa}").json()["state"] == "offline"


def test_tag_restricted_agents_see_nothing_else(stack: Stack) -> None:
    key = stack.agent()
    wa = stack.device_id(key, "fake:whatsapp_like")
    narrow = stack.agent("magaza", allowed_tags=["magaza"])
    assert stack.http(narrow).get("/v1/devices").json() == []
    r = stack.http(narrow).get(f"/v1/devices/{wa}")
    assert r.status_code == 404  # not 403: existence is not revealed


def test_keys_and_enrollment_tokens(stack: Stack) -> None:
    assert (
        httpx.get(f"{stack.url}/v1/devices", headers={"Authorization": "Bearer mph_bad_key"}).status_code
        == 401
    )
    reused = httpx.post(f"{stack.url}/v1/nodes/enroll", json={"token": stack.enrollment_token, "name": "x"})  # type: ignore[attr-defined]
    assert reused.status_code == 401


def test_racing_acquires_have_exactly_one_winner(stack: Stack) -> None:
    from concurrent.futures import ThreadPoolExecutor

    keys = [stack.agent(f"racer{i}") for i in range(20)]
    wa = stack.device_id(keys[0], "fake:whatsapp_like")
    with ThreadPoolExecutor(max_workers=20) as pool:
        codes = list(pool.map(lambda k: lease(stack, k, wa).status_code, keys))
    assert codes.count(201) == 1 and codes.count(409) == 19, codes


def test_bursts_are_rate_limited_and_the_remote_backend_waits(stack: Stack) -> None:
    key = stack.agent()
    wa = stack.device_id(key, "fake:whatsapp_like")
    p = remote_phone(stack, key, wa, lease(stack, key, wa).json()["lease_id"])
    for _ in range(30):  # far over 8 taps/s: every one still succeeds, by waiting
        p.tap(5, 5)
    rows = stack.http(key).get("/v1/audit", params={"device_id": wa, "limit": 200}).json()
    taps = [r for r in rows if r["op"] == "input.tap"]
    assert sum(r["ok"] for r in taps) == 30
    assert any(r["error_code"] == "RATE_LIMITED" for r in taps)  # throttled attempts are audited too
    metrics = httpx.get(f"{stack.url}/metrics").text
    assert 'mphone_op_total{error_code="RATE_LIMITED",ok="false",op="input.tap"}' in metrics
    assert "mphone_nodes_connected 1.0" in metrics
