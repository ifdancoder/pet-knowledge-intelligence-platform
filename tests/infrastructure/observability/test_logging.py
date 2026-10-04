import json
import logging

from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from infrastructure.observability.logging import JsonFormatter, TraceContextFilter


def test_formats_a_record_without_trace_context_as_plain_json() -> None:
    record = logging.LogRecord("test.logger", logging.INFO, __file__, 1, "hello", None, None)
    TraceContextFilter().filter(record)

    payload = json.loads(JsonFormatter().format(record))

    assert payload["level"] == "INFO"
    assert payload["logger"] == "test.logger"
    assert payload["message"] == "hello"
    assert "trace_id" not in payload


def test_includes_trace_and_span_id_when_a_span_is_active() -> None:
    exporter = InMemorySpanExporter()
    provider = TracerProvider(resource=Resource.create({"service.name": "test"}))
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    tracer = provider.get_tracer(__name__)

    with tracer.start_as_current_span("test-span"):
        record = logging.LogRecord("test.logger", logging.INFO, __file__, 1, "hello", None, None)
        TraceContextFilter().filter(record)

    payload = json.loads(JsonFormatter().format(record))

    assert len(payload["trace_id"]) == 32
    assert len(payload["span_id"]) == 16
