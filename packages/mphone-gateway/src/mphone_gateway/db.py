"""Persistent state (A5.02, Plan.md §8.4.2): the subset P5 needs, org-scoped from the start."""

import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Any, ClassVar

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Index, Integer, String, UniqueConstraint, text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

DEFAULT_ORG = "org_default"


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:16]}"


def now() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    type_annotation_map: ClassVar[dict[Any, Any]] = {dict[str, Any]: JSON, list[str]: JSON}


class Org(Base):
    __tablename__ = "orgs"
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    name: Mapped[str] = mapped_column(String(200))


class Agent(Base):
    __tablename__ = "agents"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("agt"))
    org_id: Mapped[str] = mapped_column(ForeignKey("orgs.id"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    trust_level: Mapped[str] = mapped_column(String(20), default="standard")
    allowed_tags: Mapped[list[str]] = mapped_column(default=list)  # empty = every device in the org


class ApiKey(Base):
    __tablename__ = "api_keys"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("key"))
    agent_id: Mapped[str] = mapped_column(ForeignKey("agents.id"), index=True)
    prefix: Mapped[str] = mapped_column(String(16), unique=True)
    hash: Mapped[str] = mapped_column(String(128))
    scopes: Mapped[list[str]] = mapped_column(default=list)
    # A lease credential: usable only for ops on this one lease (handed to scripts, Plan.md §8.5).
    lease_id: Mapped[str | None] = mapped_column(String(40), default=None)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)


class EnrollmentToken(Base):
    __tablename__ = "enrollment_tokens"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("enr"))
    org_id: Mapped[str] = mapped_column(ForeignKey("orgs.id"))
    hash: Mapped[str] = mapped_column(String(128), unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)


class Node(Base):
    __tablename__ = "nodes"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("nod"))
    org_id: Mapped[str] = mapped_column(ForeignKey("orgs.id"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    secret_hash: Mapped[str] = mapped_column(String(128))
    status: Mapped[str] = mapped_column(String(20), default="offline")
    version: Mapped[str | None] = mapped_column(String(40), default=None)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)


class Device(Base):
    __tablename__ = "devices"
    __table_args__ = (UniqueConstraint("node_id", "local_id"),)
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("dev"))
    org_id: Mapped[str] = mapped_column(ForeignKey("orgs.id"), index=True)
    node_id: Mapped[str] = mapped_column(ForeignKey("nodes.id"), index=True)
    local_id: Mapped[str] = mapped_column(String(200))
    platform: Mapped[str] = mapped_column(String(20))
    model: Mapped[str | None] = mapped_column(String(200), default=None)
    os_version: Mapped[str | None] = mapped_column(String(40), default=None)
    state: Mapped[str] = mapped_column(String(20), default="offline")
    ops: Mapped[list[str]] = mapped_column(default=list)
    label: Mapped[str | None] = mapped_column(String(200), default=None)
    tags: Mapped[list[str]] = mapped_column(default=list)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)


class Lease(Base):
    __tablename__ = "leases"
    # One ACTIVE lease per device, enforced by the database itself (A5.11): of two racing
    # acquires exactly one insert succeeds. Works on SQLite and Postgres (partial indexes).
    __table_args__ = (
        Index(
            "one_active_lease_per_device",
            "device_id",
            unique=True,
            sqlite_where=text("status = 'active'"),
            postgresql_where=text("status = 'active'"),
        ),
    )
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("lse"))
    org_id: Mapped[str] = mapped_column(ForeignKey("orgs.id"), index=True)
    device_id: Mapped[str] = mapped_column(ForeignKey("devices.id"))
    agent_id: Mapped[str] = mapped_column(ForeignKey("agents.id"), index=True)
    purpose: Mapped[str] = mapped_column(String(500), default="")
    status: Mapped[str] = mapped_column(String(20), default="active")  # active|released|expired|revoked
    ttl_s: Mapped[int] = mapped_column(Integer)
    acquired_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    released_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)


class OpLog(Base):
    """Append-only audit of every op (A5.15). Sensitive arguments are masked before insert."""

    __tablename__ = "op_log"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("op"))
    org_id: Mapped[str] = mapped_column(String(40), index=True)
    device_id: Mapped[str] = mapped_column(String(40), index=True)
    lease_id: Mapped[str | None] = mapped_column(String(40), default=None)
    agent_id: Mapped[str | None] = mapped_column(String(40), default=None)
    op: Mapped[str] = mapped_column(String(60))
    kw: Mapped[dict[str, Any]] = mapped_column(default=dict)
    ok: Mapped[bool] = mapped_column(Boolean)
    error_code: Mapped[str | None] = mapped_column(String(40), default=None)
    policy_rule: Mapped[str | None] = mapped_column(String(80), default=None)
    duration_ms: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, index=True)


class Database:
    def __init__(self, url: str) -> None:
        self.engine: AsyncEngine = create_async_engine(url)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)

    async def create_all(self) -> None:
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        await self.seed()

    async def seed(self) -> None:
        """Rows every gateway needs, whether the schema came from create_all or from migrations."""
        async with self.sessions() as s:
            if await s.get(Org, DEFAULT_ORG) is None:
                s.add(Org(id=DEFAULT_ORG, name="Milyonus"))
                await s.commit()

    async def session(self) -> AsyncIterator[AsyncSession]:
        async with self.sessions() as s:
            yield s

    async def dispose(self) -> None:
        await self.engine.dispose()
