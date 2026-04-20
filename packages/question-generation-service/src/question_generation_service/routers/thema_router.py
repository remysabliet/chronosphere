from fastapi import APIRouter,  HTTPException, status


thema_router = APIRouter(prefix="/v1/thema", tags=["Thema & Concepts"])