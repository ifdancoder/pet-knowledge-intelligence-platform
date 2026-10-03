from collections.abc import Iterator

import pytest
import redis
from testcontainers.redis import RedisContainer

from infrastructure.ingestion.locking import source_lock


@pytest.fixture(scope="module")
def redis_container() -> Iterator[RedisContainer]:
    with RedisContainer() as container:
        yield container


@pytest.fixture
def redis_client(redis_container: RedisContainer) -> redis.Redis:
    return redis.Redis(
        host=redis_container.get_container_host_ip(),
        port=int(redis_container.get_exposed_port(6379)),
    )


def test_lock_is_released_after_the_with_block(redis_client: redis.Redis) -> None:
    with source_lock(redis_client, "source-1"):
        assert redis_client.exists("ingestion-lock:source-1")
    assert not redis_client.exists("ingestion-lock:source-1")


def test_lock_rejects_concurrent_acquisition(redis_client: redis.Redis) -> None:
    with (
        source_lock(redis_client, "source-2"),
        pytest.raises(TimeoutError),
        source_lock(redis_client, "source-2", blocking_timeout=0.1),
    ):
        pass
