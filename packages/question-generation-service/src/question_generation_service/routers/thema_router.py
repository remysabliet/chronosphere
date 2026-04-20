from fastapi import APIRouter, HTTPException, status

from question_generation_service.db.session import SessionDep
from question_generation_service.dependencies.services import ThemaServiceDep

thema_router = APIRouter(prefix="/v1/thema", tags=["Thema & Concepts"])


# TO DO CREATE A MODEL FOR THE PAYLOAD
@thema_router.post("/extract")
def extract(raw_user_input, service: ThemaServiceDep) -> dict[str, str]:
    """
    Comments
    """

    print(f"raw_user_input {raw_user_input}")
    return {"thema": "test", "topics": "val"}
