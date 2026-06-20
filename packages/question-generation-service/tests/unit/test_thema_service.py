import pytest

from question_generation_service.services.thema_service import ThemaService


class FakeThemaRepository:
    def __init__(self):
        self.saved: dict | None = None

    async def save(self, **kwargs):
        self.saved = kwargs


@pytest.mark.asyncio
async def test_extract_thema_topic_from_raw_input(monkeypatch):
    async def fake_chat_complete(system_msg, user_msg, config):
        return {"thema": "Photosynthesis", "topics": ["Light Reactions", "Calvin Cycle"]}

    monkeypatch.setattr(
        "question_generation_service.services.thema_service.chat_complete",
        fake_chat_complete,
    )

    repository = FakeThemaRepository()
    service = ThemaService(repository)

    result = await service.extract_thema_topic_from_raw_input("how plants make food")

    assert result.thema == "Photosynthesis"
    assert result.topics == ["Light Reactions", "Calvin Cycle"]
    assert result.raw_user_input == "how plants make food"
    assert repository.saved is not None
    assert repository.saved["extracted_thema"] == "Photosynthesis"
    assert repository.saved["extracted_topic"] == "Light Reactions, Calvin Cycle"
    assert repository.saved["raw_user_input"] == "how plants make food"
