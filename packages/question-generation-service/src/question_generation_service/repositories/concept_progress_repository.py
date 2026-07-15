from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Protocol, TypedDict
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from question_generation_service.models.concept_progress import ConceptProgressTracker


class ConceptProgressEntryProtocol(Protocol):
    user_id: UUID
    concept_id: UUID
    bloom_level: str
    p_ln: float | None
    mastery_status: str | None


class ConceptProgressInput(TypedDict):
    concept_id: UUID
    bloom_level: str
    p_ln: float


class ConceptProgressRepositoryProtocol(Protocol):
    async def initialize_batch(
        self, user_id: UUID, rows: list[ConceptProgressInput]
    ) -> list[ConceptProgressEntryProtocol]: ...

    async def get(
        self, user_id: UUID, concept_id: UUID, bloom_level: str
    ) -> ConceptProgressEntryProtocol | None: ...

    async def get_batch(
        self, user_id: UUID, pairs: Sequence[tuple[UUID, str]]
    ) -> Sequence[ConceptProgressEntryProtocol]: ...

    async def record_attempt(
        self,
        user_id: UUID,
        concept_id: UUID,
        bloom_level: str,
        p_ln: float,
        is_correct: bool,
        mastery_status: str,
    ) -> None: ...


class ConceptProgressRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def initialize_batch(
        self, user_id: UUID, rows: list[ConceptProgressInput]
    ) -> list[ConceptProgressEntryProtocol]:
        """Seeds BKT state for each (user, concept, bloom) pair — but only the
        ones that don't already have a row. A learner can confirm the same
        thema more than once (concepts are reused via dedup, see
        ConceptService.map), and re-seeding an already-tracked pair would both
        crash on the primary key and, if it didn't, wipe out real progress
        with a fresh P(L0). ON CONFLICT DO NOTHING makes this a no-op for
        anything already on file instead.
        """
        if not rows:
            return []
        values = [
            {
                "user_id": user_id,
                "concept_id": row["concept_id"],
                "bloom_level": row["bloom_level"],
                "p_ln": row["p_ln"],
                "attempt_count": 0,
                "correct_count": 0,
                "slip_count": 0,
                "mastery_status": "In Progress",
            }
            for row in rows
        ]
        stmt = (
            pg_insert(ConceptProgressTracker)
            .values(values)
            .on_conflict_do_nothing(index_elements=["user_id", "concept_id", "bloom_level"])
            .returning(ConceptProgressTracker)
        )
        result = await self.session.execute(stmt)
        await self.session.commit()
        return list(result.scalars().all())  # pyright: ignore[reportReturnType]

    async def get(
        self, user_id: UUID, concept_id: UUID, bloom_level: str
    ) -> ConceptProgressEntryProtocol | None:
        result = await self.session.execute(
            select(ConceptProgressTracker).where(
                ConceptProgressTracker.user_id == user_id,
                ConceptProgressTracker.concept_id == concept_id,
                ConceptProgressTracker.bloom_level == bloom_level,
            )
        )
        return result.scalar_one_or_none()  # pyright: ignore[reportReturnType]

    async def get_batch(
        self, user_id: UUID, pairs: Sequence[tuple[UUID, str]]
    ) -> Sequence[ConceptProgressEntryProtocol]:
        if not pairs:
            return []
        concept_ids = {concept_id for concept_id, _ in pairs}
        result = await self.session.execute(
            select(ConceptProgressTracker).where(
                ConceptProgressTracker.user_id == user_id,
                ConceptProgressTracker.concept_id.in_(concept_ids),
            )
        )
        return result.scalars().all()  # pyright: ignore[reportReturnType]

    async def record_attempt(
        self,
        user_id: UUID,
        concept_id: UUID,
        bloom_level: str,
        p_ln: float,
        is_correct: bool,
        mastery_status: str,
    ) -> None:
        # concept_progress_tracker.first_attempt/last_attempt are plain
        # TIMESTAMP WITHOUT TIME ZONE columns (Knex table.timestamp(),
        # no useTz) — bind a naive UTC value, not an aware one, or asyncpg
        # rejects it outright.
        now = datetime.now(UTC).replace(tzinfo=None)
        await self.session.execute(
            update(ConceptProgressTracker)
            .where(
                ConceptProgressTracker.user_id == user_id,
                ConceptProgressTracker.concept_id == concept_id,
                ConceptProgressTracker.bloom_level == bloom_level,
            )
            .values(
                p_ln=p_ln,
                attempt_count=ConceptProgressTracker.attempt_count + 1,
                correct_count=ConceptProgressTracker.correct_count + (1 if is_correct else 0),
                slip_count=ConceptProgressTracker.slip_count + (0 if is_correct else 1),
                first_attempt=func.coalesce(ConceptProgressTracker.first_attempt, now),
                last_attempt=now,
                mastery_status=mastery_status,
            )
        )
        await self.session.commit()
        # Core-style UPDATE bypasses ORM attribute tracking — without this,
        # AdaptiveSelectionService's get_batch() later in the same request
        # would still see this pair's pre-update p_ln via the identity map.
        self.session.expire_all()
