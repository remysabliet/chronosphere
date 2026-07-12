from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Literal, Protocol, TypedDict
from uuid import UUID

from sqlalchemy import Integer, exists, func, or_, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from memosphere_messaging import JsonValue
from question_generation_service.models.learning_unit import LearningUnit
from question_generation_service.models.quiz import (
    GenerationJobCompletion,
    Outbox,
    Quiz,
    QuizConcept,
)
from question_generation_service.models.user import User

# Mirrors the wizard's sizing heuristic (quiz/new/page.tsx) — how many
# questions a time-boxed quiz with no explicit question_count is expected to
# need. Kept here (rather than duplicated in quiz_service) since this repo is
# the only place that has to express it as a SQL expression too.
SECONDS_PER_QUESTION_ESTIMATE = 45

QuizScope = Literal["mine", "shared"]
QuizStatus = Literal["ready", "generating"]


class QuizInput(TypedDict):
    id: UUID
    owner_user_id: UUID
    thema: str
    title: str
    question_types: list[str]
    question_count: int | None
    time_limit_minutes: int | None
    visibility: str


class QuizConceptInput(TypedDict):
    quiz_id: UUID
    concept_id: UUID


class OutboxInput(TypedDict):
    topic: str
    payload: dict[str, JsonValue]


class QuizEntryProtocol(Protocol):
    id: UUID
    owner_user_id: UUID
    thema: str
    title: str
    question_types: list[str]
    question_count: int | None
    time_limit_minutes: int | None
    visibility: str
    generation_questions_ready: int
    created_at: datetime
    updated_at: datetime


class QuizRepositoryProtocol(Protocol):
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

    async def increment_questions_ready(self, quiz_id: UUID, delta: int) -> None: ...

    async def claim_job_completion(self, message_id: str) -> bool: ...


def _expected_count_expr():  # noqa: ANN202 — SQLAlchemy column expression, not a plain value
    # Same shape as quiz_service._target_question_count, expressed in SQL so
    # the "Ready"/"Generating" filter can be applied (and paginated) in the DB
    # rather than fetched-then-filtered in Python.
    return func.coalesce(
        Quiz.question_count,
        func.greatest(
            1,
            func.ceil(Quiz.time_limit_minutes * 60.0 / SECONDS_PER_QUESTION_ESTIMATE).cast(Integer),
        ),
    )


class QuizRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_with_outbox(
        self,
        quiz: QuizInput,
        outbox_entries: list[OutboxInput],
        concepts: list[QuizConceptInput],
    ) -> QuizEntryProtocol:
        # One transaction: the quiz row, its generation jobs, and the
        # concepts it covers commit or roll back together — the outbox
        # pattern's whole point.
        row = Quiz(
            id=quiz["id"],
            owner_user_id=quiz["owner_user_id"],
            thema=quiz["thema"],
            title=quiz["title"],
            question_types=quiz["question_types"],
            question_count=quiz["question_count"],
            time_limit_minutes=quiz["time_limit_minutes"],
            visibility=quiz["visibility"],
        )
        self.session.add(row)
        self.session.add_all(
            Outbox(topic=entry["topic"], payload=entry["payload"]) for entry in outbox_entries
        )
        self.session.add_all(
            QuizConcept(quiz_id=c["quiz_id"], concept_id=c["concept_id"]) for c in concepts
        )
        await self.session.commit()
        return row  # type: ignore[return-value]

    async def get(self, quiz_id: UUID) -> tuple[QuizEntryProtocol, str | None] | None:
        result = await self.session.execute(
            select(Quiz, User.name)
            .outerjoin(User, User.user_id == Quiz.owner_user_id)
            .where(Quiz.id == quiz_id)
        )
        row = result.first()
        return None if row is None else (row[0], row[1])

    async def get_topics_for_quizzes(self, quiz_ids: Sequence[UUID]) -> dict[UUID, list[str]]:
        if not quiz_ids:
            return {}
        result = await self.session.execute(
            select(
                QuizConcept.quiz_id,
                func.coalesce(LearningUnit.topic, LearningUnit.concept_name),
            )
            .join(LearningUnit, LearningUnit.id == QuizConcept.concept_id)
            .where(QuizConcept.quiz_id.in_(quiz_ids))
            .distinct()
        )
        topics_by_quiz: dict[UUID, list[str]] = {}
        for quiz_id, topic in result.all():
            topics_by_quiz.setdefault(quiz_id, []).append(topic)
        return topics_by_quiz

    async def list(
        self,
        *,
        owner_user_id: UUID,
        scope: QuizScope,
        q: str | None,
        status: QuizStatus | None,
        page: int,
        page_size: int,
    ) -> tuple[list[tuple[QuizEntryProtocol, str | None]], bool]:
        stmt = select(Quiz, User.name).outerjoin(User, User.user_id == Quiz.owner_user_id)
        if scope == "mine":
            stmt = stmt.where(Quiz.owner_user_id == owner_user_id)
        else:
            stmt = stmt.where(Quiz.owner_user_id != owner_user_id, Quiz.visibility != "private")
        if q:
            like = f"%{q}%"
            topic_match = exists(
                select(1)
                .select_from(QuizConcept)
                .join(LearningUnit, LearningUnit.id == QuizConcept.concept_id)
                .where(
                    QuizConcept.quiz_id == Quiz.id,
                    or_(LearningUnit.topic.ilike(like), LearningUnit.concept_name.ilike(like)),
                )
            )
            stmt = stmt.where(or_(Quiz.thema.ilike(like), Quiz.title.ilike(like), topic_match))
        if status == "ready":
            stmt = stmt.where(Quiz.generation_questions_ready >= _expected_count_expr())
        elif status == "generating":
            stmt = stmt.where(Quiz.generation_questions_ready < _expected_count_expr())

        # Fetch one extra row to detect "more pages" without a separate COUNT query.
        stmt = (
            stmt.order_by(Quiz.updated_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size + 1)
        )
        result = await self.session.execute(stmt)
        rows = result.all()
        has_more = len(rows) > page_size
        return [(row[0], row[1]) for row in rows[:page_size]], has_more

    async def rename(self, quiz_id: UUID, title: str) -> None:
        await self.session.execute(
            update(Quiz).where(Quiz.id == quiz_id).values(title=title, updated_at=func.now())
        )
        await self.session.commit()

    async def increment_questions_ready(self, quiz_id: UUID, delta: int) -> None:
        await self.session.execute(
            update(Quiz)
            .where(Quiz.id == quiz_id)
            .values(generation_questions_ready=Quiz.generation_questions_ready + delta)
        )
        await self.session.commit()

    async def claim_job_completion(self, message_id: str) -> bool:
        """True the first time this message_id is claimed, False on every
        redelivery of the same stream message — see generation_job_completions'
        migration for why increment_questions_ready needs this guard.
        """
        result = await self.session.execute(
            pg_insert(GenerationJobCompletion)
            .values(message_id=message_id)
            .on_conflict_do_nothing(index_elements=["message_id"])
            .returning(GenerationJobCompletion.message_id)
        )
        await self.session.commit()
        return result.first() is not None


class OutboxEntryProtocol(Protocol):
    id: int
    topic: str
    payload: dict[str, JsonValue]


class OutboxRepositoryProtocol(Protocol):
    async def fetch_unpublished(self, limit: int) -> Sequence[OutboxEntryProtocol]: ...

    async def mark_published(self, ids: Sequence[int]) -> None: ...


class OutboxRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def fetch_unpublished(self, limit: int) -> Sequence[OutboxEntryProtocol]:
        # SKIP LOCKED: concurrent relay instances never double-publish a row
        # they can see; a crashed relay's rows unlock with its transaction.
        result = await self.session.execute(
            select(Outbox)
            .where(Outbox.published_at.is_(None))
            .order_by(Outbox.id)
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
        return result.scalars().all()  # type: ignore[return-value]

    async def mark_published(self, ids: Sequence[int]) -> None:
        if not ids:
            return
        await self.session.execute(
            update(Outbox).where(Outbox.id.in_(ids)).values(published_at=datetime.now(UTC))
        )
        await self.session.commit()
