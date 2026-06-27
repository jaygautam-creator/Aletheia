"""Async engine and session factory, created lazily from settings.

The engine and sessionmaker are process-wide singletons (one connection pool per
process), built on first use so importing this module never opens a socket — keeping
unit tests and key-free CI free of any database dependency. :func:`get_session` is a
FastAPI-friendly dependency that yields a session and always closes it.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from functools import lru_cache

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from aletheia.config import get_settings


@lru_cache
def get_engine() -> AsyncEngine:
    """Return the process-wide async engine, created on first use."""
    settings = get_settings()
    return create_async_engine(
        settings.database_url,
        echo=settings.db_echo,
        pool_pre_ping=True,
    )


@lru_cache
def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    """Return the process-wide session factory bound to the engine."""
    return async_sessionmaker(get_engine(), expire_on_commit=False)


async def get_session() -> AsyncIterator[AsyncSession]:
    """Yield a database session, closing it when the caller is done."""
    async with get_sessionmaker()() as session:
        yield session
