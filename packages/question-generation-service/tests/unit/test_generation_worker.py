from collections.abc import Callable
from types import TracebackType
from typing import cast
from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from memosphere_messaging import Broker, Message
from question_generation_service.repositories.quiz_repository import QuizRepositoryProtocol
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


class FakeQuizRepository:
    """Mirrors the real repository's guarantee: claim_job_completion returns
    True only the first time a given message_id is seen, backed by the
    generation_job_completions table's unique constraint in production.
    """

    def __init__(self) -> None:
        self.claimed_ids: set[str] = set()
        self.increments: list[tuple[UUID, int]] = []

    async def claim_job_completion(self, message_id: str) -> bool:
        if message_id in self.claimed_ids:
            return False
        self.claimed_ids.add(message_id)
        return True

    async def increment_questions_ready(self, quiz_id: UUID, delta: int) -> None:
        self.increments.append((quiz_id, delta))


def make_worker(
    generator: FakeGenerator, quiz_repository: FakeQuizRepository | None = None
) -> GenerationWorker:
    def generator_factory(session: AsyncSession) -> QuestionGeneratorProtocol:
        return generator

    def quiz_repository_factory(session: AsyncSession) -> QuizRepositoryProtocol:
        return cast(QuizRepositoryProtocol, quiz_repository)

    return GenerationWorker(
        cast(Callable[[], AsyncSession], FakeSession),
        cast(Broker, object()),  # handle() never touches the broker
        generator_factory,
        quiz_repository_factory if quiz_repository is not None else None,
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


async def test_first_delivery_claims_the_job_and_increments_progress():
    generator = FakeGenerator()
    quiz_repository = FakeQuizRepository()
    quiz_id = str(uuid4())
    message = job_message({"quiz_id": quiz_id})

    await make_worker(generator, quiz_repository).handle(message)

    assert quiz_repository.increments == [(UUID(quiz_id), 0)]


async def test_redelivery_of_the_same_message_does_not_double_count_progress():
    """The exact scenario reclaim_stale introduces: a crash (or rate-limit
    exhaustion) between generating and acking leaves the message pending,
    and it comes back through handle() again with the same message.id.
    """
    generator = FakeGenerator()
    quiz_repository = FakeQuizRepository()
    quiz_id = str(uuid4())
    message = job_message({"quiz_id": quiz_id})
    worker = make_worker(generator, quiz_repository)

    await worker.handle(message)
    await worker.handle(message)

    assert len(generator.calls) == 2  # generation itself does re-run
    assert quiz_repository.increments == [(UUID(quiz_id), 0)]  # but only counted once
