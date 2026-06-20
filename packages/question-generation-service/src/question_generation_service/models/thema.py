import uuid
from datetime import datetime

from sqlalchemy import Boolean, Float, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from question_generation_service.db.base import Base


class ThemaExtractionInput(Base):
    """Maps the `thema_extraction_inputs` table owned by migration-service (Knex).

    user_id/session_id are FK-constrained at the DB level to `users`/`quiz_sessions`,
    but those tables have no ORM model in this service, so no `ForeignKey()` here —
    SQLAlchemy can't resolve a target it doesn't have metadata for.
    """

    __tablename__ = "thema_extraction_inputs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    session_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    raw_user_input: Mapped[str] = mapped_column(Text, nullable=False)
    extracted_thema: Mapped[str | None] = mapped_column(String, nullable=True)
    extracted_topic: Mapped[str | None] = mapped_column(String, nullable=True)
    extraction_model: Mapped[str | None] = mapped_column(String, nullable=True)
    extraction_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    user_corrected: Mapped[bool] = mapped_column(Boolean, default=False)
    user_correction: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(server_default=func.now())
