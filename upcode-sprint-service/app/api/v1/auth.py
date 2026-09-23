from fastapi import APIRouter, Cookie, Depends, Request, Response
from sqlalchemy.orm import Session

from app.api.dependencies import CurrentUser, require_setup_completed
from app.core.config import settings
from app.core.errors import APIError
from app.core.rate_limit import limiter
from app.db.session import get_db
from app.schemas.common import MessageResponse
from app.schemas.identity import (
    AuthUserResponse,
    ForgotPasswordRequest,
    LoginRequest,
    PasswordChange,
    ProfileUpdate,
    ResetPasswordRequest,
    TokenResponse,
    UserResponse,
)
from app.services.auth_service import (
    authenticate,
    change_password,
    issue_tokens,
    refresh_access_token,
    request_password_reset,
    reset_password,
)
from app.services.permission_service import effective_permission_keys
from app.services.profile_service import update_profile as update_user_profile

router = APIRouter(prefix="/auth", tags=["auth"], dependencies=[Depends(require_setup_completed)])


def set_auth_cookies(response: Response, access: str, refresh: str) -> None:
    shared = {
        "httponly": True,
        "secure": settings.cookie_secure,
        "samesite": "strict",
        "path": "/",
    }
    response.set_cookie(
        "sprint_access", access, max_age=settings.access_token_minutes * 60, **shared
    )
    response.set_cookie(
        "sprint_refresh", refresh, max_age=settings.refresh_token_days * 86400, **shared
    )


@router.post("/login", response_model=TokenResponse)
@limiter.limit(settings.login_rate_limit)
def login(
    request: Request,
    payload: LoginRequest,
    response: Response,
    db: Session = Depends(get_db),
) -> TokenResponse:
    del request
    user = authenticate(db, payload.username, payload.password.get_secret_value())
    access, refresh = issue_tokens(user)
    set_auth_cookies(response, access, refresh)
    return TokenResponse(access_token=access, expires_in=settings.access_token_minutes * 60)


@router.post("/refresh", response_model=TokenResponse)
def refresh(
    response: Response,
    sprint_refresh: str | None = Cookie(default=None),
    db: Session = Depends(get_db),
) -> TokenResponse:
    if not sprint_refresh:
        raise APIError(401, "invalid_refresh_token", "The session has expired")
    _, access, refresh_value = refresh_access_token(db, sprint_refresh)
    set_auth_cookies(response, access, refresh_value)
    return TokenResponse(access_token=access, expires_in=settings.access_token_minutes * 60)


@router.post("/logout", response_model=MessageResponse)
def logout(response: Response, user: CurrentUser, db: Session = Depends(get_db)) -> MessageResponse:
    user.token_version += 1
    db.commit()
    response.delete_cookie("sprint_access", path="/")
    response.delete_cookie("sprint_refresh", path="/")
    return MessageResponse(message="Logged out")


@router.get("/me", response_model=AuthUserResponse)
def me(user: CurrentUser) -> AuthUserResponse:
    data = UserResponse.model_validate(user).model_dump()
    data.update({"bio": user.bio, "timezone": user.timezone, "locale": user.locale})
    data["permissions"] = sorted(effective_permission_keys(user))
    return AuthUserResponse.model_validate(data)


@router.patch("/me", response_model=AuthUserResponse)
def update_profile(
    payload: ProfileUpdate, user: CurrentUser, db: Session = Depends(get_db)
) -> AuthUserResponse:
    update_user_profile(db, user, payload)
    return me(user)


@router.post("/change-password", response_model=MessageResponse)
def update_password(
    payload: PasswordChange, user: CurrentUser, db: Session = Depends(get_db)
) -> MessageResponse:
    change_password(
        db,
        user,
        payload.current_password.get_secret_value(),
        payload.password.get_secret_value(),
    )
    return MessageResponse(message="Password changed; other sessions were revoked")


@router.post("/forgot-password", response_model=MessageResponse)
def forgot_password(
    payload: ForgotPasswordRequest, db: Session = Depends(get_db)
) -> MessageResponse:
    request_password_reset(db, str(payload.email))
    return MessageResponse(message="If the account exists, a reset email has been sent")


@router.post("/reset-password", response_model=MessageResponse)
def reset(payload: ResetPasswordRequest, db: Session = Depends(get_db)) -> MessageResponse:
    reset_password(db, payload.token, payload.password.get_secret_value())
    return MessageResponse(message="Password reset successfully")
