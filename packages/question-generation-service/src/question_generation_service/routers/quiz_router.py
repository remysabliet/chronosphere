from uuid import UUID

from fastapi import APIRouter, Depends

from question_generation_service.dependencies.auth import current_user_dependency
from question_generation_service.dependencies.services import QuizServiceDep
from question_generation_service.dependencies.user_provisioning import ProvisionedUser
from question_generation_service.schemas.quiz import QuizCreateRequest, QuizResponse

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
