import time
from typing import Annotated

from fastapi import Depends

from memosphere_auth import CognitoClaims, CognitoTokenVerifier
from question_generation_service.core.config import get_settings

settings = get_settings()

# Fixed identity served when DEV_AUTH_BYPASS is on — local development only.
DEV_BYPASS_SUB = "00000000-0000-4000-8000-000000000001"


def _dev_bypass_user() -> CognitoClaims:
    now = int(time.time())
    return CognitoClaims.model_validate(
        {
            "sub": DEV_BYPASS_SUB,
            "iss": settings.COGNITO_ISSUER,
            "aud": settings.COGNITO_CLIENT_ID,
            "exp": now + 3600,
            "iat": now,
            "token_use": "id",
            "email": "dev-bypass@local.test",
            "name": "Dev Bypass",
        }
    )


current_user_dependency = (
    _dev_bypass_user
    if settings.DEV_AUTH_BYPASS
    else CognitoTokenVerifier(issuer=settings.COGNITO_ISSUER, audience=settings.COGNITO_CLIENT_ID)
)

CurrentUser = Annotated[CognitoClaims, Depends(current_user_dependency)]
