from typing import Protocol

from question_generation_service.clients.mistral_client import chat_complete
from question_generation_service.prompts.question_generation import (
    PROMPT_3_CONFIG,
    PROMPT_3_SYSTEM,
)
from question_generation_service.repositories.question_repository import (
    QuestionInput,
    QuestionRepositoryProtocol,
    ValidationLogInput,
)
from question_generation_service.schemas.question import (
    GeneratedQuestion,
    QuestionBatchResponse,
    QuestionGenerationRequest,
    StoredQuestion,
)
from question_generation_service.services.question_validation_service import (
    ValidationResult,
    validate_question,
)

_NOTES_PREVIEW_LENGTH = 500


class QuestionGeneratorProtocol(Protocol):
    async def generate_batch(self, request: QuestionGenerationRequest) -> QuestionBatchResponse: ...


def _build_user_msg(request: QuestionGenerationRequest) -> str:
    return (
        f"CONCEPT: {request.concept_name}\n"
        f"LEARNING GOAL: {request.learning_goal}\n"
        f"BLOOM LEVEL: {request.bloom_level}\n"
        f"DIFFICULTY TIER: {request.difficulty_tier}"
    )


class QuestionService:
    def __init__(self, repository: QuestionRepositoryProtocol):
        self.repository = repository

    async def generate_batch(self, request: QuestionGenerationRequest) -> QuestionBatchResponse:
        raw = await chat_complete(PROMPT_3_SYSTEM, _build_user_msg(request), PROMPT_3_CONFIG)
        drafts = [GeneratedQuestion(**q) for q in raw["questions"]]

        log_entries: list[ValidationLogInput] = []
        to_store: list[tuple[GeneratedQuestion, ValidationResult]] = []

        for draft in drafts:
            result = validate_question(draft)
            if result["status"] == "Failed":
                log_entries.append(
                    ValidationLogInput(
                        question_id=None,
                        validation_status=result["status"],
                        failed_checks=result["failed_checks"],
                        validation_score=result["score"],
                        notes=draft.question_text[:_NOTES_PREVIEW_LENGTH],
                    )
                )
                continue
            to_store.append((draft, result))

        inputs: list[QuestionInput] = [
            QuestionInput(
                concept_id=request.concept_id,
                bloom_level=request.bloom_level,
                difficulty_tier=request.difficulty_tier,
                question_type=draft.question_type,
                question_text=draft.question_text,
                options=draft.options,
                correct_answer=draft.correct_answer,
                explanation=draft.explanation,
                estimated_time=str(draft.estimated_time_seconds),
                tags=draft.tags,
            )
            for draft, _ in to_store
        ]
        stored = await self.repository.save_batch(inputs) if inputs else []

        stored_questions: list[StoredQuestion] = []
        for entry, (draft, result) in zip(stored, to_store, strict=True):
            log_entries.append(
                ValidationLogInput(
                    question_id=entry.id,
                    validation_status=result["status"],
                    failed_checks=result["failed_checks"],
                    validation_score=result["score"],
                    notes=None,
                )
            )
            stored_questions.append(
                StoredQuestion(
                    id=entry.id,
                    concept_id=request.concept_id,
                    bloom_level=request.bloom_level,
                    difficulty_tier=request.difficulty_tier,
                    question_type=draft.question_type,
                    question_text=draft.question_text,
                    options=draft.options,
                    correct_answer=draft.correct_answer,
                    explanation=draft.explanation,
                    estimated_time_seconds=draft.estimated_time_seconds,
                    tags=draft.tags,
                    validation_status=result["status"],
                )
            )

        if log_entries:
            await self.repository.log_validations(log_entries)

        return QuestionBatchResponse(
            concept_id=request.concept_id,
            bloom_level=request.bloom_level,
            difficulty_tier=request.difficulty_tier,
            questions=stored_questions,
        )
