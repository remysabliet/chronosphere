from typing import Literal, Self
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from memosphere_domain import QuestionType

QuizVisibility = Literal["private", "shared", "public"]


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
