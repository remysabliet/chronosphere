from typing import Protocol

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from question_generation_service.models.bkt_parameter_defaults import BktParameterDefaults
from question_generation_service.models.bloom_level_weight import BloomLevelWeight


class BktParameterDefaultsEntryProtocol(Protocol):
    complexity_level: str
    P_T: float
    P_G: float | None
    P_S: float | None


class BktParametersRepositoryProtocol(Protocol):
    async def get_defaults(
        self, complexity_level: str
    ) -> BktParameterDefaultsEntryProtocol | None: ...

    async def get_bloom_weight(self, bloom_level: str) -> float | None: ...


class BktParametersRepository:
    """Read-only lookups against the two small BKT reference tables —
    bundled together since every mastery update needs both in the same call.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_defaults(self, complexity_level: str) -> BktParameterDefaultsEntryProtocol | None:
        result = await self.session.execute(
            select(BktParameterDefaults).where(
                BktParameterDefaults.complexity_level == complexity_level
            )
        )
        return result.scalar_one_or_none()  # type: ignore[return-value]

    async def get_bloom_weight(self, bloom_level: str) -> float | None:
        result = await self.session.execute(
            select(BloomLevelWeight.weight).where(BloomLevelWeight.bloom_level == bloom_level)
        )
        return result.scalar_one_or_none()
