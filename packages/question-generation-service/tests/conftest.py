import os

# Must be set before any service module is imported (they call get_settings() at module level).
os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")
os.environ.setdefault("MISTRAL_API_KEY", "test-key")
os.environ.setdefault(
    "COGNITO_ISSUER", "https://cognito-idp.us-east-1.amazonaws.com/us-east-1_test"
)
os.environ.setdefault("COGNITO_CLIENT_ID", "test-client-id")

from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from memosphere_auth import CognitoClaims
from question_generation_service.core.config import get_settings

get_settings.cache_clear()

from question_generation_service.db.session import get_session
from question_generation_service.dependencies.auth import current_user_dependency
from question_generation_service.dependencies.rate_limit import ai_rate_limiter
from question_generation_service.dependencies.services import (
    get_exposure_service,
    get_question_service,
    get_thema_service,
)
from question_generation_service.dependencies.user_provisioning import ensure_user_provisioned
from question_generation_service.main import app
from question_generation_service.services.exposure_service import ExposureService
from question_generation_service.services.question_service import QuestionService
from question_generation_service.services.thema_service import ThemaService

# Mirrors the real CognitoTokenVerifier's return type (CognitoClaims, not a
# plain dict) — a fake shaped differently from production here is exactly
# what let `user["sub"]` ship instead of `user.sub` in thema_router.py.
# Built via model_validate(), same as CognitoTokenVerifier.verify() does with
# the real decoded JWT claims, rather than the keyword-arg constructor.
_FAKE_USER = CognitoClaims.model_validate(
    {
        "sub": "11111111-1111-1111-1111-111111111111",
        "iss": "https://cognito-idp.us-east-1.amazonaws.com/us-east-1_test",
        "aud": "test-client-id",
        "exp": 9999999999,
        "iat": 0,
        "token_use": "id",
        "email": "test@example.com",
    }
)


async def _fake_session() -> AsyncGenerator[MagicMock]:
    yield MagicMock()


@pytest.fixture(autouse=True)
def _reset_rate_limiter() -> None:
    """The AI-endpoint rate limiter is a process-wide singleton — clear its
    in-memory counters between tests so one test's requests can't trip
    another's limit."""
    ai_rate_limiter._windows.clear()


@pytest.fixture(scope="session")
def anon_client():
    """TestClient with no auth override — useful for testing auth errors."""
    with TestClient(app) as c:
        yield c


@pytest.fixture
def mock_thema_service() -> MagicMock:
    svc = MagicMock(spec=ThemaService)
    svc.extract = AsyncMock()
    svc.refine = AsyncMock()
    svc.confirm = AsyncMock()
    return svc


@pytest.fixture
def mock_exposure_service() -> MagicMock:
    svc = MagicMock(spec=ExposureService)
    svc.submit = AsyncMock()
    return svc


@pytest.fixture
def mock_question_service() -> MagicMock:
    svc = MagicMock(spec=QuestionService)
    svc.generate_batch = AsyncMock()
    return svc


@pytest.fixture
def client(
    mock_thema_service: MagicMock,
    mock_exposure_service: MagicMock,
    mock_question_service: MagicMock,
):
    """TestClient with auth + DB + service fully overridden."""
    app.dependency_overrides[current_user_dependency] = lambda: _FAKE_USER
    # Router-level unit tests exercise routing, not the real JIT-provisioning
    # write — that's covered by the integration tests against a real DB.
    app.dependency_overrides[ensure_user_provisioned] = lambda: _FAKE_USER
    app.dependency_overrides[get_session] = _fake_session
    app.dependency_overrides[get_thema_service] = lambda: mock_thema_service
    app.dependency_overrides[get_exposure_service] = lambda: mock_exposure_service
    app.dependency_overrides[get_question_service] = lambda: mock_question_service
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
