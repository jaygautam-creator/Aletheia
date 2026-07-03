"""Tests for request-id propagation and the structured JSON log formatter."""

from __future__ import annotations

import json
import logging
import sys

from fastapi.testclient import TestClient

from aletheia.main import app
from aletheia.observability import JsonLogFormatter, configure_logging, request_id_var

client = TestClient(app)


def _record(message: str, *, exc_info: bool = False) -> logging.LogRecord:
    exc: tuple[object, object, object] | None = None
    if exc_info:
        try:
            raise ValueError("boom")
        except ValueError:
            exc = sys.exc_info()
    return logging.LogRecord(
        name="aletheia.test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="%s",
        args=(message,),
        exc_info=exc,  # type: ignore[arg-type]
    )


def test_every_response_carries_a_request_id() -> None:
    response = client.get("/health")

    assert len(response.headers["x-request-id"]) == 16  # minted uuid fragment


def test_an_inbound_request_id_is_honoured() -> None:
    response = client.get("/health", headers={"X-Request-ID": "trace-me-42"})

    assert response.headers["x-request-id"] == "trace-me-42"


def test_json_formatter_emits_one_parseable_object_with_the_request_id() -> None:
    token = request_id_var.set("req-abc")
    try:
        line = JsonLogFormatter().format(_record("hello world"))
    finally:
        request_id_var.reset(token)

    payload = json.loads(line)
    assert payload["message"] == "hello world"
    assert payload["level"] == "INFO"
    assert payload["logger"] == "aletheia.test"
    assert payload["request_id"] == "req-abc"
    assert "ts" in payload


def test_json_formatter_includes_exceptions_and_omits_a_missing_request_id() -> None:
    line = JsonLogFormatter().format(_record("it failed", exc_info=True))

    payload = json.loads(line)
    assert "request_id" not in payload
    assert "ValueError: boom" in payload["exception"]


def test_configure_logging_replaces_rather_than_stacks_handlers() -> None:
    configure_logging(level="INFO", log_format="json")
    configure_logging(level="DEBUG", log_format="plain")

    root = logging.getLogger()
    assert len(root.handlers) == 1
    assert root.level == logging.DEBUG
    assert not isinstance(root.handlers[0].formatter, JsonLogFormatter)

    configure_logging(level="INFO", log_format="json")
    assert isinstance(logging.getLogger().handlers[0].formatter, JsonLogFormatter)
