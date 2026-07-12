from typing import Literal, Protocol
from uuid import UUID

from question_generation_service.core.exceptions import NotFoundError
from question_generation_service.repositories.bkt_parameters_repository import (
    BktParameterDefaultsEntryProtocol,
)
from question_generation_service.repositories.concept_progress_repository import (
    ConceptProgressEntryProtocol,
)

MasteryBand = Literal["Remediate", "Practice", "Advance"]

# Bands from the adaptive decision engine spec (docs/product/main-workflow.md
# Step 11) — exhaustive over [0, 1]. MASTERY_THRESHOLD doubles as both
# "Mastered" (Step 10) and the Practice/Advance boundary (Step 11).
REMEDIATE_MAX = 0.40
MASTERY_THRESHOLD = 0.85


def classify_band(p_ln: float) -> MasteryBand:
    if p_ln < REMEDIATE_MAX:
        return "Remediate"
    if p_ln <= MASTERY_THRESHOLD:
        return "Practice"
    return "Advance"


def update_bkt(
    p_ln: float,
    p_t: float,
    p_g: float,
    p_s: float,
    response_score: float,
    bloom_weight: float = 1.0,
) -> float:
    """Bayesian Knowledge Tracing update — see docs/engineering/python-functions.md.

    response_score is 1.0 (correct), 0.0 (incorrect), or a partial-credit
    value in between.
    """
    numerator = p_ln * ((1 - p_s) * response_score + p_s * (1 - response_score))
    denominator = numerator + (1 - p_ln) * (p_g * response_score + (1 - p_g) * (1 - response_score))
    p_ln_given_obs = numerator / denominator

    weighted_gain = (1 - p_ln_given_obs) * p_t * bloom_weight
    p_ln_next = p_ln_given_obs + weighted_gain

    return round(min(max(p_ln_next, 0.0), 1.0), 4)


class ConceptProgressLookupProtocol(Protocol):
    async def get(
        self, user_id: UUID, concept_id: UUID, bloom_level: str
    ) -> ConceptProgressEntryProtocol | None: ...

    async def record_attempt(
        self,
        user_id: UUID,
        concept_id: UUID,
        bloom_level: str,
        p_ln: float,
        is_correct: bool,
        mastery_status: str,
    ) -> None: ...


class BktParametersLookupProtocol(Protocol):
    async def get_defaults(
        self, complexity_level: str
    ) -> BktParameterDefaultsEntryProtocol | None: ...

    async def get_bloom_weight(self, bloom_level: str) -> float | None: ...


class ConceptEntryProtocol(Protocol):
    complexity_level: str | None


class ConceptLookupProtocol(Protocol):
    async def get_by_id(self, concept_id: UUID) -> ConceptEntryProtocol | None: ...


class MasteryServiceProtocol(Protocol):
    async def record_attempt(
        self, user_id: UUID, concept_id: UUID, bloom_level: str, is_correct: bool
    ) -> tuple[float, MasteryBand]: ...


class MasteryService:
    """Step 10 (main-workflow.md): updates P(Ln) for the answered concept-Bloom
    pair after every response. Assumes BktInitService has already seeded the
    concept_progress_tracker row — every reachable concept goes through thema
    confirmation (which seeds it) before a quiz can be created against it.
    """

    def __init__(
        self,
        concept_progress_repository: ConceptProgressLookupProtocol,
        bkt_parameters_repository: BktParametersLookupProtocol,
        learning_unit_repository: ConceptLookupProtocol,
    ):
        self.concept_progress_repository = concept_progress_repository
        self.bkt_parameters_repository = bkt_parameters_repository
        self.learning_unit_repository = learning_unit_repository

    async def record_attempt(
        self, user_id: UUID, concept_id: UUID, bloom_level: str, is_correct: bool
    ) -> tuple[float, MasteryBand]:
        progress = await self.concept_progress_repository.get(user_id, concept_id, bloom_level)
        if progress is None or progress.p_ln is None:
            raise NotFoundError(
                f"No BKT state for user {user_id}, concept {concept_id}, bloom {bloom_level}"
            )
        # The band this question was actually selected under — computed from
        # mastery as it stood *before* this attempt, i.e. Step 11's decision.
        decision_type = classify_band(progress.p_ln)

        unit = await self.learning_unit_repository.get_by_id(concept_id)
        if unit is None or unit.complexity_level is None:
            raise NotFoundError(f"No complexity_level found for concept {concept_id}")
        complexity_level = unit.complexity_level

        defaults = await self.bkt_parameters_repository.get_defaults(complexity_level)
        if defaults is None:
            raise NotFoundError(
                f"No BKT parameter defaults for complexity level '{complexity_level}'"
            )

        bloom_weight = await self.bkt_parameters_repository.get_bloom_weight(bloom_level) or 1.0
        response_score = 1.0 if is_correct else 0.0
        p_ln_next = update_bkt(
            progress.p_ln,
            defaults.P_T,
            defaults.P_G or 0.0,
            defaults.P_S or 0.0,
            response_score,
            bloom_weight,
        )
        mastery_status = "Mastered" if p_ln_next > MASTERY_THRESHOLD else "In Progress"

        await self.concept_progress_repository.record_attempt(
            user_id, concept_id, bloom_level, p_ln_next, is_correct, mastery_status
        )
        return p_ln_next, decision_type
