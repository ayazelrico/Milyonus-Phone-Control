"""Credentials (A5.03, A5.04): agent API keys with scopes, enrollment tokens, node secrets.

Only a SHA-256 of a secret is stored; the plain value is shown once, at creation. Keys look like
`mph_<prefix>_<secret>`: the prefix finds the row, the hash proves the secret.
"""

import hashlib
import hmac
import secrets
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .db import DEFAULT_ORG, Agent, ApiKey, EnrollmentToken, Node, now

ALL_SCOPES = ["devices:read", "leases:write", "ops:write", "audit:read"]


def digest(secret: str) -> str:
    return hashlib.sha256(secret.encode()).hexdigest()


async def create_agent(
    s: AsyncSession,
    name: str,
    scopes: list[str] | None = None,
    trust_level: str = "standard",
    allowed_tags: list[str] | None = None,
) -> tuple[Agent, str]:
    agent = Agent(org_id=DEFAULT_ORG, name=name, trust_level=trust_level, allowed_tags=allowed_tags or [])
    s.add(agent)
    await s.flush()
    prefix, secret = secrets.token_hex(4), secrets.token_urlsafe(24)
    s.add(ApiKey(agent_id=agent.id, prefix=prefix, hash=digest(secret), scopes=scopes or list(ALL_SCOPES)))
    await s.commit()
    return agent, f"mph_{prefix}_{secret}"


async def create_lease_credential(s: AsyncSession, agent_id: str, lease_id: str) -> str:
    """A key that can run ops on ONE lease and nothing else; useless once the lease ends."""
    prefix, secret = secrets.token_hex(4), secrets.token_urlsafe(24)
    s.add(
        ApiKey(
            agent_id=agent_id,
            prefix=prefix,
            hash=digest(secret),
            scopes=["ops:write", "devices:read"],
            lease_id=lease_id,
        )
    )
    await s.commit()
    return f"mph_{prefix}_{secret}"


async def verify_key(s: AsyncSession, presented: str) -> tuple[Agent, ApiKey] | None:
    parts = presented.split("_", 2)
    if len(parts) != 3 or parts[0] != "mph":
        return None
    key = (await s.execute(select(ApiKey).where(ApiKey.prefix == parts[1]))).scalar_one_or_none()
    if key is None or key.revoked_at is not None or not hmac.compare_digest(key.hash, digest(parts[2])):
        return None
    agent = await s.get(Agent, key.agent_id)
    return (agent, key) if agent else None


async def create_enrollment_token(s: AsyncSession, minutes: int = 15) -> str:
    token = f"enr_{secrets.token_urlsafe(24)}"
    s.add(
        EnrollmentToken(org_id=DEFAULT_ORG, hash=digest(token), expires_at=now() + timedelta(minutes=minutes))
    )
    await s.commit()
    return token


async def enroll_node(s: AsyncSession, token: str, name: str) -> tuple[Node, str] | None:
    """Spend a one-time enrollment token; return the node and its secret (shown once)."""
    row = (
        await s.execute(select(EnrollmentToken).where(EnrollmentToken.hash == digest(token)))
    ).scalar_one_or_none()
    if row is None or row.used_at is not None or row.expires_at.replace(tzinfo=now().tzinfo) < now():
        return None
    row.used_at = now()
    secret = f"nsk_{secrets.token_urlsafe(32)}"
    node = Node(org_id=row.org_id, name=name, secret_hash=digest(secret))
    s.add(node)
    await s.commit()
    return node, secret


async def verify_node(s: AsyncSession, node_id: str, secret: str) -> Node | None:
    node = await s.get(Node, node_id)
    if node is None or not hmac.compare_digest(node.secret_hash, digest(secret)):
        return None
    return node
