"""Queue seam shared across Memosphere's Python services.

Transport today is Redis Streams with consumer groups; on AWS the same
interface fronts SQS/SNS. Services depend on this module, never on the
transport. Topic conventions: `jobs:*` (one consumer group, retried work)
and `events:*` (fan-out — one group per consuming service).

Delivery semantics: a message is acked only after its handler returns, so a
crash mid-handler leaves it pending for redelivery (at-least-once — handlers
must be idempotent). Undecodable payloads are moved to `<topic>.dlq` instead
of poisoning the group.
"""

import json
import logging
from collections.abc import AsyncIterator, Awaitable, Callable, Mapping
from dataclasses import dataclass
from typing import Protocol

logger = logging.getLogger(__name__)

JsonValue = str | int | float | bool | None | list["JsonValue"] | dict[str, "JsonValue"]
Payload = Mapping[str, JsonValue]

PAYLOAD_FIELD = "payload"

# Shape redis-py returns for XREADGROUP with decode_responses=True:
# [(stream, [(message_id, {field: value}), ...]), ...]
StreamBatch = list[tuple[str, list[tuple[str, dict[str, str]]]]]


@dataclass(frozen=True)
class Message:
    id: str
    topic: str
    payload: dict[str, JsonValue]


MessageHandler = Callable[[Message], Awaitable[None]]


def _decode_json_object(raw: str | None) -> dict[str, JsonValue] | None:
    if raw is None:
        return None
    try:
        decoded: JsonValue = json.loads(raw)
    except json.JSONDecodeError:
        return None
    if not isinstance(decoded, dict):
        return None
    return decoded


# Shape redis-py's XAUTOCLAIM returns: (next_cursor, claimed_entries, deleted_ids).
AutoclaimResult = tuple[str, list[tuple[str, dict[str, str]]], list[str]]
# Shape redis-py's XPENDING RANGE returns per entry.
PendingEntry = Mapping[str, object]


class StreamsClient(Protocol):
    """The slice of redis.asyncio.Redis this module uses — structural, so the
    real client and test fakes both fit without a hard redis dependency here.
    """

    async def xadd(self, name: str, fields: Mapping[str, str]) -> str: ...

    async def xgroup_create(self, name: str, groupname: str, id: str, mkstream: bool) -> bool: ...

    async def xreadgroup(
        self,
        groupname: str,
        consumername: str,
        streams: Mapping[str, str],
        count: int,
        block: int,
    ) -> StreamBatch | None: ...

    async def xack(self, name: str, groupname: str, *ids: str) -> int: ...

    async def xautoclaim(
        self,
        name: str,
        groupname: str,
        consumername: str,
        min_idle_time: int,
        start_id: str = "0-0",
        count: int | None = None,
    ) -> AutoclaimResult: ...

    async def xpending_range(
        self, name: str, groupname: str, min: str, max: str, count: int
    ) -> list[PendingEntry]: ...


class PubSubChannel(Protocol):
    """The slice of redis.asyncio.client.PubSub this module uses."""

    async def subscribe(self, *channels: str) -> None: ...

    async def unsubscribe(self, *channels: str) -> None: ...

    async def get_message(
        self, ignore_subscribe_messages: bool = False, timeout: float | None = 0.0
    ) -> Mapping[str, object] | None: ...

    async def aclose(self) -> None: ...


class PubSubClient(Protocol):
    """The slice of redis.asyncio.Redis the pub/sub seam uses."""

    async def publish(self, channel: str, message: str) -> int: ...

    def pubsub(self) -> PubSubChannel: ...


class EventPublisher(Protocol):
    async def publish_event(self, channel: str, payload: Payload) -> None: ...


class EventSubscriber(Protocol):
    def subscribe(
        self, channel: str, idle_timeout_s: float = 15.0
    ) -> AsyncIterator[dict[str, JsonValue] | None]: ...


class Broker(Protocol):
    async def publish(self, topic: str, payload: Payload) -> str: ...

    async def ensure_group(self, topic: str, group: str) -> None: ...

    async def consume_once(
        self,
        topic: str,
        group: str,
        consumer: str,
        handler: MessageHandler,
        count: int = 10,
        block_ms: int = 5000,
    ) -> int: ...

    async def reclaim_stale(
        self,
        topic: str,
        group: str,
        consumer: str,
        handler: MessageHandler,
        min_idle_ms: int,
        count: int = 10,
        max_deliveries: int = 5,
    ) -> int: ...


class RedisStreamsBroker:
    def __init__(self, client: StreamsClient):
        self.client = client

    async def publish(self, topic: str, payload: Payload) -> str:
        return await self.client.xadd(topic, {PAYLOAD_FIELD: json.dumps(dict(payload))})

    async def ensure_group(self, topic: str, group: str) -> None:
        # id="0" so a new group also sees messages published before it existed.
        try:
            await self.client.xgroup_create(topic, group, id="0", mkstream=True)
        except Exception as exc:  # noqa: BLE001 — no redis import here for ResponseError
            if "BUSYGROUP" not in str(exc):
                raise

    async def consume_once(
        self,
        topic: str,
        group: str,
        consumer: str,
        handler: MessageHandler,
        count: int = 10,
        block_ms: int = 5000,
    ) -> int:
        batch = await self.client.xreadgroup(
            group, consumer, {topic: ">"}, count=count, block=block_ms
        )
        if not batch:
            return 0
        processed = 0
        for _stream, entries in batch:
            for message_id, fields in entries:
                if await self._process_entry(topic, group, message_id, fields, handler):
                    processed += 1
        return processed

    async def reclaim_stale(
        self,
        topic: str,
        group: str,
        consumer: str,
        handler: MessageHandler,
        min_idle_ms: int,
        count: int = 10,
        max_deliveries: int = 5,
    ) -> int:
        """Claims entries idle longer than min_idle_ms and retries them
        through `handler` — the redelivery path this module's docstring
        promises ("a crash mid-handler leaves it pending for redelivery")
        but consume_once alone never performs, since XREADGROUP with '>'
        only ever reads brand-new entries. Call this periodically alongside
        consume_once, not instead of it. A message still failing past
        max_deliveries is dead-lettered instead of retried forever.
        """
        _next_id, claimed, _deleted = await self.client.xautoclaim(
            topic, group, consumer, min_idle_time=min_idle_ms, start_id="0-0", count=count
        )
        processed = 0
        for message_id, fields in claimed:
            deliveries = await self._delivery_count(topic, group, message_id)
            if deliveries > max_deliveries:
                logger.error(
                    "dead-lettering %s from %s after %d delivery attempts",
                    message_id,
                    topic,
                    deliveries,
                )
                await self._dead_letter(topic, group, message_id, fields)
                continue
            if await self._process_entry(topic, group, message_id, fields, handler, deliveries):
                processed += 1
        return processed

    async def _process_entry(
        self,
        topic: str,
        group: str,
        message_id: str,
        fields: dict[str, str],
        handler: MessageHandler,
        delivery: int = 1,
    ) -> bool:
        payload = _decode_json_object(fields.get(PAYLOAD_FIELD))
        if payload is None:
            await self._dead_letter(topic, group, message_id, fields)
            return False
        try:
            await handler(Message(id=message_id, topic=topic, payload=payload))
        except Exception:
            # No ack: stays pending for redelivery/claiming.
            logger.exception(
                "handler failed for %s on %s (delivery #%d)", message_id, topic, delivery
            )
            return False
        await self.client.xack(topic, group, message_id)
        return True

    async def _delivery_count(self, topic: str, group: str, message_id: str) -> int:
        entries = await self.client.xpending_range(topic, group, message_id, message_id, count=1)
        if not entries:
            return 1
        times_delivered = entries[0].get("times_delivered", 1)
        return int(times_delivered) if isinstance(times_delivered, int | float | str) else 1

    async def _dead_letter(
        self, topic: str, group: str, message_id: str, fields: dict[str, str]
    ) -> None:
        logger.error("dead-lettering undecodable message %s from %s", message_id, topic)
        await self.client.xadd(f"{topic}.dlq", fields)
        await self.client.xack(topic, group, message_id)


class RedisPubSub:
    """Ephemeral fan-out over Redis pub/sub — live UI events (`events:*`
    channels), not durable work. Undelivered messages are simply lost, which
    is the right semantic for progress pushes: a reconnecting client
    re-reads current state instead of replaying history.
    """

    def __init__(self, client: PubSubClient):
        self.client = client

    async def publish_event(self, channel: str, payload: Payload) -> None:
        await self.client.publish(channel, json.dumps(dict(payload)))

    async def subscribe(
        self, channel: str, idle_timeout_s: float = 15.0
    ) -> AsyncIterator[dict[str, JsonValue] | None]:
        """Yields decoded payloads, and None after each idle_timeout_s of
        silence so callers can emit keep-alives on a live connection.
        """
        pubsub = self.client.pubsub()
        await pubsub.subscribe(channel)
        try:
            while True:
                message = await pubsub.get_message(
                    ignore_subscribe_messages=True, timeout=idle_timeout_s
                )
                if message is None:
                    yield None
                    continue
                data = message.get("data")
                decoded = _decode_json_object(data if isinstance(data, str) else None)
                if decoded is not None:
                    yield decoded
        finally:
            await pubsub.unsubscribe(channel)
            await pubsub.aclose()


__all__ = [
    "PAYLOAD_FIELD",
    "Broker",
    "EventPublisher",
    "EventSubscriber",
    "JsonValue",
    "Message",
    "MessageHandler",
    "Payload",
    "PubSubChannel",
    "PubSubClient",
    "RedisPubSub",
    "RedisStreamsBroker",
    "StreamBatch",
    "StreamsClient",
]
