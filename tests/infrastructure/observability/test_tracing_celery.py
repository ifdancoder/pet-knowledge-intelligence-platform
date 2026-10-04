from celery import Celery
from opentelemetry import trace
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter


def test_a_celery_task_execution_produces_a_span() -> None:
    exporter = InMemorySpanExporter()
    trace.get_tracer_provider().add_span_processor(SimpleSpanProcessor(exporter))

    app = Celery("test-app-tracing")
    app.conf.task_always_eager = True

    @app.task(name="tracing_test_task")
    def add(a: int, b: int) -> int:
        return a + b

    result = add.delay(1, 2)

    assert result.get() == 3
    spans = exporter.get_finished_spans()
    assert any("tracing_test_task" in s.name for s in spans)
