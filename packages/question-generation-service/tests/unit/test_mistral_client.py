import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from question_generation_service.clients.mistral_client import (
    chat_complete_samples,
    parse_content,
)
from question_generation_service.clients.mistral_config import CompletionConfig
from question_generation_service.core.exceptions import (
    AIEmptyResponseError,
    AIInvalidResponseError,
    AIUnavailableError,
)


def _make_response(content: str) -> MagicMock:
    message = MagicMock()
    message.content = content
    choice = MagicMock()
    choice.message = message
    response = MagicMock()
    response.choices = [choice]
    return response


class TestParseContent:
    def test_valid_json_returns_dict(self):
        result = parse_content('{"thema": "Photosynthesis"}')
        assert result == {"thema": "Photosynthesis"}

    def test_empty_string_raises(self):
        with pytest.raises(AIEmptyResponseError):
            parse_content("")

    def test_none_raises(self):
        with pytest.raises(AIEmptyResponseError):
            parse_content(None)

    def test_invalid_json_raises(self):
        with pytest.raises(AIInvalidResponseError):
            parse_content("not json {")

    def test_non_string_raises(self):
        with pytest.raises(AIEmptyResponseError):
            parse_content(123)


class TestChatCompleteSamples:
    @pytest.mark.asyncio
    async def test_returns_all_valid_samples(self):
        payload = {"thema": "Photosynthesis", "domain": "Science"}
        response = _make_response(json.dumps(payload))
        config = CompletionConfig(n=3)

        with patch(
            "question_generation_service.clients.mistral_client._complete",
            new=AsyncMock(return_value=response),
        ):
            result = await chat_complete_samples("sys", "user", config)

        assert len(result) == 3
        assert result[0] == payload

    @pytest.mark.asyncio
    async def test_drops_failed_samples_keeps_valid(self):
        payload = {"thema": "X"}
        good = _make_response(json.dumps(payload))
        config = CompletionConfig(n=3)

        responses = [AIUnavailableError("fail"), good, good]
        call_count = {"n": 0}

        async def fake_complete(*args, **kwargs):
            r = responses[call_count["n"]]
            call_count["n"] += 1
            if isinstance(r, Exception):
                raise r
            return r

        with patch(
            "question_generation_service.clients.mistral_client._complete",
            new=fake_complete,
        ):
            result = await chat_complete_samples("sys", "user", config)

        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_all_failed_raises(self):
        config = CompletionConfig(n=2)

        with (
            patch(
                "question_generation_service.clients.mistral_client._complete",
                new=AsyncMock(side_effect=AIUnavailableError("all down")),
            ),
            pytest.raises(AIEmptyResponseError),
        ):
            await chat_complete_samples("sys", "user", config)

    @pytest.mark.asyncio
    async def test_empty_choices_skipped(self):
        empty = MagicMock()
        empty.choices = []
        good = _make_response(json.dumps({"thema": "T"}))
        config = CompletionConfig(n=2)

        responses = iter([empty, good])

        with patch(
            "question_generation_service.clients.mistral_client._complete",
            new=AsyncMock(side_effect=lambda *a, **kw: next(responses)),
        ):
            result = await chat_complete_samples("sys", "user", config)

        assert len(result) == 1
