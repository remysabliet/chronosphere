from collections.abc import Sequence
from typing import Protocol, TypedDict
from uuid import UUID

from sqlalchemy import ColumnElement, exists, func, or_, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from question_generation_service.core.config import get_settings
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
    embedding: list[float]


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

    async def get_by_ids(self, ids: Sequence[UUID]) -> Sequence[QuestionEntryProtocol]: ...

    async def get_pool_for_session(
        self,
        concept_ids: Sequence[UUID],
        question_types: Sequence[str],
        user_id: UUID,
        limit: int,
    ) -> Sequence[QuestionEntryProtocol]: ...

    async def get_candidates(
        self,
        concept_id: UUID,
        bloom_level: str,
        difficulty_tier: str | None,
        question_types: Sequence[str],
        user_id: UUID,
        limit: int,
    ) -> Sequence[QuestionEntryProtocol]: ...


def _not_served_condition(user_id: UUID) -> ColumnElement[bool]:
    served = select(QuestionServingLog.question_id).where(QuestionServingLog.user_id == user_id)
    return Question.id.notin_(served)


def _not_too_similar_condition(user_id: UUID) -> ColumnElement[bool]:
    """Excludes candidates whose embedding is near-identical to something
    already served to this user. Unlike _not_served_condition (exact row id
    match), this also catches duplicate content stored under a *different*
    concept_id — see docs/architecture/question-diversity-and-dedup.md.
    """
    served = aliased(Question)
    served_log = aliased(QuestionServingLog)
    threshold = get_settings().QUESTION_SIMILARITY_DISTANCE_THRESHOLD
    return ~exists(
        select(1)
        .select_from(served_log)
        .join(served, served.id == served_log.question_id)
        .where(
            served_log.user_id == user_id,
            served.embedding.is_not(None),
            Question.embedding.is_not(None),
            served.embedding.cosine_distance(Question.embedding) < threshold,
        )
    )


class QuestionRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def save_batch(self, questions: list[QuestionInput]) -> list[QuestionEntryProtocol]:
        """Skips (rather than errors on) a literal repeat generation for the
        same concept/bloom/tier — idx_questions_concept_text_dedup. Returns
        only the rows actually inserted; callers correlate the result back to
        their input list by question_text (unique within one generation batch
        by prompt design) to know which drafts were skipped as duplicates.
        """
        if not questions:
            return []
        stmt = (
            pg_insert(Question)
            .values(
                [
                    {
                        "concept_id": q["concept_id"],
                        "bloom_level": q["bloom_level"],
                        "difficulty_tier": q["difficulty_tier"],
                        "question_type": q["question_type"],
                        "question_text": q["question_text"],
                        "options": q["options"],
                        "correct_answers": q["correct_answers"],
                        "explanation": q["explanation"],
                        "estimated_time": q["estimated_time"],
                        "tags": q["tags"],
                        "embedding": q["embedding"],
                        "source": "ai_generated",
                    }
                    for q in questions
                ]
            )
            .on_conflict_do_nothing(
                index_elements=[
                    "concept_id",
                    "bloom_level",
                    "difficulty_tier",
                    "question_text_norm_hash",
                ],
                index_where=Question.owner_user_id.is_(None),
            )
            .returning(Question)
        )
        result = await self.session.execute(stmt)
        await self.session.commit()
        return list(result.scalars().all())  # pyright: ignore[reportReturnType]

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
        # (see QuestionService.generate_batch). Public pool only: the NULL
        # filter both excludes private (document-sourced) questions and lets
        # Postgres use the partial idx_questions_public_pool index.
        result = await self.session.execute(
            select(Question).where(
                Question.concept_id == concept_id,
                Question.bloom_level == bloom_level,
                Question.difficulty_tier == difficulty_tier,
                Question.owner_user_id.is_(None),
            )
        )
        return result.scalars().all()  # pyright: ignore[reportReturnType]

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

    async def get_by_ids(self, ids: Sequence[UUID]) -> Sequence[QuestionEntryProtocol]:
        if not ids:
            return []
        result = await self.session.execute(select(Question).where(Question.id.in_(ids)))
        return result.scalars().all()  # pyright: ignore[reportReturnType]

    async def get_pool_for_session(
        self,
        concept_ids: Sequence[UUID],
        question_types: Sequence[str],
        user_id: UUID,
        limit: int,
    ) -> Sequence[QuestionEntryProtocol]:
        # Public pool plus this learner's own private (document-sourced)
        # questions — a session should never surface someone else's private
        # questions. Random order gives a varied session without needing to
        # balance across concept/Bloom cells explicitly.
        if not concept_ids:
            return []
        result = await self.session.execute(
            select(Question)
            .where(
                Question.concept_id.in_(concept_ids),
                Question.question_type.in_(question_types),
                or_(Question.owner_user_id.is_(None), Question.owner_user_id == user_id),
                _not_served_condition(user_id),
                _not_too_similar_condition(user_id),
            )
            .order_by(func.random())
            .limit(limit)
        )
        return result.scalars().all()  # pyright: ignore[reportReturnType]

    async def get_candidates(
        self,
        concept_id: UUID,
        bloom_level: str,
        difficulty_tier: str | None,
        question_types: Sequence[str],
        user_id: UUID,
        limit: int,
    ) -> Sequence[QuestionEntryProtocol]:
        """Step 11 candidate lookup for one concept-Bloom(-tier) target — the
        adaptive engine's exact-match query, with `difficulty_tier=None`
        as its own any-tier fallback for that same pair.
        """
        conditions = [
            Question.concept_id == concept_id,
            Question.bloom_level == bloom_level,
            Question.question_type.in_(question_types),
            or_(Question.owner_user_id.is_(None), Question.owner_user_id == user_id),
            _not_served_condition(user_id),
            _not_too_similar_condition(user_id),
        ]
        if difficulty_tier is not None:
            conditions.append(Question.difficulty_tier == difficulty_tier)
        result = await self.session.execute(
            select(Question).where(*conditions).order_by(func.random()).limit(limit)
        )
        return result.scalars().all()  # pyright: ignore[reportReturnType]
