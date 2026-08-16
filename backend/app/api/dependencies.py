from collections.abc import Callable
from typing import Annotated

import jwt
from fastapi import Cookie, Depends, Header
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.errors import APIError
from app.core.installation import installation_store
from app.core.security import decode_token
from app.db.session import get_db
from app.models.identity import Role, User
from app.services.permission_service import require_permissions

DBSession = Annotated[Session, Depends(get_db)]


def require_setup_completed() -> None:
    if not installation_store.is_complete:
        raise APIError(503, "setup_required", "Initial setup must be completed")


def get_current_user(
    db: DBSession,
    access_token: Annotated[str | None, Cookie(alias="sprint_access")] = None,
    authorization: Annotated[str | None, Header()] = None,
) -> User:
    require_setup_completed()
    token = access_token
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization[7:].strip()
    if not token:
        raise APIError(401, "not_authenticated", "Authentication is required")
    try:
        payload = decode_token(token, "access")
    except jwt.InvalidTokenError as exc:
        raise APIError(
            401, "invalid_access_token", "The access token is invalid or expired"
        ) from exc
    user = db.scalar(
        select(User)
        .options(selectinload(User.roles).selectinload(Role.permissions))
        .where(User.id == payload.get("sub"))
    )
    if user is None or not user.is_active or payload.get("version") != user.token_version:
        raise APIError(401, "not_authenticated", "Authentication is required")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_permission(*permission_keys: str) -> Callable[[User], User]:
    def dependency(user: CurrentUser) -> User:
        require_permissions(user, permission_keys)
        return user

    return dependency
