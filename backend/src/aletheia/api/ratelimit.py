"""Per-IP token-bucket rate limiting for the LLM-spending endpoints.

The public demo (ADR-0007) exposes ``/verify`` and ``/verify/stream`` backed by a
shared free-tier LLM key, so those routes — and only those; health and metadata stay
free — are guarded by a small token bucket per client IP: ``burst`` requests
immediately, refilled at ``per_minute``. Implemented as pure ASGI (no response
wrapping) so the SSE stream passes through untouched, and kept in-process on
purpose: with a single free-tier instance the counters are exact, and reaching for
shared state would contradict the D3 honesty rule.

Client identity is the socket peer address unless ``trust_proxy_headers`` is set,
in which case the *last* ``X-Forwarded-For`` entry — the one appended by the
platform's trusted proxy — is used instead. The leftmost entries are
client-supplied and trivially spoofable, which is also why the header is ignored
entirely by default.
"""

from __future__ import annotations

import math
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Final

from starlette.datastructures import Headers
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

GUARDED_PREFIX: Final = "/verify"

# Buckets are pruned once the table grows past this; entries idle long enough to have
# refilled completely carry no state worth keeping, so dropping them is lossless.
_MAX_BUCKETS: Final = 10_000


@dataclass
class _Bucket:
    tokens: float
    updated: float


class RateLimitMiddleware:
    """Token-bucket limiter over the ``/verify`` routes, one bucket per client IP.

    The whole request path is synchronous between the bucket read and write (no
    ``await`` in between), so single-threaded asyncio needs no lock here.
    ``clock`` is injectable for deterministic tests.
    """

    def __init__(
        self,
        app: ASGIApp,
        *,
        per_minute: int,
        burst: int,
        trust_proxy_headers: bool = False,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if per_minute <= 0:
            raise ValueError("per_minute must be positive; leave the middleware off to disable")
        if burst <= 0:
            raise ValueError("burst must be positive")
        self._app = app
        self._rate_per_second = per_minute / 60.0
        self._burst = float(burst)
        self._trust_proxy_headers = trust_proxy_headers
        self._clock = clock
        self._buckets: dict[str, _Bucket] = {}

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or not scope["path"].startswith(GUARDED_PREFIX):
            await self._app(scope, receive, send)
            return

        retry_after = self._take(self._client_key(scope))
        if retry_after is not None:
            # The 429 contract: Retry-After header plus a JSON body naming the wait —
            # the shared shape for every throttled response the API returns.
            response = JSONResponse(
                {
                    "detail": "Too many verification requests from this address; slow down.",
                    "retry_after_seconds": retry_after,
                },
                status_code=429,
                headers={"Retry-After": str(retry_after)},
            )
            await response(scope, receive, send)
            return

        await self._app(scope, receive, send)

    def _client_key(self, scope: Scope) -> str:
        if self._trust_proxy_headers:
            forwarded = Headers(scope=scope).get("x-forwarded-for")
            if forwarded:
                return forwarded.rsplit(",", 1)[-1].strip()
        client = scope.get("client")
        return client[0] if client else "unknown"

    def _take(self, key: str) -> int | None:
        """Consume one token for ``key``; return seconds to wait when empty."""
        now = self._clock()
        bucket = self._buckets.get(key)
        if bucket is None:
            if len(self._buckets) >= _MAX_BUCKETS:
                self._prune(now)
            bucket = self._buckets[key] = _Bucket(tokens=self._burst, updated=now)
        else:
            bucket.tokens = min(
                self._burst, bucket.tokens + (now - bucket.updated) * self._rate_per_second
            )
            bucket.updated = now
        if bucket.tokens >= 1.0:
            bucket.tokens -= 1.0
            return None
        return math.ceil((1.0 - bucket.tokens) / self._rate_per_second)

    def _prune(self, now: float) -> None:
        refill_window = self._burst / self._rate_per_second
        stale = [key for key, b in self._buckets.items() if now - b.updated >= refill_window]
        for key in stale:
            del self._buckets[key]
