# pyright: reportInvalidTypeForm=false
# FastAPI dependency aliases (Annotated[..., Depends(...)]) are built inside create_app at runtime.
"""The gateway (P5, Plan.md §8.4): REST for agents, a WebSocket for nodes.

Op pipeline (§8.4.5): API key + scope → lease → schema/support → policy → node → audit. Agent
errors come back as protocol ErrorInfo; an op's own failure is an OpResult with ok=false, so the
remote backend can raise exactly the error a local backend would have.
"""

import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated, Any, cast

from fastapi import Depends, FastAPI, Header, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from mphone_core.audit import mask
from mphone_core.policy import Policy, evaluate
from mphone_core.transport import OpCall
from mphone_protocol import (
    OP_SPECS,
    ApprovalRequired,
    InvalidArgument,
    MphoneError,
    NotFound,
    PolicyDenied,
    Unsupported,
    models,
)

from . import auth, leases
from .db import Agent, Database, Device, Lease, Node, OpLog, now
from .hub import Hub
from .limits import SlidingWindow
from .metrics import Metrics
from .settings import Settings

POLICED = {
    "input.tap",
    "input.press",
    "input.text",
    "input.keys",
    "input.drag",
    "input.scroll",
    "input.clear",
    "raw",
    "apps.launch",
    "apps.install",
    "apps.uninstall",
    "files.push",
}
STATUS = {
    "UNSUPPORTED": 422,
    "INVALID_ARGUMENT": 422,
    "NOT_FOUND": 404,
    "LEASE_REQUIRED": 409,
    "LEASE_CONFLICT": 409,
    "LEASE_EXPIRED": 409,
    "POLICY_DENIED": 403,
    "DEVICE_OFFLINE": 503,
    "TIMEOUT": 504,
}


class LeaseIn(BaseModel):
    device_id: str
    purpose: str = ""
    ttl_s: int | None = None


class HeartbeatIn(BaseModel):
    ttl_s: int | None = None


class OpIn(BaseModel):
    op: str
    kw: dict[str, Any] = {}
    lease_id: str | None = None
    allow: list[str] = []  # rules the agent's USER explicitly approved (same contract as --allow)


class EnrollIn(BaseModel):
    token: str
    name: str


def create_app(settings: Settings | None = None, policy: Policy | None = None) -> FastAPI:
    settings = settings or Settings()
    db = Database(settings.db_url())
    hub = Hub()
    active_policy = policy or Policy.load()
    metrics = Metrics()
    agent_limit = SlidingWindow(settings.agent_ops_per_second)
    device_limit = SlidingWindow(settings.device_ops_per_second)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        if settings.auto_create_schema:
            await db.create_all()
        else:
            await db.seed()  # schema comes from `mphone-gateway migrate`
        yield
        await db.dispose()

    app = FastAPI(title="mphone gateway", version="0.1.0", lifespan=lifespan)
    app.state.db, app.state.hub, app.state.settings, app.state.metrics = db, hub, settings, metrics

    @app.exception_handler(MphoneError)
    async def protocol_error(request: Request, e: MphoneError) -> JSONResponse:
        return JSONResponse({"error": e.to_info().model_dump()}, status_code=STATUS.get(e.code, 400))

    Session = Annotated[AsyncSession, Depends(db.session)]

    def scoped(scope: str) -> Any:
        async def dependency(s: Session, authorization: Annotated[str | None, Header()] = None) -> Agent:
            token = (authorization or "").removeprefix("Bearer ").strip()
            found = await auth.verify_key(s, token) if token else None
            if found is None:
                raise HTTPException(401, "invalid or missing API key")
            agent, key = found
            if scope not in key.scopes:
                raise HTTPException(403, f"this key lacks the {scope!r} scope")
            agent.key_lease_id = key.lease_id  # pyright: ignore[reportAttributeAccessIssue]
            return agent

        return Depends(dependency)

    ReadAgent = Annotated[Agent, scoped("devices:read")]
    LeaseAgent = Annotated[Agent, scoped("leases:write")]
    OpsAgent = Annotated[Agent, scoped("ops:write")]
    AuditAgent = Annotated[Agent, scoped("audit:read")]

    async def visible_device(s: AsyncSession, agent: Agent, device_id: str) -> Device:
        device = await s.get(Device, device_id)
        # Another org's device, or one outside the agent's tags, is indistinguishable from none (IDOR).
        if (
            device is None
            or device.org_id != agent.org_id
            or (agent.allowed_tags and not set(agent.allowed_tags) & set(device.tags))
        ):
            raise NotFound(f"no device {device_id}")
        return device

    def device_view(d: Device) -> dict[str, Any]:
        return {
            "id": d.id,
            "platform": d.platform,
            "model": d.model,
            "os_version": d.os_version,
            "label": d.label,
            "tags": d.tags,
            "state": d.state if hub.online(d.node_id) else "offline",
            "ops": d.ops,
        }

    # --- health ---------------------------------------------------------------------------------

    @app.get("/metrics")
    async def prometheus() -> Response:
        metrics.nodes.set(len(hub.nodes))
        return Response(metrics.render(), media_type="text/plain; version=0.0.4")

    @app.get("/healthz")
    async def healthz() -> dict[str, Any]:
        return {"ok": True, "nodes_online": len(hub.nodes)}

    # --- devices and leases ---------------------------------------------------------------------

    @app.get("/v1/devices")
    async def list_devices(s: Session, agent: ReadAgent) -> list[dict[str, Any]]:
        rows = (await s.execute(select(Device).where(Device.org_id == agent.org_id))).scalars().all()
        return [
            device_view(d) for d in rows if not agent.allowed_tags or set(agent.allowed_tags) & set(d.tags)
        ]

    @app.get("/v1/devices/{device_id}")
    async def get_device(device_id: str, s: Session, agent: ReadAgent) -> dict[str, Any]:
        return device_view(await visible_device(s, agent, device_id))

    @app.post("/v1/leases", status_code=201)
    async def create_lease(body: LeaseIn, s: Session, agent: LeaseAgent) -> dict[str, Any]:
        device = await visible_device(s, agent, body.device_id)
        ttl = min(body.ttl_s or settings.lease_default_ttl_s, settings.lease_max_ttl_s)
        try:
            lease = await leases.acquire(s, agent, device, ttl, body.purpose)
        except MphoneError:
            metrics.leases.labels("conflict").inc()
            raise
        metrics.leases.labels("acquired").inc()
        return {"lease_id": lease.id, "device_id": device.id, "expires_at": lease.expires_at.isoformat()}

    @app.post("/v1/leases/{lease_id}/heartbeat")
    async def heartbeat(lease_id: str, body: HeartbeatIn, s: Session, agent: LeaseAgent) -> dict[str, Any]:
        lease = await s.get(Lease, lease_id)
        if lease is None or lease.agent_id != agent.id:
            raise NotFound(f"no lease {lease_id}")
        lease = await leases.require(s, lease_id, agent, lease.device_id)
        lease = await leases.heartbeat(s, lease, body.ttl_s)
        return {"lease_id": lease.id, "expires_at": lease.expires_at.isoformat()}

    @app.post("/v1/leases/{lease_id}/credential", status_code=201)
    async def lease_credential(lease_id: str, s: Session, agent: LeaseAgent) -> dict[str, str]:
        """A credential for scripts: ops on this lease only (the agent's own key never enters a script)."""
        lease = await s.get(Lease, lease_id)
        if lease is None or lease.agent_id != agent.id or getattr(agent, "key_lease_id", None):
            raise NotFound(f"no lease {lease_id}")
        await leases.require(s, lease_id, agent, lease.device_id)
        return {"credential": await auth.create_lease_credential(s, agent.id, lease_id)}

    @app.delete("/v1/leases/{lease_id}")
    async def release_lease(lease_id: str, s: Session, agent: LeaseAgent) -> dict[str, Any]:
        lease = await s.get(Lease, lease_id)
        if lease is None or lease.agent_id != agent.id:
            raise NotFound(f"no lease {lease_id}")
        await leases.release(s, lease)
        return {"lease_id": lease_id, "status": lease.status}

    # --- ops --------------------------------------------------------------------------------------

    @app.post("/v1/devices/{device_id}/ops")
    async def run_op(device_id: str, body: OpIn, s: Session, agent: OpsAgent) -> dict[str, Any]:
        start = time.monotonic()
        device = await visible_device(s, agent, device_id)
        bound = getattr(agent, "key_lease_id", None)
        if bound is not None and bound != body.lease_id:
            raise HTTPException(403, "this credential is bound to another lease")
        lease = await leases.require(s, body.lease_id, agent, device.id)
        rule: str | None = None
        result: Any = None
        error: MphoneError | None = None
        kw: dict[str, Any] = body.kw
        try:
            spec = OP_SPECS.get(body.op)
            if spec is None:
                raise InvalidArgument(f"unknown op {body.op!r}")
            if body.op not in device.ops:
                raise Unsupported(f"{device.id} cannot {body.op!r}")
            if spec.side_effect != "none":  # reads are harmless; only acting on the phone is limited
                agent_limit.check(agent.id, "this agent")
                device_limit.check(device.id, "this device")
            try:
                kw = spec.args_model.model_validate(body.kw).model_dump(by_alias=True)
            except ValidationError as e:
                raise InvalidArgument(f"bad arguments for {body.op!r}: {e.errors()[0]['msg']}") from None
            if body.op in POLICED:
                rule = await police(device, body.op, kw, agent, set(body.allow))
            result, _ = await hub.call(device.node_id, device.local_id, body.op, kw, settings.op_timeout_s)
        except MphoneError as e:
            error = e
        s.add(
            OpLog(
                org_id=agent.org_id,
                device_id=device.id,
                lease_id=lease.id,
                agent_id=agent.id,
                op=body.op,
                kw=mask(body.op, kw),
                ok=error is None,
                error_code=error.code if error else None,
                policy_rule=rule,
                duration_ms=round((time.monotonic() - start) * 1000),
            )
        )
        await s.commit()
        metrics.ops.labels(body.op, str(error is None).lower(), error.code if error else "").inc()
        metrics.op_seconds.labels(body.op).observe(time.monotonic() - start)
        if error is not None:
            return {"ok": False, "error": error.to_info().model_dump()}
        return {"ok": True, "result": result}

    async def police(
        device: Device, op: str, kw: dict[str, Any], agent: Agent, allowed: set[str]
    ) -> str | None:
        """The same policy engine as local mode; screen and app facts are read through the node."""
        cache: dict[str, Any] = {}

        def read(fact_op: str) -> Any:
            if fact_op not in cache:
                raise KeyError(fact_op)
            return cache[fact_op]

        call = OpCall(op=op, kw=kw, backend=cast(Any, None))
        # Facts are async here: prefetch what rules may ask (cheap ops; the screen only when needed).
        cache["apps.current"] = (
            await hub.call(device.node_id, device.local_id, "apps.current", {}, settings.op_timeout_s)
        )[0]
        if op in ("input.tap", "input.press", "input.text", "input.keys"):
            cache["screen.text"] = (
                await hub.call(
                    device.node_id,
                    device.local_id,
                    "screen.text",
                    {"min_confidence": 0.3},
                    settings.op_timeout_s,
                )
            )[0]
        decision = evaluate(active_policy, call, read, mode="remote", trust_level=agent.trust_level)
        rule = decision.rule.id if decision.rule else None
        metrics.policy.labels(rule or "", decision.decision).inc()
        details = {"rule": rule, "op": op, "target": (decision.target or {}).get("text")}
        if decision.decision == "deny":
            raise PolicyDenied(decision.message, details=details)
        if decision.decision == "approve" and rule not in allowed:
            raise ApprovalRequired(
                f"{decision.message} (kural: {rule})",
                user_action=f"Kullanıcıya sorun; onaylarsa isteği allow=[{rule!r}] ile yeniden gönderin.",
                details=details,
            )
        return rule

    # --- audit ------------------------------------------------------------------------------------

    @app.get("/v1/audit")
    async def audit(
        s: Session, agent: AuditAgent, device_id: str | None = None, limit: int = 100
    ) -> list[dict[str, Any]]:
        q = (
            select(OpLog)
            .where(OpLog.org_id == agent.org_id)
            .order_by(OpLog.created_at.desc())
            .limit(min(limit, 1000))
        )
        if device_id:
            q = q.where(OpLog.device_id == device_id)
        rows = (await s.execute(q)).scalars().all()
        return [
            {
                "id": r.id,
                "device_id": r.device_id,
                "agent_id": r.agent_id,
                "lease_id": r.lease_id,
                "op": r.op,
                "kw": r.kw,
                "ok": r.ok,
                "error_code": r.error_code,
                "policy_rule": r.policy_rule,
                "duration_ms": r.duration_ms,
                "at": r.created_at.isoformat(),
            }
            for r in rows
        ]

    # --- nodes ------------------------------------------------------------------------------------

    @app.post("/v1/nodes/enroll", status_code=201)
    async def enroll(body: EnrollIn, s: Session) -> dict[str, str]:
        enrolled = await auth.enroll_node(s, body.token, body.name)
        if enrolled is None:
            raise HTTPException(401, "enrollment token is invalid, used or expired")
        node, secret = enrolled
        return {"node_id": node.id, "node_secret": secret}

    @app.websocket("/v1/nodes/connect")
    async def node_socket(ws: WebSocket) -> None:
        node_id = ws.query_params.get("node_id", "")
        secret = (ws.headers.get("authorization") or "").removeprefix("Bearer ").strip()
        async with db.sessions() as s:
            node = await auth.verify_node(s, node_id, secret)
        if node is None:
            await ws.close(code=4401)
            return
        await ws.accept()
        conn = hub.attach(node.id, ws)
        try:
            while True:
                message = await ws.receive_json()
                kind = message.get("t")
                if kind == "op.response":
                    hub.resolve(conn, message)
                elif kind == "hello":
                    hello = models.NodeHello.model_validate(message)
                    device_map = await upsert_devices(node.id, hello.devices, version=hello.version)
                    await ws.send_json({"t": "welcome", "node_id": node.id, "device_map": device_map})
                elif kind == "device.update":
                    await upsert_devices(node.id, [models.NodeDeviceUpdate.model_validate(message).device])
                elif kind == "device.gone":
                    await mark_gone(node.id, str(message.get("local_id")))
        except WebSocketDisconnect:
            pass
        finally:
            hub.detach(conn)
            async with db.sessions() as s:
                row = await s.get(Node, node.id)
                if row is not None:
                    row.status, row.last_seen_at = "offline", now()
                    await s.commit()

    async def upsert_devices(
        node_id: str, devices: list[models.NodeDevice], version: str | None = None
    ) -> dict[str, str]:
        async with db.sessions() as s:
            node = await s.get(Node, node_id)
            assert node is not None
            node.status, node.last_seen_at = "online", now()
            if version:
                node.version = version
            mapping: dict[str, str] = {}
            for d in devices:
                row = (
                    await s.execute(
                        select(Device).where(Device.node_id == node_id, Device.local_id == d.local_id)
                    )
                ).scalar_one_or_none()
                if row is None:
                    row = Device(
                        org_id=node.org_id, node_id=node_id, local_id=d.local_id, platform=d.platform
                    )
                    s.add(row)
                row.model, row.os_version, row.state, row.ops, row.last_seen_at = (
                    d.model,
                    d.os_version,
                    d.state,
                    list(d.ops),
                    now(),
                )
                await s.flush()
                mapping[d.local_id] = row.id
            await s.commit()
            return mapping

    async def mark_gone(node_id: str, local_id: str) -> None:
        async with db.sessions() as s:
            row = (
                await s.execute(select(Device).where(Device.node_id == node_id, Device.local_id == local_id))
            ).scalar_one_or_none()
            if row is not None:
                row.state = "offline"
                await s.commit()

    return app
