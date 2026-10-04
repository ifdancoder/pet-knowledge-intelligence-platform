import logging

from infrastructure.observability.logging import JsonFormatter, TraceContextFilter
from infrastructure.observability.sentry import setup_sentry
from infrastructure.observability.tracing import setup_tracing


def configure_observability(*, service_name: str) -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    handler.addFilter(TraceContextFilter())
    logging.basicConfig(level=logging.INFO, handlers=[handler], force=True)

    setup_tracing(service_name=service_name)
    setup_sentry()
