from collections.abc import AsyncIterator, Iterator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession
from testcontainers.redis import RedisContainer

from infrastructure.database.session import get_db
from infrastructure.ratelimit.redis_limiter import RedisRateLimiter
from main import create_app
from presentation.api.auth.dependencies import get_rate_limiter

pytestmark = pytest.mark.integration

@pytest.fixture(scope="module")
def redis_container() -> Iterator[RedisContainer]:
    with RedisContainer() as container:
        yield container


@pytest_asyncio.fixture
async def rate_limited_client(
    db_session: AsyncSession, redis_container: RedisContainer
) -> AsyncIterator[AsyncClient]:
    redis_client = Redis(
        host=redis_container.get_container_host_ip(),
        port=int(redis_container.get_exposed_port(6379)),
    )
    limiter = RedisRateLimiter(redis_client)
    app = create_app()

    async def override_get_db() -> AsyncIterator[AsyncSession]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_rate_limiter] = lambda: limiter

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as test_client:
        yield test_client
    await redis_client.aclose()


async def test_sixth_login_attempt_from_the_same_ip_is_rate_limited(
    rate_limited_client: AsyncClient,
) -> None:
    for _ in range(5):
        response = await rate_limited_client.post(
            "/api/v1/auth/login", json={"email": "nobody@example.com", "password": "wrongpassword"}
        )
        assert response.status_code == 401

    response = await rate_limited_client.post(
        "/api/v1/auth/login", json={"email": "nobody@example.com", "password": "wrongpassword"}
    )
    assert response.status_code == 429
    assert response.json()["error"]["code"] == "rate_limit_exceeded"
