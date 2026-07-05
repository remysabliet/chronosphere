from uuid import UUID, uuid4

import pytest

from question_generation_service.core.exceptions import NotFoundError
from question_generation_service.schemas.exposure import ExposureRequest
from question_generation_service.services.exposure_service import ExposureService

USER_ID = uuid4()


class _FakeThemaEntry:
    def __init__(self, extraction_id: UUID, extracted_thema: str) -> None:
        self.id = extraction_id
        self.notes: str | None = None
        self.raw_user_input = ""
        self.extracted_thema: str | None = extracted_thema
        self.extracted_topic: str | None = None
        self.user_corrected = False
        self.user_correction: str | None = None


class FakeThemaRepository:
    def __init__(self, extracted_thema: str | None) -> None:
        self.extracted_thema = extracted_thema

    async def get(self, extraction_id: UUID) -> _FakeThemaEntry | None:
        if self.extracted_thema is None:
            return None
        return _FakeThemaEntry(extraction_id, self.extracted_thema)


class _FakeExposureEntry:
    def __init__(self, user_id: UUID, thema: str, exposure_level: str, source: str | None) -> None:
        self.user_id = user_id
        self.thema = thema
        self.exposure_level = exposure_level
        self.source = source


class FakeExposureRepository:
    def __init__(self) -> None:
        self.saved: tuple[UUID, str, str, str] | None = None

    async def get(self, user_id: UUID, thema: str) -> _FakeExposureEntry | None:
        return None

    async def save(
        self, user_id: UUID, thema: str, exposure_level: str, source: str
    ) -> _FakeExposureEntry:
        self.saved = (user_id, thema, exposure_level, source)
        return _FakeExposureEntry(user_id, thema, exposure_level, source)


class _FakeLearningUnitEntry:
    def __init__(self, concept_id: UUID, bloom_levels_supported: list[str]) -> None:
        self.id = concept_id
        self.thema = ""
        self.topic: str | None = None
        self.concept_name = ""
        self.learning_goal: str | None = None
        self.bloom_levels_supported: list[str] | None = bloom_levels_supported
        self.estimated_time_minutes: int | None = None
        self.bloom_coverage_score: int | None = None
        self.complexity_level: str | None = None


class FakeLearningUnitRepository:
    def __init__(self, entries: list[_FakeLearningUnitEntry]) -> None:
        self.entries = entries

    async def get_by_thema(self, thema: str) -> list[_FakeLearningUnitEntry]:
        return self.entries


class FakeBktInitService:
    def __init__(self) -> None:
        self.calls: list[tuple[UUID, list[tuple[UUID, str]], float]] = []

    async def initialize(
        self, user_id: UUID, concept_bloom_pairs: list[tuple[UUID, str]], p_l0: float
    ) -> int:
        self.calls.append((user_id, concept_bloom_pairs, p_l0))
        return len(concept_bloom_pairs)


@pytest.mark.asyncio
async def test_submit_saves_exposure_and_seeds_bkt():
    concept_id = uuid4()
    thema_repo = FakeThemaRepository(extracted_thema="Rust")
    exposure_repo = FakeExposureRepository()
    learning_unit_repo = FakeLearningUnitRepository(
        [_FakeLearningUnitEntry(concept_id, ["Remembering", "Applying"])]
    )
    bkt_init_service = FakeBktInitService()
    service = ExposureService(thema_repo, exposure_repo, learning_unit_repo, bkt_init_service)

    result = await service.submit(uuid4(), USER_ID, ExposureRequest(exposure_level="Practiced"))

    assert result.thema == "Rust"
    assert result.p_l0 == 0.6
    assert result.concepts_initialized == 2
    assert exposure_repo.saved == (USER_ID, "Rust", "Practiced", "self_report")
    assert len(bkt_init_service.calls) == 1
    user_id, pairs, p_l0 = bkt_init_service.calls[0]
    assert user_id == USER_ID
    assert set(pairs) == {(concept_id, "Remembering"), (concept_id, "Applying")}
    assert p_l0 == 0.6


@pytest.mark.asyncio
async def test_submit_raises_when_thema_not_confirmed():
    service = ExposureService(
        FakeThemaRepository(extracted_thema=None),
        FakeExposureRepository(),
        FakeLearningUnitRepository([]),
        FakeBktInitService(),
    )

    with pytest.raises(NotFoundError):
        await service.submit(uuid4(), USER_ID, ExposureRequest(exposure_level="Unseen"))
