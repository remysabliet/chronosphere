"""
Learning Engine Service - Minimal Stub
TODO: Implement actual BKT and IRT algorithms
"""

import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
import uvicorn

load_dotenv(Path(__file__).resolve().parent / ".env")

app = FastAPI(
    title="Learning Engine Service",
    description="BKT and IRT learning algorithms - Coming Soon",
    version="1.0.0"
)

@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "learning-engine"}

@app.get("/")
async def root():
    return {
        "message": "Learning Engine Service - Coming Soon",
        "endpoints": {
            "health": "/health",
            "docs": "/docs"
        }
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8002)))

