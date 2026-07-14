"""Alembic migration environment (async).

The database URL is read from application settings and the target metadata is the
shared declarative base, so migrations and the running application never disagree
about where the database is or what the schema should be. Migrations run over an
async connection to match the rest of the stack (psycopg3 async).
"""

from __future__ import annotations

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import Connection, pool
from sqlalchemy.ext.asyncio import create_async_engine

from aletheia.accounts import models as accounts_models  # noqa: F401 -- registers tables
from aletheia.config import get_settings
from aletheia.corpus import models  # noqa: F401 -- import registers tables on the metadata
from aletheia.db.base import Base

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata
_DATABASE_URL = get_settings().database_url


def run_migrations_offline() -> None:
    """Emit SQL without a live connection (``alembic upgrade --sql``)."""
    context.configure(
        url=_DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def _do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """Run migrations against the database over an async connection."""
    engine = create_async_engine(_DATABASE_URL, poolclass=pool.NullPool)
    async with engine.connect() as connection:
        await connection.run_sync(_do_run_migrations)
    await engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
