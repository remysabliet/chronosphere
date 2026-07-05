from typing import Protocol, TypedDict, cast

from question_generation_service.clients.mistral_client import chat_complete
from question_generation_service.prompts.concept_map import PROMPT_2_CONFIG, PROMPT_2_SYSTEM
from question_generation_service.repositories.learning_unit_repository import (
    ConceptInput,
    LearningUnitEntryProtocol,
    LearningUnitRepositoryProtocol,
)
from question_generation_service.schemas.concept import (
    BloomLevel,
    ComplexityLevel,
    ConceptItem,
    ConceptMapRequest,
    ConceptMapResponse,
    StoredConceptItem,
)
from question_generation_service.schemas.thema import LearnerContext


class ConceptMapperProtocol(Protocol):
    async def map(self, request: ConceptMapRequest) -> ConceptMapResponse: ...


class _ConceptRaw(TypedDict):
    topic: str
    concept: str
    learning_goal: str
    bloom_levels: list[str]
    estimated_time_minutes: int
    complexity_level: str


class _ResponseRaw(TypedDict):
    concepts: list[_ConceptRaw]


def _build_user_msg(thema: str, topics: list[str], learner_context: LearnerContext | None) -> str:
    lines = [
        f"THEMA: {thema}",
        f"TOPICS: {', '.join(topics)}",
    ]
    if learner_context:
        if learner_context.profession:
            lines.append(f"LEARNER PROFESSION: {learner_context.profession}")
        if learner_context.education_level:
            lines.append(f"LEARNER EDUCATION: {learner_context.education_level}")
    return "\n".join(lines)


def _from_entry(entry: LearningUnitEntryProtocol) -> StoredConceptItem:
    """Rebuilds a StoredConceptItem from an already-persisted learning_units row.

    Every field is non-null in practice — our own save_batch always populates
    them — even though the DB columns allow null for rows outside this service.
    """
    return StoredConceptItem(
        id=entry.id,
        topic=cast(str, entry.topic),
        concept=entry.concept_name,
        learning_goal=cast(str, entry.learning_goal),
        bloom_levels=cast(list[BloomLevel], entry.bloom_levels_supported),
        estimated_time_minutes=cast(int, entry.estimated_time_minutes),
        complexity_level=cast(ComplexityLevel, entry.complexity_level),
    )


class ConceptService:
    def __init__(self, repository: LearningUnitRepositoryProtocol):
        self.repository = repository

    async def map(self, request: ConceptMapRequest) -> ConceptMapResponse:
        # Prompt 1 canonicalizes thema/topic text (main-workflow.md Step 5), so the
        # same real-world subject always produces the same strings here — reuse
        # concepts a prior confirm() (by any user) already mapped for this thema,
        # and only pay for Prompt 2 on topics nobody has mapped yet.
        # Note: concurrent first-time requests for the same thema can still race
        # and each insert their own copy — acceptable duplication, not correctness
        # risk; a stronger fix would need a DB-level uniqueness constraint or lock.
        existing = await self.repository.get_by_thema(request.thema)
        requested_topics = set(request.topics)
        covered_topics = {e.topic for e in existing if e.topic in requested_topics}
        missing_topics = [t for t in request.topics if t not in covered_topics]

        new_concepts: list[StoredConceptItem] = []
        if missing_topics:
            raw = await chat_complete(
                PROMPT_2_SYSTEM,
                _build_user_msg(request.thema, missing_topics, request.learner_context),
                PROMPT_2_CONFIG,
            )
            response = cast(_ResponseRaw, raw)

            items: list[ConceptItem] = [
                ConceptItem(
                    topic=c["topic"],
                    concept=c["concept"],
                    learning_goal=c["learning_goal"],
                    bloom_levels=cast(list[BloomLevel], c["bloom_levels"]),
                    estimated_time_minutes=c["estimated_time_minutes"],
                    complexity_level=cast(ComplexityLevel, c["complexity_level"]),
                )
                for c in response["concepts"]
            ]

            inputs: list[ConceptInput] = [
                ConceptInput(
                    topic=item.topic,
                    concept_name=item.concept,
                    learning_goal=item.learning_goal,
                    bloom_levels_supported=list(item.bloom_levels),
                    estimated_time_minutes=item.estimated_time_minutes,
                    bloom_coverage_score=len(item.bloom_levels),
                    complexity_level=item.complexity_level,
                )
                for item in items
            ]

            stored = await self.repository.save_batch(request.thema, inputs)
            new_concepts = [
                StoredConceptItem(id=entry.id, **item.model_dump())
                for entry, item in zip(stored, items, strict=True)
            ]

        reused_concepts = [_from_entry(e) for e in existing if e.topic in requested_topics]

        return ConceptMapResponse(thema=request.thema, concepts=reused_concepts + new_concepts)
