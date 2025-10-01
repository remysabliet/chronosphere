"""
Question Generation Service - Minimal Stub
TODO: Implement actual question generation with Mistral AI
"""

from fastapi import FastAPI
import uvicorn

app = FastAPI(
    title="Question Generation Service",
    description="AI-powered question generation - Coming Soon",
    version="1.0.0"
)

@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "question-generation"}

@app.get("/")
async def root():
    return {
        "message": "Question Generation Service - Coming Soon",
        "endpoints": {
            "health": "/health",
            "docs": "/docs"
        }
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)

