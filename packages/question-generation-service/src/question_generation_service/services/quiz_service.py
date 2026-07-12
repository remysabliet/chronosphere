import math
from collections.abc import Sequence
from itertools import zip_longest
from typing import Protocol, cast
from uuid import UUID, uuid4

from memosphere_domain import QuestionType
from memosphere_messaging import JsonValue
from question_generation_service.core.exceptions import NotFoundError
from question_generation_service.repositories.learning_unit_repository import (
    LearningUnitEntryProtocol,
)
from question_generation_service.repositories.quiz_repository import (
    SECONDS_PER_QUESTION_ESTIMATE,
    OutboxInput,
    QuizConceptInput,
    QuizEntryProtocol,
    QuizInput,
    QuizScope,
    QuizStatus,
)
from question_generation_service.schemas.question import BATCH_SIZE
from question_generation_service.schemas.quiz import (
    QuizCreateRequest,
    QuizDetailResponse,
    QuizListItem,
    QuizListResponse,
    QuizResponse,
    QuizVisibility,
)

JOBS_GENERATE_QUESTIONS = "jobs:generate-questions"
DEFAULT_PAGE_SIZE = 20


# Narrower than each repository's full Protocol (which also covers writes/
# lookups this service never does, e.g. increment_questions_ready is the
# generation worker's job, get_by_id is the mastery/adaptive-selection path's)
# — Interface Segregation: depend only on what's actually called here. The
# real repositories already satisfy these structurally; no adapter needed.
class QuizLookupProtocol(Protocol):
    async def create_with_outbox(
        self,
        quiz: QuizInput,
        outbox_entries: list[OutboxInput],
        concepts: list[QuizConceptInput],
    ) -> QuizEntryProtocol: ...

    async def get(self, quiz_id: UUID) -> tuple[QuizEntryProtocol, str | None] | None: ...

    # Declared before `list` below — a same-named method later in this class
    # body would shadow the builtin `list` generic used in this annotation.
    async def get_topics_for_quizzes(self, quiz_ids: Sequence[UUID]) -> dict[UUID, list[str]]: ...

    async def list(
        self,
        *,
        owner_user_id: UUID,
        scope: QuizScope,
        q: str | None,
        status: QuizStatus | None,
        page: int,
        page_size: int,
    ) -> tuple[list[tuple[QuizEntryProtocol, str | None]], bool]: ...

    async def rename(self, quiz_id: UUID, title: str) -> None: ...


class LearningUnitLookupProtocol(Protocol):
    async def get_by_thema(self, thema: str) -> Sequence[LearningUnitEntryProtocol]: ...


def _expected_question_count(question_count: int | None, time_limit_minutes: int | None) -> int:
    if question_count is not None:
        return question_count
    # require_a_size guarantees time_limit_minutes is set on this path.
    minutes = time_limit_minutes or 0
    # ceil, not round, to match quiz_repository._expected_count_expr's SQL
    # func.ceil — the two must agree exactly or a quiz's ready/generating
    # status flips depending on whether it's read via this service or listed
    # through the repository's SQL filter.
    return max(1, math.ceil(minutes * 60 / SECONDS_PER_QUESTION_ESTIMATE))


def _target_question_count(body: QuizCreateRequest) -> int:
    return _expected_question_count(body.question_count, body.time_limit_minutes)


def _status(ready: int, expected: int) -> QuizStatus:
    return "ready" if ready >= expected else "generating"


def _round_robin_pairs(
    units: Sequence[LearningUnitEntryProtocol],
) -> list[tuple[LearningUnitEntryProtocol, str]]:
    """One bloom level per unit per round, cycling through units, instead of
    exhausting one unit's whole bloom ladder before moving to the next.
    `create()` below only pre-generates the first `batches_needed` pairs —
    unit-major order made pre-generation cluster on the first 1-2 units
    returned by get_by_thema instead of spreading across distinct concepts
    (see docs/architecture/question-diversity-and-dedup.md).
    """
    per_unit = [[(unit, bloom) for bloom in (unit.bloom_levels_supported or [])] for unit in units]
    return [pair for round_ in zip_longest(*per_unit) for pair in round_ if pair is not None]


def _to_list_item(
    entry: QuizEntryProtocol, owner_name: str | None, topics: list[str]
) -> QuizListItem:
    expected = _expected_question_count(entry.question_count, entry.time_limit_minutes)
    ready = min(entry.generation_questions_ready, expected)
    return QuizListItem(
        id=entry.id,
        thema=entry.thema,
        title=entry.title,
        question_types=cast(list[QuestionType], entry.question_types),
        question_count=entry.question_count,
        time_limit_minutes=entry.time_limit_minutes,
        visibility=cast(QuizVisibility, entry.visibility),
        questions_ready=ready,
        questions_expected=expected,
        status=_status(ready, expected),
        topics=topics,
        owner_name=owner_name,
        created_at=entry.created_at,
        updated_at=entry.updated_at,
    )


class QuizService:
    def __init__(
        self,
        quiz_repository: QuizLookupProtocol,
        learning_unit_repository: LearningUnitLookupProtocol,
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

        # Generated client-side (rather than left to the DB default) so it can
        # be embedded in every job payload below — the worker uses it to
        # attribute completed batches back to this quiz's progress counter.
        quiz_id = uuid4()

        pairs = _round_robin_pairs(units)
        batches_needed = max(1, math.ceil(_target_question_count(body) / BATCH_SIZE))
        buckets = pairs[:batches_needed]

        outbox_entries: list[OutboxInput] = [
            OutboxInput(
                topic=JOBS_GENERATE_QUESTIONS,
                payload={
                    "quiz_id": str(quiz_id),
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
        # Deduped, order-preserving — the concepts this quiz's topics are
        # derived from (one row per unit, not per unit-bloom pair).
        concept_ids = dict.fromkeys(unit.id for unit, _ in buckets)
        concepts = [
            QuizConceptInput(quiz_id=quiz_id, concept_id=concept_id) for concept_id in concept_ids
        ]

        quiz = await self.quiz_repository.create_with_outbox(
            QuizInput(
                id=quiz_id,
                owner_user_id=owner_user_id,
                thema=body.thema,
                title=body.title or body.thema,
                question_types=list(body.question_types),
                question_count=body.question_count,
                time_limit_minutes=body.time_limit_minutes,
                visibility=body.visibility,
            ),
            outbox_entries,
            concepts,
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

    async def get(self, quiz_id: UUID, requesting_user_id: UUID) -> QuizDetailResponse:
        found = await self.quiz_repository.get(quiz_id)
        if found is None:
            raise NotFoundError(f"No quiz found for id {quiz_id}")
        entry, owner_name = found
        is_owner = entry.owner_user_id == requesting_user_id
        # Private quizzes are invisible to everyone but their owner — 404,
        # not 403, so a guess at another user's private quiz id can't even
        # confirm the id exists.
        if not is_owner and entry.visibility == "private":
            raise NotFoundError(f"No quiz found for id {quiz_id}")

        expected = _expected_question_count(entry.question_count, entry.time_limit_minutes)
        ready = min(entry.generation_questions_ready, expected)
        topics_by_quiz = await self.quiz_repository.get_topics_for_quizzes([entry.id])
        return QuizDetailResponse(
            id=entry.id,
            thema=entry.thema,
            title=entry.title,
            question_types=cast(list[QuestionType], entry.question_types),
            question_count=entry.question_count,
            time_limit_minutes=entry.time_limit_minutes,
            visibility=cast(QuizVisibility, entry.visibility),
            questions_ready=ready,
            questions_expected=expected,
            status=_status(ready, expected),
            topics=topics_by_quiz.get(entry.id, []),
            owner_name=None if is_owner else owner_name,
            created_at=entry.created_at,
            updated_at=entry.updated_at,
        )

    async def rename(
        self, quiz_id: UUID, requesting_user_id: UUID, title: str
    ) -> QuizDetailResponse:
        found = await self.quiz_repository.get(quiz_id)
        if found is None:
            raise NotFoundError(f"No quiz found for id {quiz_id}")
        entry, _ = found
        # Same 404-not-403 reasoning as get(): a non-owner shouldn't be able
        # to distinguish "not yours" from "doesn't exist".
        if entry.owner_user_id != requesting_user_id:
            raise NotFoundError(f"No quiz found for id {quiz_id}")
        await self.quiz_repository.rename(quiz_id, title)
        return await self.get(quiz_id, requesting_user_id)

    async def list(
        self,
        requesting_user_id: UUID,
        scope: QuizScope,
        q: str | None,
        status: QuizStatus | None,
        page: int,
    ) -> QuizListResponse:
        rows, has_more = await self.quiz_repository.list(
            owner_user_id=requesting_user_id,
            scope=scope,
            q=q,
            status=status,
            page=page,
            page_size=DEFAULT_PAGE_SIZE,
        )
        topics_by_quiz = await self.quiz_repository.get_topics_for_quizzes(
            [entry.id for entry, _ in rows]
        )
        items = [
            _to_list_item(
                entry, owner_name if scope == "shared" else None, topics_by_quiz.get(entry.id, [])
            )
            for entry, owner_name in rows
        ]
        return QuizListResponse(items=items, has_more=has_more)
