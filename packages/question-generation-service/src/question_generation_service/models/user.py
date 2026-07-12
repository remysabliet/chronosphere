import uuid

from sqlalchemy import Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from question_generation_service.db.base import Base


class User(Base):
    """Read-only mapping onto the shared `users` table (owned/migrated by
    user_provisioning.py) — this service only ever reads `name` off it, to
    show quiz owners in the shared-quizzes view.
    """

    __tablename__ = "users"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    name: Mapped[str | None] = mapped_column(Text, nullable=True)
