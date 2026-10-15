"""Migrations produce exactly the models' schema, and go back down cleanly (A5.02)."""

import asyncio
import os
from pathlib import Path

from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import inspect
from sqlalchemy.ext.asyncio import create_async_engine

from mphone_gateway.db import Base
from mphone_gateway.migrate import downgrade, upgrade


def _diff_and_tables(url: str) -> tuple[list[object], set[str]]:
    async def run() -> tuple[list[object], set[str]]:
        engine = create_async_engine(url)
        async with engine.connect() as conn:
            diff = await conn.run_sync(
                lambda c: compare_metadata(MigrationContext.configure(c), Base.metadata)
            )
            tables = await conn.run_sync(lambda c: set(inspect(c).get_table_names()))
        await engine.dispose()
        return list(diff), tables

    return asyncio.run(run())


def test_upgrade_matches_models_and_downgrade_empties(tmp_path: Path) -> None:
    url = os.environ.get("MPHONE_TEST_DB_URL") or f"sqlite+aiosqlite:///{tmp_path / 'm.db'}"
    downgrade(url)  # an external database may hold a previous test's schema
    upgrade(url)
    diff, tables = _diff_and_tables(url)
    assert diff == [], f"models and migrations drifted: {diff}"
    assert {"leases", "devices", "op_log", "api_keys"} <= tables
    downgrade(url)
    _, tables = _diff_and_tables(url)
    assert tables <= {"alembic_version"}
