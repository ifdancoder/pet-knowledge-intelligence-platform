import os
from collections.abc import Awaitable, Callable

from fastapi import Depends, Header, Request
from redis.asyncio import Redis

from domain.auth.exceptions import InvalidAccessTokenError, RateLimitExceededError
from infrastructure.ratelimit.ports import RateLimiter
from infrastructure.ratelimit.redis_limiter import RedisRateLimiter
from infrastructure.security.tokens import decode_access_token


async def get_current_user_id(authorization: str = Header(...)) -> str:
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise InvalidAccessTokenError("missing bearer token")
    return decode_access_token(token)


_redis_client = Redis.from_url(os.environ.get("REDIS_URL", "redis://localhost:6380/0"))
_rate_limiter = RedisRateLimiter(_redis_client)


def get_rate_limiter() -> RateLimiter:
    return _rate_limiter


def rate_limit(*, limit: int, window_seconds: int) -> Callable[..., Awaitable[None]]:
    async def check(request: Request, limiter: RateLimiter = Depends(get_rate_limiter)) -> None:
        client_host = request.client.host if request.client else "unknown"
        key = f"ratelimit:{request.url.path}:{client_host}"
        if not await limiter.check(key=key, limit=limit, window_seconds=window_seconds):
            raise RateLimitExceededError("Too many requests, try again later.")

    return check
