"""Tests for the /extract claim-intake endpoint — no live provider calls."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

import aletheia.api.routes.extract as extract_module
from aletheia.api.routes.extract import get_audio_transcriber, get_image_transcriber
from aletheia.config import Settings
from aletheia.main import app
from aletheia.media import MediaExtractionError, MediaProviderError


class _StaticTranscriber:
    """A scripted transcriber that records what the route hands it."""

    def __init__(self, text: str = "", error: Exception | None = None) -> None:
        self._text = text
        self._error = error
        self.calls: list[tuple[bytes, str]] = []

    async def transcribe(self, data: bytes, mime_type: str) -> str:
        self.calls.append((data, mime_type))
        if self._error is not None:
            raise self._error
        return self._text


def _client(
    image: _StaticTranscriber | None = None, audio: _StaticTranscriber | None = None
) -> TestClient:
    if image is not None:
        app.dependency_overrides[get_image_transcriber] = lambda: lambda: image
    if audio is not None:
        app.dependency_overrides[get_audio_transcriber] = lambda: lambda: audio
    return TestClient(app)


@pytest.fixture(autouse=True)
def _clear_overrides() -> Iterator[None]:
    yield
    app.dependency_overrides.clear()


def _pdf_with_text(text: str) -> bytes:
    """Build a minimal one-page PDF containing ``text``, with a correct xref table."""
    stream = f"BT /F1 12 Tf 72 720 Td ({text}) Tj ET".encode()
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
        b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    out = bytearray(b"%PDF-1.4\n")
    offsets: list[int] = []
    for number, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{number} 0 obj\n".encode() + body + b"\nendobj\n"
    xref_at = len(out)
    out += f"xref\n0 {len(objects) + 1}\n".encode()
    out += b"0000000000 65535 f \n"
    for offset in offsets:
        out += f"{offset:010d} 00000 n \n".encode()
    out += (
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_at}\n%%EOF\n"
    ).encode()
    return bytes(out)


def test_pdf_upload_returns_its_text() -> None:
    client = _client()

    response = client.post(
        "/extract",
        files={"file": ("claim.pdf", _pdf_with_text("Aspirin reduces risk."), "application/pdf")},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["kind"] == "pdf"
    assert "Aspirin reduces risk." in body["text"]
    assert body["characters"] == len(body["text"])
    assert body["truncated"] is False


def test_a_pdf_with_no_text_layer_is_a_client_error() -> None:
    client = _client()

    response = client.post(
        "/extract", files={"file": ("scan.pdf", _pdf_with_text(""), "application/pdf")}
    )

    assert response.status_code == 422
    assert "scanned" in response.json()["detail"]


def test_unreadable_pdf_bytes_are_a_client_error() -> None:
    client = _client()

    response = client.post(
        "/extract", files={"file": ("junk.pdf", b"not a pdf at all", "application/pdf")}
    )

    assert response.status_code == 422


def test_image_upload_transcribes_via_the_vision_model() -> None:
    image = _StaticTranscriber(text="ALDH1 predicts poor prognosis.")
    client = _client(image=image)

    response = client.post("/extract", files={"file": ("claim.png", b"\x89PNG...", "image/png")})

    assert response.status_code == 200
    body = response.json()
    assert body["kind"] == "image"
    assert body["text"] == "ALDH1 predicts poor prognosis."
    assert image.calls == [(b"\x89PNG...", "image/png")]


def test_audio_upload_strips_codec_parameters_before_dispatch() -> None:
    audio = _StaticTranscriber(text="Does aspirin protect the heart?")
    client = _client(audio=audio)

    response = client.post(
        "/extract", files={"file": ("note.webm", b"\x1aE\xdf\xa3...", "audio/webm;codecs=opus")}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["kind"] == "audio"
    assert body["text"] == "Does aspirin protect the heart?"
    # The route hands the transcriber the bare MIME type, parameters stripped.
    assert audio.calls[0][1] == "audio/webm"


def test_unsupported_types_get_415_with_the_allowed_kinds() -> None:
    client = _client()

    response = client.post("/extract", files={"file": ("claim.txt", b"hello", "text/plain")})

    assert response.status_code == 415
    assert "PDF" in response.json()["detail"]


def test_an_empty_upload_is_refused() -> None:
    client = _client()

    response = client.post("/extract", files={"file": ("empty.png", b"", "image/png")})

    assert response.status_code == 422
    assert "empty" in response.json()["detail"]


def test_a_provider_failure_maps_to_502() -> None:
    audio = _StaticTranscriber(error=MediaProviderError("Voice transcription failed: boom"))
    client = _client(audio=audio)

    response = client.post("/extract", files={"file": ("note.wav", b"RIFF...", "audio/wav")})

    assert response.status_code == 502


def test_an_illegible_image_maps_to_422() -> None:
    image = _StaticTranscriber(error=MediaExtractionError("No legible text was found."))
    client = _client(image=image)

    response = client.post("/extract", files={"file": ("blur.jpg", b"\xff\xd8...", "image/jpeg")})

    assert response.status_code == 422


def test_long_extractions_are_truncated_to_the_cap() -> None:
    cap = Settings(_env_file=None).extract_max_chars
    image = _StaticTranscriber(text="x" * (cap + 500))
    client = _client(image=image)

    response = client.post("/extract", files={"file": ("wall.png", b"\x89PNG...", "image/png")})

    assert response.status_code == 200
    body = response.json()
    assert body["truncated"] is True
    assert body["characters"] == cap
    assert len(body["text"]) == cap


def test_missing_provider_keys_surface_as_503(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setattr(extract_module, "get_settings", lambda: Settings(_env_file=None))
    extract_module._image_transcriber.cache_clear()
    client = TestClient(app)

    response = client.post("/extract", files={"file": ("claim.png", b"\x89PNG...", "image/png")})

    assert response.status_code == 503
    assert "GEMINI_API_KEY" in response.json()["detail"]
    extract_module._image_transcriber.cache_clear()
