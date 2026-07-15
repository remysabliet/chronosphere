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
    QuizProgressCounters,
    QuizScope,
    QuizStatus,
)
from question_generation_service.schemas.question import BATCH_SIZE
from question_generation_service.schemas.quiz import (
    QuizCreateRequest,
    QuizDetailResponse,
    QuizListItem,
    QuizListResponse,
    QuizProgressEvent,
    QuizResponse,
    QuizVisibility,
)

JOBS_GENERATE_QUESTIONS = "jobs:generate-questions"
DEFAULT_PAGE_SIZE = 20


def quiz_progress_channel(user_id: UUID) -> str:
    """Per-user pub/sub channel: one SSE stream covers every quiz the user
    owns, and subscribing is authorized by identity alone (own channel only).
    """
    return f"events:quiz-progress:{user_id}"


def build_progress_event(quiz_id: UUID, counters: QuizProgressCounters) -> QuizProgressEvent:
    """Derives the pushed payload with the same expected-count clamp and
    job-based status rule the REST responses use — the worker publishes
    through this so the two transports can never disagree.
    """
    expected = _expected_question_count(
        counters["question_count"], counters["time_limit_minutes"]
    )
    return QuizProgressEvent(
        quiz_id=quiz_id,
        questions_ready=min(counters["questions_ready"], expected),
        questions_expected=expected,
        jobs_completed=counters["jobs_completed"],
        jobs_total=counters["jobs_total"],
        status=_status(counters["jobs_completed"], counters["jobs_total"]),
    )


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

    async def create_copy(
        self, source: QuizEntryProtocol, new_id: UUID, owner_user_id: UUID
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

    async def delete(self, quiz_id: UUID) -> None: ...


class LearningUnitLookupProtocol(Protocol):
    async def get_by_thema(self, thema: str) -> Sequence[LearningUnitEntryProtocol]: ...


class SessionLookupProtocol(Protocol):
    async def user_has_session_for_quiz(self, user_id: UUID, quiz_id: UUID) -> bool: ...


def _expected_question_count(question_count: int | None, time_limit_minutes: int | None) -> int:
    if question_count is not None:
        return question_count
    # require_a_size guarantees time_limit_minutes is set on this path.
    minutes = time_limit_minutes or 0
    # Only the "~N questions" display estimate — completion no longer depends on
    # this number (it tracks jobs), so it never gates ready/generating.
    return max(1, math.ceil(minutes * 60 / SECONDS_PER_QUESTION_ESTIMATE))


def _target_question_count(body: QuizCreateRequest) -> int:
    return _expected_question_count(body.question_count, body.time_limit_minutes)


def _status(jobs_completed: int, jobs_total: int) -> QuizStatus:
    # Completion tracks the jobs, not the question count: a batch can yield fewer
    # than BATCH_SIZE questions (validation/dedup), so a question-count target is
    # not reliably reachable and would leave the quiz "generating" forever.
    return "ready" if jobs_completed >= jobs_total else "generating"


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
    entry: QuizEntryProtocol, owner_name: str | None, topics: list[str], is_owner: bool
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
        jobs_completed=entry.generation_jobs_completed,
        jobs_total=entry.generation_jobs_total,
        status=_status(entry.generation_jobs_completed, entry.generation_jobs_total),
        topics=topics,
        owner_name=owner_name,
        is_owner=is_owner,
        created_at=entry.created_at,
        updated_at=entry.updated_at,
    )


class QuizService:
    def __init__(
        self,
        quiz_repository: QuizLookupProtocol,
        learning_unit_repository: LearningUnitLookupProtocol,
        session_repository: SessionLookupProtocol,
    ):
        self.quiz_repository = quiz_repository
        self.learning_unit_repository = learning_unit_repository
        self.session_repository = session_repository

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

    async def _get_live(self, quiz_id: UUID) -> tuple[QuizEntryProtocol, str | None]:
        # Tombstoned quizzes 404 like missing ones: to every quiz endpoint a
        # soft-deleted quiz no longer exists — only session history (which
        # reads via get_refs_for_ids) still sees it.
        found = await self.quiz_repository.get(quiz_id)
        if found is None or found[0].deleted_at is not None:
            raise NotFoundError(f"No quiz found for id {quiz_id}")
        return found

    async def get(self, quiz_id: UUID, requesting_user_id: UUID) -> QuizDetailResponse:
        entry, owner_name = await self._get_live(quiz_id)
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
            jobs_completed=entry.generation_jobs_completed,
            jobs_total=entry.generation_jobs_total,
            status=_status(entry.generation_jobs_completed, entry.generation_jobs_total),
            topics=topics_by_quiz.get(entry.id, []),
            owner_name=None if is_owner else owner_name,
            is_owner=is_owner,
            created_at=entry.created_at,
            updated_at=entry.updated_at,
        )

    async def rename(
        self, quiz_id: UUID, requesting_user_id: UUID, title: str
    ) -> QuizDetailResponse:
        entry, _ = await self._get_live(quiz_id)
        # Same 404-not-403 reasoning as get(): a non-owner shouldn't be able
        # to distinguish "not yours" from "doesn't exist".
        if entry.owner_user_id != requesting_user_id:
            raise NotFoundError(f"No quiz found for id {quiz_id}")
        await self.quiz_repository.rename(quiz_id, title)
        return await self.get(quiz_id, requesting_user_id)

    async def delete(self, quiz_id: UUID, requesting_user_id: UUID) -> None:
        entry, _ = await self._get_live(quiz_id)
        # Same 404-not-403 reasoning as rename()/get().
        if entry.owner_user_id != requesting_user_id:
            raise NotFoundError(f"No quiz found for id {quiz_id}")
        await self.quiz_repository.delete(quiz_id)

    async def copy(self, quiz_id: UUID, requesting_user_id: UUID) -> QuizDetailResponse:
        """Fork-on-save ("Save to my quizzes"): clones the config under the
        requester; the shared question pools make the copy immediately usable.
        A soft-deleted source stays copyable by its owner and by users with a
        session that ran against it (resurrect-from-history), but 404s for
        everyone else so tombstones can't be enumerated.
        """
        found = await self.quiz_repository.get(quiz_id)
        if found is None:
            raise NotFoundError(f"No quiz found for id {quiz_id}")
        entry, _ = found
        is_owner = entry.owner_user_id == requesting_user_id
        if not is_owner and entry.visibility == "private":
            raise NotFoundError(f"No quiz found for id {quiz_id}")
        if (
            entry.deleted_at is not None
            and not is_owner
            and not await self.session_repository.user_has_session_for_quiz(
                requesting_user_id, quiz_id
            )
        ):
            raise NotFoundError(f"No quiz found for id {quiz_id}")
        created = await self.quiz_repository.create_copy(entry, uuid4(), requesting_user_id)
        return await self.get(created.id, requesting_user_id)

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
                entry,
                owner_name if scope == "shared" else None,
                topics_by_quiz.get(entry.id, []),
                entry.owner_user_id == requesting_user_id,
            )
            for entry, owner_name in rows
        ]
        return QuizListResponse(items=items, has_more=has_more)
