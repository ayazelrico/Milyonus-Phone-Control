"""Schema migrations for production databases: `mphone-gateway migrate` (A5.02)."""

from pathlib import Path

from alembic import command
from alembic.config import Config

from .settings import Settings

HERE = Path(__file__).parent


def alembic_config(url: str | None = None) -> Config:
    cfg = Config()
    cfg.set_main_option("script_location", str(HERE / "migrations"))
    cfg.set_main_option("sqlalchemy.url", url or Settings().db_url())
    return cfg


def upgrade(url: str | None = None, revision: str = "head") -> None:
    command.upgrade(alembic_config(url), revision)


def downgrade(url: str | None = None, revision: str = "base") -> None:
    command.downgrade(alembic_config(url), revision)
