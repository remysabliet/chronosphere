from fastapi import APIRouter, Depends

from question_generation_service.dependencies.auth import current_user_dependency
from question_generation_service.dependencies.rate_limit import ai_rate_limiter
from question_generation_service.dependencies.services import ConceptServiceDep
from question_generation_service.schemas.concept import ConceptMapRequest, ConceptMapResponse

concept_router = APIRouter(
    prefix="/v1/concepts",
    tags=["Concept Mapping"],
    dependencies=[Depends(current_user_dependency), Depends(ai_rate_limiter)],
)


@concept_router.post("/map", response_model=ConceptMapResponse)
async def map_concepts(service: ConceptServiceDep, body: ConceptMapRequest) -> ConceptMapResponse:
    return await service.map(body)
