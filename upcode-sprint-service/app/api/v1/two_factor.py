from urllib.parse import urlsplit

from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel, Field, SecretStr
from sqlalchemy.orm import Session

from app.api.dependencies import CurrentUser
from app.api.v1.auth import set_auth_cookies
from app.core.config import settings
from app.core.errors import APIError
from app.core.installation import installation_store
from app.core.rate_limit import limiter
from app.core.security import verify_password
from app.db.session import get_db
from app.mcp_keys import revoke_all
from app.services import two_factor_service as two_factor
from app.services.auth_service import issue_tokens

router = APIRouter(prefix="/auth/2fa", tags=["two-factor authentication"])


class PasswordProof(BaseModel):
    password: SecretStr = Field(min_length=1, max_length=256)


class FactorProof(PasswordProof):
    code: SecretStr = Field(min_length=1, max_length=32)


def prepare(db, user, payload):
    if not verify_password(payload.password.get_secret_value(), user.password_hash):
        raise APIError(401, "invalid_current_password", "Current password is incorrect")
    two_factor.lock_account(db, user)


def renew_session(db, user, response):
    revoke_all(db, user.id)
    user.token_version += 1
    db.commit()
    access, refresh = issue_tokens(user)
    set_auth_cookies(response, access, refresh)


@router.get("")
def status(user: CurrentUser):
    return two_factor.status(user)


@router.post("/setup")
@limiter.limit(settings.login_rate_limit)
def setup(
    request: Request, payload: PasswordProof, user: CurrentUser, db: Session = Depends(get_db)
):
    prepare(db, user, payload)
    result = two_factor.setup(
        user,
        f"{user.username}@{urlsplit(installation_store.public_app_url).netloc}",
        "Upcode Sprint",
        installation_store.encrypt,
    )
    db.commit()
    return result


@router.post("/enable")
@limiter.limit(settings.login_rate_limit)
def enable(
    request: Request,
    payload: FactorProof,
    response: Response,
    user: CurrentUser,
    db: Session = Depends(get_db),
):
    prepare(db, user, payload)
    codes = two_factor.enable(
        db,
        user,
        payload.code.get_secret_value(),
        installation_store.decrypt,
    )
    renew_session(db, user, response)
    return {"recovery_codes": codes}


@router.post("/disable")
@limiter.limit(settings.login_rate_limit)
def disable(
    request: Request,
    payload: FactorProof,
    response: Response,
    user: CurrentUser,
    db: Session = Depends(get_db),
):
    prepare(db, user, payload)
    two_factor.disable(db, user, payload.code.get_secret_value(), installation_store.decrypt)
    renew_session(db, user, response)
    return {"enabled": False}


@router.post("/recovery-codes")
@limiter.limit(settings.login_rate_limit)
def regenerate(
    request: Request,
    payload: FactorProof,
    response: Response,
    user: CurrentUser,
    db: Session = Depends(get_db),
):
    prepare(db, user, payload)
    codes = two_factor.regenerate(
        db,
        user,
        payload.code.get_secret_value(),
        installation_store.decrypt,
    )
    renew_session(db, user, response)
    return {"recovery_codes": codes}
