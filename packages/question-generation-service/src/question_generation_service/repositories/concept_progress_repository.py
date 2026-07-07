from typing import Protocol, TypedDict
from uuid import UUID

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
        return list(result.scalars().all())  # type: ignore[return-value]
