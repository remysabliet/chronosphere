from collections.abc import Sequence
from typing import Protocol, TypedDict
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from question_generation_service.models.question import Question, QuestionValidationLog


class QuestionEntryProtocol(Protocol):
    id: UUID
    concept_id: UUID
    bloom_level: str
    difficulty_tier: str
    question_type: str | None
    question_text: str
    options: list[str] | None
    correct_answer: str | None
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
    correct_answer: str
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
                correct_answer=q["correct_answer"],
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
