from collections.abc import Iterator
from contextlib import contextmanager

import redis


@contextmanager
def source_lock(
    client: redis.Redis, source_id: str, *, blocking_timeout: float = 30.0
) -> Iterator[None]:
    lock = client.lock(f"ingestion-lock:{source_id}", timeout=300, blocking_timeout=blocking_timeout)
    acquired = lock.acquire()
    if not acquired:
        raise TimeoutError(f"could not acquire ingestion lock for source {source_id}")
    try:
        yield
    finally:
        lock.release()
