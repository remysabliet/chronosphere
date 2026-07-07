from uuid import UUID

from pydantic import BaseModel, Field

from memosphere_domain import (
    ALL_QUESTION_TYPES,
    BloomLevel,
    DifficultyTier,
    QuestionType,
    ValidationStatus,
)

# Prompt tokens amortize across the batch — one LLM call produces this many
# questions per concept-Bloom-tier bucket (main-workflow.md Step 8).
BATCH_SIZE = 5


class QuestionGenerationRequest(BaseModel):
    concept_id: UUID
    concept_name: str = Field(min_length=1, max_length=255)
    learning_goal: str = Field(min_length=1)
    bloom_level: BloomLevel
    difficulty_tier: DifficultyTier
    # The learner's chosen question type(s) from the wizard. Defaults to every
    # type (no restriction) so callers that don't care can omit it entirely.
    allowed_question_types: list[QuestionType] = Field(
        default_factory=lambda: list(ALL_QUESTION_TYPES), min_length=1
    )


class GeneratedQuestion(BaseModel):
    """Raw shape returned by Prompt 3, before validation (Step 8A)."""

    question_type: QuestionType
    question_text: str
    options: list[str] | None = None
    correct_answers: list[str] = Field(min_length=1)
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
    correct_answers: list[str]
    explanation: str
    estimated_time_seconds: int
    tags: list[str]
    validation_status: ValidationStatus


class QuestionBatchResponse(BaseModel):
    concept_id: UUID
    bloom_level: BloomLevel
    difficulty_tier: DifficultyTier
    questions: list[StoredQuestion]


class JudgeVerdict(BaseModel):
    """Prompt 4's independent re-derivation of one candidate question.

    The judge must work out its own answer(s) from scratch — never told the
    draft's stated correct_answers — so `derived_answers` is compared
    programmatically against it (see question_validation_service.answers_match)
    rather than trusting a self-reported correctness boolean, which a model
    can rubber-stamp as true without truly re-deriving anything. Single-answer
    questions are just the multi-select case with one element.
    """

    index: int
    requires_computation: bool
    derived_answers: list[str] = Field(min_length=1)
    bloom_aligned: bool
    concept_relevant: bool
    notes: str = ""
