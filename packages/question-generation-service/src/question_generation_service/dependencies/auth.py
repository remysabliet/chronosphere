from typing import Annotated, Any

from fastapi import Depends
from memosphere_auth import CognitoTokenVerifier

from question_generation_service.core.config import get_settings

settings = get_settings()
current_user_dependency = CognitoTokenVerifier(
    issuer=settings.COGNITO_ISSUER, audience=settings.COGNITO_CLIENT_ID
)

CurrentUser = Annotated[dict[str, Any], Depends(current_user_dependency)]
