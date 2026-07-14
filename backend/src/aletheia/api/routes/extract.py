"""Claim-intake extraction endpoint: turn one uploaded file into reviewable text.

``POST /extract`` accepts a single PDF, image, or audio upload and returns the plain
text found in it. It is deliberately *not* a verification route (ADR-0009): the
frontend places the returned text in the editable query field for the user to review
before running ``/verify``, so the pipeline and the verdict contract stay untouched.
Uploads are handled in memory and never written anywhere.

The route spends provider budget (Gemini vision for images, Groq Whisper for voice),
so it shares the per-IP rate limiter with ``/verify`` and gets its own, larger body
cap. Transcribers are built lazily per media kind — a missing Gemini key must fail
image uploads with a clear 503, not break PDF extraction, which needs no key at all.
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Callable
from functools import lru_cache
from typing import Annotated, Literal, Protocol

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from aletheia.accounts.dependencies import get_current_user_optional
from aletheia.accounts.models import KeySource, Provider, User
from aletheia.accounts.repository import get_api_key, log_request
from aletheia.accounts.security import decrypt_key
from aletheia.config import Settings, get_settings
from aletheia.db.session import get_session
from aletheia.media import (
    GeminiImageTranscriber,
    GroqAudioTranscriber,
    MediaExtractionError,
    MediaProviderError,
    extract_pdf_text,
)

router = APIRouter(tags=["intake"])
logger = logging.getLogger(__name__)

_PDF_TYPES = frozenset({"application/pdf"})
_IMAGE_TYPES = frozenset({"image/png", "image/jpeg", "image/webp"})
# Everything a browser's MediaRecorder or file picker plausibly produces; Groq's
# Whisper accepts each container (aletheia.media maps MIME type → filename).
_AUDIO_TYPES = frozenset(
    {
        "audio/webm",
        "audio/ogg",
        "audio/mpeg",
        "audio/mp3",
        "audio/mp4",
        "audio/x-m4a",
        "audio/wav",
        "audio/x-wav",
        "audio/flac",
    }
)


class Transcriber(Protocol):
    """Anything that can turn media bytes into text (satisfied by both transcribers)."""

    async def transcribe(self, data: bytes, mime_type: str) -> str: ...


# A zero-arg factory so the provider client is only built - and its key only
# required - when a request actually needs that media kind.
TranscriberFactory = Callable[[], Transcriber]


@lru_cache
def _image_transcriber() -> GeminiImageTranscriber:
    settings = get_settings()
    if settings.gemini_api_key is None:
        raise HTTPException(
            status_code=503,
            detail=(
                "Image intake needs GEMINI_API_KEY. "
                "Add a free key from https://aistudio.google.com/apikey to your .env."
            ),
        )
    return GeminiImageTranscriber(
        api_key=settings.gemini_api_key.get_secret_value(), model=settings.vision_model
    )


@lru_cache
def _audio_transcriber() -> GroqAudioTranscriber:
    settings = get_settings()
    if settings.groq_api_key is None:
        raise HTTPException(
            status_code=503,
            detail=(
                "Voice intake needs GROQ_API_KEY. "
                "Add a free key from https://console.groq.com/keys to your .env."
            ),
        )
    return GroqAudioTranscriber(
        api_key=settings.groq_api_key.get_secret_value(), model=settings.transcription_model
    )


def get_image_transcriber() -> TranscriberFactory:
    """Provide the lazy image-transcriber factory (overridable in tests)."""
    return _image_transcriber


def get_audio_transcriber() -> TranscriberFactory:
    """Provide the lazy audio-transcriber factory (overridable in tests)."""
    return _audio_transcriber


class ExtractResponse(BaseModel):
    """The text found in the upload, ready for the user to review and edit."""

    kind: Literal["pdf", "image", "audio"]
    text: str = Field(description="The extracted text, for the editable query field.")
    characters: int = Field(description="Length of `text` after any truncation.")
    truncated: bool = Field(
        description="True when the extraction exceeded the cap and only its head is returned."
    )


async def _user_key(
    session: AsyncSession, user: User | None, provider: Provider, settings: Settings
) -> str | None:
    if user is None:
        return None
    stored = await get_api_key(session, user.id, provider)
    if stored is None:
        return None
    return decrypt_key(stored.encrypted_key, settings=settings)


@router.post("/extract", response_model=ExtractResponse, summary="Extract claim text from a file")
async def extract(  # noqa: PLR0913
    file: UploadFile,
    image_transcriber: Annotated[TranscriberFactory, Depends(get_image_transcriber)],
    audio_transcriber: Annotated[TranscriberFactory, Depends(get_audio_transcriber)],
    user: Annotated[User | None, Depends(get_current_user_optional)],
    session: Annotated[AsyncSession, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> ExtractResponse:
    """Extract the text of one PDF, image, or voice-note upload."""
    data = await file.read()
    if not data:
        raise HTTPException(status_code=422, detail="The uploaded file is empty.")

    # Browsers append codec parameters ("audio/webm;codecs=opus"); match on the bare type.
    content_type = (file.content_type or "").split(";", 1)[0].strip().lower()

    kind: Literal["pdf", "image", "audio"]
    key_source = KeySource.SERVER_DEFAULT
    provider = "-"
    started_at = time.monotonic()
    try:
        if content_type in _PDF_TYPES:
            kind = "pdf"
            provider = "-"
            # pypdf is synchronous and CPU-bound; keep it off the event loop.
            text = await asyncio.to_thread(extract_pdf_text, data)
        elif content_type in _IMAGE_TYPES:
            kind = "image"
            provider = "gemini"
            byo_key = await _user_key(session, user, Provider.GEMINI, settings)
            transcriber = (
                GeminiImageTranscriber(api_key=byo_key, model=settings.vision_model)
                if byo_key
                else image_transcriber()
            )
            key_source = KeySource.USER_KEY if byo_key else KeySource.SERVER_DEFAULT
            text = await transcriber.transcribe(data, content_type)
        elif content_type in _AUDIO_TYPES:
            kind = "audio"
            provider = "groq"
            byo_key = await _user_key(session, user, Provider.GROQ, settings)
            transcriber = (
                GroqAudioTranscriber(api_key=byo_key, model=settings.transcription_model)
                if byo_key
                else audio_transcriber()
            )
            key_source = KeySource.USER_KEY if byo_key else KeySource.SERVER_DEFAULT
            text = await transcriber.transcribe(data, content_type)
        else:
            raise HTTPException(
                status_code=415,
                detail=(
                    f"Unsupported file type {content_type or '(none)'!r}. "
                    "Upload a PDF, a PNG/JPEG/WebP image, or an audio recording."
                ),
            )
    except MediaProviderError as exc:
        await _log_extract(
            session,
            user,
            kind="unknown",
            provider=provider,
            key_source=key_source,
            status="error",
            started_at=started_at,
        )
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except MediaExtractionError as exc:
        await _log_extract(
            session,
            user,
            kind="unknown",
            provider=provider,
            key_source=key_source,
            status="error",
            started_at=started_at,
        )
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    cap = settings.extract_max_chars
    truncated = len(text) > cap
    if truncated:
        text = text[:cap].rstrip()
    await _log_extract(
        session,
        user,
        kind=kind,
        provider=provider,
        key_source=key_source,
        status="ok",
        started_at=started_at,
    )
    return ExtractResponse(kind=kind, text=text, characters=len(text), truncated=truncated)


async def _log_extract(  # noqa: PLR0913
    session: AsyncSession,
    user: User | None,
    *,
    kind: str,
    provider: str,
    key_source: KeySource,
    status: str,
    started_at: float,
) -> None:
    try:
        await log_request(
            session,
            user_id=user.id if user else None,
            route="/extract",
            query_preview=f"[{kind} upload]",
            key_source=key_source,
            provider=provider,
            status=status,
            latency_ms=int((time.monotonic() - started_at) * 1000),
        )
    except Exception:
        logger.exception("failed to write request history; the response is unaffected")
