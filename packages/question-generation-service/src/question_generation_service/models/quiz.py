import uuid
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from memosphere_messaging import JsonValue
from question_generation_service.db.base import Base


class Quiz(Base):
    """User-owned quiz configuration (thema + wizard choices) — not the
    questions themselves: those live in the shared/private pools and sessions
    are runs of a quiz.
    """

    __tablename__ = "quizzes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    thema: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    question_types: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False)
    question_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    time_limit_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    visibility: Mapped[str] = mapped_column(Text, nullable=False, default="private")
    # Incremented by the worker as each jobs:generate-questions batch completes.
    generation_questions_ready: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now())


class QuizConcept(Base):
    """One row per concept a quiz was generated for — written alongside the
    outbox entries in QuizService.create(), so topics can be listed/searched
    without depending on outbox payloads or a session having started.
    """

    __tablename__ = "quiz_concepts"

    quiz_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    concept_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)


class Outbox(Base):
    """Transactional outbox row — written in the same transaction as the
    domain change it announces; the relay publishes it to the Redis stream
    named by `topic` and stamps published_at.
    """

    __tablename__ = "outbox"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    topic: Mapped[str] = mapped_column(Text, nullable=False)
    payload: Mapped[dict[str, JsonValue]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class GenerationJobCompletion(Base):
    """Claim check for one jobs:generate-questions stream message — see the
    creating migration. Existence of a row means increment_questions_ready
    already ran for that message_id; the generation worker uses this to stay
    idempotent under at-least-once redelivery.
    """

    __tablename__ = "generation_job_completions"

    message_id: Mapped[str] = mapped_column(Text, primary_key=True)
    completed_at: Mapped[datetime] = mapped_column(server_default=func.now())
