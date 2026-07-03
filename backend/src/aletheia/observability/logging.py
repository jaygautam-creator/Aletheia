"""Structured logging: one JSON object per line, carrying the request id.

``LOG_FORMAT=json`` is meant for the deployed demo (machine-collected logs);
the plain format stays the local-development default.
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Literal

from aletheia.observability.http import request_id_var

_PLAIN_FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"


class JsonLogFormatter(logging.Formatter):
    """Render each record as one JSON object: ts, level, logger, message, request_id."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "ts": datetime.fromtimestamp(record.created, tz=UTC).isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        request_id = request_id_var.get()
        if request_id is not None:
            payload["request_id"] = request_id
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def configure_logging(*, level: str, log_format: Literal["plain", "json"]) -> None:
    """Configure the root logger once at startup.

    Replaces (rather than appends to) the root handlers so repeated calls — test
    suites, dev reloads — never stack duplicate handlers. Uvicorn's own loggers keep
    their handlers; application loggers propagate to the root and land here.
    """
    handler = logging.StreamHandler()
    formatter: logging.Formatter = (
        JsonLogFormatter() if log_format == "json" else logging.Formatter(_PLAIN_FORMAT)
    )
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.setLevel(level.upper())
    root.handlers[:] = [handler]
