from typing import Annotated
from fastapi import Depends

from sqlalchemy.ext.asyncio import AsyncSession
from question_generation_service.db.session import SessionDep
from question_generation_service.services.thema_service import ThemaService


def get_thema_service(session: SessionDep):
    return ThemaService(session)


ThemaServiceDep = Annotated[ThemaService, Depends(get_thema_service)]
