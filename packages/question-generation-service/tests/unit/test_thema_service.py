import json
from typing import TypedDict
from uuid import UUID, uuid4

import pytest

from question_generation_service.core.exceptions import (
    ConflictError,
    InvalidInputError,
    NotFoundError,
)
from question_generation_service.repositories.thema_repository import (
    ThemaEntryProtocol,
)
from question_generation_service.schemas.concept import (
    ConceptMapRequest,
    ConceptMapResponse,
    StoredConceptItem,
)
from question_generation_service.schemas.thema import (
    AmbiguousThema,
    ConfirmRequest,
    NonTopicInput,
    RefineRequest,
    ResolvedThema,
    ThemaRequest,
    UnresolvedThema,
)
from question_generation_service.services.thema_service import ThemaService

TEST_USER_ID = uuid4()


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
    input_kind: str = "topic",
    reply: str = "",
) -> dict[str, object]:
    return {
        **_alt(thema, domain, topics, confidence),
        "alternates": alternates or [],
        "input_kind": input_kind,
        "reply": reply,
    }


def _non_topic_response(
    input_kind: str, reply: str = "Hi! What shall we learn?"
) -> dict[str, object]:
    return _response("None", "General", [], confidence=0.0, input_kind=input_kind, reply=reply)


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
    def __init__(
        self, *, fail: bool = False, concepts: list[StoredConceptItem] | None = None
    ) -> None:
        self.fail = fail
        self.concepts = concepts or []
        self.calls: list[ConceptMapRequest] = []

    async def map(self, request: ConceptMapRequest) -> ConceptMapResponse:
        if self.fail:
            raise RuntimeError("concept mapping failed")
        self.calls.append(request)
        return ConceptMapResponse(thema=request.thema, concepts=self.concepts)


class _FakeExposureEntry:
    def __init__(self, user_id: UUID, thema: str, exposure_level: str, source: str | None) -> None:
        self.user_id = user_id
        self.thema = thema
        self.exposure_level = exposure_level
        self.source = source


class FakeExposureRepository:
    def __init__(self, exposure_level: str | None = None) -> None:
        self._stored: dict[tuple[UUID, str], str] = {}
        self._preset_level = exposure_level

    async def get(self, user_id: UUID, thema: str) -> _FakeExposureEntry | None:
        level = self._stored.get((user_id, thema), self._preset_level)
        if level is None:
            return None
        return _FakeExposureEntry(user_id, thema, level, source=None)

    async def save(
        self, user_id: UUID, thema: str, exposure_level: str, source: str
    ) -> _FakeExposureEntry:
        self._stored[(user_id, thema)] = exposure_level
        return _FakeExposureEntry(user_id, thema, exposure_level, source)


class FakeBktInitService:
    def __init__(self) -> None:
        self.calls: list[tuple[UUID, list[tuple[UUID, str]], float]] = []

    async def initialize(
        self, user_id: UUID, concept_bloom_pairs: list[tuple[UUID, str]], p_l0: float
    ) -> int:
        self.calls.append((user_id, concept_bloom_pairs, p_l0))
        return len(concept_bloom_pairs)


def _service(
    repo: FakeThemaRepository,
    concept_mapper: FakeConceptMapper | None = None,
    exposure_repository: FakeExposureRepository | None = None,
    bkt_init_service: FakeBktInitService | None = None,
) -> ThemaService:
    return ThemaService(
        repo,
        concept_mapper or FakeConceptMapper(),
        exposure_repository or FakeExposureRepository(),
        bkt_init_service or FakeBktInitService(),
    )


def _patch_response(monkeypatch, response):
    async def fake(system_msg, user_msg, config):
        return response

    monkeypatch.setattr("question_generation_service.services.thema_service.chat_complete", fake)


def _capture_user_msg(monkeypatch, response) -> list[str]:
    """Records every user_msg passed to the model so tests can assert what the
    refine flow actually sends (e.g. the PRIOR GUESS block)."""
    captured: list[str] = []

    async def fake(system_msg, user_msg, config):
        captured.append(user_msg)
        return response

    monkeypatch.setattr("question_generation_service.services.thema_service.chat_complete", fake)
    return captured


def _stored_candidate(
    thema: str, topics: list[str], rank: int = 1, confidence: float = 0.9
) -> dict[str, object]:
    return {
        "rank": rank,
        "thema": thema,
        "domain": "Software",
        "disambiguator": f"{thema} sense",
        "confidence": confidence,
        "confirmation": f"You'll be quizzed on {thema}.",
        "topics": topics,
    }


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
async def test_greeting_returns_non_topic(monkeypatch):
    _patch_response(monkeypatch, _non_topic_response("greeting_or_chitchat"))
    repo = FakeThemaRepository()
    service = _service(repo)

    result = await service.extract(ThemaRequest(raw_user_input="hey"))

    assert isinstance(result, NonTopicInput)
    assert result.input_kind == "greeting_or_chitchat"
    assert result.reply == "Hi! What shall we learn?"
    assert repo.saved is not None
    assert json.loads(repo.saved["notes"])["status"] == "non_topic"


@pytest.mark.asyncio
async def test_chitchat_clarification_does_not_supersede(monkeypatch):
    entry = FakeEntry(
        notes=json.dumps({"status": "pending_disambiguation", "candidates": []}),
        raw_user_input="hey",
    )
    repo = FakeThemaRepository(entry)
    _patch_response(monkeypatch, _non_topic_response("greeting_or_chitchat"))
    service = _service(repo)

    result = await service.refine(entry.id, RefineRequest(clarification="Hello"))

    assert isinstance(result, NonTopicInput)
    assert entry.notes is not None
    assert json.loads(entry.notes)["status"] == "pending_disambiguation"


@pytest.mark.asyncio
async def test_confirm_rejects_non_topic():
    entry = FakeEntry(notes=json.dumps({"status": "non_topic", "candidates": []}))
    service = _service(FakeThemaRepository(entry))

    with pytest.raises(InvalidInputError):
        await service.confirm(entry.id, ConfirmRequest(), TEST_USER_ID)


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
async def test_refine_feeds_prior_guess_into_prompt(monkeypatch):
    # The subtractive-clarification regression: the model can only keep the
    # prior topics verbatim if refine() actually shows it what they were.
    prior_topics = [
        "Decorators and metaclasses",
        "Concurrency with asyncio",
        "Memory management",
        "Advanced exception handling",
    ]
    entry = FakeEntry(
        notes=json.dumps(
            {
                "status": "pending_confirmation",
                "candidates": [_stored_candidate("Advanced Python", prior_topics)],
            }
        ),
        raw_user_input="Python advanced",
    )
    repo = FakeThemaRepository(entry)
    captured = _capture_user_msg(
        monkeypatch,
        _response("Advanced Python", "Software", prior_topics[:3], confidence=0.95),
    )
    service = _service(repo)

    await service.refine(
        entry.id, RefineRequest(clarification="drop advanced exception handling")
    )

    assert len(captured) == 1
    prompt = captured[0]
    assert "PRIOR GUESS" in prompt
    assert "Advanced Python" in prompt
    for topic in prior_topics:
        assert topic in prompt
    assert "CLARIFICATION: drop advanced exception handling" in prompt


@pytest.mark.asyncio
async def test_refine_omits_prior_guess_when_no_candidates(monkeypatch):
    # A parent with no stored candidates (e.g. refined from an ambiguous root
    # whose notes carried none) must not crash or emit an empty PRIOR GUESS.
    entry = FakeEntry(
        notes=json.dumps({"status": "pending_confirmation", "candidates": []}),
        raw_user_input="Python advanced",
    )
    repo = FakeThemaRepository(entry)
    captured = _capture_user_msg(
        monkeypatch,
        _response("Advanced Python", "Software", ["Decorators", "Asyncio"], confidence=0.9),
    )
    service = _service(repo)

    result = await service.refine(entry.id, RefineRequest(clarification="focus on decorators"))

    assert isinstance(result, ResolvedThema)
    assert "PRIOR GUESS" not in captured[0]


@pytest.mark.asyncio
async def test_refine_uses_rank_one_candidate_for_prior_guess(monkeypatch):
    # Prior guess must be the top-ranked reading, not whichever candidate
    # happens to be first in storage order.
    entry = FakeEntry(
        notes=json.dumps(
            {
                "status": "pending_disambiguation",
                "candidates": [
                    _stored_candidate("Excel IF", ["Args", "Nesting"], rank=2, confidence=0.3),
                    _stored_candidate("If Statement", ["Syntax", "Branching"], rank=1),
                ],
            }
        ),
        raw_user_input="if",
    )
    repo = FakeThemaRepository(entry)
    captured = _capture_user_msg(
        monkeypatch, _response("If Statement", "Software", ["Syntax"], confidence=0.95)
    )
    service = _service(repo)

    await service.refine(entry.id, RefineRequest(clarification="the programming one"))

    prompt = captured[0]
    assert "If Statement" in prompt
    assert "Excel IF" not in prompt


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
        await service.confirm(entry.id, ConfirmRequest(), TEST_USER_ID)


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

    result = await service.confirm(entry.id, ConfirmRequest(), TEST_USER_ID)

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
        await service.confirm(entry.id, ConfirmRequest(), TEST_USER_ID)

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

    result = await service.confirm(entry.id, ConfirmRequest(chosen_rank=2), TEST_USER_ID)

    assert result.thema == "English Conditionals"
    assert entry.user_corrected is True
    assert entry.user_correction == "English Conditionals"


@pytest.mark.asyncio
async def test_confirm_already_confirmed_raises():
    entry = FakeEntry(json.dumps({"status": "confirmed", "candidates": []}))
    service = _service(FakeThemaRepository(entry))

    with pytest.raises(ConflictError):
        await service.confirm(entry.id, ConfirmRequest(), TEST_USER_ID)


@pytest.mark.asyncio
async def test_confirm_missing_extraction_raises():
    service = _service(FakeThemaRepository(entry=None))

    with pytest.raises(NotFoundError):
        await service.confirm(uuid4(), ConfirmRequest(), TEST_USER_ID)


def _candidate(thema: str, topics: list[str]) -> dict[str, object]:
    return {
        "rank": 1,
        "thema": thema,
        "domain": "Software",
        "disambiguator": "d",
        "confidence": 0.9,
        "confirmation": "c",
        "topics": topics,
    }


@pytest.mark.asyncio
async def test_confirm_flags_exposure_required_when_unknown():
    entry = FakeEntry(
        json.dumps(
            {"status": "pending_confirmation", "candidates": [_candidate("Rust", ["Ownership"])]}
        )
    )
    service = _service(FakeThemaRepository(entry), exposure_repository=FakeExposureRepository())

    result = await service.confirm(entry.id, ConfirmRequest(), TEST_USER_ID)

    assert isinstance(result, ResolvedThema)
    assert result.exposure_required is True


@pytest.mark.asyncio
async def test_confirm_seeds_bkt_when_exposure_known():
    entry = FakeEntry(
        json.dumps(
            {"status": "pending_confirmation", "candidates": [_candidate("Rust", ["Ownership"])]}
        )
    )
    concept_id = uuid4()
    concepts = [
        StoredConceptItem(
            id=concept_id,
            topic="Ownership",
            concept="Borrow checker",
            learning_goal="Understand borrowing",
            bloom_levels=["Remembering", "Understanding"],
            estimated_time_minutes=10,
            complexity_level="Medium",
        )
    ]
    bkt_init_service = FakeBktInitService()
    service = _service(
        FakeThemaRepository(entry),
        concept_mapper=FakeConceptMapper(concepts=concepts),
        exposure_repository=FakeExposureRepository(exposure_level="Practiced"),
        bkt_init_service=bkt_init_service,
    )

    result = await service.confirm(entry.id, ConfirmRequest(), TEST_USER_ID)

    assert result.exposure_required is False
    assert len(bkt_init_service.calls) == 1
    user_id, pairs, p_l0 = bkt_init_service.calls[0]
    assert user_id == TEST_USER_ID
    assert set(pairs) == {(concept_id, "Remembering"), (concept_id, "Understanding")}
    assert p_l0 == 0.6
