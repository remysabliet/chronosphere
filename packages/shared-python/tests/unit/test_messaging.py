import json
from collections.abc import Mapping

import pytest

from memosphere_messaging import (
    PAYLOAD_FIELD,
    Message,
    RedisStreamsBroker,
    StreamBatch,
)

pytestmark = pytest.mark.asyncio


class FakeStreams:
    def __init__(self, batch: StreamBatch | None = None, group_error: str | None = None):
        self.batch = batch
        self.group_error = group_error
        self.added: list[tuple[str, dict[str, str]]] = []
        self.acked: list[tuple[str, str, tuple[str, ...]]] = []
        self.groups: list[tuple[str, str, str, bool]] = []

    async def xadd(self, name: str, fields: Mapping[str, str]) -> str:
        self.added.append((name, dict(fields)))
        return f"{len(self.added)}-0"

    async def xgroup_create(self, name: str, groupname: str, id: str, mkstream: bool) -> bool:
        if self.group_error is not None:
            raise RuntimeError(self.group_error)
        self.groups.append((name, groupname, id, mkstream))
        return True

    async def xreadgroup(
        self,
        groupname: str,
        consumername: str,
        streams: Mapping[str, str],
        count: int,
        block: int,
    ) -> StreamBatch | None:
        return self.batch

    async def xack(self, name: str, groupname: str, *ids: str) -> int:
        self.acked.append((name, groupname, ids))
        return len(ids)


def entry(message_id: str, raw: str) -> tuple[str, dict[str, str]]:
    return (message_id, {PAYLOAD_FIELD: raw})


async def test_publish_serializes_payload_to_the_topic_stream():
    client = FakeStreams()
    broker = RedisStreamsBroker(client)

    message_id = await broker.publish("jobs:generate-questions", {"quiz_id": "q1", "n": 5})

    assert message_id == "1-0"
    name, fields = client.added[0]
    assert name == "jobs:generate-questions"
    assert json.loads(fields[PAYLOAD_FIELD]) == {"quiz_id": "q1", "n": 5}


async def test_ensure_group_creates_from_zero_with_mkstream():
    client = FakeStreams()
    broker = RedisStreamsBroker(client)

    await broker.ensure_group("events:response.recorded", "learning-engine")

    assert client.groups == [("events:response.recorded", "learning-engine", "0", True)]


async def test_ensure_group_swallows_busygroup_only():
    broker = RedisStreamsBroker(FakeStreams(group_error="BUSYGROUP already exists"))
    await broker.ensure_group("events:x", "g")  # no raise

    broker = RedisStreamsBroker(FakeStreams(group_error="connection refused"))
    with pytest.raises(RuntimeError, match="connection refused"):
        await broker.ensure_group("events:x", "g")


async def test_consume_once_dispatches_and_acks():
    batch: StreamBatch = [("events:x", [entry("1-0", json.dumps({"a": 1}))])]
    client = FakeStreams(batch=batch)
    broker = RedisStreamsBroker(client)
    seen: list[Message] = []

    async def handler(message: Message) -> None:
        seen.append(message)

    processed = await broker.consume_once("events:x", "g", "c1", handler)

    assert processed == 1
    assert seen[0].payload == {"a": 1}
    assert client.acked == [("events:x", "g", ("1-0",))]


async def test_consume_once_returns_zero_on_empty_poll():
    broker = RedisStreamsBroker(FakeStreams(batch=None))

    async def handler(message: Message) -> None:
        raise AssertionError("should not be called")

    assert await broker.consume_once("events:x", "g", "c1", handler) == 0


async def test_handler_failure_leaves_message_pending_and_continues():
    batch: StreamBatch = [
        (
            "events:x",
            [entry("1-0", json.dumps({"ok": False})), entry("2-0", json.dumps({"ok": True}))],
        )
    ]
    client = FakeStreams(batch=batch)
    broker = RedisStreamsBroker(client)

    async def handler(message: Message) -> None:
        if message.payload == {"ok": False}:
            raise ValueError("boom")

    processed = await broker.consume_once("events:x", "g", "c1", handler)

    assert processed == 1
    assert client.acked == [("events:x", "g", ("2-0",))]  # 1-0 stays pending


@pytest.mark.parametrize("raw", ["not json", json.dumps([1, 2]), json.dumps("str")])
async def test_undecodable_payload_goes_to_dlq_and_is_acked(raw: str):
    batch: StreamBatch = [("events:x", [entry("1-0", raw)])]
    client = FakeStreams(batch=batch)
    broker = RedisStreamsBroker(client)

    async def handler(message: Message) -> None:
        raise AssertionError("should not be called")

    processed = await broker.consume_once("events:x", "g", "c1", handler)

    assert processed == 0
    assert client.added == [("events:x.dlq", {PAYLOAD_FIELD: raw})]
    assert client.acked == [("events:x", "g", ("1-0",))]


async def test_missing_payload_field_goes_to_dlq():
    batch: StreamBatch = [("events:x", [("1-0", {"other": "field"})])]
    client = FakeStreams(batch=batch)
    broker = RedisStreamsBroker(client)

    async def handler(message: Message) -> None:
        raise AssertionError("should not be called")

    assert await broker.consume_once("events:x", "g", "c1", handler) == 0
    assert client.added[0][0] == "events:x.dlq"
