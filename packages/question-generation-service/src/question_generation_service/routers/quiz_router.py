from uuid import UUID

from fastapi import APIRouter, Depends, Query

from question_generation_service.dependencies.auth import current_user_dependency
from question_generation_service.dependencies.services import QuizServiceDep
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


@quiz_router.get("/{quiz_id}", response_model=QuizDetailResponse)
async def get_quiz(
    quiz_id: UUID, service: QuizServiceDep, user: ProvisionedUser
) -> QuizDetailResponse:
    return await service.get(quiz_id, UUID(user.sub))


@quiz_router.patch("/{quiz_id}", response_model=QuizDetailResponse)
async def rename_quiz(
    quiz_id: UUID, body: QuizUpdateRequest, service: QuizServiceDep, user: ProvisionedUser
) -> QuizDetailResponse:
    return await service.rename(quiz_id, UUID(user.sub), body.title)
