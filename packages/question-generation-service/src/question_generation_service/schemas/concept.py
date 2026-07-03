from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from question_generation_service.schemas.thema import LearnerContext

BloomLevel = Literal[
    "Remembering",
    "Understanding",
    "Applying",
    "Analyzing",
    "Evaluating",
    "Creating",
]

ComplexityLevel = Literal["Low", "Medium", "High"]


class ConceptItem(BaseModel):
    topic: str
    concept: str
    learning_goal: str
    bloom_levels: list[BloomLevel]
    estimated_time_minutes: int = Field(ge=5, le=120)
    complexity_level: ComplexityLevel


class StoredConceptItem(ConceptItem):
    id: UUID


class ConceptMapRequest(BaseModel):
    thema: str = Field(min_length=1, max_length=200)
    topics: list[str] = Field(min_length=1, max_length=20)
    learner_context: LearnerContext | None = None


class ConceptMapResponse(BaseModel):
    thema: str
    concepts: list[StoredConceptItem]
