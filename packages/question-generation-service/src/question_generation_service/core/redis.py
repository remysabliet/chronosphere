"""Process-wide Redis client, shared by the background workers (streams
broker) and the SSE endpoint (pub/sub) — one connection pool per process.
"""

from redis.asyncio import Redis

from question_generation_service.core.config import get_settings

_client: Redis | None = None


def get_redis_client() -> Redis:
    global _client  # noqa: PLW0603 — module-level singleton, mirror of db/session's engine
    if _client is None:
        _client = Redis.from_url(  # pyright: ignore[reportUnknownMemberType]
            get_settings().REDIS_URL, decode_responses=True
        )
    return _client


async def close_redis_client() -> None:
    global _client  # noqa: PLW0603
    if _client is not None:
        await _client.aclose()
        _client = None
