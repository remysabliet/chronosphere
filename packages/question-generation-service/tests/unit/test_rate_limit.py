import time

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from question_generation_service.dependencies.rate_limit import RateLimiter


def _request(ip: str = "1.2.3.4") -> Request:
    return Request(scope={"type": "http", "client": (ip, 12345), "headers": []})


class TestRateLimiter:
    @pytest.mark.asyncio
    async def test_allows_requests_under_limit(self):
        limiter = RateLimiter(max_requests=2, window_seconds=60)
        await limiter(_request())
        await limiter(_request())

    @pytest.mark.asyncio
    async def test_blocks_requests_over_limit(self):
        limiter = RateLimiter(max_requests=1, window_seconds=60)
        await limiter(_request())
        with pytest.raises(HTTPException) as exc_info:
            await limiter(_request())
        assert exc_info.value.status_code == 429
        assert exc_info.value.headers is not None
        assert "Retry-After" in exc_info.value.headers

    @pytest.mark.asyncio
    async def test_resets_after_window_elapses(self):
        limiter = RateLimiter(max_requests=1, window_seconds=30)
        await limiter(_request())
        limiter._windows["1.2.3.4"].reset_at = time.monotonic() - 1
        await limiter(_request())

    @pytest.mark.asyncio
    async def test_tracks_separate_clients_independently(self):
        limiter = RateLimiter(max_requests=1, window_seconds=60)
        await limiter(_request("1.1.1.1"))
        await limiter(_request("2.2.2.2"))
