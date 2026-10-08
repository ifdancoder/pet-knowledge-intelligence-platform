import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.integration


async def test_allowed_origin_gets_cors_header(client: AsyncClient) -> None:
    response = await client.get("/health", headers={"Origin": "http://localhost:5173"})
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"


async def test_disallowed_origin_gets_no_cors_header(client: AsyncClient) -> None:
    response = await client.get("/health", headers={"Origin": "http://evil.example.com"})
    assert response.status_code == 200
    assert "access-control-allow-origin" not in response.headers
