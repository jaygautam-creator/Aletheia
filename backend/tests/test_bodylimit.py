"""Tests for the request body size cap."""

from __future__ import annotations

import asyncio
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from aletheia.api.bodylimit import BodySizeLimitMiddleware
from aletheia.main import app as real_app


def _client(max_bytes: int) -> TestClient:
    app = FastAPI()

    @app.post("/echo")
    async def echo(payload: dict[str, str]) -> dict[str, str]:
        return payload

    @app.get("/health")
    async def health() -> dict[str, bool]:
        return {"ok": True}

    app.add_middleware(BodySizeLimitMiddleware, max_bytes=max_bytes)
    return TestClient(app)


def test_bodies_within_the_cap_pass_through() -> None:
    client = _client(max_bytes=1024)

    response = client.post("/echo", json={"q": "small"})

    assert response.status_code == 200
    assert response.json() == {"q": "small"}


def test_oversized_declared_bodies_are_refused_with_the_shared_shape() -> None:
    client = _client(max_bytes=64)

    response = client.post("/echo", json={"q": "x" * 200})

    assert response.status_code == 413
    body = response.json()
    assert body["max_bytes"] == 64
    assert "too large" in body["detail"]


def test_chunked_bodies_without_a_length_get_411() -> None:
    client = _client(max_bytes=1024)

    # An iterable body makes httpx send Transfer-Encoding: chunked with no length.
    response = client.post("/echo", content=iter([b'{"q": "chunked"}']))

    assert response.status_code == 411


def test_bodyless_methods_are_never_limited() -> None:
    client = _client(max_bytes=1)

    assert client.get("/health").status_code == 200


def test_a_malformed_length_is_refused_rather_than_trusted() -> None:
    # Crafted at the ASGI level: an HTTP client library won't emit a bad length.
    middleware = BodySizeLimitMiddleware(FastAPI(), max_bytes=1024)
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/echo",
        "headers": [(b"content-length", b"not-a-number")],
    }
    sent: list[dict[str, Any]] = []

    async def receive() -> dict[str, Any]:  # pragma: no cover - never called
        return {"type": "http.request"}

    async def send(message: dict[str, Any]) -> None:
        sent.append(message)

    asyncio.run(middleware(scope, receive, send))

    assert sent[0]["type"] == "http.response.start"
    assert sent[0]["status"] == 413


def test_misconfiguration_fails_loudly() -> None:
    with pytest.raises(ValueError):
        BodySizeLimitMiddleware(FastAPI(), max_bytes=0)


def test_the_real_app_carries_the_cap() -> None:
    client = TestClient(real_app)

    response = client.post("/verify", json={"query": "q", "evidence": "e" * 400_000})

    assert response.status_code == 413
