from unittest.mock import AsyncMock

import pytest

from memosphere_auth import CognitoClaims
from question_generation_service.dependencies.user_provisioning import ensure_user_provisioned


def _claims(**overrides: object) -> CognitoClaims:
    defaults = {
        "sub": "11111111-1111-1111-1111-111111111111",
        "iss": "https://cognito-idp.us-east-1.amazonaws.com/us-east-1_test",
        "aud": "test-client-id",
        "exp": 9999999999,
        "iat": 0,
        "token_use": "id",
        "email": "learner@example.com",
        "name": "Learner",
    }
    return CognitoClaims.model_validate({**defaults, **overrides})


@pytest.mark.asyncio
async def test_ensure_user_provisioned_upserts_users_row():
    session = AsyncMock()
    user = _claims()

    result = await ensure_user_provisioned(user, session)

    assert result is user
    session.execute.assert_awaited_once()
    statement, params = session.execute.call_args.args
    assert "INSERT INTO users" in str(statement)
    assert "ON CONFLICT" in str(statement)
    assert params == {"user_id": user.sub, "name": user.name, "email": user.email}
    session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_ensure_user_provisioned_returns_claims_unchanged():
    session = AsyncMock()
    user = _claims(sub="22222222-2222-2222-2222-222222222222", email=None, name=None)

    result = await ensure_user_provisioned(user, session)

    assert result.sub == "22222222-2222-2222-2222-222222222222"
    assert result.email is None
    assert result.name is None
