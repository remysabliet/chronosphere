from collections.abc import Sequence
from typing import Protocol, TypedDict
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from question_generation_service.core.config import get_settings
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
    embedding: list[float]


class LearningUnitRepositoryProtocol(Protocol):
    async def save_batch(
        self,
        thema: str,
        concepts: list[ConceptInput],
    ) -> Sequence[LearningUnitEntryProtocol]: ...

    async def get_by_thema(self, thema: str) -> Sequence[LearningUnitEntryProtocol]: ...

    async def get_by_id(self, concept_id: UUID) -> LearningUnitEntryProtocol | None: ...

    async def find_similar_concept(
        self, thema: str, embedding: list[float]
    ) -> LearningUnitEntryProtocol | None: ...


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
                embedding=c["embedding"],
            )
            for c in concepts
        ]
        self.session.add_all(units)
        await self.session.commit()
        return units  # type: ignore[return-value]

    async def get_by_thema(self, thema: str) -> list[LearningUnitEntryProtocol]:
        result = await self.session.execute(select(LearningUnit).where(LearningUnit.thema == thema))
        return list(result.scalars().all())  # pyright: ignore[reportReturnType]

    async def get_by_id(self, concept_id: UUID) -> LearningUnitEntryProtocol | None:
        result = await self.session.execute(
            select(LearningUnit).where(LearningUnit.id == concept_id)
        )
        return result.scalar_one_or_none()  # pyright: ignore[reportReturnType]

    async def find_similar_concept(
        self, thema: str, embedding: list[float]
    ) -> LearningUnitEntryProtocol | None:
        """Nearest existing concept for this thema by embedding, if within
        the similarity threshold — the reuse check that replaces exact-string
        matching on Prompt 1's non-deterministic topic phrasing (see
        docs/architecture/question-diversity-and-dedup.md).
        """
        distance = LearningUnit.embedding.cosine_distance(embedding)
        threshold = get_settings().CONCEPT_SIMILARITY_DISTANCE_THRESHOLD
        result = await self.session.execute(
            select(LearningUnit, distance.label("distance"))
            .where(LearningUnit.thema == thema, LearningUnit.embedding.is_not(None))
            .order_by(distance)
            .limit(1)
        )
        row = result.first()
        if row is None or row.distance >= threshold:
            return None
        unit: LearningUnit = row[0]
        return unit  # pyright: ignore[reportReturnType]
