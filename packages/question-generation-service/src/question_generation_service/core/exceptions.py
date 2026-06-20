class DomainError(Exception):
    """Base class for all business/domain exceptions."""


class NotFoundError(DomainError):
    """Requested resource does not exist."""


class AIUnavailableError(DomainError):
    """Upstream AI provider unreachable or erroring."""


class AIEmptyResponseError(DomainError):
    """Upstream AI provider returned a response with no usable content."""


class AIInvalidResponseError(DomainError):
    """Upstream AI provider response could not be parsed as expected."""
