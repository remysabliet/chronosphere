from fastapi import APIRouter

from question_generation_service.dependencies.services import ThemaServiceDep
from question_generation_service.schemas.thema import ThemaRequest, ThemaResponse

thema_router = APIRouter(prefix="/v1/thema", tags=["Thema & Topics"])


@thema_router.post("/", response_model=ThemaResponse)
async def extract_thema_topics_from_raw_input(service: ThemaServiceDep, body: ThemaRequest):
    return await service.extract_thema_topic_from_raw_input(body.raw_user_input)
