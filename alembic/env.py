"""Alembic environment — async SQLAlchemy 2.0 compatible."""
from __future__ import annotations

import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# Register all ORM models so metadata is fully populated before autogenerate
from app.core.config import settings
from app.core.database import Base
import app.models.financial  # noqa: F401

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Override alembic.ini URL with the one from app settings at runtime
config.set_main_option("sqlalchemy.url", settings.database_url_sync)

target_metadata = Base.metadata

_MANAGED_SCHEMAS = frozenset(
    ("public", "raw", "staging", "intermediate", "marts", "analytics", "monitoring")
)


def _include_name(name: str, type_: str, parent_names: dict) -> bool:
    if type_ == "schema":
        return name in _MANAGED_SCHEMAS
    return True


def run_migrations_offline() -> None:
    """Emit SQL to stdout without a live DB connection (CI diff / review)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_schemas=True,
        include_name=_include_name,
        version_table_schema="public",
    )
    with context.begin_transaction():
        context.run_migrations()


def _do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        include_schemas=True,
        include_name=_include_name,
        version_table_schema="public",
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def _run_async_migrations() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(_do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(_run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
