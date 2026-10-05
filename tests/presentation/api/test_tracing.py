import pytest
from httpx import AsyncClient
from opentelemetry import trace
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

pytestmark = pytest.mark.integration

async def test_a_request_produces_a_span(client: AsyncClient) -> None:
    exporter = InMemorySpanExporter()
    trace.get_tracer_provider().add_span_processor(SimpleSpanProcessor(exporter))

    response = await client.get("/health")

    assert response.status_code == 200
    spans = exporter.get_finished_spans()
    assert len(spans) >= 1
