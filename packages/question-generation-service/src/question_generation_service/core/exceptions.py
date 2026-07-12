class DomainError(Exception):
    """Base class for all business/domain exceptions."""


class NotFoundError(DomainError):
    """Requested resource does not exist."""


class ConflictError(DomainError):
    """Requested operation conflicts with the resource's current state."""


class InvalidInputError(DomainError):
    """Caller supplied input that is structurally valid but semantically wrong."""


class AIUnavailableError(DomainError):
    """Upstream AI provider unreachable or erroring."""


class AIRateLimitedError(AIUnavailableError):
    """Upstream AI provider throttled the request (429) — transient, not an
    outage; distinguished from AIUnavailableError so callers can wait it out
    with a longer backoff instead of failing at the same pace as a real
    outage (see docs/architecture/mistral-api-strategy.md §1 per-model RPS
    ceilings).
    """


class AIEmptyResponseError(DomainError):
    """Upstream AI provider returned a response with no usable content."""


class AIInvalidResponseError(DomainError):
    """Upstream AI provider response could not be parsed as expected."""
