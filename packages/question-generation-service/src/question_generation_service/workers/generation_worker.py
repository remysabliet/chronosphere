import asyncio
import contextlib
import logging
from collections.abc import Callable
from uuid import UUID, uuid4

from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from memosphere_messaging import Broker, Message
from question_generation_service.repositories.question_repository import QuestionRepository
from question_generation_service.schemas.question import QuestionGenerationRequest
from question_generation_service.services.question_service import (
    QuestionGeneratorProtocol,
    QuestionService,
)
from question_generation_service.services.quiz_service import JOBS_GENERATE_QUESTIONS

logger = logging.getLogger(__name__)

CONSUMER_GROUP = "question-generation"


def default_generator_factory(session: AsyncSession) -> QuestionGeneratorProtocol:
    return QuestionService(QuestionRepository(session))


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
    ):
        self.session_factory = session_factory
        self.broker = broker
        self.generator_factory = generator_factory or default_generator_factory
        self.consumer_name = f"qgs-{uuid4().hex[:8]}"

    async def handle(self, message: Message) -> None:
        try:
            request = QuestionGenerationRequest.model_validate(message.payload)
            owner = UUID(str(message.payload["owner_user_id"]))
        except (ValidationError, KeyError, ValueError):
            logger.exception("dropping malformed generation job %s", message.id)
            return
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

    async def run(self, stop: asyncio.Event) -> None:
        await self.broker.ensure_group(JOBS_GENERATE_QUESTIONS, CONSUMER_GROUP)
        while not stop.is_set():
            try:
                await self.broker.consume_once(
                    JOBS_GENERATE_QUESTIONS,
                    CONSUMER_GROUP,
                    self.consumer_name,
                    self.handle,
                    count=1,  # one Mistral pipeline at a time per worker
                    block_ms=2000,
                )
            except Exception:
                logger.exception("generation worker poll failed; retrying")
                with contextlib.suppress(TimeoutError):
                    await asyncio.wait_for(stop.wait(), timeout=1.0)
