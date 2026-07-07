from typing import Protocol
from uuid import UUID

from question_generation_service.repositories.concept_progress_repository import (
    ConceptProgressInput,
    ConceptProgressRepositoryProtocol,
)

ConceptBloomPair = tuple[UUID, str]


class BktInitServiceProtocol(Protocol):
    async def initialize(
        self, user_id: UUID, concept_bloom_pairs: list[ConceptBloomPair], p_l0: float
    ) -> int: ...


class BktInitService:
    """Step 7 (main-workflow.md): seeds P(Ln) = P(L0) per concept-Bloom pair.

    P(T)/P(G)/P(S) stay in bkt_parameter_defaults, keyed by complexity_level —
    nothing to duplicate here; this only seeds the per-user mastery starting point.
    """

    def __init__(self, repository: ConceptProgressRepositoryProtocol):
        self.repository = repository

    async def initialize(
        self, user_id: UUID, concept_bloom_pairs: list[ConceptBloomPair], p_l0: float
    ) -> int:
        if not concept_bloom_pairs:
            return 0
        rows: list[ConceptProgressInput] = [
            ConceptProgressInput(concept_id=concept_id, bloom_level=bloom_level, p_ln=p_l0)
            for concept_id, bloom_level in concept_bloom_pairs
        ]
        # Pairs already tracked (e.g. re-confirming a thema) are skipped, not
        # re-seeded — reflect what was actually newly initialized, not what
        # was merely requested.
        inserted = await self.repository.initialize_batch(user_id, rows)
        return len(inserted)
