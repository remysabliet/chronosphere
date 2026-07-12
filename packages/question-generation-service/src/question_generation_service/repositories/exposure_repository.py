from typing import Protocol
from uuid import UUID

from sqlalchemy.dialects.postgresql import insert as pg_insert
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
        # Atomic upsert, not get-then-insert: two concurrent first-time
        # submissions for the same (user_id, thema) — e.g. a double-click, or
        # two tabs — would otherwise both see no existing row and race on the
        # INSERT, and the loser would crash with a raw UniqueViolationError
        # instead of just recording the learner's (last-write-wins) answer.
        stmt = (
            pg_insert(UserThemaExposure)
            .values(user_id=user_id, thema=thema, exposure_level=exposure_level, source=source)
            .on_conflict_do_update(
                index_elements=["user_id", "thema"],
                set_={"exposure_level": exposure_level, "source": source},
            )
            .returning(UserThemaExposure)
        )
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.scalar_one()  # type: ignore[return-value]
