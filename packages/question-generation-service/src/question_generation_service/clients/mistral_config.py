from dataclasses import dataclass, field

from mistralai.client.models import ResponseFormat


@dataclass
class CompletionConfig:
    model: str = "mistral-large-latest"
    temperature: float = 0.0
    max_tokens: int = 1024
    n: int = 1
    random_seed: int | None = None
    response_format: ResponseFormat = field(
        default_factory=lambda: ResponseFormat(type="json_object")
    )
