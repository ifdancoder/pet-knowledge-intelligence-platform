import asyncio
from collections.abc import AsyncIterator, Iterator

import pytest
import pytest_asyncio
from redis.asyncio import Redis
from testcontainers.redis import RedisContainer

from infrastructure.ratelimit.redis_limiter import RedisRateLimiter

pytestmark = pytest.mark.integration

@pytest.fixture(scope="module")
def redis_container() -> Iterator[RedisContainer]:
    with RedisContainer() as container:
        yield container


@pytest_asyncio.fixture
async def redis_client(redis_container: RedisContainer) -> AsyncIterator[Redis]:
    client = Redis(
        host=redis_container.get_container_host_ip(),
        port=int(redis_container.get_exposed_port(6379)),
    )
    yield client
    await client.aclose()


async def test_allows_calls_up_to_the_limit_then_blocks(redis_client: Redis) -> None:
    limiter = RedisRateLimiter(redis_client)
    for _ in range(3):
        assert await limiter.check(key="k1", limit=3, window_seconds=60) is True
    assert await limiter.check(key="k1", limit=3, window_seconds=60) is False


async def test_resets_after_the_window_expires(redis_client: Redis) -> None:
    limiter = RedisRateLimiter(redis_client)
    assert await limiter.check(key="k2", limit=1, window_seconds=1) is True
    assert await limiter.check(key="k2", limit=1, window_seconds=1) is False
    await asyncio.sleep(1.2)
    assert await limiter.check(key="k2", limit=1, window_seconds=1) is True
