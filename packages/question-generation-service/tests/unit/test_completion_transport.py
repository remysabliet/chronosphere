import json
from types import SimpleNamespace
from typing import Any

import httpx
import pytest
from mistralai.client.errors import SDKError

from question_generation_service.clients.completion_transport import (
    BatchTransport,
    CompletionRequest,
    SyncTransport,
    get_transport,
)
from question_generation_service.clients.mistral_config import CompletionConfig
from question_generation_service.core.config import get_settings
from question_generation_service.core.exceptions import AIUnavailableError


def _request(custom_id: str, model: str = "mistral-small-latest") -> CompletionRequest:
    return CompletionRequest(
        custom_id=custom_id,
        system_msg="system",
        user_msg="user",
        config=CompletionConfig(model=model),
    )


def _output_line(custom_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "custom_id": custom_id,
        "response": {"body": {"choices": [{"message": {"content": json.dumps(payload)}}]}},
    }


def _sdk_error(status_code: int, body: str) -> SDKError:
    response = httpx.Response(
        status_code, text=body, request=httpx.Request("POST", "https://api.mistral.ai")
    )
    return SDKError("API error occurred", response, body)


class _FakeBatchJobs:
    """Stands in for client.batch.jobs: records created jobs and walks each
    poll through QUEUED -> RUNNING -> <final status>."""

    def __init__(
        self,
        outputs_by_model: dict[str, list[dict[str, Any]]],
        final_status: str = "SUCCESS",
        create_error: SDKError | None = None,
    ):
        self.outputs_by_model = outputs_by_model
        self.final_status = final_status
        self.create_error = create_error
        self.created: list[dict[str, Any]] = []
        self.polls: dict[str, int] = {}

    async def create_async(self, **kwargs: Any) -> SimpleNamespace:
        if self.create_error:
            raise self.create_error
        self.created.append(kwargs)
        return SimpleNamespace(id=f"job-{kwargs['model']}")

    async def get_async(self, *, job_id: str, inline: bool) -> SimpleNamespace:
        assert inline
        self.polls[job_id] = self.polls.get(job_id, 0) + 1
        statuses = ["QUEUED", "RUNNING", self.final_status]
        status = statuses[min(self.polls[job_id], len(statuses)) - 1]
        model = job_id.removeprefix("job-")
        return SimpleNamespace(
            status=status,
            outputs=self.outputs_by_model.get(model) if status == "SUCCESS" else None,
            completed_requests=0,
            total_requests=1,
        )


@pytest.fixture
def fast_poll(monkeypatch):
    monkeypatch.setattr(get_settings(), "MISTRAL_BATCH_POLL_INTERVAL_S", 0.001)


def _patch_batch_client(monkeypatch, jobs: _FakeBatchJobs) -> None:
    monkeypatch.setattr(
        "question_generation_service.clients.mistral_client.client",
        SimpleNamespace(batch=SimpleNamespace(jobs=jobs)),
    )


@pytest.mark.asyncio
async def test_sync_transport_maps_results_by_custom_id(monkeypatch):
    async def fake(system_msg: str, user_msg: str, config: CompletionConfig) -> dict[str, Any]:
        return {"echo": user_msg}

    monkeypatch.setattr("question_generation_service.clients.mistral_client.chat_complete", fake)
    result = await SyncTransport().complete_many([_request("a"), _request("b")])
    assert set(result) == {"a", "b"}


@pytest.mark.asyncio
async def test_batch_transport_polls_until_success(monkeypatch, fast_poll):
    jobs = _FakeBatchJobs({"mistral-small-latest": [_output_line("gen", {"questions": []})]})
    _patch_batch_client(monkeypatch, jobs)

    result = await BatchTransport().complete_many([_request("gen")])

    assert result == {"gen": {"questions": []}}
    assert jobs.polls["job-mistral-small-latest"] == 3  # QUEUED, RUNNING, SUCCESS
    (created,) = jobs.created
    assert created["endpoint"] == "/v1/chat/completions"
    body = created["requests"][0].body
    assert body["messages"][0] == {"role": "system", "content": "system"}
    assert body["response_format"]["type"] == "json_object"


@pytest.mark.asyncio
async def test_batch_transport_groups_one_job_per_model(monkeypatch, fast_poll):
    jobs = _FakeBatchJobs(
        {
            "model-a": [_output_line("gen", {"ok": 1})],
            "model-b": [_output_line("judge", {"ok": 2})],
        }
    )
    _patch_batch_client(monkeypatch, jobs)

    result = await BatchTransport().complete_many(
        [_request("gen", model="model-a"), _request("judge", model="model-b")]
    )

    assert set(result) == {"gen", "judge"}
    assert len(jobs.created) == 2


@pytest.mark.asyncio
async def test_batch_transport_402_names_the_fix(monkeypatch, fast_poll):
    error = _sdk_error(402, '{"detail": "You do not have access to this service."}')
    _patch_batch_client(monkeypatch, _FakeBatchJobs({}, create_error=error))

    with pytest.raises(AIUnavailableError, match="MISTRAL_BATCH_MODE"):
        await BatchTransport().complete_many([_request("gen")])


@pytest.mark.asyncio
async def test_batch_transport_fails_on_terminal_non_success(monkeypatch, fast_poll):
    _patch_batch_client(monkeypatch, _FakeBatchJobs({}, final_status="TIMEOUT_EXCEEDED"))

    with pytest.raises(AIUnavailableError, match="TIMEOUT_EXCEEDED"):
        await BatchTransport().complete_many([_request("gen")])


@pytest.mark.asyncio
async def test_batch_transport_fails_closed_on_missing_result(monkeypatch, fast_poll):
    # Job succeeds but one request produced no usable output line.
    jobs = _FakeBatchJobs({"mistral-small-latest": [_output_line("gen", {"ok": 1})]})
    _patch_batch_client(monkeypatch, jobs)

    with pytest.raises(AIUnavailableError, match="judge"):
        await BatchTransport().complete_many([_request("gen"), _request("judge")])


@pytest.mark.asyncio
async def test_batch_transport_skips_malformed_output_lines(monkeypatch, fast_poll):
    lines = [
        {"custom_id": "gen", "error": {"message": "boom"}},
        {
            "custom_id": "gen",
            "response": {"body": {"choices": [{"message": {"content": "not json {"}}]}},
        },
    ]
    _patch_batch_client(monkeypatch, _FakeBatchJobs({"mistral-small-latest": lines}))

    with pytest.raises(AIUnavailableError, match="gen"):
        await BatchTransport().complete_many([_request("gen")])


def test_get_transport_honours_batch_mode_flag(monkeypatch):
    get_transport.cache_clear()
    monkeypatch.setattr(get_settings(), "MISTRAL_BATCH_MODE", False)
    assert isinstance(get_transport(), SyncTransport)

    get_transport.cache_clear()
    monkeypatch.setattr(get_settings(), "MISTRAL_BATCH_MODE", True)
    assert isinstance(get_transport(), BatchTransport)
    get_transport.cache_clear()
