"""Profile routes: view/edit the current account and manage stored BYO API keys.

A stored key is never returned in plaintext after it is saved — only its provider,
when it was created/last used, and a masked suffix, so the profile UI can show "a key
is configured" without re-exposing the secret.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.ext.asyncio import AsyncSession

from aletheia.accounts.dependencies import get_current_user
from aletheia.accounts.models import ApiKey, Provider, User
from aletheia.accounts.repository import delete_api_key, list_api_keys, update_user, upsert_api_key
from aletheia.accounts.security import EncryptionNotConfigured, encrypt_key
from aletheia.api.routes.auth import UserOut
from aletheia.config import Settings, get_settings
from aletheia.db.session import get_session

router = APIRouter(prefix="/profile", tags=["accounts"])


class ProfileUpdate(BaseModel):
    display_name: str | None = Field(default=None, max_length=120)
    email: EmailStr | None = None


class ApiKeyIn(BaseModel):
    key: str = Field(min_length=8, description="The provider's raw API key.")


class ApiKeyOut(BaseModel):
    provider: str
    masked_key: str
    created_at: str
    last_used_at: str | None

    @classmethod
    def from_model(cls, key: ApiKey) -> ApiKeyOut:
        # The plaintext is never stored, so "masking" here just means never returning
        # anything derived from the ciphertext beyond metadata.
        return cls(
            provider=key.provider,
            masked_key="•" * 8,
            created_at=key.created_at.isoformat(),
            last_used_at=key.last_used_at.isoformat() if key.last_used_at else None,
        )


@router.get("", response_model=UserOut, summary="Current account info")
async def get_profile(user: Annotated[User, Depends(get_current_user)]) -> UserOut:
    return UserOut.from_model(user)


@router.patch("", response_model=UserOut, summary="Edit account info")
async def patch_profile(
    request: ProfileUpdate,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> UserOut:
    updated = await update_user(
        session, user, display_name=request.display_name, email=request.email
    )
    return UserOut.from_model(updated)


@router.get("/api-keys", response_model=list[ApiKeyOut], summary="List configured provider keys")
async def get_api_keys(
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> list[ApiKeyOut]:
    keys = await list_api_keys(session, user.id)
    return [ApiKeyOut.from_model(key) for key in keys]


@router.put("/api-keys/{provider}", response_model=ApiKeyOut, summary="Store your own provider key")
async def put_api_key(
    provider: Provider,
    request: ApiKeyIn,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> ApiKeyOut:
    try:
        encrypted = encrypt_key(request.key, settings=settings)
    except EncryptionNotConfigured as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    key = await upsert_api_key(session, user.id, provider, encrypted)
    return ApiKeyOut.from_model(key)


@router.delete("/api-keys/{provider}", summary="Remove your own provider key")
async def remove_api_key(
    provider: Provider,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, bool]:
    deleted = await delete_api_key(session, user.id, provider)
    if not deleted:
        raise HTTPException(status_code=404, detail="No key stored for that provider.")
    return {"ok": True}
