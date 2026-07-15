from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from question_generation_service.core.exceptions import InvalidInputError, NotFoundError
from question_generation_service.repositories.learning_unit_repository import (
    LearningUnitEntryProtocol,
)
from question_generation_service.repositories.quiz_repository import QuizEntryProtocol, QuizRef
from question_generation_service.repositories.session_repository import (
    ResponseInput,
    SessionEntryProtocol,
    SessionInput,
)
from question_generation_service.schemas.session import SubmitAnswerRequest
from question_generation_service.services.mastery_service import MasteryBand
from question_generation_service.services.session_service import SessionService

pytestmark = pytest.mark.asyncio


@dataclass
class FakeQuiz:
    id: UUID
    owner_user_id: UUID
    thema: str
    title: str
    question_types: list[str]
    question_count: int | None
    time_limit_minutes: int | None
    visibility: str
    generation_questions_ready: int = 0
    generation_jobs_total: int = 0
    generation_jobs_completed: int = 0
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    deleted_at: datetime | None = None


@dataclass
class FakeQuizRepository:
    quizzes: dict[UUID, FakeQuiz] = field(default_factory=dict)

    async def get(self, quiz_id: UUID) -> tuple[QuizEntryProtocol, str | None] | None:
        row = self.quizzes.get(quiz_id)
        return None if row is None else (row, None)

    async def get_refs_for_ids(self, quiz_ids: Sequence[UUID]) -> dict[UUID, QuizRef]:
        return {
            quiz_id: QuizRef(title=self.quizzes[quiz_id].title, deleted=False)
            for quiz_id in quiz_ids
            if quiz_id in self.quizzes
        }


@dataclass
class FakeUnit:
    id: UUID
    thema: str
    topic: str | None = "Topic"
    concept_name: str = "Concept"
    learning_goal: str | None = "Goal"
    bloom_levels_supported: list[str] | None = None
    estimated_time_minutes: int | None = 10
    bloom_coverage_score: int | None = 3
    complexity_level: str | None = "Medium"


@dataclass
class FakeLearningUnitRepository:
    units: list[FakeUnit]

    async def get_by_thema(self, thema: str) -> Sequence[LearningUnitEntryProtocol]:
        return [u for u in self.units if u.thema == thema]


@dataclass
class FakeQuestion:
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


@dataclass
class FakeQuestionRepository:
    questions: list[FakeQuestion] = field(default_factory=list)

    async def get_by_ids(self, ids: Sequence[UUID]) -> list[FakeQuestion]:
        by_id = {q.id: q for q in self.questions}
        return [by_id[i] for i in ids if i in by_id]

    async def get_pool_for_session(
        self,
        concept_ids: Sequence[UUID],
        question_types: Sequence[str],
        user_id: UUID,
        limit: int,
    ) -> list[FakeQuestion]:
        matches = [
            q
            for q in self.questions
            if q.concept_id in concept_ids and q.question_type in question_types
        ]
        return matches[:limit]

    async def mark_served(self, user_id: UUID, question_ids: Sequence[UUID]) -> None:
        pass


@dataclass
class FakeAdaptiveSelectionService:
    questions: list[FakeQuestion] = field(default_factory=list)
    served: set[UUID] = field(default_factory=set)

    async def select_next(
        self,
        user_id: UUID,
        units: Sequence[LearningUnitEntryProtocol],
        question_types: Sequence[str],
    ) -> tuple[FakeQuestion, MasteryBand] | None:
        concept_ids = {u.id for u in units}
        for question in self.questions:
            if question.id in self.served:
                continue
            if question.concept_id in concept_ids and question.question_type in question_types:
                self.served.add(question.id)
                return question, "Practice"
        return None


@dataclass
class FakeMasteryService:
    p_ln_next: float = 0.9
    decision_type: MasteryBand = "Practice"
    # When set, record_attempt expires every session, mirroring the real
    # ConceptProgressRepository.expire_all() the mastery path triggers.
    expires: "FakeSessionRepository | None" = None

    async def record_attempt(
        self, user_id: UUID, concept_id: UUID, bloom_level: str, is_correct: bool
    ) -> tuple[float, MasteryBand]:
        if self.expires is not None:
            for session in self.expires.sessions.values():
                session.expired = True
        return self.p_ln_next, self.decision_type


@dataclass
class FakeUserRepository:
    modes: dict[UUID, str] = field(default_factory=dict)

    async def get_default_feedback_mode(self, user_id: UUID) -> str | None:
        return self.modes.get(user_id)

    async def set_default_feedback_mode(self, user_id: UUID, mode: str) -> None:
        self.modes[user_id] = mode


class _ExpiredAttributeError(RuntimeError):
    """Stand-in for SQLAlchemy's MissingGreenlet: reading an ORM attribute that
    was expired by expire_all() lazy-loads it, which needs an await the caller
    isn't in."""


@dataclass
class FakeSession:
    session_id: UUID
    user_id: UUID
    quiz_id: UUID | None
    question_ids: list[UUID]
    thema: str | None
    feedback_mode: str = "end"
    session_status: str = "active"
    total_questions: int = 0
    correct_answers: int = 0
    start_time: datetime = field(default_factory=lambda: datetime.now(UTC))
    end_time: datetime | None = None
    total_time_seconds: int | None = None
    # Set by ConceptProgressRepository.expire_all() in production; a fresh
    # repository.get() clears it. Only quiz_id is guarded here because that's the
    # attribute the regression covers, but any expired attribute behaves this way.
    expired: bool = False

    def __getattribute__(self, name: str) -> object:
        if name == "quiz_id" and object.__getattribute__(self, "expired"):
            raise _ExpiredAttributeError("quiz_id read after expire_all()")
        return object.__getattribute__(self, name)


@dataclass
class FakeResponseEntry:
    question_id: UUID
    selected_option: str | None
    is_correct: bool | None
    question_sequence_order: int | None


@dataclass
class FakeSessionRepository:
    sessions: dict[UUID, FakeSession] = field(default_factory=dict)
    responses: list[ResponseInput] = field(default_factory=list)

    async def create(self, session_input: SessionInput) -> SessionEntryProtocol:
        row = FakeSession(
            session_id=uuid4(),
            user_id=session_input["user_id"],
            quiz_id=session_input["quiz_id"],
            question_ids=session_input["question_ids"],
            thema=session_input["thema"],
            feedback_mode=session_input["feedback_mode"],
        )
        self.sessions[row.session_id] = row
        return row  # type: ignore[return-value]

    async def get(self, session_id: UUID) -> SessionEntryProtocol | None:
        row = self.sessions.get(session_id)
        if row is not None:
            row.expired = False  # a fresh SELECT repopulates expired attributes
        return row  # type: ignore[return-value]

    async def record_response(self, response: ResponseInput) -> None:
        self.responses.append(response)
        row = self.sessions[response["session_id"]]
        row.total_questions += 1
        if response["is_correct"]:
            row.correct_answers += 1

    async def append_question(self, session_id: UUID, question_id: UUID) -> None:
        self.sessions[session_id].question_ids.append(question_id)

    async def complete(self, session_id: UUID, total_time_seconds: int) -> None:
        row = self.sessions[session_id]
        row.session_status = "completed"
        row.total_time_seconds = total_time_seconds
        row.end_time = datetime.now(UTC)

    async def list_responses(self, session_id: UUID) -> Sequence[FakeResponseEntry]:
        return [
            FakeResponseEntry(
                question_id=r["question_id"],
                selected_option=r["selected_option"],
                is_correct=r["is_correct"],
                question_sequence_order=r["question_sequence_order"],
            )
            for r in self.responses
            if r["session_id"] == session_id
        ]

    async def list_by_user(
        self, user_id: UUID, quiz_id: UUID | None, limit: int
    ) -> Sequence[SessionEntryProtocol]:
        rows = [
            s
            for s in self.sessions.values()
            if s.user_id == user_id and (quiz_id is None or s.quiz_id == quiz_id)
        ]
        return rows[:limit]  # type: ignore[return-value]


def make_service(
    quiz: FakeQuiz, units: list[FakeUnit], questions: list[FakeQuestion]
) -> tuple[SessionService, FakeSessionRepository]:
    session_repository = FakeSessionRepository()
    service = SessionService(
        session_repository,
        FakeQuizRepository({quiz.id: quiz}),
        FakeLearningUnitRepository(units),
        FakeQuestionRepository(questions),
        FakeMasteryService(),
        FakeAdaptiveSelectionService(questions),
        FakeUserRepository(),
    )
    return service, session_repository


def make_question(concept_id: UUID, correct: str = "A") -> FakeQuestion:
    return FakeQuestion(
        id=uuid4(),
        concept_id=concept_id,
        bloom_level="Remembering",
        difficulty_tier="medium",
        question_type="MCQ",
        question_text="What is A?",
        options=["A", "B"],
        correct_answers=[correct],
        explanation="Because A.",
        estimated_time="30",
        tags=[],
    )


async def test_start_creates_session_with_pool_questions():
    owner = uuid4()
    concept = FakeUnit(id=uuid4(), thema="Photosynthesis")
    quiz = FakeQuiz(
        id=uuid4(),
        owner_user_id=owner,
        thema="Photosynthesis",
        title="Photosynthesis",
        question_types=["MCQ"],
        question_count=2,
        time_limit_minutes=None,
        visibility="private",
    )
    questions = [make_question(concept.id) for _ in range(3)]
    service, _ = make_service(quiz, [concept], questions)

    state = await service.start(quiz.id, owner, None)

    assert state.total_questions == 2
    assert state.current_index == 0
    assert state.session_complete is False
    assert state.question is not None
    # Answer-stripped: no correct_answers/explanation leak to the client.
    assert not hasattr(state.question, "correct_answers")


async def test_start_rejects_non_owner_on_private_quiz():
    owner = uuid4()
    stranger = uuid4()
    concept = FakeUnit(id=uuid4(), thema="Photosynthesis")
    quiz = FakeQuiz(
        id=uuid4(),
        owner_user_id=owner,
        thema="Photosynthesis",
        title="Photosynthesis",
        question_types=["MCQ"],
        question_count=2,
        time_limit_minutes=None,
        visibility="private",
    )
    service, _ = make_service(quiz, [concept], [make_question(concept.id)])

    with pytest.raises(NotFoundError):
        await service.start(quiz.id, stranger, None)


async def test_start_raises_when_no_questions_available_yet():
    owner = uuid4()
    concept = FakeUnit(id=uuid4(), thema="Photosynthesis")
    quiz = FakeQuiz(
        id=uuid4(),
        owner_user_id=owner,
        thema="Photosynthesis",
        title="Photosynthesis",
        question_types=["MCQ"],
        question_count=5,
        time_limit_minutes=None,
        visibility="private",
    )
    service, _ = make_service(quiz, [concept], [])

    with pytest.raises(InvalidInputError):
        await service.start(quiz.id, owner, None)


async def test_submit_answer_grades_and_advances():
    owner = uuid4()
    concept = FakeUnit(id=uuid4(), thema="Photosynthesis")
    quiz = FakeQuiz(
        id=uuid4(),
        owner_user_id=owner,
        thema="Photosynthesis",
        title="Photosynthesis",
        question_types=["MCQ"],
        question_count=2,
        time_limit_minutes=None,
        visibility="private",
    )
    questions = [make_question(concept.id, correct="A"), make_question(concept.id, correct="B")]
    service, _ = make_service(quiz, [concept], questions)
    state = await service.start(quiz.id, owner, "immediate")
    assert state.question is not None
    first_question_id = state.question.id
    first_question = next(q for q in questions if q.id == first_question_id)
    assert first_question.correct_answers is not None

    result = await service.submit_answer(
        state.session_id,
        owner,
        SubmitAnswerRequest(
            question_id=first_question_id, selected=[first_question.correct_answers[0]]
        ),
    )

    assert result.is_correct is True
    assert result.state.current_index == 1
    assert result.state.correct_count == 1
    assert result.state.session_complete is False


async def test_submit_wrong_answer_and_completes_session_on_last_question():
    owner = uuid4()
    concept = FakeUnit(id=uuid4(), thema="Photosynthesis")
    quiz = FakeQuiz(
        id=uuid4(),
        owner_user_id=owner,
        thema="Photosynthesis",
        title="Photosynthesis",
        question_types=["MCQ"],
        question_count=1,
        time_limit_minutes=None,
        visibility="private",
    )
    question = make_question(concept.id, correct="A")
    service, repo = make_service(quiz, [concept], [question])
    state = await service.start(quiz.id, owner, "immediate")
    assert state.question is not None

    result = await service.submit_answer(
        state.session_id, owner, SubmitAnswerRequest(question_id=question.id, selected=["B"])
    )

    assert result.is_correct is False
    assert result.state.session_complete is True
    assert result.state.question is None
    assert repo.sessions[state.session_id].session_status == "completed"


async def test_submit_answer_survives_identity_map_expiry_after_record_attempt():
    # Regression: mastery_service.record_attempt expire_all()s the shared session,
    # so submit_answer must have already read session.quiz_id — reading it after
    # (to load the quiz) lazy-loads an expired attribute and raises MissingGreenlet.
    owner = uuid4()
    concept = FakeUnit(id=uuid4(), thema="Photosynthesis")
    quiz = FakeQuiz(
        id=uuid4(),
        owner_user_id=owner,
        thema="Photosynthesis",
        title="Photosynthesis",
        question_types=["TrueFalse"],
        question_count=2,
        time_limit_minutes=None,
        visibility="private",
    )
    questions = [make_question(concept.id, correct="A"), make_question(concept.id, correct="B")]
    for q in questions:
        q.question_type = "TrueFalse"
    session_repository = FakeSessionRepository()
    service = SessionService(
        session_repository,
        FakeQuizRepository({quiz.id: quiz}),
        FakeLearningUnitRepository([concept]),
        FakeQuestionRepository(questions),
        FakeMasteryService(expires=session_repository),
        FakeAdaptiveSelectionService(questions),
        FakeUserRepository(),
    )
    state = await service.start(quiz.id, owner, "immediate")
    assert state.question is not None
    first_question = next(q for q in questions if q.id == state.question.id)
    assert first_question.correct_answers is not None

    # Must not raise _ExpiredAttributeError.
    result = await service.submit_answer(
        state.session_id,
        owner,
        SubmitAnswerRequest(
            question_id=first_question.id, selected=[first_question.correct_answers[0]]
        ),
    )

    assert result.is_correct is True
    assert result.state.current_index == 1


async def test_submit_answer_rejects_wrong_question_id():
    owner = uuid4()
    concept = FakeUnit(id=uuid4(), thema="Photosynthesis")
    quiz = FakeQuiz(
        id=uuid4(),
        owner_user_id=owner,
        thema="Photosynthesis",
        title="Photosynthesis",
        question_types=["MCQ"],
        question_count=2,
        time_limit_minutes=None,
        visibility="private",
    )
    questions = [make_question(concept.id), make_question(concept.id)]
    service, _ = make_service(quiz, [concept], questions)
    state = await service.start(quiz.id, owner, None)
    assert state.question is not None
    wrong_question = next(q for q in questions if q.id != state.question.id)

    with pytest.raises(InvalidInputError):
        await service.submit_answer(
            state.session_id,
            owner,
            SubmitAnswerRequest(question_id=wrong_question.id, selected=["A"]),
        )


async def test_summary_reflects_final_stats():
    owner = uuid4()
    concept = FakeUnit(id=uuid4(), thema="Photosynthesis")
    quiz = FakeQuiz(
        id=uuid4(),
        owner_user_id=owner,
        thema="Photosynthesis",
        title="Photosynthesis",
        question_types=["MCQ"],
        question_count=1,
        time_limit_minutes=None,
        visibility="private",
    )
    question = make_question(concept.id, correct="A")
    service, _ = make_service(quiz, [concept], [question])
    state = await service.start(quiz.id, owner, None)
    assert state.question is not None
    await service.submit_answer(
        state.session_id, owner, SubmitAnswerRequest(question_id=question.id, selected=["A"])
    )

    summary = await service.summary(state.session_id, owner)

    assert summary.status == "completed"
    assert summary.total_questions == 1
    assert summary.correct_answers == 1
    assert summary.accuracy == 1.0


async def test_get_current_rejects_other_users_session():
    owner = uuid4()
    stranger = uuid4()
    concept = FakeUnit(id=uuid4(), thema="Photosynthesis")
    quiz = FakeQuiz(
        id=uuid4(),
        owner_user_id=owner,
        thema="Photosynthesis",
        title="Photosynthesis",
        question_types=["MCQ"],
        question_count=1,
        time_limit_minutes=None,
        visibility="private",
    )
    service, _ = make_service(quiz, [concept], [make_question(concept.id)])
    state = await service.start(quiz.id, owner, None)

    with pytest.raises(NotFoundError):
        await service.get_current(state.session_id, stranger)
