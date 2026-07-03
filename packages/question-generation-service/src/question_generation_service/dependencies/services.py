from typing import Annotated

from fastapi import Depends

from question_generation_service.db.session import SessionDep
from question_generation_service.repositories.learning_unit_repository import LearningUnitRepository
from question_generation_service.repositories.thema_repository import ThemaRepository
from question_generation_service.services.concept_service import ConceptService
from question_generation_service.services.thema_service import ThemaService


def get_thema_repository(session: SessionDep) -> ThemaRepository:
    return ThemaRepository(session)


def get_thema_service(
    repository: Annotated[ThemaRepository, Depends(get_thema_repository)]
) -> ThemaService:
    return ThemaService(repository)


def get_learning_unit_repository(session: SessionDep) -> LearningUnitRepository:
    return LearningUnitRepository(session)


def get_concept_service(
    repository: Annotated[LearningUnitRepository, Depends(get_learning_unit_repository)]
) -> ConceptService:
    return ConceptService(repository)


ThemaServiceDep = Annotated[ThemaService, Depends(get_thema_service)]
ConceptServiceDep = Annotated[ConceptService, Depends(get_concept_service)]
