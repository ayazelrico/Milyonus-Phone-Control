"""Leases (A5.11, Plan.md §8.4.4): exclusive, time-limited use of one device by one agent."""

from datetime import UTC, datetime, timedelta

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from mphone_protocol import LeaseConflict, LeaseExpired, LeaseRequired

from .db import Agent, Device, Lease, now


def aware(dt: datetime) -> datetime:
    """SQLite returns naive datetimes; everything here is UTC."""
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)


async def expire_due(s: AsyncSession) -> int:
    result = await s.execute(
        update(Lease).where(Lease.status == "active", Lease.expires_at < now()).values(status="expired")
    )
    await s.commit()
    return result.rowcount or 0  # pyright: ignore[reportAttributeAccessIssue]


async def acquire(s: AsyncSession, agent: Agent, device: Device, ttl_s: int, purpose: str) -> Lease:
    # Read ids first: after a rollback SQLAlchemy expires every loaded object, and touching one then
    # triggers a lazy load that async sessions forbid (MissingGreenlet → HTTP 500 instead of 409).
    device_id, org_id, agent_id = device.id, agent.org_id, agent.id
    await expire_due(s)
    lease = Lease(
        org_id=org_id,
        device_id=device_id,
        agent_id=agent_id,
        purpose=purpose,
        ttl_s=ttl_s,
        expires_at=now() + timedelta(seconds=ttl_s),
    )
    s.add(lease)
    try:
        await s.commit()
    except IntegrityError:
        await s.rollback()
        holder = (
            await s.execute(select(Lease).where(Lease.device_id == device_id, Lease.status == "active"))
        ).scalar_one_or_none()
        raise LeaseConflict(
            f"{device_id} is leased until {holder.expires_at if holder else '?'} ({holder.purpose if holder else ''})",
            user_action="Kiralama bitene kadar bekleyin veya başka bir cihaz isteyin.",
            details={"holder_lease": holder.id if holder else None},
        ) from None
    return lease


async def require(s: AsyncSession, lease_id: str | None, agent: Agent, device_id: str) -> Lease:
    """The caller's active lease on this device, or the protocol error explaining why not."""
    if not lease_id:
        raise LeaseRequired(
            "this op needs a lease on the device", user_action="Önce POST /v1/leases ile cihazı kiralayın."
        )
    lease = await s.get(Lease, lease_id)
    if lease is None or lease.agent_id != agent.id or lease.device_id != device_id:
        raise LeaseRequired(f"no lease {lease_id} for this agent on {device_id}")
    if lease.status == "active" and aware(lease.expires_at) < now():
        lease.status = "expired"
        await s.commit()
    if lease.status != "active":
        raise LeaseExpired(
            f"lease {lease_id} is {lease.status}",
            user_action="Cihazı yeniden kiralayın; başka cihaza geçilmez.",
        )
    return lease


async def heartbeat(s: AsyncSession, lease: Lease, ttl_s: int | None) -> Lease:
    lease.expires_at = now() + timedelta(seconds=ttl_s or lease.ttl_s)
    await s.commit()
    return lease


async def release(s: AsyncSession, lease: Lease) -> None:
    if lease.status == "active":
        lease.status = "released"
        lease.released_at = now()
        await s.commit()
