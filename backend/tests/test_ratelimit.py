"""Tests for the per-IP token-bucket rate limiter guarding the /verify routes."""

from __future__ import annotations

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from aletheia.api.ratelimit import RateLimitMiddleware
from aletheia.api.routes.verify import get_pipeline
from aletheia.config import Settings
from aletheia.main import create_app


class FakeClock:
    """A monotonic clock the tests advance by hand."""

    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


def _guarded_client(
    *,
    per_minute: int,
    burst: int,
    trust_proxy_headers: bool = False,
    clock: FakeClock | None = None,
) -> TestClient:
    """A stub app with the middleware armed: /verify spends tokens, /health is free."""
    app = FastAPI()

    @app.post("/verify")
    async def verify_stub() -> dict[str, bool]:
        return {"ok": True}

    @app.post("/verify/stream")
    async def stream_stub() -> dict[str, bool]:
        return {"ok": True}

    @app.get("/health")
    async def health_stub() -> dict[str, bool]:
        return {"ok": True}

    app.add_middleware(
        RateLimitMiddleware,
        per_minute=per_minute,
        burst=burst,
        trust_proxy_headers=trust_proxy_headers,
        clock=clock if clock is not None else FakeClock(),
    )
    return TestClient(app)


def test_burst_is_allowed_then_throttled_with_the_shared_429_shape() -> None:
    client = _guarded_client(per_minute=60, burst=3)

    assert all(client.post("/verify").status_code == 200 for _ in range(3))

    throttled = client.post("/verify")
    assert throttled.status_code == 429
    body = throttled.json()
    assert "slow down" in body["detail"]
    assert body["retry_after_seconds"] == 1  # 60/min refills one token per second
    assert throttled.headers["Retry-After"] == "1"


def test_tokens_refill_at_the_configured_rate() -> None:
    clock = FakeClock()
    client = _guarded_client(per_minute=6, burst=1, clock=clock)  # one token per 10s

    assert client.post("/verify").status_code == 200
    denied = client.post("/verify")
    assert denied.status_code == 429
    assert denied.json()["retry_after_seconds"] == 10

    clock.advance(10.0)
    assert client.post("/verify").status_code == 200


def test_the_stream_route_shares_the_guard_and_health_stays_free() -> None:
    client = _guarded_client(per_minute=60, burst=1)

    assert client.post("/verify/stream").status_code == 200
    assert client.post("/verify/stream").status_code == 429
    # Health (and anything outside /verify) never spends a token.
    assert all(client.get("/health").status_code == 200 for _ in range(10))


def test_forwarded_header_is_ignored_unless_proxies_are_trusted() -> None:
    client = _guarded_client(per_minute=60, burst=1)

    # Rotating X-Forwarded-For must not mint fresh buckets on a direct exposure.
    assert client.post("/verify", headers={"X-Forwarded-For": "1.1.1.1"}).status_code == 200
    assert client.post("/verify", headers={"X-Forwarded-For": "2.2.2.2"}).status_code == 429


def test_trusted_proxy_uses_the_last_forwarded_entry() -> None:
    client = _guarded_client(per_minute=60, burst=1, trust_proxy_headers=True)

    # The last entry is the one the platform proxy appended; the leftmost is
    # client-supplied. Spoofing the left side must not escape the bucket.
    real = {"X-Forwarded-For": "9.9.9.9, 3.3.3.3"}
    spoofed = {"X-Forwarded-For": "8.8.8.8, 3.3.3.3"}
    assert client.post("/verify", headers=real).status_code == 200
    assert client.post("/verify", headers=spoofed).status_code == 429

    other = {"X-Forwarded-For": "9.9.9.9, 4.4.4.4"}
    assert client.post("/verify", headers=other).status_code == 200


def test_misconfigured_limits_fail_loudly() -> None:
    # Constructed directly: add_middleware defers instantiation to app startup,
    # which would hide the constructor's validation from this test.
    with pytest.raises(ValueError):
        RateLimitMiddleware(FastAPI(), per_minute=0, burst=1)
    with pytest.raises(ValueError):
        RateLimitMiddleware(FastAPI(), per_minute=60, burst=0)


def test_production_refuses_to_start_without_a_rate_limit() -> None:
    settings = Settings(_env_file=None, app_env="production", rate_limit_per_minute=0)

    with pytest.raises(RuntimeError, match="RATE_LIMIT_PER_MINUTE"):
        create_app(settings)


def test_production_app_arms_the_limiter_over_verify() -> None:
    settings = Settings(
        _env_file=None, app_env="production", rate_limit_per_minute=60, rate_limit_burst=1
    )
    app = create_app(settings)

    def _unavailable() -> None:
        raise HTTPException(status_code=503, detail="no provider key in this test")

    app.dependency_overrides[get_pipeline] = _unavailable
    client = TestClient(app)

    # First request spends the single burst token and reaches the route (503 from the
    # stub dependency proves it got through); the second is throttled by the middleware.
    assert client.post("/verify", json={"query": "q"}).status_code == 503
    assert client.post("/verify", json={"query": "q"}).status_code == 429
    # The development default (rate_limit_per_minute=0) leaves the app un-throttled,
    # which the rest of the suite exercises implicitly on every request.
