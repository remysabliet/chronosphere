import uuid

from sqlalchemy import Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from question_generation_service.db.base import Base


class User(Base):
    """Mapping onto the shared `users` table (provisioned by
    user_provisioning.py) — this service reads `name` to show quiz owners in
    the shared-quizzes view and reads/writes `default_feedback_mode` as the
    remembered feedback-timing preference.
    """

    __tablename__ = "users"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    name: Mapped[str | None] = mapped_column(Text, nullable=True)
    default_feedback_mode: Mapped[str] = mapped_column(Text, nullable=False, default="end")
