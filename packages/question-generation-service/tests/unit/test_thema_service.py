import json
from typing import TypedDict
from uuid import UUID, uuid4

import pytest

from question_generation_service.core.exceptions import ConflictError, NotFoundError
from question_generation_service.repositories.thema_repository import (
    ThemaEntryProtocol,
)
from question_generation_service.schemas.concept import ConceptMapRequest, ConceptMapResponse
from question_generation_service.schemas.thema import (
    AmbiguousThema,
    ConfirmRequest,
    RefineRequest,
    ResolvedThema,
    ThemaRequest,
    UnresolvedThema,
)
from question_generation_service.services.thema_service import ThemaService


def _alt(thema: str, domain: str, topics: list[str], confidence: float) -> dict[str, object]:
    return {
        "thema": thema,
        "domain": domain,
        "disambiguator": f"{thema} sense",
        "confirmation": f"You'll be quizzed on {thema}.",
        "topics": topics,
        "confidence": confidence,
    }


def _response(
    thema: str,
    domain: str,
    topics: list[str],
    confidence: float,
    alternates: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    return {**_alt(thema, domain, topics, confidence), "alternates": alternates or []}


class _SavedKwargs(TypedDict):
    raw_user_input: str
    extracted_thema: str
    extracted_topic: str
    extraction_model: str
    extraction_confidence: float
    notes: str


class FakeEntry:
    def __init__(self, notes: str | None, raw_user_input: str = "raw input") -> None:
        self.id: UUID = uuid4()
        self.notes: str | None = notes
        self.raw_user_input: str = raw_user_input
        self.extracted_thema: str | None = None
        self.extracted_topic: str | None = None
        self.user_corrected: bool = False
        self.user_correction: str | None = None


class FakeThemaRepository:
    def __init__(self, entry: FakeEntry | None = None) -> None:
        self.saved: _SavedKwargs | None = None
        self.entry: FakeEntry | None = entry

    async def save(
        self,
        raw_user_input: str,
        extracted_thema: str,
        extracted_topic: str,
        extraction_model: str,
        extraction_confidence: float,
        notes: str,
    ) -> FakeEntry:
        self.saved = _SavedKwargs(
            raw_user_input=raw_user_input,
            extracted_thema=extracted_thema,
            extracted_topic=extracted_topic,
            extraction_model=extraction_model,
            extraction_confidence=extraction_confidence,
            notes=notes,
        )
        self.entry = FakeEntry(notes, raw_user_input=raw_user_input)
        return self.entry

    async def get(self, extraction_id: UUID) -> FakeEntry | None:
        return self.entry

    async def update_on_confirm(
        self,
        entry: ThemaEntryProtocol,
        extracted_thema: str,
        extracted_topic: str,
        notes: str,
        user_corrected: bool,
        user_correction: str | None,
    ) -> ThemaEntryProtocol:
        entry.extracted_thema = extracted_thema
        entry.extracted_topic = extracted_topic
        entry.notes = notes
        entry.user_corrected = user_corrected
        entry.user_correction = user_correction
        return entry

    async def mark_superseded(self, entry: ThemaEntryProtocol, notes: str) -> ThemaEntryProtocol:
        entry.notes = notes
        return entry


class FakeConceptMapper:
    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.calls: list[ConceptMapRequest] = []

    async def map(self, request: ConceptMapRequest) -> ConceptMapResponse:
        if self.fail:
            raise RuntimeError("concept mapping failed")
        self.calls.append(request)
        return ConceptMapResponse(thema=request.thema, concepts=[])


def _service(
    repo: FakeThemaRepository, concept_mapper: FakeConceptMapper | None = None
) -> ThemaService:
    return ThemaService(repo, concept_mapper or FakeConceptMapper())


def _patch_response(monkeypatch, response):
    async def fake(system_msg, user_msg, config):
        return response

    monkeypatch.setattr("question_generation_service.services.thema_service.chat_complete", fake)


@pytest.mark.asyncio
async def test_resolved_when_clear_winner(monkeypatch):
    _patch_response(
        monkeypatch,
        _response(
            "Photosynthesis", "Science", ["Light Reactions", "Calvin Cycle"], confidence=0.95
        ),
    )
    service = _service(FakeThemaRepository())

    result = await service.extract(ThemaRequest(raw_user_input="how plants make food"))

    assert isinstance(result, ResolvedThema)
    assert result.thema == "Photosynthesis"
    assert result.confidence == 0.95
    assert result.confirmation
    assert result.alternates == []


@pytest.mark.asyncio
async def test_resolved_exposes_runner_up_as_alternate(monkeypatch):
    _patch_response(
        monkeypatch,
        _response(
            "Photosynthesis",
            "Science",
            ["Light Reactions", "Calvin Cycle"],
            confidence=0.9,
            alternates=[
                _alt("Cellular Respiration", "Science", ["Glycolysis", "Krebs Cycle"], 0.1)
            ],
        ),
    )
    service = _service(FakeThemaRepository())

    result = await service.extract(ThemaRequest(raw_user_input="how cells make energy"))

    assert isinstance(result, ResolvedThema)
    assert result.thema == "Photosynthesis"
    assert len(result.alternates) == 1
    assert result.alternates[0].thema == "Cellular Respiration"


@pytest.mark.asyncio
async def test_ambiguous_when_split(monkeypatch):
    _patch_response(
        monkeypatch,
        _response(
            "If Statement",
            "Software",
            ["Syntax", "Truthiness", "Branching"],
            confidence=0.4,
            alternates=[
                _alt("English Conditionals", "Language", ["Zero", "First", "Second"], 0.4),
                _alt("Excel IF", "Data", ["Args", "Nesting", "IFS"], 0.2),
            ],
        ),
    )
    service = _service(FakeThemaRepository())

    result = await service.extract(ThemaRequest(raw_user_input="if"))

    assert isinstance(result, AmbiguousThema)
    assert len(result.candidates) == 3
    assert result.candidates[0].confidence == 0.4


@pytest.mark.asyncio
async def test_unresolved_when_scattered(monkeypatch):
    _patch_response(
        monkeypatch,
        _response("A", "Software", ["x", "y", "z"], confidence=0.2),
    )
    service = _service(FakeThemaRepository())

    result = await service.extract(ThemaRequest(raw_user_input="asdf"))

    assert isinstance(result, UnresolvedThema)


@pytest.mark.asyncio
async def test_refine_supersedes_original_and_reextracts(monkeypatch):
    entry = FakeEntry(
        notes=json.dumps({"status": "pending_confirmation", "candidates": []}),
        raw_user_input="agr",
    )
    repo = FakeThemaRepository(entry)
    _patch_response(
        monkeypatch,
        _response(
            "Computer Architecture", "Software", ["CPU", "Memory", "Pipelining"], confidence=0.9
        ),
    )
    service = _service(repo)

    result = await service.refine(entry.id, RefineRequest(clarification="I mean CPU design"))

    assert isinstance(result, ResolvedThema)
    assert result.thema == "Computer Architecture"
    assert entry.notes is not None
    assert json.loads(entry.notes)["status"] == "superseded"
    assert json.loads(entry.notes)["superseded_by"] == str(result.extraction_id)
    assert repo.saved is not None
    assert "CLARIFICATION: I mean CPU design" in repo.saved["raw_user_input"]


@pytest.mark.asyncio
async def test_refine_allowed_after_confirmation(monkeypatch):
    entry = FakeEntry(
        notes=json.dumps({"status": "confirmed", "candidates": []}),
        raw_user_input="agr",
    )
    repo = FakeThemaRepository(entry)
    _patch_response(
        monkeypatch,
        _response("Agriculture", "Science", ["Soil", "Crops", "Livestock"], confidence=0.9),
    )
    service = _service(repo)

    result = await service.refine(entry.id, RefineRequest(clarification="actually computing"))

    assert isinstance(result, ResolvedThema)
    assert entry.notes is not None
    assert json.loads(entry.notes)["status"] == "superseded"


@pytest.mark.asyncio
async def test_refine_rejects_already_superseded_extraction(monkeypatch):
    entry = FakeEntry(notes=json.dumps({"status": "superseded", "candidates": []}))
    service = _service(FakeThemaRepository(entry))

    with pytest.raises(ConflictError):
        await service.refine(entry.id, RefineRequest(clarification="more context"))


@pytest.mark.asyncio
async def test_confirm_rejects_superseded_extraction():
    entry = FakeEntry(notes=json.dumps({"status": "superseded", "candidates": []}))
    service = _service(FakeThemaRepository(entry))

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
    mapper = FakeConceptMapper()
    service = _service(repo, mapper)

    result = await service.confirm(entry.id, ConfirmRequest())

    assert isinstance(result, ResolvedThema)
    assert result.thema == "If Statement"
    assert entry.user_corrected is False
    assert entry.notes is not None
    assert json.loads(entry.notes)["status"] == "confirmed"
    assert len(mapper.calls) == 1
    assert mapper.calls[0].thema == "If Statement"
    assert mapper.calls[0].topics == ["Syntax", "Truthiness", "Branching"]


@pytest.mark.asyncio
async def test_confirm_leaves_extraction_retryable_when_concept_mapping_fails():
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
    service = _service(repo, FakeConceptMapper(fail=True))

    with pytest.raises(RuntimeError):
        await service.confirm(entry.id, ConfirmRequest())

    assert entry.notes is not None
    assert json.loads(entry.notes)["status"] == "pending_confirmation"


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
    service = _service(FakeThemaRepository(entry))

    result = await service.confirm(entry.id, ConfirmRequest(chosen_rank=2))

    assert result.thema == "English Conditionals"
    assert entry.user_corrected is True
    assert entry.user_correction == "English Conditionals"


@pytest.mark.asyncio
async def test_confirm_already_confirmed_raises():
    entry = FakeEntry(json.dumps({"status": "confirmed", "candidates": []}))
    service = _service(FakeThemaRepository(entry))

    with pytest.raises(ConflictError):
        await service.confirm(entry.id, ConfirmRequest())


@pytest.mark.asyncio
async def test_confirm_missing_extraction_raises():
    service = _service(FakeThemaRepository(entry=None))

    with pytest.raises(NotFoundError):
        await service.confirm(uuid4(), ConfirmRequest())
