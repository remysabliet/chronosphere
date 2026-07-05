from uuid import UUID

from fastapi import APIRouter, Depends

from question_generation_service.dependencies.auth import current_user_dependency
from question_generation_service.dependencies.rate_limit import ai_rate_limiter
from question_generation_service.dependencies.services import ThemaServiceDep
from question_generation_service.schemas.thema import (
    ConfirmRequest,
    RefineRequest,
    ResolvedThema,
    ThemaExtractionResult,
    ThemaRequest,
)

thema_router = APIRouter(
    prefix="/v1/thema",
    tags=["Thema & Topics"],
    dependencies=[Depends(current_user_dependency), Depends(ai_rate_limiter)],
)


@thema_router.post("/extract", response_model=ThemaExtractionResult)
async def extract_thema_topics(
    service: ThemaServiceDep, body: ThemaRequest
) -> ThemaExtractionResult:
    return await service.extract(body)


@thema_router.post("/{extraction_id}/refine", response_model=ThemaExtractionResult)
async def refine_thema(
    service: ThemaServiceDep, extraction_id: UUID, body: RefineRequest
) -> ThemaExtractionResult:
    return await service.refine(extraction_id, body)


@thema_router.post("/{extraction_id}/confirm", response_model=ResolvedThema)
async def confirm_thema(
    service: ThemaServiceDep, extraction_id: UUID, body: ConfirmRequest
) -> ResolvedThema:
    return await service.confirm(extraction_id, body)
