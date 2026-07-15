from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from memosphere_domain import QuestionType

SessionStatus = Literal["active", "completed"]
FeedbackMode = Literal["immediate", "end", "never"]


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


class StartSessionRequest(BaseModel):
    """feedback_mode omitted → the user's remembered default; provided → used
    for this session and saved as the new default.
    """

    feedback_mode: FeedbackMode | None = None


class SessionState(BaseModel):
    session_id: UUID
    quiz_id: UUID | None
    feedback_mode: FeedbackMode
    total_questions: int
    current_index: int
    # None while the session is active outside immediate mode — running
    # correctness must not leak before the results page.
    correct_count: int | None
    session_complete: bool
    question: SessionQuestion | None


class SubmitAnswerRequest(BaseModel):
    question_id: UUID
    selected: list[str] = Field(min_length=1)
    response_time_seconds: int | None = None


class AnswerResult(BaseModel):
    """Grading fields are None outside immediate mode — the answer is
    recorded silently and only surfaces on the results page.
    """

    is_correct: bool | None
    correct_answers: list[str] | None
    explanation: str | None
    state: SessionState


class SessionSummary(BaseModel):
    """quiz_title/thema label the session even after its quiz is deleted;
    quiz_deleted marks the tombstone so clients can disable retake and badge
    the results.
    """

    session_id: UUID
    quiz_id: UUID | None
    quiz_title: str | None
    quiz_deleted: bool
    thema: str | None
    total_questions: int
    correct_answers: int
    accuracy: float
    total_time_seconds: int | None
    status: SessionStatus


class SessionReviewEntry(BaseModel):
    """correct_answers/explanation are None in never mode — an exam-mode
    session reveals per-question correctness but never the expected answer.
    is_correct is None for ungraded legacy responses.
    """

    question_id: UUID
    question_type: QuestionType
    question_text: str
    options: list[str] | None
    selected: list[str]
    is_correct: bool | None
    correct_answers: list[str] | None
    explanation: str | None


class SessionReview(BaseModel):
    summary: SessionSummary
    feedback_mode: FeedbackMode
    entries: list[SessionReviewEntry]


class SessionPreferences(BaseModel):
    default_feedback_mode: FeedbackMode


class SessionHistoryEntry(SessionSummary):
    feedback_mode: FeedbackMode
    started_at: datetime


class SessionHistory(BaseModel):
    sessions: list[SessionHistoryEntry]
