import uuid
from datetime import datetime

from sqlalchemy import String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from question_generation_service.db.base import Base


class UserThemaExposure(Base):
    """Maps the `user_thema_exposure` table owned by migration-service (Knex).

    No ForeignKey() to `users` — this service has no ORM model for that table.
    """

    __tablename__ = "user_thema_exposure"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    thema: Mapped[str] = mapped_column(String, primary_key=True)
    exposure_level: Mapped[str] = mapped_column(String, nullable=False)
    source: Mapped[str | None] = mapped_column(String, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(server_default=func.now())
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
