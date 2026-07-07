from collections.abc import Callable
from types import TracebackType
from typing import cast
from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from memosphere_messaging import Broker, Message
from question_generation_service.schemas.question import (
    QuestionBatchResponse,
    QuestionGenerationRequest,
)
from question_generation_service.services.question_service import QuestionGeneratorProtocol
from question_generation_service.workers.generation_worker import GenerationWorker

pytestmark = pytest.mark.asyncio


class FakeSession:
    async def __aenter__(self) -> "FakeSession":
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        return None


class FakeGenerator:
    def __init__(self) -> None:
        self.calls: list[tuple[QuestionGenerationRequest, UUID]] = []

    async def generate_batch(
        self, request: QuestionGenerationRequest, user_id: UUID
    ) -> QuestionBatchResponse:
        self.calls.append((request, user_id))
        return QuestionBatchResponse(
            concept_id=request.concept_id,
            bloom_level=request.bloom_level,
            difficulty_tier=request.difficulty_tier,
            questions=[],
        )


def make_worker(generator: FakeGenerator) -> GenerationWorker:
    def generator_factory(session: AsyncSession) -> QuestionGeneratorProtocol:
        return generator

    return GenerationWorker(
        cast(Callable[[], AsyncSession], FakeSession),
        cast(Broker, object()),  # handle() never touches the broker
        generator_factory,
    )


def job_message(payload_overrides: dict[str, object] | None = None) -> Message:
    concept_id = str(uuid4())
    payload: dict[str, object] = {
        "owner_user_id": str(uuid4()),
        "concept_id": concept_id,
        "concept_name": "Photosynthesis Inputs",
        "learning_goal": "Identify what the process consumes",
        "bloom_level": "Remembering",
        "difficulty_tier": "medium",
        "allowed_question_types": ["MCQ"],
    }
    payload.update(payload_overrides or {})
    return Message(id="1-0", topic="jobs:generate-questions", payload=payload)  # type: ignore[arg-type]


async def test_valid_job_runs_the_generation_pipeline():
    generator = FakeGenerator()
    message = job_message()

    await make_worker(generator).handle(message)

    assert len(generator.calls) == 1
    request, owner = generator.calls[0]
    assert str(request.concept_id) == message.payload["concept_id"]
    assert request.bloom_level == "Remembering"
    assert request.difficulty_tier == "medium"
    assert request.allowed_question_types == ["MCQ"]
    assert str(owner) == message.payload["owner_user_id"]


async def test_malformed_payload_is_dropped_not_raised():
    generator = FakeGenerator()

    # Missing concept fields entirely.
    await make_worker(generator).handle(
        Message(id="2-0", topic="jobs:generate-questions", payload={"owner_user_id": "nope"})
    )
    # Valid request shape but no owner.
    await make_worker(generator).handle(job_message({"owner_user_id": "not-a-uuid"}))

    assert generator.calls == []
