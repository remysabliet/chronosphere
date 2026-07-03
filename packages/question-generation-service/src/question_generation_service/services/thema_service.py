import json
from typing import Any, TypedDict
from uuid import UUID

from question_generation_service.clients.mistral_client import chat_complete_samples
from question_generation_service.core.config import get_settings
from question_generation_service.core.exceptions import (
    ConflictError,
    InvalidInputError,
    NotFoundError,
)
from question_generation_service.prompts.thema_topic_extract import (
    PROMPT_1_CONFIG,
    PROMPT_1_SYSTEM,
)
from question_generation_service.repositories.thema_repository import ThemaRepositoryProtocol
from question_generation_service.schemas.thema import (
    AmbiguousThema,
    ConfirmRequest,
    RefineRequest,
    ResolvedThema,
    ThemaCandidate,
    ThemaExtractionResult,
    ThemaRequest,
    UnresolvedThema,
)

EXTRACTED_TOPIC_MAX_LENGTH = 255
MAX_EXPOSED_CANDIDATES = 3
MAX_EXPOSED_ALTERNATES = 2
MAX_REFINED_INPUT_LENGTH = 10000

_PERSIST_STATUS = {
    "resolved": "pending_confirmation",
    "ambiguous": "pending_disambiguation",
    "unresolved": "unresolved",
}


class _RawCandidate(TypedDict):
    thema: str
    domain: str
    disambiguator: str
    confirmation: str
    topics: list[str]
    confidence: float


class _Candidate(_RawCandidate):
    rank: int


class _Group(TypedDict):
    count: int
    sample: dict[str, Any]


class _ChosenCandidate(TypedDict):
    thema: str
    domain: str
    topics: list[str]


class _NotesPayloadBase(TypedDict):
    status: str
    candidates: list[_Candidate]


class _NotesPayload(_NotesPayloadBase, total=False):
    parent_extraction_id: str
    superseded_by: str
    chosen: _ChosenCandidate


class _ResolvedFields(TypedDict):
    thema: str
    domain: str
    topics: list[str]
    confidence: float
    confirmation: str
    alternates: list[ThemaCandidate]


def _build_user_message(request: ThemaRequest) -> str:
    parts = [f"INPUT: {request.raw_user_input}"]
    ctx = request.learner_context
    if ctx:
        bits = []
        if ctx.profession:
            bits.append(f"profession={ctx.profession}")
        if ctx.education_level:
            bits.append(f"education={ctx.education_level}")
        if ctx.prior_themas:
            bits.append("prior_themas=" + ", ".join(ctx.prior_themas))
        if bits:
            parts.append("LEARNER CONTEXT: " + "; ".join(bits))
    if request.content_body:
        parts.append("CONTENT BODY (authoritative):\n" + request.content_body)
    return "\n\n".join(parts)


def _join_topics(topics: list[str]) -> str:
    return ", ".join(topics)[:EXTRACTED_TOPIC_MAX_LENGTH]


def _aggregate(samples: list[dict[str, Any]]) -> list[_Candidate]:
    """Cluster samples by (thema, domain); vote share is the confidence."""
    groups: dict[tuple[str, str], _Group] = {}
    order: list[tuple[str, str]] = []
    for s in samples:
        key = (s["thema"].strip().lower(), s["domain"])
        if key not in groups:
            groups[key] = {"count": 0, "sample": s}
            order.append(key)
        groups[key]["count"] += 1

    total = len(samples)
    raw: list[_RawCandidate] = []
    for key in order:
        g = groups[key]
        s = g["sample"]
        raw.append(
            _RawCandidate(
                thema=s["thema"],
                domain=s["domain"],
                disambiguator=s["disambiguator"],
                confirmation=s["confirmation"],
                topics=s["topics"],
                confidence=round(g["count"] / total, 3),
            )
        )
    raw.sort(key=lambda c: c["confidence"], reverse=True)
    return [_Candidate(**raw_c, rank=rank) for rank, raw_c in enumerate(raw, start=1)]


def _resolved_fields(candidate: _Candidate, alternates: list[ThemaCandidate]) -> _ResolvedFields:
    return _ResolvedFields(
        thema=candidate["thema"],
        domain=candidate["domain"],
        topics=candidate["topics"],
        confidence=candidate["confidence"],
        confirmation=candidate["confirmation"],
        alternates=alternates,
    )


class ThemaService:
    def __init__(self, repository: ThemaRepositoryProtocol):
        self.repository = repository
        self.settings = get_settings()

    def _decide(self, candidates: list[_Candidate], *, is_refine: bool) -> str:
        top = candidates[0]
        second = candidates[1] if len(candidates) > 1 else None
        t_high = self.settings.THEMA_REFINE_T_HIGH if is_refine else self.settings.THEMA_T_HIGH
        margin = self.settings.THEMA_REFINE_MARGIN if is_refine else self.settings.THEMA_MARGIN
        if top["confidence"] <= self.settings.THEMA_T_LOW:
            return "unresolved"
        clear_winner = second is None or (top["confidence"] - second["confidence"] >= margin)
        if top["confidence"] >= t_high and clear_winner:
            return "resolved"
        return "ambiguous"

    async def _extract_and_persist(
        self, raw_user_input: str, llm_user_msg: str, parent_extraction_id: UUID | None
    ) -> ThemaExtractionResult:
        samples = await chat_complete_samples(
            system_msg=PROMPT_1_SYSTEM,
            user_msg=llm_user_msg,
            config=PROMPT_1_CONFIG,
        )
        candidates = _aggregate(samples)
        decision = self._decide(candidates, is_refine=parent_extraction_id is not None)
        top = candidates[0]

        notes_payload: _NotesPayload = {
            "status": _PERSIST_STATUS[decision],
            "candidates": candidates,
        }
        if parent_extraction_id is not None:
            notes_payload["parent_extraction_id"] = str(parent_extraction_id)

        entry = await self.repository.save(
            raw_user_input=raw_user_input,
            extracted_thema=top["thema"],
            extracted_topic=_join_topics(top["topics"]),
            extraction_model=PROMPT_1_CONFIG.model,
            extraction_confidence=top["confidence"],
            notes=json.dumps(notes_payload),
        )

        if decision == "resolved":
            alternates = [
                ThemaCandidate(**c) for c in candidates[1 : 1 + MAX_EXPOSED_ALTERNATES]
            ]
            return ResolvedThema(
                extraction_id=entry.id, **_resolved_fields(top, alternates)
            )
        if decision == "ambiguous":
            return AmbiguousThema(
                extraction_id=entry.id,
                candidates=[
                    ThemaCandidate(**c) for c in candidates[:MAX_EXPOSED_CANDIDATES]
                ],
            )
        return UnresolvedThema(extraction_id=entry.id)

    async def extract(self, request: ThemaRequest) -> ThemaExtractionResult:
        return await self._extract_and_persist(
            raw_user_input=request.raw_user_input,
            llm_user_msg=_build_user_message(request),
            parent_extraction_id=None,
        )

    async def refine(self, extraction_id: UUID, request: RefineRequest) -> ThemaExtractionResult:
        entry = await self.repository.get(extraction_id)
        if entry is None or not entry.notes:
            raise NotFoundError(f"No extraction found for id {extraction_id}")

        data: _NotesPayload = json.loads(entry.notes)
        if data["status"] == "superseded":
            raise ConflictError("This extraction has already been refined")

        combined_input = f"{entry.raw_user_input}\nCLARIFICATION: {request.clarification}"
        if len(combined_input) > MAX_REFINED_INPUT_LENGTH:
            raise InvalidInputError(
                "This thread has too much context to refine further — start a new extraction"
            )

        result = await self._extract_and_persist(
            raw_user_input=combined_input,
            llm_user_msg=_build_user_message(ThemaRequest(raw_user_input=combined_input)),
            parent_extraction_id=extraction_id,
        )

        superseded_notes: _NotesPayload = json.loads(entry.notes)
        superseded_notes["status"] = "superseded"
        superseded_notes["superseded_by"] = str(result.extraction_id)
        await self.repository.mark_superseded(entry, notes=json.dumps(superseded_notes))

        return result

    async def confirm(self, extraction_id: UUID, request: ConfirmRequest) -> ResolvedThema:
        entry = await self.repository.get(extraction_id)
        if entry is None or not entry.notes:
            raise NotFoundError(f"No extraction found for id {extraction_id}")

        data: _NotesPayload = json.loads(entry.notes)
        if data["status"] == "confirmed":
            raise ConflictError("This extraction has already been confirmed")
        if data["status"] == "superseded":
            raise ConflictError("This extraction was refined — confirm the newer one instead")
        candidates = data["candidates"]

        chosen, corrected, correction, confidence, confirmation, domain = self._pick(
            request, candidates
        )

        confirmed_payload: _NotesPayload = {
            "status": "confirmed",
            "candidates": candidates,
            "chosen": _ChosenCandidate(
                thema=chosen["thema"],
                domain=domain,
                topics=chosen["topics"],
            ),
        }
        await self.repository.update_on_confirm(
            entry,
            extracted_thema=chosen["thema"],
            extracted_topic=_join_topics(chosen["topics"]),
            notes=json.dumps(confirmed_payload),
            user_corrected=corrected,
            user_correction=correction,
        )
        return ResolvedThema(
            extraction_id=entry.id,
            thema=chosen["thema"],
            domain=domain,
            topics=chosen["topics"],
            confidence=confidence,
            confirmation=confirmation,
        )

    def _pick(
        self, request: ConfirmRequest, candidates: list[_Candidate]
    ) -> tuple[_Candidate, bool, str | None, float, str, str]:
        if not candidates:
            raise NotFoundError("No candidates stored for this extraction")

        rank = request.chosen_rank or 1
        match: _Candidate | None = next(
            (c for c in candidates if c["rank"] == rank), None
        )
        if match is None:
            raise InvalidInputError(f"No candidate with rank {rank}")

        corrected = rank != 1
        return (
            match,
            corrected,
            match["thema"] if corrected else None,
            match["confidence"],
            match["confirmation"],
            match["domain"],
        )
