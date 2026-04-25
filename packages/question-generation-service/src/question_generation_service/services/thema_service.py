from sqlalchemy.ext.asyncio import AsyncSession
from mistralai.client import Mistral
from mistralai.client.models import UserMessage, SystemMessage

from question_generation_service.schemas.thema import ThemaResponse
from question_generation_service.core.config import settings

client = Mistral(api_key=settings.MISTRAL_API_KEY)


class ThemaService:

    def __init__(self, session: AsyncSession):
        self.session = session

    # Extract thema/topic pair from raw_user_input

    async def extract_thema_topic_from_raw_input(
        self, raw_user_input: str
    ) -> ThemaResponse:
        response = await client.chat.complete_async(
            model="mistral-large-latest",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": raw_user_input},
            ],  # type: ignore[arg-type]
        )

        message = response.choices[0].message if response.choices else None
        content = message.content if message else ""
        text = content if isinstance(content, str) else "Nothing"
        print(response)
        return ThemaResponse(
            thema="thema",
            topics=[text],
            raw_user_input=raw_user_input,
        )
