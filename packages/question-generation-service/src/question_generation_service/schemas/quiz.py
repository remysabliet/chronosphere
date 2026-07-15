from datetime import datetime
from typing import Literal, Self
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from memosphere_domain import QuestionType

QuizVisibility = Literal["private", "shared", "public"]
QuizScope = Literal["mine", "shared"]
QuizStatus = Literal["ready", "generating"]


class QuizCreateRequest(BaseModel):
    thema: str = Field(min_length=1, max_length=200)
    title: str | None = Field(default=None, min_length=1, max_length=200)
    question_types: list[QuestionType] = Field(min_length=1)
    question_count: int | None = Field(default=None, ge=1, le=200)
    time_limit_minutes: int | None = Field(default=None, ge=1, le=480)
    visibility: QuizVisibility = "private"

    @model_validator(mode="after")
    def require_a_size(self) -> Self:
        # Mirrors chk_quizzes_has_size — reject at the edge, not in Postgres.
        if self.question_count is None and self.time_limit_minutes is None:
            raise ValueError("either question_count or time_limit_minutes is required")
        return self


class QuizUpdateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=200)


class QuizResponse(BaseModel):
    id: UUID
    thema: str
    title: str
    question_types: list[QuestionType]
    question_count: int | None
    time_limit_minutes: int | None
    visibility: QuizVisibility
    # How many jobs:generate-questions messages were enqueued (outbox rows);
    # the pool warms in the background while the learner reads the wizard's
    # completion bubble.
    generation_batches_enqueued: int


class QuizListItem(BaseModel):
    id: UUID
    thema: str
    title: str
    question_types: list[QuestionType]
    question_count: int | None
    time_limit_minutes: int | None
    visibility: QuizVisibility
    # Informational only — a batch may yield fewer questions than planned.
    questions_ready: int
    questions_expected: int
    # Completion signal + progress source: ready once completed >= total.
    jobs_completed: int
    jobs_total: int
    status: QuizStatus
    # Distinct topics of the concepts this quiz was generated for.
    topics: list[str]
    # Populated only for scope='shared' — the owner's display name.
    owner_name: str | None
    # Explicit ownership flag — drives owner-only UI (delete/rename) vs
    # "Save to my quizzes"; owner_name can't express this (users.name is
    # nullable).
    is_owner: bool
    created_at: datetime
    updated_at: datetime


class QuizListResponse(BaseModel):
    items: list[QuizListItem]
    has_more: bool


class QuizProgressEvent(BaseModel):
    """One generation-progress push, streamed over `GET /v1/quizzes/events`
    (SSE). Field meanings match QuizListItem/QuizDetailResponse so the
    frontend can patch its caches in place.
    """

    quiz_id: UUID
    questions_ready: int
    questions_expected: int
    jobs_completed: int
    jobs_total: int
    status: QuizStatus


class QuizDetailResponse(BaseModel):
    id: UUID
    thema: str
    title: str
    question_types: list[QuestionType]
    question_count: int | None
    time_limit_minutes: int | None
    visibility: QuizVisibility
    questions_ready: int
    questions_expected: int
    jobs_completed: int
    jobs_total: int
    status: QuizStatus
    topics: list[str]
    owner_name: str | None
    is_owner: bool
    created_at: datetime
    updated_at: datetime
