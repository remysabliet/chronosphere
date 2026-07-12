"""End-to-end async quiz-creation flow against real Postgres + real Redis:
QuizService writes quiz + outbox in one transaction → OutboxRelay publishes to
jobs:generate-questions → GenerationWorker consumes and runs the (stubbed)
generation pipeline. Skips cleanly when Redis is unreachable.
"""

import uuid
from collections.abc import Callable
from typing import cast

import pytest
from redis.asyncio import Redis
from redis.exceptions import RedisError
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from memosphere_messaging import RedisStreamsBroker, StreamsClient
from question_generation_service.core.config import get_settings
from question_generation_service.repositories.learning_unit_repository import (
    ConceptInput,
    LearningUnitRepository,
)
from question_generation_service.repositories.quiz_repository import QuizRepository
from question_generation_service.schemas.question import (
    QuestionBatchResponse,
    QuestionGenerationRequest,
    StoredQuestion,
)
from question_generation_service.schemas.quiz import QuizCreateRequest
from question_generation_service.services import quiz_service as quiz_service_module
from question_generation_service.services.question_service import QuestionGeneratorProtocol
from question_generation_service.services.quiz_service import QuizService
from question_generation_service.workers.generation_worker import GenerationWorker
from question_generation_service.workers.outbox_relay import OutboxRelay

pytestmark = pytest.mark.asyncio


QUESTIONS_PER_STUBBED_BATCH = 2


def _fake_question(request: QuestionGenerationRequest) -> StoredQuestion:
    return StoredQuestion(
        id=uuid.uuid4(),
        concept_id=request.concept_id,
        bloom_level=request.bloom_level,
        difficulty_tier=request.difficulty_tier,
        question_type="MCQ",
        question_text="Stub question",
        options=["A", "B"],
        correct_answers=["A"],
        explanation="Because.",
        estimated_time_seconds=30,
        tags=[],
        validation_status="Passed",
    )


class CapturingGenerator:
    def __init__(self) -> None:
        self.calls: list[tuple[QuestionGenerationRequest, uuid.UUID]] = []

    async def generate_batch(
        self, request: QuestionGenerationRequest, user_id: uuid.UUID
    ) -> QuestionBatchResponse:
        self.calls.append((request, user_id))
        return QuestionBatchResponse(
            concept_id=request.concept_id,
            bloom_level=request.bloom_level,
            difficulty_tier=request.difficulty_tier,
            questions=[_fake_question(request) for _ in range(QUESTIONS_PER_STUBBED_BATCH)],
        )


def _concept_input(name: str) -> ConceptInput:
    return ConceptInput(
        topic="Topic",
        concept_name=name,
        learning_goal=f"Master {name}",
        bloom_levels_supported=["Remembering", "Understanding"],
        estimated_time_minutes=10,
        bloom_coverage_score=3,
        complexity_level="Medium",
        embedding=[0.0] * 1024,
    )


async def test_quiz_flow_end_to_end(monkeypatch: pytest.MonkeyPatch):
    settings = get_settings()
    redis: Redis = Redis.from_url(  # pyright: ignore[reportUnknownMemberType]
        settings.REDIS_URL, decode_responses=True, socket_connect_timeout=1
    )
    try:
        await redis.ping()  # pyright: ignore[reportUnknownMemberType, reportGeneralTypeIssues]
    except (RedisError, OSError):
        pytest.skip(f"Redis not reachable at {settings.REDIS_URL}")

    engine = create_async_engine(
        settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")
    )
    session_factory = async_sessionmaker(bind=engine, expire_on_commit=False)
    broker = RedisStreamsBroker(cast(StreamsClient, redis))

    user_id = uuid.uuid4()
    thema = f"Quiz Flow Thema {uuid.uuid4().hex[:8]}"
    # The compose Redis is shared with the dev stack: publish to a test-unique
    # topic so the real dev worker can never consume (and pay Mistral for)
    # jobs whose concepts only exist in the test database.
    test_topic = f"itest:jobs:generate-questions:{uuid.uuid4().hex[:8]}"
    monkeypatch.setattr(quiz_service_module, "JOBS_GENERATE_QUESTIONS", test_topic)

    async with session_factory() as session:
        await session.execute(
            text(
                "INSERT INTO users (user_id, name, email, created_at) "
                "VALUES (:user_id, 'Quiz Flow User', :email, now())"
            ),
            {"user_id": str(user_id), "email": f"{user_id}@example.com"},
        )
        await session.commit()

        unit_repository = LearningUnitRepository(session)
        units = await unit_repository.save_batch(
            thema, [_concept_input("Concept A"), _concept_input("Concept B")]
        )
        unit_ids = {str(u.id) for u in units}

        # 1. Quiz + outbox rows commit together.
        service = QuizService(QuizRepository(session), unit_repository)
        response = await service.create(
            user_id,
            QuizCreateRequest(thema=thema, question_types=["MCQ"], question_count=15),
        )
        assert response.generation_batches_enqueued == 3

        unpublished = await session.execute(
            text(
                "SELECT count(*) FROM outbox WHERE published_at IS NULL "
                "AND payload->>'owner_user_id' = :owner"
            ),
            {"owner": str(user_id)},
        )
        assert unpublished.scalar_one() == 3

    # 2. Relay publishes every unpublished row and stamps published_at.
    relay = OutboxRelay(cast(Callable[[], AsyncSession], session_factory), broker)
    published = await relay.relay_once()
    assert published >= 3

    async with session_factory() as session:
        remaining = await session.execute(
            text(
                "SELECT count(*) FROM outbox WHERE published_at IS NULL "
                "AND payload->>'owner_user_id' = :owner"
            ),
            {"owner": str(user_id)},
        )
        assert remaining.scalar_one() == 0

    # 3. Worker consumes the jobs and runs the generation pipeline (stubbed).
    generator = CapturingGenerator()
    worker = GenerationWorker(
        cast(Callable[[], AsyncSession], session_factory),
        broker,
        lambda session: cast(QuestionGeneratorProtocol, generator),
    )
    await broker.ensure_group(test_topic, "itest-quiz-flow")
    ours: list[tuple[QuestionGenerationRequest, uuid.UUID]] = []
    for _ in range(5):
        consumed = await broker.consume_once(
            test_topic, "itest-quiz-flow", "itest-c1", worker.handle, block_ms=100
        )
        ours = [c for c in generator.calls if str(c[0].concept_id) in unit_ids]
        if len(ours) == 3 or consumed == 0:
            break

    assert len(ours) == 3
    buckets = {(str(r.concept_id), r.bloom_level) for r, _ in ours}
    assert len(buckets) == 3  # three distinct concept-Bloom cells, no dupes
    assert all(bloom in ("Remembering", "Understanding") for _, bloom in buckets)
    assert all(owner == user_id for _, owner in ours)
    assert all(r.difficulty_tier == "medium" for r, _ in ours)
    assert all(r.allowed_question_types == ["MCQ"] for r, _ in ours)

    # 4. Each processed job attributed its stubbed questions back to the quiz's
    # progress counter, keyed by the quiz_id carried in the job payload.
    async with session_factory() as session:
        ready = await session.execute(
            text("SELECT generation_questions_ready FROM quizzes WHERE id = :id"),
            {"id": str(response.id)},
        )
        assert ready.scalar_one() == len(ours) * QUESTIONS_PER_STUBBED_BATCH

    # Cleanup: our DB rows and the test consumer group.
    async with session_factory() as session:
        await session.execute(
            text("DELETE FROM outbox WHERE payload->>'owner_user_id' = :owner"),
            {"owner": str(user_id)},
        )
        await session.execute(
            text("DELETE FROM quizzes WHERE owner_user_id = :owner"), {"owner": str(user_id)}
        )
        await session.execute(text("DELETE FROM learning_units WHERE thema = :t"), {"t": thema})
        await session.execute(text("DELETE FROM users WHERE user_id = :id"), {"id": str(user_id)})
        await session.commit()
    await redis.delete(test_topic)  # drops the stream and its consumer groups
    await redis.aclose()
    await engine.dispose()
