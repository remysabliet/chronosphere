import uuid
from datetime import datetime

from sqlalchemy import Float, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from question_generation_service.db.base import Base


class ConceptProgressTracker(Base):
    """Maps the `concept_progress_tracker` table owned by migration-service (Knex).

    No ForeignKey() to `users` — this service has no ORM model for that table.
    """

    __tablename__ = "concept_progress_tracker"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    concept_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    bloom_level: Mapped[str] = mapped_column(String, primary_key=True)
    first_attempt: Mapped[datetime | None] = mapped_column(nullable=True)
    last_attempt: Mapped[datetime | None] = mapped_column(nullable=True)
    attempt_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    correct_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    slip_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    mastery_status: Mapped[str | None] = mapped_column(String, nullable=True)
    p_ln: Mapped[float | None] = mapped_column(Float, nullable=True)
