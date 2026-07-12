from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol, cast, get_args
from uuid import UUID

from memosphere_domain import BloomLevel, DifficultyTier, QuestionType
from question_generation_service.core.exceptions import DomainError
from question_generation_service.repositories.concept_progress_repository import (
    ConceptProgressEntryProtocol,
)
from question_generation_service.repositories.learning_unit_repository import (
    LearningUnitEntryProtocol,
)
from question_generation_service.repositories.question_repository import QuestionEntryProtocol
from question_generation_service.schemas.question import QuestionGenerationRequest
from question_generation_service.services.mastery_service import MasteryBand, classify_band
from question_generation_service.services.question_service import QuestionGeneratorProtocol

BLOOM_ORDER: tuple[str, ...] = get_args(BloomLevel)

ConceptBloomPair = tuple[UUID, str]


class ConceptProgressBatchLookupProtocol(Protocol):
    async def get_batch(
        self, user_id: UUID, pairs: Sequence[ConceptBloomPair]
    ) -> Sequence[ConceptProgressEntryProtocol]: ...


class QuestionCandidateLookupProtocol(Protocol):
    async def get_candidates(
        self,
        concept_id: UUID,
        bloom_level: str,
        difficulty_tier: str | None,
        question_types: Sequence[str],
        user_id: UUID,
        limit: int,
    ) -> Sequence[QuestionEntryProtocol]: ...

    async def get_pool_for_session(
        self,
        concept_ids: Sequence[UUID],
        question_types: Sequence[str],
        user_id: UUID,
        limit: int,
    ) -> Sequence[QuestionEntryProtocol]: ...

    async def get_by_ids(self, ids: Sequence[UUID]) -> Sequence[QuestionEntryProtocol]: ...


@dataclass(frozen=True)
class _SelectionPlan:
    concept_id: UUID
    bloom_level: str
    difficulty_tier: str
    decision_type: MasteryBand


class AdaptiveSelectionService:
    """Step 11 (main-workflow.md): decides which concept-Bloom pair and
    difficulty tier to serve next, from the learner's current BKT mastery —
    Remediate (P(Ln) < 0.40), Practice (0.40-0.85), or Advance (> 0.85).
    """

    def __init__(
        self,
        concept_progress_repository: ConceptProgressBatchLookupProtocol,
        question_repository: QuestionCandidateLookupProtocol,
        question_generator: QuestionGeneratorProtocol,
    ):
        self.concept_progress_repository = concept_progress_repository
        self.question_repository = question_repository
        self.question_generator = question_generator

    async def select_next(
        self,
        user_id: UUID,
        units: Sequence[LearningUnitEntryProtocol],
        question_types: Sequence[str],
    ) -> tuple[QuestionEntryProtocol, MasteryBand] | None:
        pairs = [
            (unit.id, bloom) for unit in units for bloom in (unit.bloom_levels_supported or [])
        ]
        if not pairs:
            return None
        mastery = await self._mastery_by_pair(user_id, pairs)
        plan = self._plan_next(pairs, mastery)
        if plan is None:
            return None
        units_by_id = {unit.id: unit for unit in units}
        question = await self._find_question(plan, question_types, user_id, pairs, units_by_id)
        if question is None:
            return None
        return question, plan.decision_type

    async def _mastery_by_pair(
        self, user_id: UUID, pairs: Sequence[ConceptBloomPair]
    ) -> dict[ConceptBloomPair, float]:
        rows = await self.concept_progress_repository.get_batch(user_id, pairs)
        wanted = set(pairs)
        return {
            (row.concept_id, row.bloom_level): row.p_ln
            for row in rows
            if row.p_ln is not None and (row.concept_id, row.bloom_level) in wanted
        }

    def _plan_next(
        self, pairs: Sequence[ConceptBloomPair], mastery: dict[ConceptBloomPair, float]
    ) -> _SelectionPlan | None:
        scored = [(pair, mastery[pair]) for pair in pairs if pair in mastery]
        if not scored:
            return None

        by_band: dict[MasteryBand, list[tuple[ConceptBloomPair, float]]] = {
            "Remediate": [],
            "Practice": [],
            "Advance": [],
        }
        for pair, p_ln in scored:
            by_band[classify_band(p_ln)].append((pair, p_ln))

        if by_band["Remediate"]:
            pair, _ = min(by_band["Remediate"], key=lambda item: item[1])
            return self._remediate_plan(pair, pairs, mastery)

        if by_band["Practice"]:
            pair, p_ln = min(by_band["Practice"], key=lambda item: item[1])
            tier = "easy" if p_ln < 0.6 else "medium"
            return _SelectionPlan(pair[0], pair[1], tier, "Practice")

        pairs_set = set(pairs)
        for pair, _ in sorted(by_band["Advance"], key=lambda item: item[1]):
            next_pair = self._next_bloom_pair(pair, pairs_set)
            if next_pair is not None:
                return _SelectionPlan(next_pair[0], next_pair[1], "hard", "Advance")

        # Bloom ladder exhausted everywhere: fall back to the weakest of the
        # mastered pairs, same level, hardest tier.
        pair, _ = min(by_band["Advance"], key=lambda item: item[1])
        return _SelectionPlan(pair[0], pair[1], "hard", "Advance")

    def _remediate_plan(
        self,
        pair: ConceptBloomPair,
        pairs: Sequence[ConceptBloomPair],
        mastery: dict[ConceptBloomPair, float],
    ) -> _SelectionPlan:
        concept_id, bloom_level = pair
        pairs_set = set(pairs)
        idx = BLOOM_ORDER.index(bloom_level)
        if idx > 0:
            lower_pair = (concept_id, BLOOM_ORDER[idx - 1])
            # Don't step down into a level already proven mastered — that's
            # not remediation, it's a ping-pong: Advance climbs back up,
            # a slip drops back to Remediate, which sends it right back to
            # the level it just climbed from. Reinforce the current level
            # instead when there's nowhere lower left to usefully land.
            lower_band = classify_band(mastery[lower_pair]) if lower_pair in mastery else None
            if lower_pair in pairs_set and lower_band != "Advance":
                return _SelectionPlan(lower_pair[0], lower_pair[1], "easy", "Remediate")
        return _SelectionPlan(concept_id, bloom_level, "easy", "Remediate")

    def _next_bloom_pair(
        self, pair: ConceptBloomPair, pairs_set: set[ConceptBloomPair]
    ) -> ConceptBloomPair | None:
        concept_id, bloom_level = pair
        idx = BLOOM_ORDER.index(bloom_level)
        if idx + 1 < len(BLOOM_ORDER):
            higher = BLOOM_ORDER[idx + 1]
            if (concept_id, higher) in pairs_set:
                return (concept_id, higher)
        return None

    async def _find_question(
        self,
        plan: _SelectionPlan,
        question_types: Sequence[str],
        user_id: UUID,
        pairs: Sequence[ConceptBloomPair],
        units_by_id: dict[UUID, LearningUnitEntryProtocol],
    ) -> QuestionEntryProtocol | None:
        exact = await self.question_repository.get_candidates(
            plan.concept_id, plan.bloom_level, plan.difficulty_tier, question_types, user_id, 1
        )
        if exact:
            return exact[0]

        any_tier = await self.question_repository.get_candidates(
            plan.concept_id, plan.bloom_level, None, question_types, user_id, 1
        )
        if any_tier:
            return any_tier[0]

        concept_ids = list({concept_id for concept_id, _ in pairs})
        fallback = await self.question_repository.get_pool_for_session(
            concept_ids, question_types, user_id, 1
        )
        if fallback:
            return fallback[0]

        return await self._generate_live(plan, question_types, user_id, units_by_id)

    async def _generate_live(
        self,
        plan: _SelectionPlan,
        question_types: Sequence[str],
        user_id: UUID,
        units_by_id: dict[UUID, LearningUnitEntryProtocol],
    ) -> QuestionEntryProtocol | None:
        """Step 8's exhausted-pool fallback — every other path came up empty,
        so ask the LLM directly instead of failing the request. This is the
        exception, not the norm: the async generation pipeline is supposed to
        keep buckets warm; this only fires when it hasn't caught up yet.
        """
        unit = units_by_id.get(plan.concept_id)
        if unit is None:
            return None
        request = QuestionGenerationRequest(
            concept_id=plan.concept_id,
            concept_name=unit.concept_name,
            learning_goal=unit.learning_goal or f"Understand {unit.concept_name}",
            bloom_level=cast(BloomLevel, plan.bloom_level),
            difficulty_tier=cast(DifficultyTier, plan.difficulty_tier),
            allowed_question_types=cast(list[QuestionType], list(question_types)),
        )
        try:
            batch = await self.question_generator.generate_batch(request, user_id)
        except DomainError:
            return None
        if not batch.questions:
            return None
        generated = await self.question_repository.get_by_ids([batch.questions[0].id])
        return generated[0] if generated else None
