from typing import Literal, Optional, Union
from uuid import UUID

from pydantic import BaseModel, Field


class LearnerContext(BaseModel):
    profession: Optional[str] = None
    education_level: Optional[str] = None
    prior_themas: list[str] = Field(default_factory=list)


class ThemaRequest(BaseModel):
    # Beyond ~10k chars the AI struggles to extract a single coherent Thema anyway.
    raw_user_input: str = Field(min_length=2, max_length=10000)
    content_body: Optional[str] = Field(default=None, max_length=50000)
    learner_context: Optional[LearnerContext] = None


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


ThemaExtractionResult = Union[ResolvedThema, AmbiguousThema, UnresolvedThema]


class ConfirmRequest(BaseModel):
    chosen_rank: Optional[int] = Field(default=None, ge=1)


class RefineRequest(BaseModel):
    clarification: str = Field(min_length=2, max_length=2000)
