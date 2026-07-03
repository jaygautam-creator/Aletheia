"""Right-sized observability: Prometheus metrics, request ids, structured logs.

Deliberately small (master plan D2): a hand-rolled metric surface on the default
prometheus-client registry, two pure-ASGI middlewares (request id, HTTP metrics),
and a JSON log formatter — no tracing stack, no k8s observability.
"""

from aletheia.observability.http import MetricsMiddleware, RequestIDMiddleware, request_id_var
from aletheia.observability.logging import JsonLogFormatter, configure_logging
from aletheia.observability.metrics import timed_stages

__all__ = [
    "JsonLogFormatter",
    "MetricsMiddleware",
    "RequestIDMiddleware",
    "configure_logging",
    "request_id_var",
    "timed_stages",
]
