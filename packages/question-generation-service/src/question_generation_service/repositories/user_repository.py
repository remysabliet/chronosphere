from typing import Protocol
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from question_generation_service.models.user import User


class UserRepositoryProtocol(Protocol):
    async def get_default_feedback_mode(self, user_id: UUID) -> str | None: ...

    async def set_default_feedback_mode(self, user_id: UUID, mode: str) -> None: ...


class UserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_default_feedback_mode(self, user_id: UUID) -> str | None:
        result = await self.session.execute(
            select(User.default_feedback_mode).where(User.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def set_default_feedback_mode(self, user_id: UUID, mode: str) -> None:
        await self.session.execute(
            update(User).where(User.user_id == user_id).values(default_feedback_mode=mode)
        )
        await self.session.commit()
        self.session.expire_all()
