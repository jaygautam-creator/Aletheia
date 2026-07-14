"""History routes: a user's own request log, and the admin audit view over everyone's.

``/history/me`` answers "what have I run"; ``/history/admin`` (role-gated) answers
"who ran what" across all accounts, including anonymous (unauthenticated) requests.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from aletheia.accounts.dependencies import get_current_user, require_admin
from aletheia.accounts.models import RequestLog, User
from aletheia.accounts.repository import list_all_history, list_user_history
from aletheia.db.session import get_session

router = APIRouter(prefix="/history", tags=["accounts"])


class RequestLogOut(BaseModel):
    id: str
    user_id: str | None
    route: str
    query_preview: str | None
    key_source: str
    provider: str
    status: str
    latency_ms: int | None
    created_at: str

    @classmethod
    def from_model(cls, entry: RequestLog) -> RequestLogOut:
        return cls(
            id=str(entry.id),
            user_id=str(entry.user_id) if entry.user_id else None,
            route=entry.route,
            query_preview=entry.query_preview,
            key_source=entry.key_source,
            provider=entry.provider,
            status=entry.status,
            latency_ms=entry.latency_ms,
            created_at=entry.created_at.isoformat(),
        )


@router.get("/me", response_model=list[RequestLogOut], summary="Your own request history")
async def history_me(
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[RequestLogOut]:
    entries = await list_user_history(session, user.id, limit=limit, offset=offset)
    return [RequestLogOut.from_model(entry) for entry in entries]


@router.get(
    "/admin", response_model=list[RequestLogOut], summary="All accounts' request history (audit)"
)
async def history_admin(
    _admin: Annotated[User, Depends(require_admin)],
    session: Annotated[AsyncSession, Depends(get_session)],
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[RequestLogOut]:
    entries = await list_all_history(session, limit=limit, offset=offset)
    return [RequestLogOut.from_model(entry) for entry in entries]
