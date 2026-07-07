import random
from typing import Protocol, cast
from uuid import UUID

from memosphere_domain import BloomLevel, DifficultyTier, QuestionType
from question_generation_service.clients.mistral_client import chat_complete
from question_generation_service.prompts.question_generation import (
    build_prompt_3_config,
    build_prompt_3_system,
)
from question_generation_service.prompts.question_judge import PROMPT_4_CONFIG, PROMPT_4_SYSTEM
from question_generation_service.repositories.question_repository import (
    QuestionEntryProtocol,
    QuestionInput,
    QuestionRepositoryProtocol,
    ValidationLogInput,
)
from question_generation_service.schemas.question import (
    BATCH_SIZE,
    GeneratedQuestion,
    JudgeVerdict,
    QuestionBatchResponse,
    QuestionGenerationRequest,
    StoredQuestion,
)
from question_generation_service.services.question_validation_service import (
    ValidationResult,
    merge_judge_verdict,
    validate_question,
)

_NOTES_PREVIEW_LENGTH = 500


class QuestionGeneratorProtocol(Protocol):
    async def generate_batch(
        self, request: QuestionGenerationRequest, user_id: UUID
    ) -> QuestionBatchResponse: ...


def _build_user_msg(request: QuestionGenerationRequest) -> str:
    return (
        f"CONCEPT: {request.concept_name}\n"
        f"LEARNING GOAL: {request.learning_goal}\n"
        f"BLOOM LEVEL: {request.bloom_level}\n"
        f"DIFFICULTY TIER: {request.difficulty_tier}"
    )


def _build_judge_user_msg(
    request: QuestionGenerationRequest, drafts: list[GeneratedQuestion]
) -> str:
    # Deliberately omits correct_answer/explanation — the judge must derive
    # its own answer from the question alone, not grade the draft's homework.
    lines = [
        f"CONCEPT: {request.concept_name}",
        f"LEARNING GOAL: {request.learning_goal}",
        f"BLOOM LEVEL: {request.bloom_level}",
        f"DIFFICULTY TIER: {request.difficulty_tier}",
        "",
        "QUESTIONS TO AUDIT:",
    ]
    for i, draft in enumerate(drafts):
        lines.append(f"\n[{i}] ({draft.question_type}) {draft.question_text}")
        if draft.options:
            lines.append(f"    options: {draft.options}")
    return "\n".join(lines)


def _missing_verdict(index: int) -> JudgeVerdict:
    return JudgeVerdict(
        index=index,
        requires_computation=True,
        derived_answers=[""],
        bloom_aligned=False,
        concept_relevant=False,
        notes="Judge did not return a verdict for this question",
    )


def _from_pool_entry(entry: QuestionEntryProtocol) -> StoredQuestion:
    # Pool rows never carry their original Passed/Warning label (that lives in
    # question_validation_log, keyed by a point-in-time check) — but only
    # Passed/Warning drafts are ever stored in the first place, so "Passed" is
    # always a safe, honest label for anything read back out of the pool.
    return StoredQuestion(
        id=entry.id,
        concept_id=entry.concept_id,
        bloom_level=cast(BloomLevel, entry.bloom_level),
        difficulty_tier=cast(DifficultyTier, entry.difficulty_tier),
        question_type=cast(QuestionType, entry.question_type),
        question_text=entry.question_text,
        options=entry.options,
        correct_answers=entry.correct_answers or [],
        explanation=entry.explanation or "",
        estimated_time_seconds=int(entry.estimated_time) if entry.estimated_time else 0,
        tags=entry.tags or [],
        validation_status="Passed",
    )


class QuestionService:
    def __init__(self, repository: QuestionRepositoryProtocol):
        self.repository = repository

    async def _judge_batch(
        self, request: QuestionGenerationRequest, drafts: list[GeneratedQuestion]
    ) -> list[JudgeVerdict]:
        raw = await chat_complete(
            PROMPT_4_SYSTEM, _build_judge_user_msg(request, drafts), PROMPT_4_CONFIG
        )
        verdicts_by_index = {v["index"]: JudgeVerdict(**v) for v in raw["verdicts"]}
        return [verdicts_by_index.get(i, _missing_verdict(i)) for i in range(len(drafts))]

    async def _generate_new(
        self, request: QuestionGenerationRequest
    ) -> tuple[list[StoredQuestion], list[ValidationLogInput]]:
        """Runs the full write-then-judge pipeline (Prompt 3 + structural
        checks + Prompt 4) and stores whatever survives. Always asks for a
        full BATCH_SIZE batch regardless of how large the shortfall actually
        is — dynamically sizing the LLM request itself is a separate change;
        any surplus here still gets stored and simply grows the shared pool
        for the next learner who hits this same cell.
        """
        system_msg = build_prompt_3_system(request.allowed_question_types)
        config = build_prompt_3_config(request.allowed_question_types)
        raw = await chat_complete(system_msg, _build_user_msg(request), config)
        drafts = [GeneratedQuestion(**q) for q in raw["questions"]]

        log_entries: list[ValidationLogInput] = []
        candidates: list[tuple[GeneratedQuestion, ValidationResult]] = []

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
            candidates.append((draft, result))

        # Judge is only run on drafts that already passed structural checks —
        # no point spending a large-model call auditing an obviously broken draft.
        if candidates:
            verdicts = await self._judge_batch(request, [draft for draft, _ in candidates])
            candidates = [
                (draft, merge_judge_verdict(result, draft, verdict))
                for (draft, result), verdict in zip(candidates, verdicts, strict=True)
            ]

        to_store: list[tuple[GeneratedQuestion, ValidationResult]] = []
        for draft, result in candidates:
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
                correct_answers=draft.correct_answers,
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
                    correct_answers=draft.correct_answers,
                    explanation=draft.explanation,
                    estimated_time_seconds=draft.estimated_time_seconds,
                    tags=draft.tags,
                    validation_status=result["status"],
                )
            )

        return stored_questions, log_entries

    async def generate_batch(
        self, request: QuestionGenerationRequest, user_id: UUID
    ) -> QuestionBatchResponse:
        """Serves up to BATCH_SIZE questions for one (concept, Bloom level,
        difficulty) cell — preferring the existing shared pool over a fresh
        LLM call, and preferring pool questions this learner hasn't seen yet
        over ones they have.

        Order of preference: unseen pool -> freshly generated (grows the pool
        for everyone) -> already-seen pool as a last resort, so a returning
        learner degrades gracefully instead of under-delivering when a cell
        is genuinely exhausted.
        """
        pool = await self.repository.get_by_concept_bloom_difficulty(
            request.concept_id, request.bloom_level, request.difficulty_tier
        )
        served_ids = await self.repository.get_served_question_ids(
            user_id, [entry.id for entry in pool]
        )
        unseen_pool = [entry for entry in pool if entry.id not in served_ids]
        random.shuffle(unseen_pool)

        stored_questions = [_from_pool_entry(entry) for entry in unseen_pool[:BATCH_SIZE]]
        log_entries: list[ValidationLogInput] = []

        if len(stored_questions) < BATCH_SIZE:
            generated_questions, generated_log_entries = await self._generate_new(request)
            stored_questions.extend(generated_questions)
            log_entries.extend(generated_log_entries)

        if len(stored_questions) < BATCH_SIZE:
            seen_pool = [entry for entry in pool if entry.id in served_ids]
            random.shuffle(seen_pool)
            shortfall = BATCH_SIZE - len(stored_questions)
            stored_questions.extend(_from_pool_entry(entry) for entry in seen_pool[:shortfall])

        if log_entries:
            await self.repository.log_validations(log_entries)

        if stored_questions:
            await self.repository.mark_served(user_id, [q.id for q in stored_questions])

        return QuestionBatchResponse(
            concept_id=request.concept_id,
            bloom_level=request.bloom_level,
            difficulty_tier=request.difficulty_tier,
            questions=stored_questions,
        )
