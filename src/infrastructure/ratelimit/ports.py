from typing import Protocol


class RateLimiter(Protocol):
    async def check(self, *, key: str, limit: int, window_seconds: int) -> bool:
        """Returns True if the call is allowed (and counts it), False if the limit is exceeded."""
        ...
