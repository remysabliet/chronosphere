from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Protocol, TypedDict
from uuid import UUID

from sqlalchemy import exists, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from question_generation_service.models.session import QuizSession, UserResponse


class SessionInput(TypedDict):
    user_id: UUID
    quiz_id: UUID
    thema: str
    question_ids: list[UUID]
    feedback_mode: str


class ResponseInput(TypedDict):
    session_id: UUID
    user_id: UUID
    question_id: UUID
    concept_id: UUID
    bloom_level: str
    selected_option: str | None
    is_correct: bool
    response_time: int | None
    question_sequence_order: int
    decision_type: str


class SessionEntryProtocol(Protocol):
    session_id: UUID
    user_id: UUID
    quiz_id: UUID | None
    question_ids: list[UUID]
    thema: str | None
    session_status: str
    feedback_mode: str
    total_questions: int
    correct_answers: int
    start_time: datetime
    end_time: datetime | None
    total_time_seconds: int | None


class ResponseEntryProtocol(Protocol):
    question_id: UUID
    selected_option: str | None
    is_correct: bool | None
    question_sequence_order: int | None


class SessionRepositoryProtocol(Protocol):
    async def create(self, session_input: SessionInput) -> SessionEntryProtocol: ...

    async def get(self, session_id: UUID) -> SessionEntryProtocol | None: ...

    async def record_response(self, response: ResponseInput) -> None: ...

    async def append_question(self, session_id: UUID, question_id: UUID) -> None: ...

    async def complete(self, session_id: UUID, total_time_seconds: int) -> None: ...

    async def list_responses(self, session_id: UUID) -> Sequence[ResponseEntryProtocol]: ...

    async def list_by_user(
        self, user_id: UUID, quiz_id: UUID | None, limit: int
    ) -> Sequence[SessionEntryProtocol]: ...

    async def user_has_session_for_quiz(self, user_id: UUID, quiz_id: UUID) -> bool: ...


class SessionRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, session_input: SessionInput) -> SessionEntryProtocol:
        row = QuizSession(
            user_id=session_input["user_id"],
            quiz_id=session_input["quiz_id"],
            thema=session_input["thema"],
            question_ids=session_input["question_ids"],
            session_type="assessment",
            feedback_mode=session_input["feedback_mode"],
        )
        self.session.add(row)
        await self.session.commit()
        return row  # pyright: ignore[reportReturnType]

    async def get(self, session_id: UUID) -> SessionEntryProtocol | None:
        result = await self.session.execute(
            select(QuizSession).where(QuizSession.session_id == session_id)
        )
        return result.scalar_one_or_none()  # pyright: ignore[reportReturnType]

    async def record_response(self, response: ResponseInput) -> None:
        # Session row and its response share a transaction — the counters
        # must never drift from the responses that produced them.
        self.session.add(
            UserResponse(
                session_id=response["session_id"],
                user_id=response["user_id"],
                question_id=response["question_id"],
                concept_id=response["concept_id"],
                bloom_level=response["bloom_level"],
                selected_option=response["selected_option"],
                is_correct=response["is_correct"],
                response_time=response["response_time"],
                question_sequence_order=response["question_sequence_order"],
                decision_type=response["decision_type"],
            )
        )
        await self.session.execute(
            update(QuizSession)
            .where(QuizSession.session_id == response["session_id"])
            .values(
                total_questions=QuizSession.total_questions + 1,
                correct_answers=QuizSession.correct_answers + (1 if response["is_correct"] else 0),
            )
        )
        await self.session.commit()
        # Core-style UPDATE, not an ORM attribute write — the QuizSession
        # instance already in this AsyncSession's identity map (loaded by an
        # earlier get() in the same request) would otherwise keep serving its
        # pre-update total_questions/question_ids on every later get().
        self.session.expire_all()

    async def append_question(self, session_id: UUID, question_id: UUID) -> None:
        await self.session.execute(
            update(QuizSession)
            .where(QuizSession.session_id == session_id)
            .values(question_ids=func.array_append(QuizSession.question_ids, question_id))
        )
        await self.session.commit()
        self.session.expire_all()

    async def complete(self, session_id: UUID, total_time_seconds: int) -> None:
        await self.session.execute(
            update(QuizSession)
            .where(QuizSession.session_id == session_id)
            .values(
                session_status="completed",
                end_time=datetime.now(UTC),
                total_time_seconds=total_time_seconds,
            )
        )
        await self.session.commit()
        self.session.expire_all()

    async def list_responses(self, session_id: UUID) -> Sequence[ResponseEntryProtocol]:
        result = await self.session.execute(
            select(UserResponse)
            .where(UserResponse.session_id == session_id)
            .order_by(UserResponse.question_sequence_order)
        )
        return result.scalars().all()  # pyright: ignore[reportReturnType]

    async def list_by_user(
        self, user_id: UUID, quiz_id: UUID | None, limit: int
    ) -> Sequence[SessionEntryProtocol]:
        query = select(QuizSession).where(QuizSession.user_id == user_id)
        if quiz_id is not None:
            query = query.where(QuizSession.quiz_id == quiz_id)
        result = await self.session.execute(
            query.order_by(QuizSession.start_time.desc()).limit(limit)
        )
        return result.scalars().all()  # pyright: ignore[reportReturnType]

    async def user_has_session_for_quiz(self, user_id: UUID, quiz_id: UUID) -> bool:
        result = await self.session.execute(
            select(
                exists().where(QuizSession.user_id == user_id, QuizSession.quiz_id == quiz_id)
            )
        )
        return bool(result.scalar())
