from pydantic import BaseModel, Field
from typing import Optional


class ThemaResponse(BaseModel):
    thema: str
    topics: list[str]
    raw_user_input: str


class ThemaRequest(BaseModel):
    raw_user_input: str = Field(
        min_length=2, max_length=10000
    )  # Beyond that you're into territory where the AI will struggle to extract a single coherent Thema anyway
