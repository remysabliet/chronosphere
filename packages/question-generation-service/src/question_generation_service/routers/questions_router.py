from fastapi import APIRouter, HTTPException, status


questions_router = APIRouter(
    prefix="/v1/questions", tags=["Question Generation", "Question Feedback"]
)
