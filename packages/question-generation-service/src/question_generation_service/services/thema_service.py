from sqlalchemy.ext.asyncio import AsyncSession


class ThemaService:

    def __init__(self, session: AsyncSession):
        self.session = session

    # Extract thema/topic pair from raw_user_input
    async def extract_thema_topic_from_raw_input(
        self, raw_user_input: str
    ) -> dict[str, str]:
        return {"thema": "tempoTema", "topic": "tempotopic"}
