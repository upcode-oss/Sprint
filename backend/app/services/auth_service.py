from datetime import UTC, datetime, timedelta

import jwt
from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from app.core.config import settings
from app.core.errors import APIError
from app.core.security import (
    create_access_token,
    create_refresh_token,
    create_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.identity import Role, SMTPConfiguration, User
from app.services.mail_service import send_email


def find_user_for_login(db: Session, identifier: str) -> User | None:
    normalized = identifier.strip().lower()
    return db.scalar(
        select(User)
        .options(selectinload(User.roles).selectinload(Role.permissions))
        .where(or_(User.username == identifier.strip(), User.email == normalized))
    )


def authenticate(db: Session, identifier: str, password: str) -> User:
    user = find_user_for_login(db, identifier)
    if user is None or not verify_password(password, user.password_hash):
        raise APIError(401, "invalid_credentials", "Username or password is incorrect")
    if not user.is_active:
        raise APIError(403, "account_disabled", "This account has been disabled")
    user.last_login = datetime.now(UTC)
    db.commit()
    db.refresh(user)
    return user


def issue_tokens(user: User) -> tuple[str, str]:
    return create_access_token(user.id, user.token_version), create_refresh_token(
        user.id, user.token_version
    )


def refresh_access_token(db: Session, refresh_token: str) -> tuple[User, str, str]:
    try:
        payload = decode_token(refresh_token, "refresh")
    except jwt.InvalidTokenError as exc:
        raise APIError(401, "invalid_refresh_token", "The session has expired") from exc
    user = db.scalar(
        select(User)
        .options(selectinload(User.roles).selectinload(Role.permissions))
        .where(User.id == payload.get("sub"))
    )
    if user is None or not user.is_active or payload.get("version") != user.token_version:
        raise APIError(401, "invalid_refresh_token", "The session has expired")
    return user, *issue_tokens(user)


def change_password(db: Session, user: User, current: str, new: str) -> None:
    if not verify_password(current, user.password_hash):
        raise APIError(400, "invalid_current_password", "Current password is incorrect")
    user.password_hash = hash_password(new)
    user.token_version += 1
    db.commit()


def request_password_reset(db: Session, email: str) -> None:
    user = db.scalar(select(User).where(User.email == email.lower(), User.is_active.is_(True)))
    if user is None:
        return
    smtp = db.scalar(
        select(SMTPConfiguration).where(
            SMTPConfiguration.organization_id == user.organization_id,
            SMTPConfiguration.is_enabled.is_(True),
        )
    )
    if smtp is None:
        return
    token = create_token(
        user.id,
        "password_reset",
        timedelta(minutes=30),
        {"version": user.token_version},
    )
    link = f"{settings.public_app_url.rstrip('/')}/reset-password?token={token}"
    send_email(
        smtp,
        user.email,
        "Reset your Upcode sprint password",
        f"Use this link within 30 minutes to reset your password:\n\n{link}",
    )


def reset_password(db: Session, token: str, new_password: str) -> None:
    try:
        payload = decode_token(token, "password_reset")
    except jwt.InvalidTokenError as exc:
        raise APIError(
            400, "invalid_reset_token", "The password reset link is invalid or expired"
        ) from exc
    user = db.get(User, payload.get("sub"))
    if user is None or not user.is_active or payload.get("version") != user.token_version:
        raise APIError(400, "invalid_reset_token", "The password reset link is invalid or expired")
    user.password_hash = hash_password(new_password)
    user.token_version += 1
    db.commit()
