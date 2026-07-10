"""Turn an uploaded PDF, image, or voice note into plain text.

Extraction is presentation-layer plumbing (ADR-0009): each helper returns the text
found in an upload so the frontend can place it in the *editable* query field for the
user to review before verifying. Nothing here judges a claim — the pipeline and the
verdict contract are untouched — and uploads are processed in memory, never stored.

Two failure families keep the API honest about whose problem a failure is:
:class:`MediaExtractionError` means the upload itself carries no usable text (the
caller's file), while :class:`MediaProviderError` means the transcription provider
call failed (our upstream) — the route maps them to 422 and 502 respectively.
"""

from __future__ import annotations

import io

from google import genai
from google.genai import types
from groq import AsyncGroq
from pypdf import PdfReader

# Per-attempt HTTP timeout for the vision call, in milliseconds (the SDK's unit) —
# the same bound the Gemini chat adapter uses, for the same reason: a hung connect
# must surface as an error the user sees, not a request that never returns.
_HTTP_TIMEOUT_MS = 60_000

# Groq's transcription endpoint infers the container format from the *filename*,
# so the upload's MIME type is mapped to an extension it recognises.
_AUDIO_EXTENSION: dict[str, str] = {
    "audio/webm": "webm",
    "audio/ogg": "ogg",
    "audio/mpeg": "mp3",
    "audio/mp3": "mp3",
    "audio/mp4": "mp4",
    "audio/x-m4a": "m4a",
    "audio/wav": "wav",
    "audio/x-wav": "wav",
    "audio/flac": "flac",
}

_IMAGE_INSTRUCTION = (
    "Transcribe the text visible in this image, exactly as written. Return only the "
    "transcribed text - no commentary, no markdown, no translation. If the image "
    "contains no legible text, return an empty string."
)


class MediaExtractionError(RuntimeError):
    """The upload yields no usable text (empty, unreadable, illegible, or silent)."""


class MediaProviderError(RuntimeError):
    """The transcription provider call failed (network, quota, or server error)."""


def extract_pdf_text(data: bytes) -> str:
    """Return the concatenated page text of a PDF, or raise when it carries none."""
    try:
        reader = PdfReader(io.BytesIO(data))
        if reader.is_encrypted:
            raise MediaExtractionError("The PDF is encrypted; upload a decrypted copy.")
        pages = [page.extract_text() for page in reader.pages]
    except MediaExtractionError:
        raise
    except Exception as exc:  # pypdf raises a zoo of parse errors; the cause is the file
        raise MediaExtractionError(f"Could not read the PDF: {exc}") from exc

    text = "\n\n".join(page.strip() for page in pages if page and page.strip())
    if not text:
        raise MediaExtractionError(
            "The PDF contains no extractable text - it may be a scanned document; "
            "try uploading the page as an image instead."
        )
    return text


class GeminiImageTranscriber:
    """Read the text out of an image with a Gemini vision model (free tier)."""

    def __init__(self, *, api_key: str, model: str) -> None:
        self._model = model
        self._client = genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(timeout=_HTTP_TIMEOUT_MS),
        )

    async def transcribe(self, data: bytes, mime_type: str) -> str:
        """Return the text visible in the image, exactly as the model reads it."""
        content = types.Content(
            role="user",
            parts=[
                types.Part.from_bytes(data=data, mime_type=mime_type),
                types.Part(text=_IMAGE_INSTRUCTION),
            ],
        )
        try:
            response = await self._client.aio.models.generate_content(
                model=self._model,
                contents=content,
                config=types.GenerateContentConfig(temperature=0.0),
            )
        except Exception as exc:
            raise MediaProviderError(f"Image transcription failed: {exc}") from exc

        text = (response.text or "").strip()
        if not text:
            raise MediaExtractionError("No legible text was found in the image.")
        return text


class GroqAudioTranscriber:
    """Transcribe a voice note with Groq's hosted Whisper (free tier)."""

    def __init__(self, *, api_key: str, model: str) -> None:
        self._model = model
        self._client = AsyncGroq(api_key=api_key)

    async def transcribe(self, data: bytes, mime_type: str) -> str:
        """Return the speech in the recording as plain text."""
        extension = _AUDIO_EXTENSION.get(mime_type, "webm")
        try:
            result = await self._client.audio.transcriptions.create(
                file=(f"claim.{extension}", data),
                model=self._model,
                temperature=0.0,
            )
        except Exception as exc:
            raise MediaProviderError(f"Voice transcription failed: {exc}") from exc

        text = result.text.strip()
        if not text:
            raise MediaExtractionError("No speech was heard in the recording.")
        return text
