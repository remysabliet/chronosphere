from collections.abc import Sequence
from typing import Protocol, TypedDict
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from question_generation_service.models.question import (
    Question,
    QuestionServingLog,
    QuestionValidationLog,
)


class QuestionEntryProtocol(Protocol):
    id: UUID
    concept_id: UUID
    bloom_level: str
    difficulty_tier: str
    question_type: str | None
    question_text: str
    options: list[str] | None
    correct_answers: list[str] | None
    explanation: str | None
    estimated_time: str | None
    tags: list[str] | None


class QuestionInput(TypedDict):
    concept_id: UUID
    bloom_level: str
    difficulty_tier: str
    question_type: str
    question_text: str
    options: list[str] | None
    correct_answers: list[str]
    explanation: str
    estimated_time: str
    tags: list[str]


class ValidationLogInput(TypedDict):
    question_id: UUID | None
    validation_status: str
    failed_checks: list[str]
    validation_score: float
    notes: str | None


class QuestionRepositoryProtocol(Protocol):
    async def save_batch(
        self, questions: list[QuestionInput]
    ) -> Sequence[QuestionEntryProtocol]: ...

    async def log_validations(self, entries: list[ValidationLogInput]) -> None: ...

    async def get_by_concept_bloom_difficulty(
        self, concept_id: UUID, bloom_level: str, difficulty_tier: str
    ) -> Sequence[QuestionEntryProtocol]: ...

    async def get_served_question_ids(
        self, user_id: UUID, question_ids: Sequence[UUID]
    ) -> set[UUID]: ...

    async def mark_served(self, user_id: UUID, question_ids: Sequence[UUID]) -> None: ...


class QuestionRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def save_batch(self, questions: list[QuestionInput]) -> list[QuestionEntryProtocol]:
        rows = [
            Question(
                concept_id=q["concept_id"],
                bloom_level=q["bloom_level"],
                difficulty_tier=q["difficulty_tier"],
                question_type=q["question_type"],
                question_text=q["question_text"],
                options=q["options"],
                correct_answers=q["correct_answers"],
                explanation=q["explanation"],
                estimated_time=q["estimated_time"],
                tags=q["tags"],
                source="ai_generated",
            )
            for q in questions
        ]
        self.session.add_all(rows)
        await self.session.commit()
        return rows  # type: ignore[return-value]

    async def log_validations(self, entries: list[ValidationLogInput]) -> None:
        rows = [
            QuestionValidationLog(
                question_id=entry["question_id"],
                validation_status=entry["validation_status"],
                failed_checks=entry["failed_checks"],
                validation_score=entry["validation_score"],
                notes=entry["notes"],
            )
            for entry in entries
        ]
        self.session.add_all(rows)
        await self.session.commit()

    async def get_by_concept_bloom_difficulty(
        self, concept_id: UUID, bloom_level: str, difficulty_tier: str
    ) -> Sequence[QuestionEntryProtocol]:
        # Only Passed/Warning drafts ever get a row here in the first place
        # (see QuestionService.generate_batch) — nothing further to filter.
        result = await self.session.execute(
            select(Question).where(
                Question.concept_id == concept_id,
                Question.bloom_level == bloom_level,
                Question.difficulty_tier == difficulty_tier,
            )
        )
        return result.scalars().all()  # type: ignore[return-value]

    async def get_served_question_ids(
        self, user_id: UUID, question_ids: Sequence[UUID]
    ) -> set[UUID]:
        if not question_ids:
            return set()
        result = await self.session.execute(
            select(QuestionServingLog.question_id).where(
                QuestionServingLog.user_id == user_id,
                QuestionServingLog.question_id.in_(question_ids),
            )
        )
        return set(result.scalars().all())

    async def mark_served(self, user_id: UUID, question_ids: Sequence[UUID]) -> None:
        if not question_ids:
            return
        stmt = (
            pg_insert(QuestionServingLog)
            .values([{"user_id": user_id, "question_id": qid} for qid in question_ids])
            .on_conflict_do_update(
                index_elements=["user_id", "question_id"],
                set_={"served_at": pg_insert(QuestionServingLog).excluded.served_at},
            )
        )
        await self.session.execute(stmt)
        await self.session.commit()
