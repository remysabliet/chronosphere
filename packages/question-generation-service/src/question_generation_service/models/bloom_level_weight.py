from sqlalchemy import Float, String
from sqlalchemy.orm import Mapped, mapped_column

from question_generation_service.db.base import Base


class BloomLevelWeight(Base):
    """Maps `bloom_level_weights`, owned by migration-service (Knex)."""

    __tablename__ = "bloom_level_weights"

    bloom_level: Mapped[str] = mapped_column(String, primary_key=True)
    weight: Mapped[float] = mapped_column(Float, nullable=False)
