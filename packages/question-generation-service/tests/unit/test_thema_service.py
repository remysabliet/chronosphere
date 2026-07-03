import json
from uuid import uuid4

import pytest

from question_generation_service.core.exceptions import ConflictError, NotFoundError
from question_generation_service.schemas.thema import (
    AmbiguousThema,
    ConfirmRequest,
    RefineRequest,
    ResolvedThema,
    ThemaRequest,
    UnresolvedThema,
)
from question_generation_service.services.thema_service import ThemaService


def _sample(thema, domain, topics):
    return {
        "thema": thema,
        "domain": domain,
        "disambiguator": f"{thema} sense",
        "confirmation": f"You'll be quizzed on {thema}.",
        "topics": topics,
    }


class FakeEntry:
    def __init__(self, notes, raw_user_input="raw input"):
        self.id = uuid4()
        self.notes = notes
        self.raw_user_input = raw_user_input
        self.extracted_thema = None
        self.extracted_topic = None
        self.user_corrected = False
        self.user_correction = None


class FakeThemaRepository:
    def __init__(self, entry=None):
        self.saved: dict | None = None
        self.entry = entry

    async def save(self, **kwargs):
        self.saved = kwargs
        self.entry = FakeEntry(kwargs["notes"], raw_user_input=kwargs["raw_user_input"])
        return self.entry

    async def get(self, extraction_id):
        return self.entry

    async def update_on_confirm(self, entry, **kwargs):
        for k, v in kwargs.items():
            setattr(entry, k, v)
        return entry

    async def mark_superseded(self, entry, notes):
        entry.notes = notes
        return entry


def _patch_samples(monkeypatch, samples):
    async def fake(system_msg, user_msg, config):
        return samples

    monkeypatch.setattr(
        "question_generation_service.services.thema_service.chat_complete_samples", fake
    )


@pytest.mark.asyncio
async def test_resolved_when_clear_winner(monkeypatch):
    _patch_samples(
        monkeypatch,
        [_sample("Photosynthesis", "Science", ["Light Reactions", "Calvin Cycle"])] * 5,
    )
    service = ThemaService(FakeThemaRepository())

    result = await service.extract(ThemaRequest(raw_user_input="how plants make food"))

    assert isinstance(result, ResolvedThema)
    assert result.thema == "Photosynthesis"
    assert result.confidence == 1.0
    assert result.confirmation
    assert result.alternates == []


@pytest.mark.asyncio
async def test_resolved_exposes_runner_up_as_alternate(monkeypatch):
    _patch_samples(
        monkeypatch,
        [_sample("Photosynthesis", "Science", ["Light Reactions", "Calvin Cycle"])] * 4
        + [_sample("Cellular Respiration", "Science", ["Glycolysis", "Krebs Cycle"])],
    )
    service = ThemaService(FakeThemaRepository())

    result = await service.extract(ThemaRequest(raw_user_input="how cells make energy"))

    assert isinstance(result, ResolvedThema)
    assert result.thema == "Photosynthesis"
    assert len(result.alternates) == 1
    assert result.alternates[0].thema == "Cellular Respiration"


@pytest.mark.asyncio
async def test_ambiguous_when_split(monkeypatch):
    _patch_samples(
        monkeypatch,
        [
            _sample("If Statement", "Software", ["Syntax", "Truthiness", "Branching"]),
            _sample("If Statement", "Software", ["Syntax", "Truthiness", "Branching"]),
            _sample("English Conditionals", "Language", ["Zero", "First", "Second"]),
            _sample("English Conditionals", "Language", ["Zero", "First", "Second"]),
            _sample("Excel IF", "Data", ["Args", "Nesting", "IFS"]),
        ],
    )
    service = ThemaService(FakeThemaRepository())

    result = await service.extract(ThemaRequest(raw_user_input="if"))

    assert isinstance(result, AmbiguousThema)
    assert len(result.candidates) == 3
    assert result.candidates[0].confidence == 0.4


@pytest.mark.asyncio
async def test_unresolved_when_scattered(monkeypatch):
    _patch_samples(
        monkeypatch,
        [
            _sample("A", "Software", ["x", "y", "z"]),
            _sample("B", "DevOps", ["x", "y", "z"]),
            _sample("C", "Language", ["x", "y", "z"]),
            _sample("D", "Math", ["x", "y", "z"]),
            _sample("E", "Arts", ["x", "y", "z"]),
        ],
    )
    service = ThemaService(FakeThemaRepository())

    result = await service.extract(ThemaRequest(raw_user_input="asdf"))

    assert isinstance(result, UnresolvedThema)


@pytest.mark.asyncio
async def test_refine_supersedes_original_and_reextracts(monkeypatch):
    entry = FakeEntry(
        notes=json.dumps({"status": "pending_confirmation", "candidates": []}),
        raw_user_input="agr",
    )
    repo = FakeThemaRepository(entry)
    _patch_samples(
        monkeypatch,
        [_sample("Computer Architecture", "Software", ["CPU", "Memory", "Pipelining"])] * 5,
    )
    service = ThemaService(repo)

    result = await service.refine(entry.id, RefineRequest(clarification="I mean CPU design"))

    assert isinstance(result, ResolvedThema)
    assert result.thema == "Computer Architecture"
    assert json.loads(entry.notes)["status"] == "superseded"
    assert json.loads(entry.notes)["superseded_by"] == str(result.extraction_id)
    assert "CLARIFICATION: I mean CPU design" in repo.saved["raw_user_input"]


@pytest.mark.asyncio
async def test_refine_allowed_after_confirmation(monkeypatch):
    entry = FakeEntry(
        notes=json.dumps({"status": "confirmed", "candidates": []}),
        raw_user_input="agr",
    )
    repo = FakeThemaRepository(entry)
    _patch_samples(
        monkeypatch,
        [_sample("Agriculture", "Science", ["Soil", "Crops", "Livestock"])] * 5,
    )
    service = ThemaService(repo)

    result = await service.refine(entry.id, RefineRequest(clarification="actually computing"))

    assert isinstance(result, ResolvedThema)
    assert json.loads(entry.notes)["status"] == "superseded"


@pytest.mark.asyncio
async def test_refine_rejects_already_superseded_extraction(monkeypatch):
    entry = FakeEntry(notes=json.dumps({"status": "superseded", "candidates": []}))
    service = ThemaService(FakeThemaRepository(entry))

    with pytest.raises(ConflictError):
        await service.refine(entry.id, RefineRequest(clarification="more context"))


@pytest.mark.asyncio
async def test_confirm_rejects_superseded_extraction():
    entry = FakeEntry(notes=json.dumps({"status": "superseded", "candidates": []}))
    service = ThemaService(FakeThemaRepository(entry))

    with pytest.raises(ConflictError):
        await service.confirm(entry.id, ConfirmRequest())


@pytest.mark.asyncio
async def test_confirm_default_rank_not_flagged_as_correction():
    candidates = [
        {
            "rank": 1,
            "thema": "If Statement",
            "domain": "Software",
            "disambiguator": "if control flow",
            "confidence": 0.6,
            "confirmation": "You'll be quizzed on if statements.",
            "topics": ["Syntax", "Truthiness", "Branching"],
        }
    ]
    entry = FakeEntry(json.dumps({"status": "pending_confirmation", "candidates": candidates}))
    repo = FakeThemaRepository(entry)
    service = ThemaService(repo)

    result = await service.confirm(entry.id, ConfirmRequest())

    assert isinstance(result, ResolvedThema)
    assert result.thema == "If Statement"
    assert entry.user_corrected is False
    assert json.loads(entry.notes)["status"] == "confirmed"


@pytest.mark.asyncio
async def test_confirm_other_rank_records_correction():
    candidates = [
        {
            "rank": 1,
            "thema": "If Statement",
            "domain": "Software",
            "disambiguator": "a",
            "confidence": 0.4,
            "confirmation": "c1",
            "topics": ["Syntax"],
        },
        {
            "rank": 2,
            "thema": "English Conditionals",
            "domain": "Language",
            "disambiguator": "b",
            "confidence": 0.4,
            "confirmation": "c2",
            "topics": ["Zero", "First", "Second"],
        },
    ]
    entry = FakeEntry(json.dumps({"status": "pending_disambiguation", "candidates": candidates}))
    service = ThemaService(FakeThemaRepository(entry))

    result = await service.confirm(entry.id, ConfirmRequest(chosen_rank=2))

    assert result.thema == "English Conditionals"
    assert entry.user_corrected is True
    assert entry.user_correction == "English Conditionals"


@pytest.mark.asyncio
async def test_confirm_already_confirmed_raises():
    entry = FakeEntry(json.dumps({"status": "confirmed", "candidates": []}))
    service = ThemaService(FakeThemaRepository(entry))

    with pytest.raises(ConflictError):
        await service.confirm(entry.id, ConfirmRequest())


@pytest.mark.asyncio
async def test_confirm_missing_extraction_raises():
    service = ThemaService(FakeThemaRepository(entry=None))

    with pytest.raises(NotFoundError):
        await service.confirm(uuid4(), ConfirmRequest())
