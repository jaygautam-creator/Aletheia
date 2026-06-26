"""Tests for the system/health endpoints."""

from __future__ import annotations

from fastapi.testclient import TestClient

from aletheia import __version__
from aletheia.main import app

client = TestClient(app)


def test_health_returns_ok() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["service"] == "aletheia-backend"
    assert body["version"] == __version__


def test_root_returns_service_metadata() -> None:
    response = client.get("/")

    assert response.status_code == 200
    body = response.json()
    assert body["service"] == "aletheia-backend"
    assert body["health"] == "/health"
