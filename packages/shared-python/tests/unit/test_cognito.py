import time
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from jose.exceptions import JOSEError

from memosphere_auth.cognito import _JWKS_CACHE_TTL_SECONDS, CognitoTokenVerifier

FAKE_ISSUER = "https://cognito-idp.us-east-1.amazonaws.com/us-east-1_FAKE"
FAKE_AUDIENCE = "fake-client-id"

_FAKE_JWKS: dict[str, Any] = {"keys": [{"kid": "key-1", "kty": "RSA", "n": "abc", "e": "AQAB"}]}
_FAKE_CLAIMS: dict[str, Any] = {
    "sub": "user-123",
    "iss": FAKE_ISSUER,
    "aud": FAKE_AUDIENCE,
    "exp": int(time.time()) + 3600,
    "iat": int(time.time()),
    "token_use": "id",
    "email": "user@example.com",
}


def _verifier() -> CognitoTokenVerifier:
    return CognitoTokenVerifier(issuer=FAKE_ISSUER, audience=FAKE_AUDIENCE)


def _bearer(token: str) -> HTTPAuthorizationCredentials:
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)


class TestGetJwks:
    @pytest.mark.asyncio
    async def test_fetches_jwks_on_first_call(self):
        verifier = _verifier()
        mock_response = MagicMock()
        mock_response.json.return_value = _FAKE_JWKS
        mock_response.raise_for_status = MagicMock()

        with patch("memosphere_auth.cognito.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client_cls.return_value = mock_client

            jwks = await verifier._get_jwks()

        assert jwks == _FAKE_JWKS
        assert verifier._jwks == _FAKE_JWKS

    @pytest.mark.asyncio
    async def test_returns_cached_jwks_when_fresh(self):
        verifier = _verifier()
        verifier._jwks = _FAKE_JWKS
        verifier._jwks_fetched_at = time.monotonic()  # just fetched

        with patch("memosphere_auth.cognito.httpx.AsyncClient") as mock_client_cls:
            jwks = await verifier._get_jwks()
            mock_client_cls.assert_not_called()

        assert jwks == _FAKE_JWKS

    @pytest.mark.asyncio
    async def test_refetches_stale_cache(self):
        verifier = _verifier()
        verifier._jwks = {"keys": []}
        verifier._jwks_fetched_at = time.monotonic() - _JWKS_CACHE_TTL_SECONDS - 1

        mock_response = MagicMock()
        mock_response.json.return_value = _FAKE_JWKS
        mock_response.raise_for_status = MagicMock()

        with patch("memosphere_auth.cognito.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client_cls.return_value = mock_client

            jwks = await verifier._get_jwks()

        assert jwks == _FAKE_JWKS


class TestVerify:
    @pytest.mark.asyncio
    async def test_malformed_token_raises_401(self):
        verifier = _verifier()
        verifier._jwks = _FAKE_JWKS
        verifier._jwks_fetched_at = time.monotonic()

        with patch(
            "memosphere_auth.cognito.jwt.get_unverified_header", side_effect=JOSEError("bad")
        ):
            with pytest.raises(HTTPException) as exc_info:
                await verifier.verify("not.a.token")

        assert exc_info.value.status_code == 401
        assert "Malformed" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_unknown_signing_key_raises_401(self):
        verifier = _verifier()
        verifier._jwks = _FAKE_JWKS
        verifier._jwks_fetched_at = time.monotonic()

        with patch(
            "memosphere_auth.cognito.jwt.get_unverified_header", return_value={"kid": "unknown-kid"}
        ):
            with pytest.raises(HTTPException) as exc_info:
                await verifier.verify("some.valid.header")

        assert exc_info.value.status_code == 401
        assert "signing key" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_invalid_jwt_raises_401(self):
        verifier = _verifier()
        verifier._jwks = _FAKE_JWKS
        verifier._jwks_fetched_at = time.monotonic()

        with patch(
            "memosphere_auth.cognito.jwt.get_unverified_header", return_value={"kid": "key-1"}
        ):
            with patch("memosphere_auth.cognito.jwt.decode", side_effect=JOSEError("expired")):
                with pytest.raises(HTTPException) as exc_info:
                    await verifier.verify("expired.jwt.token")

        assert exc_info.value.status_code == 401
        assert "Invalid token" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_valid_token_returns_claims(self):
        verifier = _verifier()
        verifier._jwks = _FAKE_JWKS
        verifier._jwks_fetched_at = time.monotonic()

        with patch(
            "memosphere_auth.cognito.jwt.get_unverified_header", return_value={"kid": "key-1"}
        ):
            with patch("memosphere_auth.cognito.jwt.decode", return_value=_FAKE_CLAIMS):
                result = await verifier.verify("valid.jwt.token")

        assert result.sub == "user-123"
        assert result.email == "user@example.com"

    @pytest.mark.asyncio
    async def test_non_id_token_use_raises_401(self):
        verifier = _verifier()
        verifier._jwks = _FAKE_JWKS
        verifier._jwks_fetched_at = time.monotonic()
        access_token_claims = {**_FAKE_CLAIMS, "token_use": "access"}

        with patch(
            "memosphere_auth.cognito.jwt.get_unverified_header", return_value={"kid": "key-1"}
        ):
            with patch("memosphere_auth.cognito.jwt.decode", return_value=access_token_claims):
                with pytest.raises(HTTPException) as exc_info:
                    await verifier.verify("access.jwt.token")

        assert exc_info.value.status_code == 401
        assert "Invalid token" in exc_info.value.detail


class TestCall:
    @pytest.mark.asyncio
    async def test_missing_credentials_raises_401(self):
        verifier = _verifier()
        with pytest.raises(HTTPException) as exc_info:
            await verifier(credentials=None)
        assert exc_info.value.status_code == 401
        assert "Missing" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_valid_credentials_delegates_to_verify(self):
        verifier = _verifier()
        verifier._jwks = _FAKE_JWKS
        verifier._jwks_fetched_at = time.monotonic()

        with patch(
            "memosphere_auth.cognito.jwt.get_unverified_header", return_value={"kid": "key-1"}
        ):
            with patch("memosphere_auth.cognito.jwt.decode", return_value=_FAKE_CLAIMS):
                result = await verifier(credentials=_bearer("valid.token"))

        assert result.sub == "user-123"
        assert result.email == "user@example.com"
