from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class LearnerContext(BaseModel):
    profession: str | None = None
    education_level: str | None = None
    prior_themas: list[str] = Field(default_factory=list)


class ThemaRequest(BaseModel):
    # Beyond ~10k chars the AI struggles to extract a single coherent Thema anyway.
    raw_user_input: str = Field(min_length=2, max_length=10000)
    content_body: str | None = Field(default=None, max_length=50000)
    learner_context: LearnerContext | None = None


class ThemaCandidate(BaseModel):
    rank: int
    thema: str
    domain: str
    disambiguator: str
    confidence: float
    confirmation: str
    topics: list[str]


class ResolvedThema(BaseModel):
    status: Literal["resolved"] = "resolved"
    extraction_id: UUID
    thema: str
    domain: str
    topics: list[str]
    confidence: float
    confirmation: str
    # Runner-up interpretations from the same sampling round, in case the winner
    # is wrong — lets the client offer a one-tap alternative before free text.
    alternates: list[ThemaCandidate] = Field(default_factory=list)


class AmbiguousThema(BaseModel):
    status: Literal["ambiguous"] = "ambiguous"
    extraction_id: UUID
    candidates: list[ThemaCandidate]


class UnresolvedThema(BaseModel):
    status: Literal["unresolved"] = "unresolved"
    extraction_id: UUID


NonTopicKind = Literal["greeting_or_chitchat", "meta_question", "unintelligible"]


class NonTopicInput(BaseModel):
    """The learner's message was not a study topic (e.g. a greeting to the wizard)."""

    status: Literal["non_topic"] = "non_topic"
    extraction_id: UUID
    input_kind: NonTopicKind
    # Short in-character wizard reply generated in the same LLM call; the client
    # may fall back to a canned line when empty.
    reply: str = ""


ThemaExtractionResult = ResolvedThema | AmbiguousThema | UnresolvedThema | NonTopicInput


class ConfirmRequest(BaseModel):
    chosen_rank: int | None = Field(default=None, ge=1)


class RefineRequest(BaseModel):
    clarification: str = Field(min_length=2, max_length=2000)
