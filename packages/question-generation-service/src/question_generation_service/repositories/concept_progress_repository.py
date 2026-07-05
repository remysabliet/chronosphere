from typing import Protocol, TypedDict
from uuid import UUID

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
        entries = [
            ConceptProgressTracker(
                user_id=user_id,
                concept_id=row["concept_id"],
                bloom_level=row["bloom_level"],
                p_ln=row["p_ln"],
                attempt_count=0,
                correct_count=0,
                slip_count=0,
                mastery_status="In Progress",
            )
            for row in rows
        ]
        self.session.add_all(entries)
        await self.session.commit()
        return entries  # type: ignore[return-value]
