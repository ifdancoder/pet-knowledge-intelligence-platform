import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.integration

async def test_metrics_endpoint_exposes_http_request_series(client: AsyncClient) -> None:
    await client.get("/health")

    response = await client.get("/metrics")

    assert response.status_code == 200
    assert "http_requests_total" in response.text
