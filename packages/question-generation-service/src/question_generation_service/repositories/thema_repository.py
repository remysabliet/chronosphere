from sqlalchemy.ext.asyncio import AsyncSession

from question_generation_service.models.thema import ThemaExtractionInput


class ThemaRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def save(
        self,
        raw_user_input: str,
        extracted_thema: str,
        extracted_topic: str,
        extraction_model: str,
    ) -> ThemaExtractionInput:
        entry = ThemaExtractionInput(
            raw_user_input=raw_user_input,
            extracted_thema=extracted_thema,
            extracted_topic=extracted_topic,
            extraction_model=extraction_model,
        )
        self.session.add(entry)
        await self.session.commit()
        return entry
