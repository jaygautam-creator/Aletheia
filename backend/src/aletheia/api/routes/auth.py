"""Account routes: signup, login, logout, and "who am I".

Sessions are a JWT in an httpOnly cookie (:data:`aletheia.accounts.dependencies.
SESSION_COOKIE`) — no refresh tokens, no revocation list. ``JWT_SECRET`` must be set
for any of these routes to work; its absence surfaces as a clear 503 rather than a
crash, matching the pattern already used for missing LLM provider keys.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.ext.asyncio import AsyncSession

from aletheia.accounts.dependencies import SESSION_COOKIE, get_current_user
from aletheia.accounts.models import User
from aletheia.accounts.repository import create_user, get_user_by_email
from aletheia.accounts.security import create_access_token, hash_password, verify_password
from aletheia.config import Settings, get_settings
from aletheia.db.session import get_session

router = APIRouter(prefix="/auth", tags=["accounts"])


def _require_jwt_secret(settings: Settings) -> None:
    if settings.jwt_secret is None:
        raise HTTPException(
            status_code=503,
            detail="Accounts are not configured on this server: JWT_SECRET is unset.",
        )


class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    display_name: str | None = Field(default=None, max_length=120)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: str
    email: str
    display_name: str | None
    role: str

    @classmethod
    def from_model(cls, user: User) -> UserOut:
        return cls(
            id=str(user.id), email=user.email, display_name=user.display_name, role=user.role
        )


def _set_session_cookie(response: Response, user: User, settings: Settings) -> None:
    token = create_access_token(user_id=user.id, role=user.role, settings=settings)
    response.set_cookie(
        SESSION_COOKIE,
        token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        max_age=settings.jwt_expire_minutes * 60,
    )


@router.post("/signup", response_model=UserOut, summary="Create an account")
async def signup(
    request: SignupRequest,
    response: Response,
    session: Annotated[AsyncSession, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> UserOut:
    _require_jwt_secret(settings)
    if await get_user_by_email(session, request.email) is not None:
        raise HTTPException(status_code=409, detail="An account with that email already exists.")
    user = await create_user(
        session,
        email=request.email,
        password_hash=hash_password(request.password),
        display_name=request.display_name,
    )
    _set_session_cookie(response, user, settings)
    return UserOut.from_model(user)


@router.post("/login", response_model=UserOut, summary="Sign in")
async def login(
    request: LoginRequest,
    response: Response,
    session: Annotated[AsyncSession, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> UserOut:
    _require_jwt_secret(settings)
    user = await get_user_by_email(session, request.email)
    if user is None or not verify_password(request.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password.")
    _set_session_cookie(response, user, settings)
    return UserOut.from_model(user)


@router.post("/logout", summary="Sign out")
async def logout(response: Response) -> dict[str, bool]:
    response.delete_cookie(SESSION_COOKIE)
    return {"ok": True}


@router.get("/me", response_model=UserOut, summary="The signed-in account")
async def me(user: Annotated[User, Depends(get_current_user)]) -> UserOut:
    return UserOut.from_model(user)
