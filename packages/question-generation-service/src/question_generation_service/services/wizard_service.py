from question_generation_service.clients.mistral_client import chat_complete
from question_generation_service.prompts.quiz_length_interpret import (
    MAX_MINUTES,
    MAX_QUESTIONS,
    QUIZ_LENGTH_CONFIG,
    QUIZ_LENGTH_SYSTEM,
)
from question_generation_service.schemas.wizard import (
    QuizLengthInterpretation,
    QuizLengthRequest,
)


def _clamp(value: int | None, maximum: int) -> int | None:
    if value is None:
        return None
    return max(1, min(value, maximum))


class WizardService:
    async def interpret_quiz_length(self, request: QuizLengthRequest) -> QuizLengthInterpretation:
        response = await chat_complete(
            system_msg=QUIZ_LENGTH_SYSTEM,
            user_msg=f"LEARNER REPLY: {request.raw_user_input}",
            config=QUIZ_LENGTH_CONFIG,
        )
        # Belt-and-braces: the prompt asks the model to clamp, enforce it anyway.
        return QuizLengthInterpretation(
            minutes=_clamp(response["minutes"], MAX_MINUTES),
            question_count=_clamp(response["question_count"], MAX_QUESTIONS),
            unlimited=response["unlimited"],
            reply=response["reply"],
        )
