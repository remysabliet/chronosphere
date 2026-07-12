from fastapi import APIRouter

moderation_router = APIRouter(prefix="/v1/moderation", tags=["Moderation", "Admin"])
