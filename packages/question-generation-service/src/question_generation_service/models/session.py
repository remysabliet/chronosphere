import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from question_generation_service.db.base import Base


class QuizSession(Base):
    """One run of a quiz: `question_ids` grows one at a time as
    AdaptiveSelectionService (Step 11) picks each next question from current
    BKT mastery — it always holds exactly the questions served so far, plus
    the one pending an answer.
    """

    __tablename__ = "quiz_sessions"

    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    quiz_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    question_ids: Mapped[list[uuid.UUID]] = mapped_column(
        ARRAY(UUID(as_uuid=True)), nullable=False, default=list
    )
    thema: Mapped[str | None] = mapped_column(String, nullable=True)
    session_type: Mapped[str] = mapped_column(String, nullable=False, default="assessment")
    feedback_mode: Mapped[str] = mapped_column(String, nullable=False, default="end")
    start_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    end_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    total_questions: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    correct_answers: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_time_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    session_status: Mapped[str] = mapped_column(String, nullable=False, default="active")
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now())


class UserResponse(Base):
    """One answered question. Partitioned by `timestamp` (see migration
    20260706180000_partition_user_responses) — existing monthly partitions
    already cover the current date range, so plain inserts land correctly
    with no partition-management logic needed here.
    """

    __tablename__ = "user_responses"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    question_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    concept_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    bloom_level: Mapped[str] = mapped_column(String, nullable=False)
    selected_option: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_correct: Mapped[bool | None] = mapped_column(nullable=True)
    response_time: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Partition key — must be part of the primary key on a partitioned table.
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), primary_key=True, default=lambda: datetime.now(UTC)
    )
    question_sequence_order: Mapped[int | None] = mapped_column(Integer, nullable=True)
    decision_type: Mapped[str | None] = mapped_column(String, nullable=True)
