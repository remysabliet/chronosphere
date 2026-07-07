from typing import Annotated

from fastapi import Depends
from sqlalchemy import text

from memosphere_auth import CognitoClaims
from question_generation_service.db.session import SessionDep
from question_generation_service.dependencies.auth import CurrentUser


async def ensure_user_provisioned(user: CurrentUser, session: SessionDep) -> CognitoClaims:
    """JIT-provisions a `users` row for a Cognito-authenticated learner.

    Nothing else in this system creates that row (there's no sign-up flow
    wired to it yet), and every table keyed on `user_id` — user_thema_exposure,
    concept_progress_tracker, etc. — has an FK back to `users`. Any route that
    threads `user.sub` into a write needs this ahead of it, not just CurrentUser.
    """
    await session.execute(
        text(
            "INSERT INTO users (user_id, name, email, created_at) "
            "VALUES (:user_id, :name, :email, now()) "
            "ON CONFLICT (user_id) DO NOTHING"
        ),
        {"user_id": user.sub, "name": user.name, "email": user.email},
    )
    await session.commit()
    return user


ProvisionedUser = Annotated[CognitoClaims, Depends(ensure_user_provisioned)]
