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
from collections.abc import Awaitable, Callable, Mapping
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
                payload = self._decode(fields.get(PAYLOAD_FIELD))
                if payload is None:
                    await self._dead_letter(topic, group, message_id, fields)
                    continue
                try:
                    await handler(Message(id=message_id, topic=topic, payload=payload))
                except Exception:
                    # No ack: stays pending for redelivery/claiming.
                    logger.exception("handler failed for %s on %s", message_id, topic)
                    continue
                await self.client.xack(topic, group, message_id)
                processed += 1
        return processed

    @staticmethod
    def _decode(raw: str | None) -> dict[str, JsonValue] | None:
        if raw is None:
            return None
        try:
            decoded: JsonValue = json.loads(raw)
        except json.JSONDecodeError:
            return None
        if not isinstance(decoded, dict):
            return None
        return decoded

    async def _dead_letter(
        self, topic: str, group: str, message_id: str, fields: dict[str, str]
    ) -> None:
        logger.error("dead-lettering undecodable message %s from %s", message_id, topic)
        await self.client.xadd(f"{topic}.dlq", fields)
        await self.client.xack(topic, group, message_id)


__all__ = [
    "PAYLOAD_FIELD",
    "Broker",
    "JsonValue",
    "Message",
    "MessageHandler",
    "Payload",
    "RedisStreamsBroker",
    "StreamBatch",
    "StreamsClient",
]
