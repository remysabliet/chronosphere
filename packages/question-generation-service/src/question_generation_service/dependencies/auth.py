from typing import Annotated

from fastapi import Depends

from memosphere_auth import CognitoClaims, CognitoTokenVerifier
from question_generation_service.core.config import get_settings

settings = get_settings()
current_user_dependency = CognitoTokenVerifier(
    issuer=settings.COGNITO_ISSUER, audience=settings.COGNITO_CLIENT_ID
)

CurrentUser = Annotated[CognitoClaims, Depends(current_user_dependency)]
