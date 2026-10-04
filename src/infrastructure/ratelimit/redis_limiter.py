from redis.asyncio import Redis


class RedisRateLimiter:
    def __init__(self, client: Redis) -> None:
        self._client = client

    async def check(self, *, key: str, limit: int, window_seconds: int) -> bool:
        count = await self._client.incr(key)
        if count == 1:
            await self._client.expire(key, window_seconds)
        return count <= limit
