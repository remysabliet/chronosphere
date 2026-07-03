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


class AIEmptyResponseError(DomainError):
    """Upstream AI provider returned a response with no usable content."""


class AIInvalidResponseError(DomainError):
    """Upstream AI provider response could not be parsed as expected."""
