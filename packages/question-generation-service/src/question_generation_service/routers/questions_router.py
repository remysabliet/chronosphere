from uuid import UUID

from fastapi import APIRouter, Depends

from question_generation_service.dependencies.auth import current_user_dependency
from question_generation_service.dependencies.rate_limit import ai_rate_limiter
from question_generation_service.dependencies.services import QuestionServiceDep
from question_generation_service.dependencies.user_provisioning import ProvisionedUser
from question_generation_service.schemas.question import (
    QuestionBatchResponse,
    QuestionGenerationRequest,
)

questions_router = APIRouter(
    prefix="/v1/questions",
    tags=["Question Generation", "Question Feedback"],
    dependencies=[Depends(current_user_dependency), Depends(ai_rate_limiter)],
)


@questions_router.post("/generate", response_model=QuestionBatchResponse)
async def generate_questions(
    service: QuestionServiceDep, body: QuestionGenerationRequest, user: ProvisionedUser
) -> QuestionBatchResponse:
    return await service.generate_batch(body, UUID(user.sub))
