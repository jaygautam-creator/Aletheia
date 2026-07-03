"""Request-scoped HTTP plumbing: request ids and request metrics, as pure ASGI.

Pure ASGI (no response wrapping) for the same reason as the rate limiter: the SSE
stream must pass through untouched.
"""

from __future__ import annotations

import time
import uuid
from contextvars import ContextVar

from starlette.datastructures import Headers, MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from aletheia.observability.metrics import HTTP_REQUEST_SECONDS, HTTP_REQUESTS

_REQUEST_ID_HEADER = "x-request-id"

# Read by the JSON log formatter so every log line names the request it belongs to.
request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)


class RequestIDMiddleware:
    """Give every request an id: honour an inbound ``X-Request-ID`` or mint one.

    The id is exposed to logging via :data:`request_id_var` for the request's
    lifetime and echoed on the response so a client error report can be matched
    to its server-side log lines.
    """

    def __init__(self, app: ASGIApp) -> None:
        self._app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self._app(scope, receive, send)
            return

        inbound = Headers(scope=scope).get(_REQUEST_ID_HEADER, "")
        request_id = inbound.strip()[:64] or uuid.uuid4().hex[:16]
        token = request_id_var.set(request_id)

        async def send_with_id(message: Message) -> None:
            if message["type"] == "http.response.start":
                MutableHeaders(scope=message)[_REQUEST_ID_HEADER] = request_id
            await send(message)

        try:
            await self._app(scope, receive, send_with_id)
        finally:
            request_id_var.reset(token)


class MetricsMiddleware:
    """Count and time every HTTP request by method, route template, and status.

    The route label is the template the router resolved (e.g. ``/verify``), never the
    raw path: requests that match no route collapse into ``(unmatched)`` so a URL
    scanner cannot mint unbounded label values. An exception before any response
    counts as a 500 and is re-raised for the server-error handler.
    """

    def __init__(self, app: ASGIApp) -> None:
        self._app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self._app(scope, receive, send)
            return

        status = "500"

        async def send_capturing(message: Message) -> None:
            nonlocal status
            if message["type"] == "http.response.start":
                status = str(message["status"])
            await send(message)

        start = time.perf_counter()
        try:
            await self._app(scope, receive, send_capturing)
        finally:
            # The router sets scope["route"] once a route matches — by now it has run.
            route = getattr(scope.get("route"), "path_format", None) or "(unmatched)"
            method: str = scope["method"]
            HTTP_REQUESTS.labels(method=method, route=route, status=status).inc()
            HTTP_REQUEST_SECONDS.labels(method=method, route=route).observe(
                time.perf_counter() - start
            )
