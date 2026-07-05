from uuid import UUID, uuid4

import pytest

from question_generation_service.repositories.learning_unit_repository import ConceptInput
from question_generation_service.schemas.concept import ConceptMapRequest
from question_generation_service.services.concept_service import ConceptService


class _FakeEntry:
    def __init__(
        self,
        entry_id: UUID,
        thema: str,
        topic: str,
        concept_name: str,
        learning_goal: str,
        bloom_levels_supported: list[str],
        estimated_time_minutes: int,
        complexity_level: str,
    ) -> None:
        self.id = entry_id
        self.thema = thema
        self.topic: str | None = topic
        self.concept_name = concept_name
        self.learning_goal: str | None = learning_goal
        self.bloom_levels_supported: list[str] | None = bloom_levels_supported
        self.estimated_time_minutes: int | None = estimated_time_minutes
        self.bloom_coverage_score: int | None = len(bloom_levels_supported)
        self.complexity_level: str | None = complexity_level


class FakeLearningUnitRepository:
    def __init__(self, existing: list[_FakeEntry] | None = None) -> None:
        self.existing = existing or []
        self.save_batch_calls: list[tuple[str, list[ConceptInput]]] = []

    async def get_by_thema(self, thema: str) -> list[_FakeEntry]:
        return [e for e in self.existing if e.thema == thema]

    async def save_batch(self, thema: str, concepts: list[ConceptInput]) -> list[_FakeEntry]:
        self.save_batch_calls.append((thema, concepts))
        return [
            _FakeEntry(
                uuid4(),
                thema,
                c["topic"],
                c["concept_name"],
                c["learning_goal"],
                c["bloom_levels_supported"],
                c["estimated_time_minutes"],
                c["complexity_level"],
            )
            for c in concepts
        ]


def _concept_response(topic: str, concept: str) -> dict[str, object]:
    return {
        "concepts": [
            {
                "topic": topic,
                "concept": concept,
                "learning_goal": f"Explain {concept}",
                "bloom_levels": ["Remembering", "Understanding"],
                "estimated_time_minutes": 10,
                "complexity_level": "Medium",
            }
        ]
    }


def _patch_response(monkeypatch, response: dict[str, object]) -> list[str]:
    calls: list[str] = []

    async def fake(system_msg, user_msg, config):
        calls.append(user_msg)
        return response

    monkeypatch.setattr("question_generation_service.services.concept_service.chat_complete", fake)
    return calls


@pytest.mark.asyncio
async def test_calls_llm_for_all_topics_when_thema_is_new(monkeypatch):
    _patch_response(monkeypatch, _concept_response("Ownership", "Move semantics"))
    repo = FakeLearningUnitRepository()
    service = ConceptService(repo)

    result = await service.map(ConceptMapRequest(thema="Rust Ownership", topics=["Ownership"]))

    assert len(result.concepts) == 1
    assert result.concepts[0].concept == "Move semantics"
    assert len(repo.save_batch_calls) == 1


@pytest.mark.asyncio
async def test_reuses_existing_concepts_without_calling_llm(monkeypatch):
    calls = _patch_response(monkeypatch, _concept_response("Ownership", "Move semantics"))
    existing = _FakeEntry(
        uuid4(),
        "Rust Ownership",
        "Ownership",
        "Move semantics",
        "Explain move semantics",
        ["Remembering", "Understanding"],
        10,
        "Medium",
    )
    repo = FakeLearningUnitRepository([existing])
    service = ConceptService(repo)

    result = await service.map(ConceptMapRequest(thema="Rust Ownership", topics=["Ownership"]))

    assert len(result.concepts) == 1
    assert result.concepts[0].id == existing.id
    assert result.concepts[0].concept == "Move semantics"
    assert calls == []
    assert repo.save_batch_calls == []


@pytest.mark.asyncio
async def test_calls_llm_only_for_missing_topics(monkeypatch):
    calls = _patch_response(monkeypatch, _concept_response("Borrowing", "Borrow checker"))
    existing = _FakeEntry(
        uuid4(),
        "Rust Ownership",
        "Ownership",
        "Move semantics",
        "Explain move semantics",
        ["Remembering"],
        10,
        "Medium",
    )
    repo = FakeLearningUnitRepository([existing])
    service = ConceptService(repo)

    result = await service.map(
        ConceptMapRequest(thema="Rust Ownership", topics=["Ownership", "Borrowing"])
    )

    assert len(result.concepts) == 2
    concept_names = {c.concept for c in result.concepts}
    assert concept_names == {"Move semantics", "Borrow checker"}
    assert len(calls) == 1
    assert "TOPICS: Borrowing" in calls[0]
    assert len(repo.save_batch_calls) == 1
    assert repo.save_batch_calls[0][1][0]["topic"] == "Borrowing"


@pytest.mark.asyncio
async def test_only_returns_concepts_for_requested_topics(monkeypatch):
    _patch_response(monkeypatch, _concept_response("Ownership", "Move semantics"))
    unrelated = _FakeEntry(
        uuid4(),
        "Rust Ownership",
        "Lifetimes",
        "Lifetime elision",
        "Explain lifetime elision",
        ["Applying"],
        15,
        "High",
    )
    repo = FakeLearningUnitRepository([unrelated])
    service = ConceptService(repo)

    result = await service.map(ConceptMapRequest(thema="Rust Ownership", topics=["Ownership"]))

    assert len(result.concepts) == 1
    assert result.concepts[0].topic == "Ownership"
