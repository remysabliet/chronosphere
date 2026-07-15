from uuid import UUID

from fastapi import APIRouter, Depends, Query

from question_generation_service.dependencies.auth import current_user_dependency
from question_generation_service.dependencies.services import SessionServiceDep
from question_generation_service.dependencies.user_provisioning import ProvisionedUser
from question_generation_service.schemas.session import (
    AnswerResult,
    SessionHistory,
    SessionPreferences,
    SessionReview,
    SessionState,
    SessionSummary,
    StartSessionRequest,
    SubmitAnswerRequest,
)

session_router = APIRouter(tags=["Quiz Sessions"], dependencies=[Depends(current_user_dependency)])


@session_router.post("/v1/quizzes/{quiz_id}/sessions", response_model=SessionState, status_code=201)
async def start_session(
    quiz_id: UUID,
    service: SessionServiceDep,
    user: ProvisionedUser,
    body: StartSessionRequest | None = None,
) -> SessionState:
    feedback_mode = body.feedback_mode if body else None
    return await service.start(quiz_id, UUID(user.sub), feedback_mode)


@session_router.get("/v1/me/session-preferences", response_model=SessionPreferences)
async def get_session_preferences(
    service: SessionServiceDep, user: ProvisionedUser
) -> SessionPreferences:
    return await service.preferences(UUID(user.sub))


@session_router.get("/v1/sessions", response_model=SessionHistory)
async def list_sessions(
    service: SessionServiceDep,
    user: ProvisionedUser,
    quiz_id: UUID | None = None,
    limit: int = Query(default=50, ge=1, le=200),
) -> SessionHistory:
    return await service.history(UUID(user.sub), quiz_id, limit)


@session_router.get("/v1/sessions/{session_id}", response_model=SessionState)
async def get_session(
    session_id: UUID, service: SessionServiceDep, user: ProvisionedUser
) -> SessionState:
    return await service.get_current(session_id, UUID(user.sub))


@session_router.post("/v1/sessions/{session_id}/answers", response_model=AnswerResult)
async def submit_answer(
    session_id: UUID,
    body: SubmitAnswerRequest,
    service: SessionServiceDep,
    user: ProvisionedUser,
) -> AnswerResult:
    return await service.submit_answer(session_id, UUID(user.sub), body)


@session_router.get("/v1/sessions/{session_id}/summary", response_model=SessionSummary)
async def get_summary(
    session_id: UUID, service: SessionServiceDep, user: ProvisionedUser
) -> SessionSummary:
    return await service.summary(session_id, UUID(user.sub))


@session_router.get("/v1/sessions/{session_id}/review", response_model=SessionReview)
async def get_review(
    session_id: UUID, service: SessionServiceDep, user: ProvisionedUser
) -> SessionReview:
    return await service.review(session_id, UUID(user.sub))
