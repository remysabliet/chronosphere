import logging
import time
from typing import Any

import httpx
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import jwt
from jose.exceptions import JOSEError

logger = logging.getLogger(__name__)

_JWKS_CACHE_TTL_SECONDS = 3600

_bearer_scheme = HTTPBearer(auto_error=False)


class CognitoTokenVerifier:
    """Verifies Cognito-issued JWTs (ID tokens) against the user pool's published JWKS.

    One instance per service, reused across requests: the JWKS is fetched once and
    cached, since Cognito rotates signing keys rarely (key rollover, not per-token).
    """

    def __init__(self, issuer: str, audience: str) -> None:
        self.issuer = issuer
        self.audience = audience
        self._jwks: dict[str, Any] | None = None
        self._jwks_fetched_at: float = 0.0

    async def _get_jwks(self) -> dict[str, Any]:
        stale = time.monotonic() - self._jwks_fetched_at > _JWKS_CACHE_TTL_SECONDS
        if self._jwks is None or stale:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.issuer}/.well-known/jwks.json")
                response.raise_for_status()
                self._jwks = response.json()
                self._jwks_fetched_at = time.monotonic()
        return self._jwks

    async def verify(self, token: str) -> dict[str, Any]:
        jwks = await self._get_jwks()
        try:
            header = jwt.get_unverified_header(token)
        except JOSEError as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Malformed token"
            ) from exc

        key = next((k for k in jwks["keys"] if k["kid"] == header.get("kid")), None)
        if key is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Unknown signing key"
            )

        try:
            return jwt.decode(
                token,
                key,
                algorithms=["RS256"],
                audience=self.audience,
                issuer=self.issuer,
                # ID tokens carry at_hash (binds to the access token); we only ever
                # see the ID token here, so there's nothing to compare it against.
                options={"verify_at_hash": False},
            )
        except JOSEError as exc:
            logger.warning("Cognito token verification failed: %s", exc)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
            ) from exc

    async def __call__(
        self,
        credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    ) -> dict[str, Any]:
        if credentials is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token"
            )
        return await self.verify(credentials.credentials)
