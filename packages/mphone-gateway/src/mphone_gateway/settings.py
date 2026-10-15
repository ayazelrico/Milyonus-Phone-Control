"""Gateway settings from the environment (MPHONE_GW_*)."""

from pydantic_settings import BaseSettings, SettingsConfigDict

from mphone_core import config


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="MPHONE_GW_")

    # SQLite for development and tests; Postgres in production (`mphone-gateway[postgres]`,
    # postgresql+asyncpg://…). Same models either way (docs/decisions.md).
    database_url: str = ""
    lease_default_ttl_s: int = 300
    lease_max_ttl_s: int = 3600
    node_grace_s: int = 120
    op_timeout_s: float = 30.0

    def db_url(self) -> str:
        return self.database_url or f"sqlite+aiosqlite:///{config.subdir('gateway') / 'gateway.db'}"
