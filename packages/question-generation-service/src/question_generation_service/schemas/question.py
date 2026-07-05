from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from question_generation_service.schemas.concept import BloomLevel

QuestionType = Literal["MCQ", "TrueFalse", "FillInBlank"]
DifficultyTier = Literal["easy", "medium", "hard"]
ValidationStatus = Literal["Passed", "Failed", "Warning"]

# Prompt tokens amortize across the batch — one LLM call produces this many
# questions per concept-Bloom-tier bucket (main-workflow.md Step 8).
BATCH_SIZE = 5


class QuestionGenerationRequest(BaseModel):
    concept_id: UUID
    concept_name: str = Field(min_length=1, max_length=255)
    learning_goal: str = Field(min_length=1)
    bloom_level: BloomLevel
    difficulty_tier: DifficultyTier


class GeneratedQuestion(BaseModel):
    """Raw shape returned by Prompt 3, before validation (Step 8A)."""

    question_type: QuestionType
    question_text: str
    options: list[str] | None = None
    correct_answer: str
    explanation: str
    estimated_time_seconds: int = Field(ge=5, le=300)
    tags: list[str] = Field(default_factory=list)


class StoredQuestion(BaseModel):
    id: UUID
    concept_id: UUID
    bloom_level: BloomLevel
    difficulty_tier: DifficultyTier
    question_type: QuestionType
    question_text: str
    options: list[str] | None
    correct_answer: str
    explanation: str
    estimated_time_seconds: int
    tags: list[str]
    validation_status: ValidationStatus


class QuestionBatchResponse(BaseModel):
    concept_id: UUID
    bloom_level: BloomLevel
    difficulty_tier: DifficultyTier
    questions: list[StoredQuestion]
