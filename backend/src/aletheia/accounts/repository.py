"""Database access for accounts: users, their API keys, and the request log.

Kept as a thin function layer over the async session rather than a class, matching
this codebase's preference for small, direct pieces over premature abstraction.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aletheia.accounts.models import ApiKey, KeySource, Provider, RequestLog, Role, User


async def get_user_by_email(session: AsyncSession, email: str) -> User | None:
    result = await session.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def get_user_by_id(session: AsyncSession, user_id: uuid.UUID) -> User | None:
    return await session.get(User, user_id)


async def create_user(
    session: AsyncSession,
    *,
    email: str,
    password_hash: str,
    display_name: str | None = None,
    role: Role = Role.USER,
) -> User:
    user = User(email=email, password_hash=password_hash, display_name=display_name, role=role)
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def update_user(
    session: AsyncSession, user: User, *, display_name: str | None, email: str | None
) -> User:
    if display_name is not None:
        user.display_name = display_name
    if email is not None:
        user.email = email
    await session.commit()
    await session.refresh(user)
    return user


async def list_api_keys(session: AsyncSession, user_id: uuid.UUID) -> Sequence[ApiKey]:
    result = await session.execute(select(ApiKey).where(ApiKey.user_id == user_id))
    return result.scalars().all()


async def get_api_key(
    session: AsyncSession, user_id: uuid.UUID, provider: Provider
) -> ApiKey | None:
    result = await session.execute(
        select(ApiKey).where(ApiKey.user_id == user_id, ApiKey.provider == provider)
    )
    return result.scalar_one_or_none()


async def upsert_api_key(
    session: AsyncSession, user_id: uuid.UUID, provider: Provider, encrypted_key: str
) -> ApiKey:
    existing = await get_api_key(session, user_id, provider)
    if existing is not None:
        existing.encrypted_key = encrypted_key
        await session.commit()
        await session.refresh(existing)
        return existing
    key = ApiKey(user_id=user_id, provider=provider, encrypted_key=encrypted_key)
    session.add(key)
    await session.commit()
    await session.refresh(key)
    return key


async def delete_api_key(session: AsyncSession, user_id: uuid.UUID, provider: Provider) -> bool:
    existing = await get_api_key(session, user_id, provider)
    if existing is None:
        return False
    await session.delete(existing)
    await session.commit()
    return True


async def log_request(  # noqa: PLR0913
    session: AsyncSession,
    *,
    user_id: uuid.UUID | None,
    route: str,
    query_preview: str | None,
    key_source: KeySource,
    provider: str,
    status: str,
    latency_ms: int | None,
) -> None:
    session.add(
        RequestLog(
            user_id=user_id,
            route=route,
            query_preview=query_preview[:200] if query_preview else None,
            key_source=key_source,
            provider=provider,
            status=status,
            latency_ms=latency_ms,
        )
    )
    await session.commit()


async def list_user_history(
    session: AsyncSession, user_id: uuid.UUID, *, limit: int = 50, offset: int = 0
) -> Sequence[RequestLog]:
    result = await session.execute(
        select(RequestLog)
        .where(RequestLog.user_id == user_id)
        .order_by(RequestLog.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return result.scalars().all()


async def list_all_history(
    session: AsyncSession, *, limit: int = 50, offset: int = 0
) -> Sequence[RequestLog]:
    result = await session.execute(
        select(RequestLog).order_by(RequestLog.created_at.desc()).limit(limit).offset(offset)
    )
    return result.scalars().all()
