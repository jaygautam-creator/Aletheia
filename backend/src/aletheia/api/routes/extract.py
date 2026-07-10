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
from collections.abc import Callable
from functools import lru_cache
from typing import Annotated, Literal, Protocol

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from pydantic import BaseModel, Field

from aletheia.config import get_settings
from aletheia.media import (
    GeminiImageTranscriber,
    GroqAudioTranscriber,
    MediaExtractionError,
    MediaProviderError,
    extract_pdf_text,
)

router = APIRouter(tags=["intake"])

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


@router.post("/extract", response_model=ExtractResponse, summary="Extract claim text from a file")
async def extract(
    file: UploadFile,
    image_transcriber: Annotated[TranscriberFactory, Depends(get_image_transcriber)],
    audio_transcriber: Annotated[TranscriberFactory, Depends(get_audio_transcriber)],
) -> ExtractResponse:
    """Extract the text of one PDF, image, or voice-note upload."""
    data = await file.read()
    if not data:
        raise HTTPException(status_code=422, detail="The uploaded file is empty.")

    # Browsers append codec parameters ("audio/webm;codecs=opus"); match on the bare type.
    content_type = (file.content_type or "").split(";", 1)[0].strip().lower()

    kind: Literal["pdf", "image", "audio"]
    try:
        if content_type in _PDF_TYPES:
            kind = "pdf"
            # pypdf is synchronous and CPU-bound; keep it off the event loop.
            text = await asyncio.to_thread(extract_pdf_text, data)
        elif content_type in _IMAGE_TYPES:
            kind = "image"
            text = await image_transcriber().transcribe(data, content_type)
        elif content_type in _AUDIO_TYPES:
            kind = "audio"
            text = await audio_transcriber().transcribe(data, content_type)
        else:
            raise HTTPException(
                status_code=415,
                detail=(
                    f"Unsupported file type {content_type or '(none)'!r}. "
                    "Upload a PDF, a PNG/JPEG/WebP image, or an audio recording."
                ),
            )
    except MediaProviderError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except MediaExtractionError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    cap = get_settings().extract_max_chars
    truncated = len(text) > cap
    if truncated:
        text = text[:cap].rstrip()
    return ExtractResponse(kind=kind, text=text, characters=len(text), truncated=truncated)
