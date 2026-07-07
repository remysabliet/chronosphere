"""Drives RedisStreamsBroker through the real redis-py client against a live
Redis (the compose container). Skips cleanly when Redis is unreachable."""

import os
from collections.abc import AsyncIterator
from typing import cast
from uuid import uuid4

import pytest
import pytest_asyncio
from redis.asyncio import Redis
from redis.exceptions import RedisError

from memosphere_messaging import PAYLOAD_FIELD, Message, RedisStreamsBroker, StreamsClient

pytestmark = pytest.mark.asyncio

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379")


@pytest_asyncio.fixture
async def redis_client() -> AsyncIterator[Redis]:
    client: Redis = Redis.from_url(  # pyright: ignore[reportUnknownMemberType]
        REDIS_URL, decode_responses=True, socket_connect_timeout=1
    )
    try:
        await client.ping()  # pyright: ignore[reportUnknownMemberType]
    except (RedisError, OSError):
        pytest.skip(f"Redis not reachable at {REDIS_URL}")
    yield client
    await client.aclose()


@pytest_asyncio.fixture
async def topic(redis_client: Redis) -> AsyncIterator[str]:
    name = f"itest:{uuid4().hex}"
    yield name
    await redis_client.delete(name, f"{name}.dlq")


def broker_for(redis_client: Redis) -> RedisStreamsBroker:
    # redis-py's method signatures are broader unions than StreamsClient's
    # (sync/async overloads); runtime behaviour is what this test verifies.
    return RedisStreamsBroker(cast(StreamsClient, redis_client))


async def test_publish_consume_roundtrip_against_real_redis(
    redis_client: Redis, topic: str
) -> None:
    broker = broker_for(redis_client)
    await broker.ensure_group(topic, "g0")
    await broker.ensure_group(topic, "g0")  # idempotent: real BUSYGROUP swallowed

    await broker.publish(topic, {"quiz_id": "q1", "bucket": {"bloom": "Applying", "n": 5}})
    await broker.publish(topic, {"quiz_id": "q2", "bucket": None})

    seen: list[Message] = []

    async def handler(message: Message) -> None:
        seen.append(message)

    processed = await broker.consume_once(topic, "g0", "c1", handler, block_ms=100)

    assert processed == 2
    assert [m.payload for m in seen] == [
        {"quiz_id": "q1", "bucket": {"bloom": "Applying", "n": 5}},
        {"quiz_id": "q2", "bucket": None},
    ]
    pending = await redis_client.xpending(topic, "g0")  # pyright: ignore[reportUnknownMemberType]
    assert pending["pending"] == 0


async def test_failed_handler_leaves_message_pending_on_real_redis(
    redis_client: Redis, topic: str
) -> None:
    broker = broker_for(redis_client)
    await broker.ensure_group(topic, "g0")
    await broker.publish(topic, {"will": "fail"})

    async def handler(message: Message) -> None:
        raise ValueError("boom")

    processed = await broker.consume_once(topic, "g0", "c1", handler, block_ms=100)

    assert processed == 0
    pending = await redis_client.xpending(topic, "g0")  # pyright: ignore[reportUnknownMemberType]
    assert pending["pending"] == 1  # unacked → redeliverable via XAUTOCLAIM


async def test_undecodable_payload_lands_in_dlq_on_real_redis(
    redis_client: Redis, topic: str
) -> None:
    broker = broker_for(redis_client)
    await broker.ensure_group(topic, "g0")
    await redis_client.xadd(topic, {PAYLOAD_FIELD: "not json"})  # pyright: ignore[reportUnknownMemberType]

    async def handler(message: Message) -> None:
        raise AssertionError("should not be called")

    processed = await broker.consume_once(topic, "g0", "c1", handler, block_ms=100)

    assert processed == 0
    assert await redis_client.xlen(f"{topic}.dlq") == 1  # pyright: ignore[reportUnknownMemberType]
    pending = await redis_client.xpending(topic, "g0")  # pyright: ignore[reportUnknownMemberType]
    assert pending["pending"] == 0  # acked away from the group
