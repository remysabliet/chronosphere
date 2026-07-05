from typing import Protocol
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from question_generation_service.models.exposure import UserThemaExposure


class ExposureEntryProtocol(Protocol):
    user_id: UUID
    thema: str
    exposure_level: str
    source: str | None


class ExposureRepositoryProtocol(Protocol):
    async def get(self, user_id: UUID, thema: str) -> ExposureEntryProtocol | None: ...

    async def save(
        self, user_id: UUID, thema: str, exposure_level: str, source: str
    ) -> ExposureEntryProtocol: ...


class ExposureRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, user_id: UUID, thema: str) -> ExposureEntryProtocol | None:
        return await self.session.get(UserThemaExposure, {"user_id": user_id, "thema": thema})  # type: ignore[return-value]

    async def save(
        self, user_id: UUID, thema: str, exposure_level: str, source: str
    ) -> ExposureEntryProtocol:
        entry = await self.session.get(UserThemaExposure, {"user_id": user_id, "thema": thema})
        if entry is None:
            entry = UserThemaExposure(user_id=user_id, thema=thema)
            self.session.add(entry)
        entry.exposure_level = exposure_level
        entry.source = source
        await self.session.commit()
        return entry  # type: ignore[return-value]
