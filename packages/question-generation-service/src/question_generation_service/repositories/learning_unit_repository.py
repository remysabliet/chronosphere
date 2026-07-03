from typing import Protocol, TypedDict
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from question_generation_service.models.learning_unit import LearningUnit


class LearningUnitEntryProtocol(Protocol):
    id: UUID
    thema: str
    topic: str | None
    concept_name: str
    learning_goal: str | None
    bloom_levels_supported: list[str] | None
    estimated_time_minutes: int | None
    bloom_coverage_score: int | None
    complexity_level: str | None


class ConceptInput(TypedDict):
    topic: str
    concept_name: str
    learning_goal: str
    bloom_levels_supported: list[str]
    estimated_time_minutes: int
    bloom_coverage_score: int
    complexity_level: str


class LearningUnitRepositoryProtocol(Protocol):
    async def save_batch(
        self,
        thema: str,
        concepts: list[ConceptInput],
    ) -> list[LearningUnitEntryProtocol]: ...


class LearningUnitRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def save_batch(
        self,
        thema: str,
        concepts: list[ConceptInput],
    ) -> list[LearningUnitEntryProtocol]:
        units = [
            LearningUnit(
                thema=thema,
                topic=c["topic"],
                concept_name=c["concept_name"],
                learning_goal=c["learning_goal"],
                bloom_levels_supported=c["bloom_levels_supported"],
                estimated_time_minutes=c["estimated_time_minutes"],
                bloom_coverage_score=c["bloom_coverage_score"],
                complexity_level=c["complexity_level"],
            )
            for c in concepts
        ]
        self.session.add_all(units)
        await self.session.commit()
        return units  # type: ignore[return-value]
