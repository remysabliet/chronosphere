from typing import Protocol
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from question_generation_service.models.thema import ThemaExtractionInput


class ThemaEntryProtocol(Protocol):
    id: UUID
    notes: str | None
    raw_user_input: str
    extracted_thema: str | None
    extracted_topic: str | None
    user_corrected: bool
    user_correction: str | None


class ThemaRepositoryProtocol(Protocol):
    async def save(
        self,
        raw_user_input: str,
        extracted_thema: str,
        extracted_topic: str,
        extraction_model: str,
        extraction_confidence: float,
        notes: str,
    ) -> ThemaEntryProtocol: ...

    async def get(self, extraction_id: UUID) -> ThemaEntryProtocol | None: ...

    async def mark_superseded(
        self, entry: ThemaEntryProtocol, notes: str
    ) -> ThemaEntryProtocol: ...

    async def update_on_confirm(
        self,
        entry: ThemaEntryProtocol,
        extracted_thema: str,
        extracted_topic: str,
        notes: str,
        user_corrected: bool,
        user_correction: str | None,
    ) -> ThemaEntryProtocol: ...


class ThemaRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def save(
        self,
        raw_user_input: str,
        extracted_thema: str,
        extracted_topic: str,
        extraction_model: str,
        extraction_confidence: float,
        notes: str,
    ) -> ThemaEntryProtocol:
        entry = ThemaExtractionInput(
            raw_user_input=raw_user_input,
            extracted_thema=extracted_thema,
            extracted_topic=extracted_topic,
            extraction_model=extraction_model,
            extraction_confidence=extraction_confidence,
            notes=notes,
        )
        self.session.add(entry)
        await self.session.commit()
        return entry  # type: ignore[return-value]

    async def get(self, extraction_id: UUID) -> ThemaEntryProtocol | None:
        return await self.session.get(ThemaExtractionInput, extraction_id)  # type: ignore[return-value]

    async def mark_superseded(
        self, entry: ThemaEntryProtocol, notes: str
    ) -> ThemaEntryProtocol:
        entry.notes = notes
        await self.session.commit()
        return entry

    async def update_on_confirm(
        self,
        entry: ThemaEntryProtocol,
        extracted_thema: str,
        extracted_topic: str,
        notes: str,
        user_corrected: bool,
        user_correction: str | None,
    ) -> ThemaEntryProtocol:
        entry.extracted_thema = extracted_thema
        entry.extracted_topic = extracted_topic
        entry.notes = notes
        entry.user_corrected = user_corrected
        entry.user_correction = user_correction
        await self.session.commit()
        return entry
