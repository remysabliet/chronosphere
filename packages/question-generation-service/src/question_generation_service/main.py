from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from scalar_fastapi import get_scalar_api_reference

from question_generation_service.clients import mistral_client
from question_generation_service.core.exceptions import (
    AIEmptyResponseError,
    AIInvalidResponseError,
    AIUnavailableError,
    DomainError,
    NotFoundError,
)
from question_generation_service.db.session import engine
from question_generation_service.routers.moderation_router import moderation_router
from question_generation_service.routers.questions_router import questions_router
from question_generation_service.routers.thema_router import thema_router

_STATUS_BY_EXCEPTION = {
    NotFoundError: 404,
    AIUnavailableError: 503,
    AIEmptyResponseError: 502,
    AIInvalidResponseError: 502,
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await mistral_client.aclose()
    await engine.dispose()


app = FastAPI(
    title="Question Generation Service",
    description="AI-powered question generation",
    version="1.0.0",
    lifespan=lifespan,
)


@app.exception_handler(DomainError)
async def domain_error_handler(request: Request, exc: DomainError):
    status_code = _STATUS_BY_EXCEPTION.get(type(exc), 400)
    return JSONResponse(status_code=status_code, content={"detail": str(exc)})


@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "question-generation"}


app.include_router(questions_router)
app.include_router(thema_router)
app.include_router(moderation_router)


@app.get("/")
async def root():
    return {
        "message": "Question Generation Service - Coming Soon",
        "endpoints": {"health": "/health", "docs": "/docs"},
    }


@app.get("/scalar", include_in_schema=False)
def get_scalar_docs():
    return get_scalar_api_reference(openapi_url=app.openapi_url, title="Scalar API")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)
