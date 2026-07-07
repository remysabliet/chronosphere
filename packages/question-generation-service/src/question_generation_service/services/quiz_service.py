import math
from typing import cast
from uuid import UUID

from memosphere_domain import QuestionType
from memosphere_messaging import JsonValue
from question_generation_service.core.exceptions import NotFoundError
from question_generation_service.repositories.learning_unit_repository import (
    LearningUnitRepositoryProtocol,
)
from question_generation_service.repositories.quiz_repository import (
    OutboxInput,
    QuizInput,
    QuizRepositoryProtocol,
)
from question_generation_service.schemas.question import BATCH_SIZE
from question_generation_service.schemas.quiz import (
    QuizCreateRequest,
    QuizResponse,
    QuizVisibility,
)

JOBS_GENERATE_QUESTIONS = "jobs:generate-questions"

# Mirrors the wizard's sizing heuristics (quiz/new/wizard/page.tsx).
SECONDS_PER_QUESTION_ESTIMATE = 45


def _target_question_count(body: QuizCreateRequest) -> int:
    if body.question_count is not None:
        return body.question_count
    # require_a_size guarantees time_limit_minutes is set on this path.
    minutes = body.time_limit_minutes or 0
    return max(1, round(minutes * 60 / SECONDS_PER_QUESTION_ESTIMATE))


class QuizService:
    def __init__(
        self,
        quiz_repository: QuizRepositoryProtocol,
        learning_unit_repository: LearningUnitRepositoryProtocol,
    ):
        self.quiz_repository = quiz_repository
        self.learning_unit_repository = learning_unit_repository

    async def create(self, owner_user_id: UUID, body: QuizCreateRequest) -> QuizResponse:
        """Persists the quiz config and enqueues one generation job per
        concept–Bloom bucket (same bucket walk as the wizard used to run
        inline) — quiz row and jobs commit in a single transaction, and the
        relay/worker warm the pool with nobody waiting.
        """
        units = await self.learning_unit_repository.get_by_thema(body.thema)
        if not units:
            raise NotFoundError(
                f"No concepts mapped for thema '{body.thema}' — confirm the thema first"
            )

        pairs = [
            (unit, bloom_level)
            for unit in units
            for bloom_level in (unit.bloom_levels_supported or [])
        ]
        batches_needed = max(1, math.ceil(_target_question_count(body) / BATCH_SIZE))
        buckets = pairs[:batches_needed]

        outbox_entries: list[OutboxInput] = [
            OutboxInput(
                topic=JOBS_GENERATE_QUESTIONS,
                payload={
                    "owner_user_id": str(owner_user_id),
                    "concept_id": str(unit.id),
                    "concept_name": unit.concept_name,
                    "learning_goal": unit.learning_goal or f"Understand {unit.concept_name}",
                    "bloom_level": bloom_level,
                    "difficulty_tier": "medium",
                    "allowed_question_types": cast(list[JsonValue], list(body.question_types)),
                },
            )
            for unit, bloom_level in buckets
        ]

        quiz = await self.quiz_repository.create_with_outbox(
            QuizInput(
                owner_user_id=owner_user_id,
                thema=body.thema,
                title=body.title or body.thema,
                question_types=list(body.question_types),
                question_count=body.question_count,
                time_limit_minutes=body.time_limit_minutes,
                visibility=body.visibility,
            ),
            outbox_entries,
        )
        return QuizResponse(
            id=quiz.id,
            thema=quiz.thema,
            title=quiz.title,
            question_types=cast(list[QuestionType], quiz.question_types),
            question_count=quiz.question_count,
            time_limit_minutes=quiz.time_limit_minutes,
            visibility=cast(QuizVisibility, quiz.visibility),
            generation_batches_enqueued=len(outbox_entries),
        )
