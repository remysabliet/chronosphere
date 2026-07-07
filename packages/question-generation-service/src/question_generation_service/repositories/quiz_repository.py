from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Protocol, TypedDict
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from memosphere_messaging import JsonValue
from question_generation_service.models.quiz import Outbox, Quiz


class QuizInput(TypedDict):
    owner_user_id: UUID
    thema: str
    title: str
    question_types: list[str]
    question_count: int | None
    time_limit_minutes: int | None
    visibility: str


class OutboxInput(TypedDict):
    topic: str
    payload: dict[str, JsonValue]


class QuizEntryProtocol(Protocol):
    id: UUID
    owner_user_id: UUID
    thema: str
    title: str
    question_types: list[str]
    question_count: int | None
    time_limit_minutes: int | None
    visibility: str


class QuizRepositoryProtocol(Protocol):
    async def create_with_outbox(
        self, quiz: QuizInput, outbox_entries: list[OutboxInput]
    ) -> QuizEntryProtocol: ...


class QuizRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_with_outbox(
        self, quiz: QuizInput, outbox_entries: list[OutboxInput]
    ) -> QuizEntryProtocol:
        # One transaction: the quiz row and its generation jobs commit or
        # roll back together — the outbox pattern's whole point.
        row = Quiz(
            owner_user_id=quiz["owner_user_id"],
            thema=quiz["thema"],
            title=quiz["title"],
            question_types=quiz["question_types"],
            question_count=quiz["question_count"],
            time_limit_minutes=quiz["time_limit_minutes"],
            visibility=quiz["visibility"],
        )
        self.session.add(row)
        self.session.add_all(
            Outbox(topic=entry["topic"], payload=entry["payload"]) for entry in outbox_entries
        )
        await self.session.commit()
        return row  # type: ignore[return-value]


class OutboxEntryProtocol(Protocol):
    id: int
    topic: str
    payload: dict[str, JsonValue]


class OutboxRepositoryProtocol(Protocol):
    async def fetch_unpublished(self, limit: int) -> Sequence[OutboxEntryProtocol]: ...

    async def mark_published(self, ids: Sequence[int]) -> None: ...


class OutboxRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def fetch_unpublished(self, limit: int) -> Sequence[OutboxEntryProtocol]:
        # SKIP LOCKED: concurrent relay instances never double-publish a row
        # they can see; a crashed relay's rows unlock with its transaction.
        result = await self.session.execute(
            select(Outbox)
            .where(Outbox.published_at.is_(None))
            .order_by(Outbox.id)
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
        return result.scalars().all()  # type: ignore[return-value]

    async def mark_published(self, ids: Sequence[int]) -> None:
        if not ids:
            return
        await self.session.execute(
            update(Outbox).where(Outbox.id.in_(ids)).values(published_at=datetime.now(UTC))
        )
        await self.session.commit()
