import time
from collections import defaultdict
from dataclasses import dataclass

from fastapi import HTTPException, Request, status

_DEFAULT_MAX_REQUESTS = 20
_DEFAULT_WINDOW_SECONDS = 60.0


@dataclass
class _Window:
    count: int = 0
    reset_at: float = 0.0


class RateLimiter:
    """Fixed-window rate limiter keyed by client IP.

    In-process only, so limits are per-replica rather than global — move to a
    shared store (e.g. Redis) if this service ever runs with multiple replicas.
    """

    def __init__(
        self,
        max_requests: int = _DEFAULT_MAX_REQUESTS,
        window_seconds: float = _DEFAULT_WINDOW_SECONDS,
    ) -> None:
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._windows: dict[str, _Window] = defaultdict(_Window)

    async def __call__(self, request: Request) -> None:
        key = request.client.host if request.client else "unknown"
        now = time.monotonic()
        window = self._windows[key]
        if now >= window.reset_at:
            window.count = 0
            window.reset_at = now + self.window_seconds
        window.count += 1
        if window.count > self.max_requests:
            retry_after = max(0, int(window.reset_at - now))
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded",
                headers={"Retry-After": str(retry_after)},
            )


ai_rate_limiter = RateLimiter()
