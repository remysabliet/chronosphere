import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import Integer, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from question_generation_service.db.base import Base
from question_generation_service.models.question import EMBEDDING_DIM


class LearningUnit(Base):
    __tablename__ = "learning_units"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    thema: Mapped[str] = mapped_column(String, nullable=False)
    topic: Mapped[str | None] = mapped_column(String, nullable=True)
    concept_name: Mapped[str] = mapped_column(String, nullable=False)
    learning_goal: Mapped[str | None] = mapped_column(Text, nullable=True)
    bloom_levels_supported: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)
    estimated_time_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    bloom_coverage_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    complexity_level: Mapped[str | None] = mapped_column(String, nullable=True)
    created_by: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    author: Mapped[str | None] = mapped_column(String, nullable=True)
    version: Mapped[str | None] = mapped_column(String, nullable=True)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(EMBEDDING_DIM), nullable=True)
