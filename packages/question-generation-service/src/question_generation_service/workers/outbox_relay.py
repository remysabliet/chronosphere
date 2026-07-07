import asyncio
import contextlib
import logging
from collections.abc import Callable

from sqlalchemy.ext.asyncio import AsyncSession

from memosphere_messaging import Broker
from question_generation_service.repositories.quiz_repository import OutboxRepository

logger = logging.getLogger(__name__)

RELAY_BATCH_SIZE = 100


class OutboxRelay:
    """Publishes unpublished outbox rows (in id order) to their Redis stream,
    then stamps published_at. Publish-then-stamp means a crash in between
    republishes on restart — at-least-once, matching the broker's semantics.
    """

    def __init__(
        self,
        session_factory: Callable[[], AsyncSession],
        broker: Broker,
        poll_interval_seconds: float = 0.5,
    ):
        self.session_factory = session_factory
        self.broker = broker
        self.poll_interval_seconds = poll_interval_seconds

    async def relay_once(self) -> int:
        async with self.session_factory() as session:
            repository = OutboxRepository(session)
            rows = await repository.fetch_unpublished(RELAY_BATCH_SIZE)
            published_ids: list[int] = []
            for row in rows:
                await self.broker.publish(row.topic, row.payload)
                published_ids.append(row.id)
            await repository.mark_published(published_ids)
            return len(published_ids)

    async def run(self, stop: asyncio.Event) -> None:
        while not stop.is_set():
            try:
                published = await self.relay_once()
            except Exception:
                logger.exception("outbox relay pass failed; retrying")
                published = 0
            if published == 0:
                # Nothing to do (or an error): wait, but wake instantly on stop.
                with contextlib.suppress(TimeoutError):
                    await asyncio.wait_for(stop.wait(), timeout=self.poll_interval_seconds)
