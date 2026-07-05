from pydantic import BaseModel, Field


class QuizLengthRequest(BaseModel):
    raw_user_input: str = Field(min_length=1, max_length=500)


class QuizLengthInterpretation(BaseModel):
    """AI reading of a free-text answer to 'how do you want to size the quiz?'."""

    minutes: int | None = Field(default=None, ge=1)
    question_count: int | None = Field(default=None, ge=1)
    unlimited: bool = False
    # In-character wizard sentence; non-empty only when no size could be read.
    reply: str = ""
