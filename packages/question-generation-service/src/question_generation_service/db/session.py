from typing import Annotated
from fastapi import Depends

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from question_generation_service.db.config import settings

# Create a db engine to connect with DB
engine = create_async_engine(
    url=settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://"),
    # Log sql queries
    echo=True,
)


async def get_session():
    async_session = async_sessionmaker(
        bind=engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session() as session:
        yield session


# Session Dependency Annotation
# Annotated[AsyncSession, Depends(get_session)] is a type alias that says:
# "This parameter is an AsyncSession, and FastAPI should get it by calling get_session()."
SessionDep = Annotated[AsyncSession, Depends(get_session)]
