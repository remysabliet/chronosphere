from typing import Annotated

from fastapi import Depends

from question_generation_service.db.session import SessionDep
from question_generation_service.repositories.thema_repository import ThemaRepository
from question_generation_service.services.thema_service import ThemaService


def get_thema_repository(session: SessionDep) -> ThemaRepository:
    return ThemaRepository(session)


def get_thema_service(
    repository: Annotated[ThemaRepository, Depends(get_thema_repository)]
) -> ThemaService:
    return ThemaService(repository)


ThemaServiceDep = Annotated[ThemaService, Depends(get_thema_service)]
