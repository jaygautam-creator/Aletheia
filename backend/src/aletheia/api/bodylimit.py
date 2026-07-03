"""Request body size cap for every API route.

A JSON verification request is a query plus optional pasted evidence — generous
headroom is a quarter megabyte, not gigabytes. Oversized declared bodies are
refused with a 413 sharing the limiter's JSON shape (a ``detail`` plus the
machine-readable limit); bodies with no declared length (chunked uploads, which
no browser or normal client sends for JSON) get a 411 rather than a mid-stream
abort, keeping the middleware free of half-sent-response edge cases.
"""

from __future__ import annotations

from starlette.datastructures import Headers
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

_BODY_METHODS = frozenset({"POST", "PUT", "PATCH"})


class BodySizeLimitMiddleware:
    """Reject requests whose declared body exceeds ``max_bytes``."""

    def __init__(self, app: ASGIApp, *, max_bytes: int) -> None:
        if max_bytes <= 0:
            raise ValueError("max_bytes must be positive")
        self._app = app
        self._max_bytes = max_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope["method"] not in _BODY_METHODS:
            await self._app(scope, receive, send)
            return

        headers = Headers(scope=scope)
        content_length = headers.get("content-length")
        if content_length is None:
            if headers.get("transfer-encoding", "").lower() == "chunked":
                response: JSONResponse = JSONResponse(
                    {"detail": "A declared Content-Length is required."}, status_code=411
                )
                await response(scope, receive, send)
                return
            # No body at all (e.g. a bare POST): nothing to limit.
            await self._app(scope, receive, send)
            return

        try:
            declared = int(content_length)
        except ValueError:
            declared = self._max_bytes + 1  # malformed header: refuse rather than trust

        if declared > self._max_bytes:
            response = JSONResponse(
                {
                    "detail": "Request body too large.",
                    "max_bytes": self._max_bytes,
                },
                status_code=413,
            )
            await response(scope, receive, send)
            return

        await self._app(scope, receive, send)
