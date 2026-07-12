from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from memosphere_domain import QuestionType

SessionStatus = Literal["active", "completed"]


class SessionQuestion(BaseModel):
    """Answer-stripped view of a stored question — no correct_answers, no
    explanation. Those only ever go out in AnswerResult, after the learner
    has submitted something to grade.
    """

    id: UUID
    question_type: QuestionType
    question_text: str
    options: list[str] | None
    estimated_time_seconds: int | None


class SessionState(BaseModel):
    session_id: UUID
    quiz_id: UUID | None
    total_questions: int
    current_index: int
    correct_count: int
    session_complete: bool
    question: SessionQuestion | None


class SubmitAnswerRequest(BaseModel):
    question_id: UUID
    selected: list[str] = Field(min_length=1)
    response_time_seconds: int | None = None


class AnswerResult(BaseModel):
    is_correct: bool
    correct_answers: list[str]
    explanation: str
    state: SessionState


class SessionSummary(BaseModel):
    session_id: UUID
    quiz_id: UUID | None
    total_questions: int
    correct_answers: int
    accuracy: float
    total_time_seconds: int | None
    status: SessionStatus
