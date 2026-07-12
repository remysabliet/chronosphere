import json
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Protocol, cast
from uuid import UUID

from memosphere_domain import QuestionType
from question_generation_service.core.exceptions import InvalidInputError, NotFoundError
from question_generation_service.repositories.learning_unit_repository import (
    LearningUnitEntryProtocol,
)
from question_generation_service.repositories.question_repository import QuestionEntryProtocol
from question_generation_service.repositories.quiz_repository import QuizEntryProtocol
from question_generation_service.repositories.session_repository import (
    ResponseInput,
    SessionEntryProtocol,
    SessionInput,
    SessionRepositoryProtocol,
)
from question_generation_service.schemas.session import (
    AnswerResult,
    SessionQuestion,
    SessionState,
    SessionSummary,
    SubmitAnswerRequest,
)
from question_generation_service.services.mastery_service import MasteryBand, MasteryServiceProtocol
from question_generation_service.services.question_validation_service import answers_match
from question_generation_service.services.quiz_service import _expected_question_count

# Upper bound on how many questions a single session ever pulls, independent
# of the quiz's own target — a defensive cap, not a product decision.
MAX_SESSION_POOL_SIZE = 100


# Narrower than the repositories' full protocols (QuizRepositoryProtocol etc.
# also cover writes/listing this service never does) — Interface Segregation:
# depend only on what's actually called here. The real repositories already
# satisfy these structurally; no adapter needed.
class QuizLookupProtocol(Protocol):
    async def get(self, quiz_id: UUID) -> tuple[QuizEntryProtocol, str | None] | None: ...


class ConceptLookupProtocol(Protocol):
    async def get_by_thema(self, thema: str) -> Sequence[LearningUnitEntryProtocol]: ...


class QuestionLookupProtocol(Protocol):
    async def get_by_ids(self, ids: Sequence[UUID]) -> Sequence[QuestionEntryProtocol]: ...

    async def mark_served(self, user_id: UUID, question_ids: Sequence[UUID]) -> None: ...


class AdaptiveSelectionServiceProtocol(Protocol):
    async def select_next(
        self,
        user_id: UUID,
        units: Sequence[LearningUnitEntryProtocol],
        question_types: Sequence[str],
    ) -> tuple[QuestionEntryProtocol, MasteryBand] | None: ...


def _to_session_question(entry: QuestionEntryProtocol) -> SessionQuestion:
    return SessionQuestion(
        id=entry.id,
        question_type=cast(QuestionType, entry.question_type),
        question_text=entry.question_text,
        options=entry.options,
        estimated_time_seconds=int(entry.estimated_time) if entry.estimated_time else None,
    )


class SessionService:
    def __init__(
        self,
        session_repository: SessionRepositoryProtocol,
        quiz_repository: QuizLookupProtocol,
        learning_unit_repository: ConceptLookupProtocol,
        question_repository: QuestionLookupProtocol,
        mastery_service: MasteryServiceProtocol,
        adaptive_selection_service: AdaptiveSelectionServiceProtocol,
    ):
        self.session_repository = session_repository
        self.quiz_repository = quiz_repository
        self.learning_unit_repository = learning_unit_repository
        self.question_repository = question_repository
        self.mastery_service = mastery_service
        self.adaptive_selection_service = adaptive_selection_service

    async def start(self, quiz_id: UUID, user_id: UUID) -> SessionState:
        found = await self.quiz_repository.get(quiz_id)
        if found is None:
            raise NotFoundError(f"No quiz found for id {quiz_id}")
        quiz, _owner_name = found
        if quiz.owner_user_id != user_id and quiz.visibility == "private":
            raise NotFoundError(f"No quiz found for id {quiz_id}")

        units = await self.learning_unit_repository.get_by_thema(quiz.thema)
        target = self._target(quiz)

        selected = await self.adaptive_selection_service.select_next(
            user_id, units, quiz.question_types
        )
        if selected is None:
            raise InvalidInputError(
                "No questions are ready for this quiz yet — check back once generation completes"
            )
        question, _decision_type = selected
        await self.question_repository.mark_served(user_id, [question.id])

        session = await self.session_repository.create(
            SessionInput(
                user_id=user_id,
                quiz_id=quiz_id,
                thema=quiz.thema,
                question_ids=[question.id],
            )
        )
        return await self._state(session, target)

    async def get_current(self, session_id: UUID, user_id: UUID) -> SessionState:
        session = await self._get_owned_session(session_id, user_id)
        quiz = await self._quiz_for_session(session)
        return await self._state(session, self._target(quiz))

    async def submit_answer(
        self, session_id: UUID, user_id: UUID, body: SubmitAnswerRequest
    ) -> AnswerResult:
        session = await self._get_owned_session(session_id, user_id)
        index = session.total_questions
        if index >= len(session.question_ids):
            raise InvalidInputError("This session is already complete")
        if body.question_id != session.question_ids[index]:
            raise InvalidInputError("That isn't the current question for this session")

        matches = await self.question_repository.get_by_ids([body.question_id])
        if not matches:
            raise NotFoundError(f"No question found for id {body.question_id}")
        question = matches[0]
        # Pulled out now, not read off `question` again below: record_attempt
        # and the repository writes that follow all do Core-style UPDATEs and
        # expire the session's whole identity map to keep later reads fresh
        # (see SessionRepository/ConceptProgressRepository) — touching an
        # expired ORM attribute outside an awaited call breaks SQLAlchemy's
        # async greenlet bridge (MissingGreenlet), so `question` itself must
        # not be touched again past this point.
        question_id = question.id
        question_concept_id = question.concept_id
        question_bloom_level = question.bloom_level
        question_correct_answers = question.correct_answers or []
        question_explanation = question.explanation or ""
        is_correct = answers_match(body.selected, question_correct_answers, False)

        # Run before logging the response: the band a question was picked
        # under is Step 11's decision, made from mastery as it stood prior
        # to this attempt — record_attempt reads that prior state.
        _p_ln_next, decision_type = await self.mastery_service.record_attempt(
            user_id, question_concept_id, question_bloom_level, is_correct
        )

        quiz = await self._quiz_for_session(session)
        target = self._target(quiz)

        # Resolved before record_response is persisted: if selection raises,
        # nothing about this attempt has been committed yet, so
        # total_questions/question_ids can't drift out of sync the way they
        # would if this ran after the response was already recorded.
        next_question_id: UUID | None = None
        if index + 1 < target:
            units = await self.learning_unit_repository.get_by_thema(quiz.thema)
            selected = await self.adaptive_selection_service.select_next(
                user_id, units, quiz.question_types
            )
            if selected is not None:
                next_question, _next_decision_type = selected
                await self.question_repository.mark_served(user_id, [next_question.id])
                next_question_id = next_question.id

        await self.session_repository.record_response(
            ResponseInput(
                session_id=session_id,
                user_id=user_id,
                question_id=question_id,
                concept_id=question_concept_id,
                bloom_level=question_bloom_level,
                selected_option=json.dumps(body.selected),
                is_correct=is_correct,
                response_time=body.response_time_seconds,
                question_sequence_order=index,
                decision_type=decision_type,
            )
        )

        if next_question_id is not None:
            await self.session_repository.append_question(session_id, next_question_id)
            refreshed = await self._get_owned_session(session_id, user_id)
        else:
            # Either the target was reached, or every band's pool is
            # exhausted — end the session gracefully rather than error
            # mid-quiz; the learner still gets a summary for what they did
            # answer.
            refreshed = await self._complete_session(
                session_id, await self._get_owned_session(session_id, user_id)
            )

        return AnswerResult(
            is_correct=is_correct,
            correct_answers=question_correct_answers,
            explanation=question_explanation,
            state=await self._state(refreshed, target),
        )

    async def summary(self, session_id: UUID, user_id: UUID) -> SessionSummary:
        session = await self._get_owned_session(session_id, user_id)
        total = len(session.question_ids)
        return SessionSummary(
            session_id=session.session_id,
            quiz_id=session.quiz_id,
            total_questions=total,
            correct_answers=session.correct_answers,
            accuracy=(session.correct_answers / total) if total else 0.0,
            total_time_seconds=session.total_time_seconds,
            status="completed" if session.session_status == "completed" else "active",
        )

    async def _get_owned_session(self, session_id: UUID, user_id: UUID) -> SessionEntryProtocol:
        session = await self.session_repository.get(session_id)
        if session is None or session.user_id != user_id:
            raise NotFoundError(f"No session found for id {session_id}")
        return session

    async def _quiz_for_session(self, session: SessionEntryProtocol) -> QuizEntryProtocol:
        if session.quiz_id is None:
            raise NotFoundError(f"Session {session.session_id} has no associated quiz")
        found = await self.quiz_repository.get(session.quiz_id)
        if found is None:
            raise NotFoundError(f"No quiz found for id {session.quiz_id}")
        quiz, _owner_name = found
        return quiz

    def _target(self, quiz: QuizEntryProtocol) -> int:
        return min(
            _expected_question_count(quiz.question_count, quiz.time_limit_minutes),
            MAX_SESSION_POOL_SIZE,
        )

    async def _complete_session(
        self, session_id: UUID, refreshed: SessionEntryProtocol
    ) -> SessionEntryProtocol:
        # Both pulled out before complete() — it expires the identity map
        # (same reasoning as submit_answer above), so `refreshed` itself
        # can't be read again after that call.
        user_id = refreshed.user_id
        elapsed = int((datetime.now(UTC) - refreshed.start_time).total_seconds())
        await self.session_repository.complete(session_id, elapsed)
        return await self._get_owned_session(session_id, user_id)

    async def _state(self, session: SessionEntryProtocol, target: int) -> SessionState:
        index = session.total_questions
        complete = session.session_status == "completed"
        question = None
        if not complete and index < len(session.question_ids):
            matches = await self.question_repository.get_by_ids([session.question_ids[index]])
            question = _to_session_question(matches[0]) if matches else None
        return SessionState(
            session_id=session.session_id,
            quiz_id=session.quiz_id,
            total_questions=target,
            current_index=index,
            correct_count=session.correct_answers,
            session_complete=complete,
            question=question,
        )
