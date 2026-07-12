from uuid import UUID

from fastapi import APIRouter, Depends

from question_generation_service.dependencies.auth import current_user_dependency
from question_generation_service.dependencies.services import SessionServiceDep
from question_generation_service.dependencies.user_provisioning import ProvisionedUser
from question_generation_service.schemas.session import (
    AnswerResult,
    SessionState,
    SessionSummary,
    SubmitAnswerRequest,
)

session_router = APIRouter(tags=["Quiz Sessions"], dependencies=[Depends(current_user_dependency)])


@session_router.post("/v1/quizzes/{quiz_id}/sessions", response_model=SessionState, status_code=201)
async def start_session(
    quiz_id: UUID, service: SessionServiceDep, user: ProvisionedUser
) -> SessionState:
    return await service.start(quiz_id, UUID(user.sub))


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
