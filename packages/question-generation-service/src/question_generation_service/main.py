"""
Question Generation Service - Minimal Stub
TODO: Implement actual question generation with Mistral AI
"""

from scalar_fastapi import get_scalar_api_reference
from fastapi import FastAPI

from question_generation_service.routers.questions_router import (
    questions_router,
)
from question_generation_service.routers.thema_router import thema_router
from question_generation_service.routers.moderation_router import moderation_router

import uvicorn

app = FastAPI(
    title="Question Generation Service",
    description="AI-powered question generation",
    version="1.0.0",
)


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
