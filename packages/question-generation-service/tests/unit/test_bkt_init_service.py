from uuid import UUID, uuid4

import pytest

from question_generation_service.repositories.concept_progress_repository import (
    ConceptProgressEntryProtocol,
    ConceptProgressInput,
)
from question_generation_service.services.bkt_init_service import BktInitService


class _FakeEntry:
    def __init__(self, user_id: UUID, concept_id: UUID, bloom_level: str, p_ln: float) -> None:
        self.user_id = user_id
        self.concept_id = concept_id
        self.bloom_level = bloom_level
        self.p_ln: float | None = p_ln
        self.mastery_status: str | None = "In Progress"


class FakeConceptProgressRepository:
    def __init__(self) -> None:
        self.calls: list[tuple[UUID, list[ConceptProgressInput]]] = []

    async def initialize_batch(
        self, user_id: UUID, rows: list[ConceptProgressInput]
    ) -> list[ConceptProgressEntryProtocol]:
        self.calls.append((user_id, rows))
        return [
            _FakeEntry(user_id, row["concept_id"], row["bloom_level"], row["p_ln"]) for row in rows
        ]


@pytest.mark.asyncio
async def test_initialize_writes_one_row_per_pair():
    repo = FakeConceptProgressRepository()
    service = BktInitService(repo)
    user_id = uuid4()
    concept_id = uuid4()

    count = await service.initialize(
        user_id, [(concept_id, "Remembering"), (concept_id, "Understanding")], p_l0=0.4
    )

    assert count == 2
    assert len(repo.calls) == 1
    _, rows = repo.calls[0]
    assert {(r["concept_id"], r["bloom_level"], r["p_ln"]) for r in rows} == {
        (concept_id, "Remembering", 0.4),
        (concept_id, "Understanding", 0.4),
    }


@pytest.mark.asyncio
async def test_initialize_skips_repository_call_when_no_pairs():
    repo = FakeConceptProgressRepository()
    service = BktInitService(repo)

    count = await service.initialize(uuid4(), [], p_l0=0.2)

    assert count == 0
    assert repo.calls == []
