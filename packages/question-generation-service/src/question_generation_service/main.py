import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import cast

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from scalar_fastapi import get_scalar_api_reference

from memosphere_messaging import PubSubClient, RedisPubSub, RedisStreamsBroker, StreamsClient
from question_generation_service.clients import mistral_client
from question_generation_service.core.config import get_settings
from question_generation_service.core.exceptions import (
    AIEmptyResponseError,
    AIInvalidResponseError,
    AIUnavailableError,
    ConflictError,
    DomainError,
    NotFoundError,
)
from question_generation_service.core.redis import close_redis_client, get_redis_client
from question_generation_service.db.session import async_session, engine
from question_generation_service.routers.concept_router import concept_router
from question_generation_service.routers.moderation_router import moderation_router
from question_generation_service.routers.questions_router import questions_router
from question_generation_service.routers.quiz_router import quiz_router
from question_generation_service.routers.session_router import session_router
from question_generation_service.routers.thema_router import thema_router
from question_generation_service.routers.wizard_router import wizard_router
from question_generation_service.workers.generation_worker import GenerationWorker
from question_generation_service.workers.outbox_relay import OutboxRelay

_STATUS_BY_EXCEPTION = {
    NotFoundError: 404,
    ConflictError: 409,
    AIUnavailableError: 503,
    AIEmptyResponseError: 502,
    AIInvalidResponseError: 502,
}

_WORKER_SHUTDOWN_TIMEOUT_SECONDS = 10


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    worker_tasks: list[asyncio.Task[None]] = []
    stop = asyncio.Event()
    if settings.ENABLE_BACKGROUND_WORKERS:
        redis = get_redis_client()
        broker = RedisStreamsBroker(cast(StreamsClient, redis))
        relay = OutboxRelay(async_session, broker)
        worker = GenerationWorker(
            async_session, broker, event_publisher=RedisPubSub(cast(PubSubClient, redis))
        )
        worker_tasks = [
            asyncio.create_task(relay.run(stop), name="outbox-relay"),
            asyncio.create_task(worker.run(stop), name="generation-worker"),
        ]
    yield
    stop.set()
    if worker_tasks:
        await asyncio.wait(worker_tasks, timeout=_WORKER_SHUTDOWN_TIMEOUT_SECONDS)
    await close_redis_client()
    await mistral_client.aclose()
    await engine.dispose()


app = FastAPI(
    title="Question Generation Service",
    description="AI-powered question generation",
    version="1.0.0",
    lifespan=lifespan,
)


def _status_for(exc: DomainError) -> int:
    # Walks the MRO instead of an exact-type lookup so a new subclass (e.g.
    # AIRateLimitedError under AIUnavailableError) inherits its parent's
    # status by default instead of silently falling through to 400.
    for cls in type(exc).__mro__:
        if cls in _STATUS_BY_EXCEPTION:
            return _STATUS_BY_EXCEPTION[cls]
    return 400


@app.exception_handler(DomainError)
async def domain_error_handler(request: Request, exc: DomainError) -> JSONResponse:
    return JSONResponse(status_code=_status_for(exc), content={"detail": str(exc)})


@app.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok", "service": "question-generation"}


app.include_router(concept_router)
app.include_router(questions_router)
app.include_router(quiz_router)
app.include_router(session_router)
app.include_router(thema_router)
app.include_router(wizard_router)
app.include_router(moderation_router)


@app.get("/")
async def root() -> dict[str, str | dict[str, str]]:
    return {
        "message": "Question Generation Service - Coming Soon",
        "endpoints": {"health": "/health", "docs": "/docs"},
    }


@app.get("/scalar", include_in_schema=False)
def get_scalar_docs() -> HTMLResponse:
    return get_scalar_api_reference(openapi_url=app.openapi_url, title="Scalar API")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)
