"""Request body size cap for every API route.

A JSON verification request is a query plus optional pasted evidence — generous
headroom is a quarter megabyte, not gigabytes — so that strict cap is the default.
Routes that legitimately carry more can be granted a larger cap by path prefix:
the only one today is ``/extract``, whose multipart upload (a PDF, an image, or a
voice note) is capped separately (ADR-0009). Oversized declared bodies are refused
with a 413 sharing the limiter's JSON shape (a ``detail`` plus the machine-readable
limit); bodies with no declared length (chunked uploads, which no browser or normal
client sends) get a 411 rather than a mid-stream abort, keeping the middleware free
of half-sent-response edge cases.
"""

from __future__ import annotations

from collections.abc import Mapping

from starlette.datastructures import Headers
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

_BODY_METHODS = frozenset({"POST", "PUT", "PATCH"})


class BodySizeLimitMiddleware:
    """Reject requests whose declared body exceeds the cap for their path.

    ``max_bytes`` governs every route; ``path_limits`` maps a path prefix to the
    cap used instead for requests under it (the longest matching prefix wins).
    """

    def __init__(
        self,
        app: ASGIApp,
        *,
        max_bytes: int,
        path_limits: Mapping[str, int] | None = None,
    ) -> None:
        if max_bytes <= 0:
            raise ValueError("max_bytes must be positive")
        if path_limits and any(limit <= 0 for limit in path_limits.values()):
            raise ValueError("every path limit must be positive")
        self._app = app
        self._max_bytes = max_bytes
        self._path_limits = dict(path_limits or {})

    def _limit_for(self, path: str) -> int:
        matches = [prefix for prefix in self._path_limits if path.startswith(prefix)]
        if not matches:
            return self._max_bytes
        return self._path_limits[max(matches, key=len)]

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope["method"] not in _BODY_METHODS:
            await self._app(scope, receive, send)
            return

        max_bytes = self._limit_for(scope["path"])
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
            declared = max_bytes + 1  # malformed header: refuse rather than trust

        if declared > max_bytes:
            response = JSONResponse(
                {
                    "detail": "Request body too large.",
                    "max_bytes": max_bytes,
                },
                status_code=413,
            )
            await response(scope, receive, send)
            return

        await self._app(scope, receive, send)
