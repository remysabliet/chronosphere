import uuid
from datetime import datetime

from sqlalchemy import String, Text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from question_generation_service.db.base import Base


class Question(Base):
    __tablename__ = "questions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    concept_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    bloom_level: Mapped[str] = mapped_column(String, nullable=False)
    difficulty_tier: Mapped[str] = mapped_column(String, nullable=False)
    question_type: Mapped[str | None] = mapped_column(String, nullable=True)
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    options: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    correct_answers: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    estimated_time: Mapped[str | None] = mapped_column(String, nullable=True)
    tags: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)
    language: Mapped[str | None] = mapped_column(String, nullable=True)
    source: Mapped[str | None] = mapped_column(String, nullable=True)
    version: Mapped[str | None] = mapped_column(String, nullable=True)
    created_by: Mapped[str | None] = mapped_column(String, nullable=True)
    # NULL = public shared pool; non-NULL = private to that user (document-sourced)
    owner_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class QuestionValidationLog(Base):
    __tablename__ = "question_validation_log"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    question_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    validation_status: Mapped[str] = mapped_column(String, nullable=False)
    failed_checks: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)
    timestamp: Mapped[datetime] = mapped_column(server_default=func.now())
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    validation_score: Mapped[float | None] = mapped_column(nullable=True)
    validator_version: Mapped[str | None] = mapped_column(String, nullable=True)


class QuestionServingLog(Base):
    """Tracks which stored questions a user has already been served, so the
    pool-reuse path can prefer unseen questions for them first. Separate from
    `user_responses` (actual answers, owned by the future quiz-taking loop).
    """

    __tablename__ = "question_serving_log"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    question_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    served_at: Mapped[datetime] = mapped_column(server_default=func.now())
