import asyncio
import json
import logging
from typing import Any, cast

from mistralai.client import Mistral
from mistralai.client.errors import SDKError
from mistralai.client.models import SystemMessageTypedDict, UserMessageTypedDict
from mistralai.client.models.chatcompletionrequest import (
    ChatCompletionRequestMessageTypedDict,
)
from tenacity import (
    RetryCallState,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from question_generation_service.clients.mistral_config import CompletionConfig
from question_generation_service.core.config import get_settings
from question_generation_service.core.exceptions import (
    AIEmptyResponseError,
    AIInvalidResponseError,
    AIRateLimitedError,
    AIUnavailableError,
)

logger = logging.getLogger(__name__)

settings = get_settings()
# httpx's default read timeout is 5s — too short for max_tokens=4096 structured
# completions (e.g. concept mapping), which can legitimately take longer to generate.
client = Mistral(api_key=settings.MISTRAL_API_KEY, timeout_ms=60_000)

_OUTAGE_WAIT = wait_exponential(multiplier=0.5, max=8)
# A 429 is throttling, not an outage — some Mistral models' per-model RPS
# ceiling is as tight as ~1 request/14s (mistral-large, see
# docs/architecture/mistral-api-strategy.md §1), so the short outage backoff
# above would exhaust all attempts before the window ever clears.
_RATE_LIMIT_WAIT = wait_exponential(multiplier=2, max=20)


async def aclose() -> None:
    await client.__aexit__(None, None, None)  # type: ignore[no-untyped-call]


def _wait_for_mistral(retry_state: RetryCallState) -> float:
    exception = retry_state.outcome.exception() if retry_state.outcome else None
    wait = _RATE_LIMIT_WAIT if isinstance(exception, AIRateLimitedError) else _OUTAGE_WAIT
    return wait(retry_state)


@retry(
    retry=retry_if_exception_type(AIUnavailableError),
    wait=_wait_for_mistral,
    stop=stop_after_attempt(5),
    reraise=True,
)
async def _complete(system_msg: str, user_msg: str, config: CompletionConfig) -> Any:
    try:
        messages: list[ChatCompletionRequestMessageTypedDict] = [
            SystemMessageTypedDict(role="system", content=system_msg),
            UserMessageTypedDict(role="user", content=user_msg),
        ]
        return await client.chat.complete_async(
            model=config.model,
            messages=messages,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
            random_seed=config.random_seed,
            response_format=config.response_format,
        )
    except SDKError as e:
        logger.error("Mistral API error: status=%s body=%s", e.status_code, e.body)
        if e.status_code == 429:
            raise AIRateLimitedError("Mistral API rate limit exceeded") from e
        raise AIUnavailableError(f"Mistral API returned {e.status_code}") from e
    except Exception as e:
        logger.error("Mistral network error: %s: %r", type(e).__name__, e)
        raise AIUnavailableError("Mistral API unreachable") from e


def parse_content(content: object) -> dict[str, Any]:
    if not content or not isinstance(content, str):
        raise AIEmptyResponseError("Mistral returned no content")
    try:
        return cast(dict[str, Any], json.loads(content))
    except json.JSONDecodeError as e:
        logger.error("Mistral invalid JSON: %s | raw=%s", e, content)
        raise AIInvalidResponseError("Mistral response is not valid JSON") from e


async def chat_complete(system_msg: str, user_msg: str, config: CompletionConfig) -> dict[str, Any]:
    response = await _complete(system_msg, user_msg, config)
    message = response.choices[0].message if response.choices else None
    content = message.content if message else None
    if content is None:
        logger.error("Mistral empty response: choices=%s", response.choices)
    return parse_content(content)


@retry(
    retry=retry_if_exception_type(AIUnavailableError),
    wait=_wait_for_mistral,
    stop=stop_after_attempt(5),
    reraise=True,
)
async def embed(texts: list[str]) -> list[list[float]]:
    """Batched embeddings for question/concept similarity checks (see
    docs/architecture/question-diversity-and-dedup.md). One call for the
    whole list, not one per text — embeddings are a separate model/endpoint
    from chat completions, so this never rides along with a generation call;
    callers should run it concurrently with whatever else doesn't depend on
    it (e.g. the judge call) rather than awaiting it in sequence.
    """
    if not texts:
        return []
    try:
        response = await client.embeddings.create_async(
            model=settings.MISTRAL_EMBED_MODEL, inputs=texts
        )
    except SDKError as e:
        logger.error("Mistral embeddings API error: status=%s body=%s", e.status_code, e.body)
        if e.status_code == 429:
            raise AIRateLimitedError("Mistral API rate limit exceeded") from e
        raise AIUnavailableError(f"Mistral API returned {e.status_code}") from e
    except Exception as e:
        logger.error("Mistral embeddings network error: %s: %r", type(e).__name__, e)
        raise AIUnavailableError("Mistral API unreachable") from e

    by_index = {item.index: item.embedding for item in response.data if item.embedding is not None}
    if len(by_index) != len(texts):
        raise AIEmptyResponseError(
            f"Mistral returned {len(by_index)} embeddings for {len(texts)} inputs"
        )
    return [by_index[i] for i in range(len(texts))]


async def chat_complete_samples(
    system_msg: str, user_msg: str, config: CompletionConfig
) -> list[dict[str, Any]]:
    """Self-consistency sampling: Mistral caps n=1 per request, so fan out config.n concurrent calls."""
    responses = await asyncio.gather(
        *(_complete(system_msg, user_msg, config) for _ in range(config.n)),
        return_exceptions=True,
    )

    samples: list[dict[str, Any]] = []
    for response in responses:
        if isinstance(response, BaseException):
            logger.error("Mistral sample failed: %s", response)
            continue
        if not response.choices:
            continue
        content = response.choices[0].message.content if response.choices[0].message else None
        if not content or not isinstance(content, str):
            continue
        try:
            samples.append(parse_content(content))
        except AIInvalidResponseError:
            continue  # drop a single malformed sample; aggregate over the rest

    if not samples:
        raise AIEmptyResponseError("Mistral returned no parseable samples")
    return samples
