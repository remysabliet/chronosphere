import asyncio
import contextlib
import logging
import time
from collections.abc import Callable
from uuid import UUID, uuid4

from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from memosphere_messaging import Broker, Message
from question_generation_service.repositories.question_repository import QuestionRepository
from question_generation_service.repositories.quiz_repository import (
    QuizRepository,
    QuizRepositoryProtocol,
)
from question_generation_service.schemas.question import QuestionGenerationRequest
from question_generation_service.services.question_service import (
    QuestionGeneratorProtocol,
    QuestionService,
)
from question_generation_service.services.quiz_service import JOBS_GENERATE_QUESTIONS

logger = logging.getLogger(__name__)

CONSUMER_GROUP = "question-generation"
# Well above the worst-case retry budget for one handle() call (up to 5
# attempts x 20s backoff per Mistral request, 2 sequential requests per
# batch — see clients/mistral_client.py) so a message still being legitimately
# (slowly) retried by its own consumer is never reclaimed out from under it.
RECLAIM_MIN_IDLE_MS = 5 * 60 * 1000
RECLAIM_INTERVAL_S = 60.0


def default_generator_factory(session: AsyncSession) -> QuestionGeneratorProtocol:
    return QuestionService(QuestionRepository(session))


def default_quiz_repository_factory(session: AsyncSession) -> QuizRepositoryProtocol:
    return QuizRepository(session)


class GenerationWorker:
    """Consumes jobs:generate-questions and runs the full generate/judge/store
    pipeline per message — the same code the sync endpoint uses, just with
    nobody waiting. A ValidationError on the payload is a poison message:
    re-raising would leave it pending forever, so it's logged and dropped
    (acked) — the DLQ already caught undecodable JSON upstream.
    """

    def __init__(
        self,
        session_factory: Callable[[], AsyncSession],
        broker: Broker,
        generator_factory: Callable[[AsyncSession], QuestionGeneratorProtocol] | None = None,
        quiz_repository_factory: Callable[[AsyncSession], QuizRepositoryProtocol] | None = None,
    ):
        self.session_factory = session_factory
        self.broker = broker
        self.generator_factory = generator_factory or default_generator_factory
        self.quiz_repository_factory = quiz_repository_factory or default_quiz_repository_factory
        self.consumer_name = f"qgs-{uuid4().hex[:8]}"
        self._last_reclaim = 0.0

    async def handle(self, message: Message) -> None:
        try:
            request = QuestionGenerationRequest.model_validate(message.payload)
            owner = UUID(str(message.payload["owner_user_id"]))
        except (ValidationError, KeyError, ValueError):
            logger.exception("dropping malformed generation job %s", message.id)
            return
        # Optional: jobs enqueued outside quiz creation (if any, in future)
        # simply skip progress tracking rather than failing.
        quiz_id_raw = message.payload.get("quiz_id")

        async with self.session_factory() as session:
            generator = self.generator_factory(session)
            batch = await generator.generate_batch(request, owner)
            logger.info(
                "generated %d questions for %s/%s/%s (job %s)",
                len(batch.questions),
                request.concept_name,
                request.bloom_level,
                request.difficulty_tier,
                message.id,
            )
            if quiz_id_raw:
                quiz_repository = self.quiz_repository_factory(session)
                # Redelivery (crash/timeout between generating and acking the
                # stream entry, or a reclaimed stale message) must not
                # increment the counter a second time for the same job.
                if await quiz_repository.claim_job_completion(message.id):
                    await quiz_repository.increment_questions_ready(
                        UUID(str(quiz_id_raw)), len(batch.questions)
                    )

    async def run(self, stop: asyncio.Event) -> None:
        while not stop.is_set():
            try:
                # Idempotent (swallows BUSYGROUP), so it's also the recovery
                # path: if the stream/group is trimmed or lost underneath us,
                # the next iteration recreates it instead of dead-looping on
                # NOGROUP.
                await self.broker.ensure_group(JOBS_GENERATE_QUESTIONS, CONSUMER_GROUP)
                await self.broker.consume_once(
                    JOBS_GENERATE_QUESTIONS,
                    CONSUMER_GROUP,
                    self.consumer_name,
                    self.handle,
                    count=1,  # one Mistral pipeline at a time per worker
                    block_ms=2000,
                )
                await self._reclaim_if_due()
            except Exception:
                logger.exception("generation worker poll failed; retrying")
                with contextlib.suppress(TimeoutError):
                    await asyncio.wait_for(stop.wait(), timeout=1.0)

    async def _reclaim_if_due(self) -> None:
        now = time.monotonic()
        if now - self._last_reclaim < RECLAIM_INTERVAL_S:
            return
        self._last_reclaim = now
        reclaimed = await self.broker.reclaim_stale(
            JOBS_GENERATE_QUESTIONS,
            CONSUMER_GROUP,
            self.consumer_name,
            self.handle,
            min_idle_ms=RECLAIM_MIN_IDLE_MS,
        )
        if reclaimed:
            logger.warning("reclaimed and retried %d stale generation job(s)", reclaimed)
