"""FastAPI dependencies for authentication: reading the session cookie, loading the
current user, and gating admin-only routes.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Cookie, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from aletheia.accounts.models import Role, User
from aletheia.accounts.repository import get_user_by_id
from aletheia.accounts.security import TokenError, decode_access_token
from aletheia.config import Settings, get_settings
from aletheia.db.session import get_session

SESSION_COOKIE = "aletheia_session"


async def get_current_user(
    aletheia_session: Annotated[str | None, Cookie()] = None,
    settings: Annotated[Settings, Depends(get_settings)] = None,  # type: ignore[assignment]
    session: Annotated[AsyncSession, Depends(get_session)] = None,  # type: ignore[assignment]
) -> User:
    """Resolve the signed-in user from the session cookie, or raise 401."""
    if aletheia_session is None or settings.jwt_secret is None:
        raise HTTPException(status_code=401, detail="Not authenticated.")
    try:
        user_id, _role = decode_access_token(aletheia_session, settings=settings)
    except TokenError as exc:
        raise HTTPException(status_code=401, detail="Invalid or expired session.") from exc
    user = await get_user_by_id(session, user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="Account no longer exists.")
    return user


async def get_current_user_optional(
    aletheia_session: Annotated[str | None, Cookie()] = None,
    settings: Annotated[Settings, Depends(get_settings)] = None,  # type: ignore[assignment]
    session: Annotated[AsyncSession, Depends(get_session)] = None,  # type: ignore[assignment]
) -> User | None:
    """Resolve the signed-in user if present, else ``None`` (never raises)."""
    if aletheia_session is None or settings.jwt_secret is None:
        return None
    try:
        user_id, _role = decode_access_token(aletheia_session, settings=settings)
    except TokenError:
        return None
    return await get_user_by_id(session, user_id)


async def require_admin(user: Annotated[User, Depends(get_current_user)]) -> User:
    if user.role != Role.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required.")
    return user
