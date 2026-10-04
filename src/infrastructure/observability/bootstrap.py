import logging

from infrastructure.observability.logging import JsonFormatter, TraceContextFilter


def configure_observability(*, service_name: str) -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    handler.addFilter(TraceContextFilter())
    logging.basicConfig(level=logging.INFO, handlers=[handler], force=True)
