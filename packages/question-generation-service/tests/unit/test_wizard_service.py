import pytest

from question_generation_service.schemas.wizard import QuizLengthRequest
from question_generation_service.services.wizard_service import WizardService


def _response(
    minutes: int | None = None,
    question_count: int | None = None,
    unlimited: bool = False,
    reply: str = "",
) -> dict[str, object]:
    return {
        "minutes": minutes,
        "question_count": question_count,
        "unlimited": unlimited,
        "reply": reply,
    }


def _patch_response(monkeypatch, response):
    async def fake(system_msg, user_msg, config):
        return response

    monkeypatch.setattr("question_generation_service.services.wizard_service.chat_complete", fake)


@pytest.mark.asyncio
async def test_interprets_minutes(monkeypatch):
    _patch_response(monkeypatch, _response(minutes=20))

    result = await WizardService().interpret_quiz_length(
        QuizLengthRequest(raw_user_input="20 minutes please")
    )

    assert result.minutes == 20
    assert result.question_count is None
    assert result.unlimited is False
    assert result.reply == ""


@pytest.mark.asyncio
async def test_interprets_both_time_and_count(monkeypatch):
    _patch_response(monkeypatch, _response(minutes=7, question_count=7))

    result = await WizardService().interpret_quiz_length(
        QuizLengthRequest(raw_user_input="7min 7 questions")
    )

    assert result.minutes == 7
    assert result.question_count == 7


@pytest.mark.asyncio
async def test_interprets_unlimited(monkeypatch):
    _patch_response(monkeypatch, _response(unlimited=True))

    result = await WizardService().interpret_quiz_length(
        QuizLengthRequest(raw_user_input="no limit")
    )

    assert result.unlimited is True
    assert result.minutes is None


@pytest.mark.asyncio
async def test_no_clue_passes_reply_through(monkeypatch):
    _patch_response(monkeypatch, _response(reply="I just need a size!"))

    result = await WizardService().interpret_quiz_length(
        QuizLengthRequest(raw_user_input="I like cats")
    )

    assert result.minutes is None
    assert result.question_count is None
    assert result.unlimited is False
    assert result.reply == "I just need a size!"


@pytest.mark.asyncio
async def test_clamps_out_of_range_values(monkeypatch):
    _patch_response(monkeypatch, _response(minutes=999, question_count=500))

    result = await WizardService().interpret_quiz_length(
        QuizLengthRequest(raw_user_input="999 minutes 500 questions")
    )

    assert result.minutes == 180
    assert result.question_count == 100
