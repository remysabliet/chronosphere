from typing import TypedDict, cast

from question_generation_service.clients.mistral_client import chat_complete
from question_generation_service.prompts.concept_map import PROMPT_2_CONFIG, PROMPT_2_SYSTEM
from question_generation_service.repositories.learning_unit_repository import (
    ConceptInput,
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


class _ConceptRaw(TypedDict):
    topic: str
    concept: str
    learning_goal: str
    bloom_levels: list[str]
    estimated_time_minutes: int
    complexity_level: str


class _ResponseRaw(TypedDict):
    concepts: list[_ConceptRaw]


def _build_user_msg(request: ConceptMapRequest) -> str:
    lines = [
        f"THEMA: {request.thema}",
        f"TOPICS: {', '.join(request.topics)}",
    ]
    if request.learner_context:
        ctx = request.learner_context
        if ctx.profession:
            lines.append(f"LEARNER PROFESSION: {ctx.profession}")
        if ctx.education_level:
            lines.append(f"LEARNER EDUCATION: {ctx.education_level}")
    return "\n".join(lines)


class ConceptService:
    def __init__(self, repository: LearningUnitRepositoryProtocol):
        self.repository = repository

    async def map(self, request: ConceptMapRequest) -> ConceptMapResponse:
        raw = await chat_complete(PROMPT_2_SYSTEM, _build_user_msg(request), PROMPT_2_CONFIG)
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

        return ConceptMapResponse(
            thema=request.thema,
            concepts=[
                StoredConceptItem(id=entry.id, **item.model_dump())
                for entry, item in zip(stored, items)
            ],
        )
