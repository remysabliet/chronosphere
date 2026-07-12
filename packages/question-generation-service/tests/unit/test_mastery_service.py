from dataclasses import dataclass
from uuid import UUID, uuid4

import pytest

from question_generation_service.core.exceptions import NotFoundError
from question_generation_service.repositories.concept_progress_repository import (
    ConceptProgressEntryProtocol,
)
from question_generation_service.services.mastery_service import (
    MASTERY_THRESHOLD,
    REMEDIATE_MAX,
    MasteryService,
    classify_band,
    update_bkt,
)

# --- Level 1: update_bkt / classify_band as pure functions, no DB, no fakes ---


class TestUpdateBkt:
    def test_correct_answer_raises_mastery_more_than_incorrect_answer(self):
        # Same starting state and parameters, differing only in outcome —
        # the whole point of the evidence step is to reward correctness.
        p_ln, p_t, p_g, p_s = 0.4, 0.15, 0.25, 0.1

        correct = update_bkt(p_ln, p_t, p_g, p_s, response_score=1.0)
        incorrect = update_bkt(p_ln, p_t, p_g, p_s, response_score=0.0)

        assert correct > incorrect

    def test_learning_transition_always_moves_mastery_up_from_the_posterior(self):
        # Even on an incorrect answer, BKT's transition step (p_t) still
        # applies — an answer never *decreases* p_ln relative to what the
        # evidence step alone would have produced for that same observation.
        p_ln, p_g, p_s = 0.4, 0.25, 0.1
        no_transition = update_bkt(p_ln, p_t=0.0, p_g=p_g, p_s=p_s, response_score=0.0)
        with_transition = update_bkt(p_ln, p_t=0.3, p_g=p_g, p_s=p_s, response_score=0.0)

        assert with_transition >= no_transition

    def test_clamps_at_upper_bound(self):
        # High p_t and a correct answer push the raw update past 1.0.
        result = update_bkt(p_ln=0.95, p_t=0.9, p_g=0.25, p_s=0.1, response_score=1.0)
        assert result <= 1.0

    def test_clamps_at_lower_bound(self):
        result = update_bkt(p_ln=0.0, p_t=0.0, p_g=0.0, p_s=1.0, response_score=0.0)
        assert result >= 0.0

    def test_higher_transition_probability_yields_higher_next_mastery(self):
        base = {"p_ln": 0.3, "p_g": 0.25, "p_s": 0.1, "response_score": 1.0}
        low_pt = update_bkt(p_t=0.05, **base)
        high_pt = update_bkt(p_t=0.5, **base)
        assert high_pt > low_pt

    def test_bloom_weight_scales_the_transition_gain(self):
        base = {"p_ln": 0.3, "p_t": 0.2, "p_g": 0.25, "p_s": 0.1, "response_score": 1.0}
        light = update_bkt(**base, bloom_weight=0.5)
        heavy = update_bkt(**base, bloom_weight=1.5)
        assert heavy > light

    def test_result_is_rounded_to_four_decimal_places(self):
        result = update_bkt(p_ln=0.2, p_t=0.15, p_g=0.25, p_s=0.1, response_score=1.0)
        assert result == round(result, 4)


class TestClassifyBand:
    def test_below_remediate_max_is_remediate(self):
        assert classify_band(REMEDIATE_MAX - 0.01) == "Remediate"

    def test_at_remediate_max_boundary_is_practice(self):
        # classify_band uses `< REMEDIATE_MAX`, so the boundary itself is Practice.
        assert classify_band(REMEDIATE_MAX) == "Practice"

    def test_at_mastery_threshold_boundary_is_practice(self):
        # classify_band uses `<= MASTERY_THRESHOLD`, so the boundary itself is Practice.
        assert classify_band(MASTERY_THRESHOLD) == "Practice"

    def test_above_mastery_threshold_is_advance(self):
        assert classify_band(MASTERY_THRESHOLD + 0.0001) == "Advance"

    def test_midrange_is_practice(self):
        assert classify_band((REMEDIATE_MAX + MASTERY_THRESHOLD) / 2) == "Practice"


# --- Level 2: MasteryService.record_attempt orchestration, against fakes ---


@dataclass
class FakeProgress:
    user_id: UUID
    concept_id: UUID
    bloom_level: str
    p_ln: float | None
    mastery_status: str | None = "In Progress"


class FakeConceptProgressRepository:
    def __init__(self, progress: ConceptProgressEntryProtocol | None) -> None:
        self._progress = progress
        self.record_attempt_calls: list[tuple] = []

    async def get(self, user_id, concept_id, bloom_level) -> ConceptProgressEntryProtocol | None:
        return self._progress

    async def record_attempt(
        self, user_id, concept_id, bloom_level, p_ln, is_correct, mastery_status
    ) -> None:
        self.record_attempt_calls.append(
            (user_id, concept_id, bloom_level, p_ln, is_correct, mastery_status)
        )


@dataclass
class FakeBktDefaults:
    complexity_level: str
    P_T: float
    P_G: float | None
    P_S: float | None


class FakeBktParametersRepository:
    def __init__(self, defaults: FakeBktDefaults | None, bloom_weight: float | None = None) -> None:
        self._defaults = defaults
        self._bloom_weight = bloom_weight

    async def get_defaults(self, complexity_level: str) -> FakeBktDefaults | None:
        return self._defaults

    async def get_bloom_weight(self, bloom_level: str) -> float | None:
        return self._bloom_weight


@dataclass
class FakeUnit:
    complexity_level: str | None


class FakeLearningUnitRepository:
    def __init__(self, unit: FakeUnit | None) -> None:
        self._unit = unit

    async def get_by_id(self, concept_id) -> FakeUnit | None:
        return self._unit


_DEFAULT_UNIT = FakeUnit(complexity_level="Medium")
_DEFAULT_BKT_DEFAULTS = FakeBktDefaults(complexity_level="Medium", P_T=0.15, P_G=0.25, P_S=0.1)


def make_service(
    progress: FakeProgress | None,
    unit: FakeUnit | None = _DEFAULT_UNIT,
    defaults: FakeBktDefaults | None = _DEFAULT_BKT_DEFAULTS,
    bloom_weight: float | None = 0.8,
) -> tuple[MasteryService, FakeConceptProgressRepository]:
    concept_progress_repository = FakeConceptProgressRepository(progress)
    service = MasteryService(
        concept_progress_repository,
        FakeBktParametersRepository(defaults, bloom_weight),
        FakeLearningUnitRepository(unit),
    )
    return service, concept_progress_repository


@pytest.mark.asyncio
async def test_record_attempt_raises_when_no_bkt_state_exists():
    service, _ = make_service(progress=None)

    with pytest.raises(NotFoundError):
        await service.record_attempt(uuid4(), uuid4(), "Remembering", is_correct=True)


@pytest.mark.asyncio
async def test_record_attempt_raises_when_p_ln_is_none():
    service, _ = make_service(
        progress=FakeProgress(
            user_id=uuid4(), concept_id=uuid4(), bloom_level="Remembering", p_ln=None
        )
    )

    with pytest.raises(NotFoundError):
        await service.record_attempt(uuid4(), uuid4(), "Remembering", is_correct=True)


@pytest.mark.asyncio
async def test_record_attempt_raises_when_concept_has_no_complexity_level():
    service, _ = make_service(
        progress=FakeProgress(uuid4(), uuid4(), "Remembering", p_ln=0.3),
        unit=FakeUnit(complexity_level=None),
    )

    with pytest.raises(NotFoundError):
        await service.record_attempt(uuid4(), uuid4(), "Remembering", is_correct=True)


@pytest.mark.asyncio
async def test_record_attempt_raises_when_no_bkt_defaults_for_complexity_level():
    service, _ = make_service(
        progress=FakeProgress(uuid4(), uuid4(), "Remembering", p_ln=0.3), defaults=None
    )

    with pytest.raises(NotFoundError):
        await service.record_attempt(uuid4(), uuid4(), "Remembering", is_correct=True)


@pytest.mark.asyncio
async def test_record_attempt_computes_the_same_value_as_update_bkt_directly():
    # Cross-checks the service's orchestration against the pure function it
    # wraps: given the same inputs, record_attempt must persist exactly what
    # update_bkt() would compute — no hidden rounding/param-passing bugs.
    prior_p_ln = 0.3
    user_id, concept_id = uuid4(), uuid4()
    service, repo = make_service(
        progress=FakeProgress(user_id, concept_id, "Remembering", p_ln=prior_p_ln)
    )

    p_ln_next, _ = await service.record_attempt(user_id, concept_id, "Remembering", is_correct=True)

    expected = update_bkt(
        prior_p_ln, p_t=0.15, p_g=0.25, p_s=0.1, response_score=1.0, bloom_weight=0.8
    )
    assert p_ln_next == expected
    assert repo.record_attempt_calls == [
        (user_id, concept_id, "Remembering", expected, True, "In Progress")
    ]


@pytest.mark.asyncio
async def test_record_attempt_marks_mastered_once_threshold_crossed():
    # Prior mastery already close enough that even without a perfect roll
    # the next update should cross MASTERY_THRESHOLD.
    user_id, concept_id = uuid4(), uuid4()
    service, repo = make_service(
        progress=FakeProgress(user_id, concept_id, "Remembering", p_ln=0.84)
    )

    p_ln_next, _ = await service.record_attempt(user_id, concept_id, "Remembering", is_correct=True)

    assert p_ln_next > MASTERY_THRESHOLD
    assert repo.record_attempt_calls[0][5] == "Mastered"


@pytest.mark.asyncio
async def test_record_attempt_decision_type_reflects_band_before_this_attempt():
    # decision_type is the band the question was *served* under — computed
    # from p_ln as it stood before this attempt's update is applied.
    user_id, concept_id = uuid4(), uuid4()
    service, _ = make_service(progress=FakeProgress(user_id, concept_id, "Remembering", p_ln=0.1))

    _, decision_type = await service.record_attempt(
        user_id, concept_id, "Remembering", is_correct=False
    )

    assert decision_type == "Remediate"


@pytest.mark.asyncio
async def test_record_attempt_defaults_bloom_weight_to_one_when_unset():
    user_id, concept_id = uuid4(), uuid4()
    service, repo = make_service(
        progress=FakeProgress(user_id, concept_id, "Remembering", p_ln=0.3), bloom_weight=None
    )

    p_ln_next, _ = await service.record_attempt(user_id, concept_id, "Remembering", is_correct=True)

    expected = update_bkt(0.3, p_t=0.15, p_g=0.25, p_s=0.1, response_score=1.0, bloom_weight=1.0)
    assert p_ln_next == expected


@pytest.mark.asyncio
async def test_record_attempt_defaults_p_g_and_p_s_to_zero_when_unset():
    user_id, concept_id = uuid4(), uuid4()
    service, repo = make_service(
        progress=FakeProgress(user_id, concept_id, "Remembering", p_ln=0.3),
        defaults=FakeBktDefaults(complexity_level="Medium", P_T=0.15, P_G=None, P_S=None),
    )

    p_ln_next, _ = await service.record_attempt(user_id, concept_id, "Remembering", is_correct=True)

    expected = update_bkt(0.3, p_t=0.15, p_g=0.0, p_s=0.0, response_score=1.0, bloom_weight=0.8)
    assert p_ln_next == expected
