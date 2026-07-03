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
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from question_generation_service.clients.mistral_config import CompletionConfig
from question_generation_service.core.config import get_settings
from question_generation_service.core.exceptions import (
    AIEmptyResponseError,
    AIInvalidResponseError,
    AIUnavailableError,
)

logger = logging.getLogger(__name__)

settings = get_settings()
client = Mistral(api_key=settings.MISTRAL_API_KEY)

async def aclose() -> None:
    await client.__aexit__(None, None, None)  # type: ignore[no-untyped-call]


@retry(
    retry=retry_if_exception_type(AIUnavailableError),
    wait=wait_exponential(multiplier=0.5, max=8),
    stop=stop_after_attempt(3),
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
        raise AIUnavailableError(f"Mistral API returned {e.status_code}") from e
    except Exception as e:
        logger.error("Mistral network error: %s", e)
        raise AIUnavailableError("Mistral API unreachable") from e


def _parse_content(content: Any) -> dict[str, Any]:
    if not content or not isinstance(content, str):
        raise AIEmptyResponseError("Mistral returned no content")
    try:
        return cast(dict[str, Any], json.loads(content))
    except json.JSONDecodeError as e:
        logger.error("Mistral invalid JSON: %s | raw=%s", e, content)
        raise AIInvalidResponseError("Mistral response is not valid JSON") from e


async def chat_complete(
    system_msg: str, user_msg: str, config: CompletionConfig
) -> dict[str, Any]:
    response = await _complete(system_msg, user_msg, config)
    message = response.choices[0].message if response.choices else None
    content = message.content if message else None
    if content is None:
        logger.error("Mistral empty response: choices=%s", response.choices)
    return _parse_content(content)


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
            samples.append(_parse_content(content))
        except AIInvalidResponseError:
            continue  # drop a single malformed sample; aggregate over the rest

    if not samples:
        raise AIEmptyResponseError("Mistral returned no parseable samples")
    return samples
