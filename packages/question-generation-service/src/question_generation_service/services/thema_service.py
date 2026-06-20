from question_generation_service.clients.mistral_client import chat_complete
from question_generation_service.prompts.thema_topic_extract import (
    PROMPT_1_CONFIG,
    PROMPT_1_SYSTEM,
)
from question_generation_service.repositories.thema_repository import ThemaRepository
from question_generation_service.schemas.thema import ThemaResponse

# extracted_topic is varchar(255) in the DB; joined topics are truncated to fit.
EXTRACTED_TOPIC_MAX_LENGTH = 255


class ThemaService:
    def __init__(self, repository: ThemaRepository):
        self.repository = repository

    async def extract_thema_topic_from_raw_input(self, raw_user_input: str) -> ThemaResponse:
        result = await chat_complete(
            system_msg=PROMPT_1_SYSTEM, user_msg=raw_user_input, config=PROMPT_1_CONFIG
        )
        extracted_topic = ", ".join(result["topics"])[:EXTRACTED_TOPIC_MAX_LENGTH]
        await self.repository.save(
            raw_user_input=raw_user_input,
            extracted_thema=result["thema"],
            extracted_topic=extracted_topic,
            extraction_model=PROMPT_1_CONFIG.model,
        )
        return ThemaResponse(raw_user_input=raw_user_input, **result)
