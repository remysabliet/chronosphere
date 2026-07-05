from fastapi import APIRouter, Depends

from question_generation_service.dependencies.auth import current_user_dependency
from question_generation_service.dependencies.rate_limit import ai_rate_limiter
from question_generation_service.dependencies.services import WizardServiceDep
from question_generation_service.schemas.wizard import (
    QuizLengthInterpretation,
    QuizLengthRequest,
)

wizard_router = APIRouter(
    prefix="/v1/wizard",
    tags=["Wizard"],
    dependencies=[Depends(current_user_dependency), Depends(ai_rate_limiter)],
)


@wizard_router.post("/quiz-length/interpret", response_model=QuizLengthInterpretation)
async def interpret_quiz_length(
    service: WizardServiceDep, body: QuizLengthRequest
) -> QuizLengthInterpretation:
    return await service.interpret_quiz_length(body)
