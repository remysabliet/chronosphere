from sqlalchemy import Float, String
from sqlalchemy.orm import Mapped, mapped_column

from question_generation_service.db.base import Base


class BktParameterDefaults(Base):
    """Maps `bkt_parameter_defaults`, owned by migration-service (Knex).

    Column names match the BKT literature (P_T/P_L0/P_G/P_S) and the DB's own
    mixed-case identifiers — SQLAlchemy quotes them automatically since they
    aren't all-lowercase.
    """

    __tablename__ = "bkt_parameter_defaults"

    complexity_level: Mapped[str] = mapped_column(String, primary_key=True)
    P_T: Mapped[float] = mapped_column(Float, nullable=False)
    P_L0: Mapped[float | None] = mapped_column(Float, nullable=True)
    P_G: Mapped[float | None] = mapped_column(Float, nullable=True)
    P_S: Mapped[float | None] = mapped_column(Float, nullable=True)
