import asyncio
import logging
from collections.abc import Sequence
from dataclasses import dataclass
from functools import lru_cache
from typing import Protocol

from mistralai.client.errors import SDKError
from mistralai.client.models import BatchRequest

from memosphere_messaging import JsonValue
from question_generation_service.clients import mistral_client
from question_generation_service.clients.mistral_config import CompletionConfig
from question_generation_service.core.config import get_settings
from question_generation_service.core.exceptions import (
    AIEmptyResponseError,
    AIInvalidResponseError,
    AIUnavailableError,
)

logger = logging.getLogger(__name__)

_TERMINAL_STATUSES = frozenset({"SUCCESS", "FAILED", "TIMEOUT_EXCEEDED", "CANCELLED"})
# Inline batching (requests embedded in the job, results read back via
# get(inline=True)) is capped by Mistral at 10k requests; beyond that the
# file-upload flavour of the Batch API is required.
_INLINE_REQUEST_LIMIT = 10_000
_MAX_CONSECUTIVE_POLL_FAILURES = 5


def _as_object(value: JsonValue | None) -> dict[str, JsonValue]:
    """Narrows a JSON value of unknown shape to an object, defaulting to
    empty — the batch API's response envelope is untyped JSON on the wire;
    a field being absent or the wrong shape is treated the same as empty.
    """
    return value if isinstance(value, dict) else {}


def _as_list(value: JsonValue | None) -> list[JsonValue]:
    return value if isinstance(value, list) else []


@dataclass
class CompletionRequest:
    custom_id: str
    system_msg: str
    user_msg: str
    config: CompletionConfig


class CompletionTransportProtocol(Protocol):
    async def complete_many(
        self, requests: Sequence[CompletionRequest]
    ) -> dict[str, dict[str, JsonValue]]: ...


class SyncTransport:
    """One synchronous HTTPS call per request — the default. Seconds of
    latency, but bounded by the per-model requests/sec limit under load.
    """

    async def complete_many(
        self, requests: Sequence[CompletionRequest]
    ) -> dict[str, dict[str, JsonValue]]:
        parsed = await asyncio.gather(
            *(mistral_client.chat_complete(r.system_msg, r.user_msg, r.config) for r in requests)
        )
        return {r.custom_id: result for r, result in zip(requests, parsed, strict=True)}


class BatchTransport:
    """Runs requests through Mistral's Batch API: one inline batch job per
    distinct model, polled until a terminal status (Mistral has no completion
    webhook), results mapped back by custom_id. Fails closed: any request
    without a usable result fails the whole call, mirroring the judge
    pipeline's fail-closed philosophy.
    """

    async def complete_many(
        self, requests: Sequence[CompletionRequest]
    ) -> dict[str, dict[str, JsonValue]]:
        by_model: dict[str, list[CompletionRequest]] = {}
        for request in requests:
            by_model.setdefault(request.config.model, []).append(request)

        results: dict[str, dict[str, JsonValue]] = {}
        for part in await asyncio.gather(
            *(self._run_job(model, reqs) for model, reqs in by_model.items())
        ):
            results.update(part)

        missing = [r.custom_id for r in requests if r.custom_id not in results]
        if missing:
            raise AIUnavailableError(f"Batch job returned no usable result for: {missing}")
        return results

    def _request_body(self, request: CompletionRequest) -> dict[str, JsonValue]:
        body: dict[str, JsonValue] = {
            "messages": [
                {"role": "system", "content": request.system_msg},
                {"role": "user", "content": request.user_msg},
            ],
            "temperature": request.config.temperature,
            "max_tokens": request.config.max_tokens,
            "response_format": request.config.response_format.model_dump(
                by_alias=True, exclude_none=True
            ),
        }
        if request.config.random_seed is not None:
            body["random_seed"] = request.config.random_seed
        return body

    async def _run_job(
        self, model: str, requests: list[CompletionRequest]
    ) -> dict[str, dict[str, JsonValue]]:
        if len(requests) > _INLINE_REQUEST_LIMIT:
            raise AIUnavailableError(
                f"{len(requests)} requests exceeds the inline batch limit of "
                f"{_INLINE_REQUEST_LIMIT}; file-based batching is not implemented"
            )
        try:
            job = await mistral_client.client.batch.jobs.create_async(
                endpoint="/v1/chat/completions",
                model=model,
                requests=[
                    BatchRequest(custom_id=r.custom_id, body=self._request_body(r))
                    for r in requests
                ],
                timeout_hours=get_settings().MISTRAL_BATCH_TIMEOUT_H,
            )
        except SDKError as e:
            if e.status_code == 402:
                raise AIUnavailableError(
                    "Mistral Batch API requires a paid plan (402): enable billing "
                    "in the console or unset MISTRAL_BATCH_MODE"
                ) from e
            logger.error("Batch job creation failed: status=%s body=%s", e.status_code, e.body)
            raise AIUnavailableError(f"Batch job creation failed ({e.status_code})") from e

        logger.info("batch job %s created: %d request(s) on %s", job.id, len(requests), model)
        return await self._await_results(job.id)

    async def _await_results(self, job_id: str) -> dict[str, dict[str, JsonValue]]:
        settings = get_settings()
        poll_failures = 0
        while True:
            await asyncio.sleep(settings.MISTRAL_BATCH_POLL_INTERVAL_S)
            try:
                job = await mistral_client.client.batch.jobs.get_async(job_id=job_id, inline=True)
            except Exception:
                # A long-running job must survive transient poll errors, but a
                # dead API must not leave us polling forever.
                poll_failures += 1
                logger.warning("batch job %s poll failed (%d)", job_id, poll_failures)
                if poll_failures >= _MAX_CONSECUTIVE_POLL_FAILURES:
                    raise AIUnavailableError(f"Lost contact with batch job {job_id}") from None
                continue
            poll_failures = 0
            status = str(job.status)
            if status in _TERMINAL_STATUSES:
                break
            logger.debug(
                "batch job %s status=%s done=%s/%s",
                job_id,
                status,
                job.completed_requests,
                job.total_requests,
            )
        if status != "SUCCESS":
            raise AIUnavailableError(f"Batch job {job_id} ended with status {status}")
        return self._parse_outputs(job.outputs or [])

    def _parse_outputs(
        self, outputs: list[dict[str, JsonValue]]
    ) -> dict[str, dict[str, JsonValue]]:
        results: dict[str, dict[str, JsonValue]] = {}
        for line in outputs:
            custom_id = line.get("custom_id")
            response = _as_object(line.get("response"))
            body = _as_object(response.get("body"))
            choices = _as_list(body.get("choices"))
            message = _as_object(choices[0]).get("message") if choices else None
            content = _as_object(message).get("content")
            if not isinstance(custom_id, str) or not isinstance(content, str):
                logger.error("unusable batch output line: %s", line.get("error") or line)
                continue
            try:
                results[custom_id] = mistral_client.parse_content(content)
            except (AIInvalidResponseError, AIEmptyResponseError):
                continue  # already logged by parse_content; surfaces as missing
        return results


@lru_cache
def get_transport() -> CompletionTransportProtocol:
    if get_settings().MISTRAL_BATCH_MODE:
        logger.info(
            "Mistral transport: BATCH mode (poll every %.0fs, job timeout %dh)",
            get_settings().MISTRAL_BATCH_POLL_INTERVAL_S,
            get_settings().MISTRAL_BATCH_TIMEOUT_H,
        )
        return BatchTransport()
    return SyncTransport()
