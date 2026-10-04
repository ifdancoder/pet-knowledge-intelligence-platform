import json
import logging

from opentelemetry import trace


class TraceContextFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        context = trace.get_current_span().get_span_context()
        if context.is_valid:
            record.trace_id = format(context.trace_id, "032x")
            record.span_id = format(context.span_id, "016x")
        else:
            record.trace_id = None
            record.span_id = None
        return True


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, str] = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        trace_id = getattr(record, "trace_id", None)
        span_id = getattr(record, "span_id", None)
        if trace_id is not None:
            payload["trace_id"] = trace_id
        if span_id is not None:
            payload["span_id"] = span_id
        return json.dumps(payload)
