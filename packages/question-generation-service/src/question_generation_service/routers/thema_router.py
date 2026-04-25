from fastapi import APIRouter, Body, HTTPException, status

from question_generation_service.db.session import SessionDep
from question_generation_service.dependencies.services import ThemaServiceDep
from question_generation_service.schemas.thema import ThemaResponse, ThemaRequest

thema_router = APIRouter(prefix="/v1/thema", tags=["Thema & Topics"])


@thema_router.post("/", response_model=ThemaResponse)
async def extract_thema_topics_from_raw_input(
    service: ThemaServiceDep, body: ThemaRequest
):
    print(f"Router raw_user_input {body.raw_user_input}")
    return await service.extract_thema_topic_from_raw_input(body.raw_user_input)
