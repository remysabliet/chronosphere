import json
from collections.abc import AsyncIterator
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse

from question_generation_service.dependencies.auth import CurrentUser, current_user_dependency
from question_generation_service.dependencies.services import EventSubscriberDep, QuizServiceDep
from question_generation_service.dependencies.user_provisioning import ProvisionedUser
from question_generation_service.schemas.quiz import (
    QuizCreateRequest,
    QuizDetailResponse,
    QuizListResponse,
    QuizResponse,
    QuizScope,
    QuizStatus,
    QuizUpdateRequest,
)
from question_generation_service.services.quiz_service import quiz_progress_channel

SSE_KEEPALIVE_S = 15.0

quiz_router = APIRouter(
    prefix="/v1/quizzes",
    tags=["Quizzes"],
    dependencies=[Depends(current_user_dependency)],
)


@quiz_router.post("", response_model=QuizResponse, status_code=201)
async def create_quiz(
    service: QuizServiceDep, body: QuizCreateRequest, user: ProvisionedUser
) -> QuizResponse:
    return await service.create(UUID(user.sub), body)


@quiz_router.get("", response_model=QuizListResponse)
async def list_quizzes(
    service: QuizServiceDep,
    user: ProvisionedUser,
    scope: QuizScope = "mine",
    q: str | None = None,
    status: QuizStatus | None = None,
    page: int = Query(default=1, ge=1),
) -> QuizListResponse:
    return await service.list(UUID(user.sub), scope, q, status, page)


# Registered before /{quiz_id} so the literal path wins the match.
@quiz_router.get("/events", include_in_schema=False)
async def quiz_events(user: CurrentUser, subscriber: EventSubscriberDep) -> StreamingResponse:
    """SSE stream of the caller's quiz generation progress.

    Auth is JWT-only (CurrentUser, no ProvisionedUser): a DB-backed dependency
    would pin a pooled connection for the whole life of the stream. Idle
    periods emit SSE comments so proxies don't reap the connection.
    """
    channel = quiz_progress_channel(UUID(user.sub))

    async def stream() -> AsyncIterator[str]:
        async for payload in subscriber.subscribe(channel, idle_timeout_s=SSE_KEEPALIVE_S):
            if payload is None:
                yield ": keep-alive\n\n"
            else:
                yield f"data: {json.dumps(payload)}\n\n"

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache, no-transform", "X-Accel-Buffering": "no"},
    )


@quiz_router.get("/{quiz_id}", response_model=QuizDetailResponse)
async def get_quiz(
    quiz_id: UUID, service: QuizServiceDep, user: ProvisionedUser
) -> QuizDetailResponse:
    return await service.get(quiz_id, UUID(user.sub))


@quiz_router.post("/{quiz_id}/copy", response_model=QuizDetailResponse, status_code=201)
async def copy_quiz(
    quiz_id: UUID, service: QuizServiceDep, user: ProvisionedUser
) -> QuizDetailResponse:
    return await service.copy(quiz_id, UUID(user.sub))


@quiz_router.patch("/{quiz_id}", response_model=QuizDetailResponse)
async def rename_quiz(
    quiz_id: UUID, body: QuizUpdateRequest, service: QuizServiceDep, user: ProvisionedUser
) -> QuizDetailResponse:
    return await service.rename(quiz_id, UUID(user.sub), body.title)


@quiz_router.delete("/{quiz_id}", status_code=204)
async def delete_quiz(quiz_id: UUID, service: QuizServiceDep, user: ProvisionedUser) -> None:
    await service.delete(quiz_id, UUID(user.sub))
