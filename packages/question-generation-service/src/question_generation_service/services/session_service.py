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
from question_generation_service.repositories.quiz_repository import QuizEntryProtocol, QuizRef
from question_generation_service.repositories.session_repository import (
    ResponseInput,
    SessionEntryProtocol,
    SessionInput,
    SessionRepositoryProtocol,
)
from question_generation_service.schemas.session import (
    AnswerResult,
    FeedbackMode,
    SessionHistory,
    SessionHistoryEntry,
    SessionPreferences,
    SessionQuestion,
    SessionReview,
    SessionReviewEntry,
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

    async def get_refs_for_ids(self, quiz_ids: Sequence[UUID]) -> dict[UUID, QuizRef]: ...


class ConceptLookupProtocol(Protocol):
    async def get_by_thema(self, thema: str) -> Sequence[LearningUnitEntryProtocol]: ...


class QuestionLookupProtocol(Protocol):
    async def get_by_ids(self, ids: Sequence[UUID]) -> Sequence[QuestionEntryProtocol]: ...

    async def mark_served(self, user_id: UUID, question_ids: Sequence[UUID]) -> None: ...


class UserPreferenceProtocol(Protocol):
    async def get_default_feedback_mode(self, user_id: UUID) -> str | None: ...

    async def set_default_feedback_mode(self, user_id: UUID, mode: str) -> None: ...


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


def _to_feedback_mode(raw: str) -> FeedbackMode:
    if raw not in ("immediate", "end", "never"):
        return "end"
    return cast(FeedbackMode, raw)


def _quiz_label(quiz_id: UUID | None, refs: dict[UUID, QuizRef]) -> tuple[str | None, bool]:
    """(title, deleted) for the quiz a session ran against. A quiz_id whose
    row is gone (hard-purged) counts as deleted; a session with no quiz_id
    at all doesn't — there's simply nothing to retake.
    """
    if quiz_id is None:
        return None, False
    ref = refs.get(quiz_id)
    if ref is None:
        return None, True
    return ref["title"], ref["deleted"]


def _parse_selected(raw: str | None) -> list[str]:
    # selected_option predates JSON encoding — older rows hold plain text.
    if raw is None:
        return []
    try:
        decoded = json.loads(raw)
    except ValueError:
        return [raw]
    if isinstance(decoded, list):
        return [str(item) for item in decoded]  # pyright: ignore[reportUnknownVariableType, reportUnknownArgumentType]
    return [str(decoded)]


class SessionService:
    def __init__(
        self,
        session_repository: SessionRepositoryProtocol,
        quiz_repository: QuizLookupProtocol,
        learning_unit_repository: ConceptLookupProtocol,
        question_repository: QuestionLookupProtocol,
        mastery_service: MasteryServiceProtocol,
        adaptive_selection_service: AdaptiveSelectionServiceProtocol,
        user_repository: UserPreferenceProtocol,
    ):
        self.session_repository = session_repository
        self.quiz_repository = quiz_repository
        self.learning_unit_repository = learning_unit_repository
        self.question_repository = question_repository
        self.mastery_service = mastery_service
        self.adaptive_selection_service = adaptive_selection_service
        self.user_repository = user_repository

    async def preferences(self, user_id: UUID) -> SessionPreferences:
        stored = await self.user_repository.get_default_feedback_mode(user_id)
        return SessionPreferences(default_feedback_mode=_to_feedback_mode(stored or "end"))

    async def start(
        self, quiz_id: UUID, user_id: UUID, feedback_mode: FeedbackMode | None
    ) -> SessionState:
        found = await self.quiz_repository.get(quiz_id)
        if found is None:
            raise NotFoundError(f"No quiz found for id {quiz_id}")
        quiz, _owner_name = found
        # Deleted quizzes can't start new runs (404, matching QuizService);
        # sessions already in flight keep working via _quiz_by_id, which
        # deliberately still resolves tombstones.
        if quiz.deleted_at is not None or (
            quiz.owner_user_id != user_id and quiz.visibility == "private"
        ):
            raise NotFoundError(f"No quiz found for id {quiz_id}")

        # Hoisted before the preference persist below: set_default_feedback_mode
        # commits and expires the identity map, so quiz/question attributes must
        # not be read from ORM objects after it runs.
        thema = quiz.thema
        question_types = quiz.question_types
        target = self._target(quiz)

        units = await self.learning_unit_repository.get_by_thema(thema)
        selected = await self.adaptive_selection_service.select_next(user_id, units, question_types)
        if selected is None:
            raise InvalidInputError(
                "No questions are ready for this quiz yet — check back once generation completes"
            )
        question, _decision_type = selected
        question_id = question.id

        # Persist only once the start is known to succeed, so a failed start
        # never mutates the stored default.
        if feedback_mode is None:
            stored = await self.user_repository.get_default_feedback_mode(user_id)
            resolved_mode = _to_feedback_mode(stored or "end")
        else:
            resolved_mode = feedback_mode
            await self.user_repository.set_default_feedback_mode(user_id, feedback_mode)

        await self.question_repository.mark_served(user_id, [question_id])

        session = await self.session_repository.create(
            SessionInput(
                user_id=user_id,
                quiz_id=quiz_id,
                thema=thema,
                question_ids=[question_id],
                feedback_mode=resolved_mode,
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
        # Read off `session` now, before record_attempt below expire_all()s the
        # identity map (see the `question` hoist comment): touching these ORM
        # attributes afterward would lazy-load and break the async greenlet bridge.
        session_quiz_id = session.quiz_id
        session_feedback_mode = _to_feedback_mode(session.feedback_mode)

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

        quiz = await self._quiz_by_id(session_quiz_id, session_id)
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

        # Outside immediate mode the answer is recorded silently: grading only
        # surfaces on the results page (and never for exam-mode expected answers).
        immediate = session_feedback_mode == "immediate"
        return AnswerResult(
            is_correct=is_correct if immediate else None,
            correct_answers=question_correct_answers if immediate else None,
            explanation=question_explanation if immediate else None,
            state=await self._state(refreshed, target),
        )

    async def summary(self, session_id: UUID, user_id: UUID) -> SessionSummary:
        session = await self._get_owned_session(session_id, user_id)
        return self._summary_of(session, await self._quiz_refs_for(session))

    async def history(self, user_id: UUID, quiz_id: UUID | None, limit: int) -> SessionHistory:
        sessions = await self.session_repository.list_by_user(user_id, quiz_id, limit)
        # One batch ref lookup for the whole page — deleted quizzes included,
        # so history rows can still name them (and badge the tombstone).
        refs = await self.quiz_repository.get_refs_for_ids(
            list({session.quiz_id for session in sessions if session.quiz_id is not None})
        )
        entries: list[SessionHistoryEntry] = []
        for session in sessions:
            entries.append(
                SessionHistoryEntry(
                    **self._summary_of(session, refs).model_dump(),
                    feedback_mode=_to_feedback_mode(session.feedback_mode),
                    started_at=session.start_time,
                )
            )
        return SessionHistory(sessions=entries)

    async def review(self, session_id: UUID, user_id: UUID) -> SessionReview:
        session = await self._get_owned_session(session_id, user_id)
        if session.session_status != "completed":
            # Opening the review mid-session would leak expected answers in
            # end/never modes — the results page only exists once it's over.
            raise InvalidInputError("This session isn't finished yet")
        mode = _to_feedback_mode(session.feedback_mode)
        summary = self._summary_of(session, await self._quiz_refs_for(session))

        responses = await self.session_repository.list_responses(session_id)
        question_ids = [response.question_id for response in responses]
        questions = await self.question_repository.get_by_ids(question_ids)
        by_id = {question.id: question for question in questions}

        reveal = mode != "never"
        entries: list[SessionReviewEntry] = []
        for response in responses:
            question = by_id.get(response.question_id)
            if question is None:
                continue
            entries.append(
                SessionReviewEntry(
                    question_id=response.question_id,
                    question_type=cast(QuestionType, question.question_type),
                    question_text=question.question_text,
                    options=question.options,
                    selected=_parse_selected(response.selected_option),
                    is_correct=response.is_correct,
                    correct_answers=(question.correct_answers or []) if reveal else None,
                    explanation=(question.explanation or "") if reveal else None,
                )
            )
        return SessionReview(summary=summary, feedback_mode=mode, entries=entries)

    async def _quiz_refs_for(self, session: SessionEntryProtocol) -> dict[UUID, QuizRef]:
        if session.quiz_id is None:
            return {}
        return await self.quiz_repository.get_refs_for_ids([session.quiz_id])

    def _summary_of(
        self, session: SessionEntryProtocol, refs: dict[UUID, QuizRef]
    ) -> SessionSummary:
        # Answered count, not len(question_ids): an active session always has
        # one served-but-unanswered question that must not drag accuracy down.
        total = session.total_questions
        quiz_title, quiz_deleted = _quiz_label(session.quiz_id, refs)
        return SessionSummary(
            session_id=session.session_id,
            quiz_id=session.quiz_id,
            quiz_title=quiz_title,
            quiz_deleted=quiz_deleted,
            thema=session.thema,
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
        return await self._quiz_by_id(session.quiz_id, session.session_id)

    async def _quiz_by_id(self, quiz_id: UUID | None, session_id: UUID) -> QuizEntryProtocol:
        if quiz_id is None:
            raise NotFoundError(f"Session {session_id} has no associated quiz")
        found = await self.quiz_repository.get(quiz_id)
        if found is None:
            raise NotFoundError(f"No quiz found for id {quiz_id}")
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
        mode = _to_feedback_mode(session.feedback_mode)
        question = None
        if not complete and index < len(session.question_ids):
            matches = await self.question_repository.get_by_ids([session.question_ids[index]])
            question = _to_session_question(matches[0]) if matches else None
        # Running correctness stays hidden mid-session outside immediate mode —
        # a live counter would leak per-question grading before the results page.
        show_count = complete or mode == "immediate"
        return SessionState(
            session_id=session.session_id,
            quiz_id=session.quiz_id,
            feedback_mode=mode,
            total_questions=target,
            current_index=index,
            correct_count=session.correct_answers if show_count else None,
            session_complete=complete,
            question=question,
        )
