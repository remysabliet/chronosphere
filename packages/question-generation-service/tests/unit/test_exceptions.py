from uuid import uuid4
from unittest.mock import AsyncMock

import pytest

from question_generation_service.core.exceptions import (
    AIEmptyResponseError,
    AIInvalidResponseError,
    AIUnavailableError,
    ConflictError,
    DomainError,
    InvalidInputError,
    NotFoundError,
)


def test_exception_hierarchy():
    assert issubclass(NotFoundError, DomainError)
    assert issubclass(ConflictError, DomainError)
    assert issubclass(InvalidInputError, DomainError)
    assert issubclass(AIUnavailableError, DomainError)
    assert issubclass(AIEmptyResponseError, DomainError)
    assert issubclass(AIInvalidResponseError, DomainError)


def test_exception_messages():
    assert str(NotFoundError("not here")) == "not here"
    assert str(ConflictError("already done")) == "already done"


# These tests verify the exception handler in main.py maps errors to correct HTTP status.
# They trigger the handler indirectly via the thema router.

def test_not_found_maps_to_404(client, mock_thema_service):
    mock_thema_service.extract = AsyncMock(side_effect=NotFoundError("no such extraction"))
    response = client.post("/v1/thema/extract", json={"raw_user_input": "photosynthesis"})
    assert response.status_code == 404
    assert "no such extraction" in response.json()["detail"]


def test_conflict_maps_to_409(client, mock_thema_service):
    mock_thema_service.confirm = AsyncMock(side_effect=ConflictError("already confirmed"))
    response = client.post(f"/v1/thema/{uuid4()}/confirm", json={})
    assert response.status_code == 409


def test_ai_unavailable_maps_to_503(client, mock_thema_service):
    mock_thema_service.extract = AsyncMock(side_effect=AIUnavailableError("Mistral down"))
    response = client.post("/v1/thema/extract", json={"raw_user_input": "photosynthesis"})
    assert response.status_code == 503


def test_ai_empty_response_maps_to_502(client, mock_thema_service):
    mock_thema_service.extract = AsyncMock(side_effect=AIEmptyResponseError("no content"))
    response = client.post("/v1/thema/extract", json={"raw_user_input": "photosynthesis"})
    assert response.status_code == 502


def test_base_domain_error_maps_to_400(client, mock_thema_service):
    mock_thema_service.extract = AsyncMock(side_effect=DomainError("generic error"))
    response = client.post("/v1/thema/extract", json={"raw_user_input": "photosynthesis"})
    assert response.status_code == 400
