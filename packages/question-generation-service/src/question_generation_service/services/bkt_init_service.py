from collections.abc import Sequence
from typing import Protocol
from uuid import UUID

from question_generation_service.repositories.concept_progress_repository import (
    ConceptProgressEntryProtocol,
    ConceptProgressInput,
)

ConceptBloomPair = tuple[UUID, str]


class BktInitServiceProtocol(Protocol):
    async def initialize(
        self, user_id: UUID, concept_bloom_pairs: Sequence[ConceptBloomPair], p_l0: float
    ) -> int: ...


# Narrower than ConceptProgressRepositoryProtocol (which also covers reads/
# per-attempt updates this service never does) — Interface Segregation:
# depend only on what's actually called here. ConceptProgressRepository
# already satisfies this structurally; no adapter needed.
class ConceptProgressBatchInitProtocol(Protocol):
    async def initialize_batch(
        self, user_id: UUID, rows: list[ConceptProgressInput]
    ) -> list[ConceptProgressEntryProtocol]: ...


class BktInitService:
    """Step 7 (main-workflow.md): seeds P(Ln) = P(L0) per concept-Bloom pair.

    P(T)/P(G)/P(S) stay in bkt_parameter_defaults, keyed by complexity_level —
    nothing to duplicate here; this only seeds the per-user mastery starting point.
    """

    def __init__(self, repository: ConceptProgressBatchInitProtocol):
        self.repository = repository

    async def initialize(
        self, user_id: UUID, concept_bloom_pairs: Sequence[ConceptBloomPair], p_l0: float
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
