from collections.abc import Sequence
from typing import Protocol
from uuid import UUID

from memosphere_domain import EXPOSURE_TO_P_L0
from question_generation_service.core.exceptions import NotFoundError
from question_generation_service.repositories.exposure_repository import (
    ExposureRepositoryProtocol,
)
from question_generation_service.repositories.learning_unit_repository import (
    LearningUnitEntryProtocol,
)
from question_generation_service.repositories.thema_repository import ThemaEntryProtocol
from question_generation_service.schemas.exposure import ExposureRequest, ExposureResult
from question_generation_service.services.bkt_init_service import BktInitServiceProtocol


class ThemaLookupProtocol(Protocol):
    """Only the read the confirmed thema for an extraction — ExposureService
    never writes through this repository, so it doesn't depend on the rest of
    ThemaRepositoryProtocol."""

    async def get(self, extraction_id: UUID) -> ThemaEntryProtocol | None: ...


class LearningUnitLookupProtocol(Protocol):
    async def get_by_thema(self, thema: str) -> Sequence[LearningUnitEntryProtocol]: ...


class ExposureService:
    """Handles the exposure answer when it wasn't already on file at confirm()
    time — stores it, then runs the BKT init that confirm() deferred (Step 7)."""

    def __init__(
        self,
        thema_repository: ThemaLookupProtocol,
        exposure_repository: ExposureRepositoryProtocol,
        learning_unit_repository: LearningUnitLookupProtocol,
        bkt_init_service: BktInitServiceProtocol,
    ):
        self.thema_repository = thema_repository
        self.exposure_repository = exposure_repository
        self.learning_unit_repository = learning_unit_repository
        self.bkt_init_service = bkt_init_service

    async def submit(
        self, extraction_id: UUID, user_id: UUID, request: ExposureRequest
    ) -> ExposureResult:
        entry = await self.thema_repository.get(extraction_id)
        if entry is None or not entry.extracted_thema:
            raise NotFoundError(f"No confirmed thema found for extraction {extraction_id}")

        thema = entry.extracted_thema
        await self.exposure_repository.save(
            user_id, thema, request.exposure_level, source="self_report"
        )

        concepts = await self.learning_unit_repository.get_by_thema(thema)
        pairs = [
            (concept.id, bloom_level)
            for concept in concepts
            for bloom_level in concept.bloom_levels_supported or []
        ]
        p_l0 = EXPOSURE_TO_P_L0[request.exposure_level]
        concepts_initialized = await self.bkt_init_service.initialize(user_id, pairs, p_l0)

        return ExposureResult(
            thema=thema,
            exposure_level=request.exposure_level,
            p_l0=p_l0,
            concepts_initialized=concepts_initialized,
        )
