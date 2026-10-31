from fastapi import APIRouter, Request
from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator

from app import mcp_keys
from app.api.dependencies import CurrentUser, DBSession
from app.core.config import settings
from app.core.installation import installation_store
from app.core.rate_limit import limiter
from app.core.security import verify_password
from app.services import two_factor_service as two_factor

router = APIRouter(prefix="/auth/mcp-keys", tags=["personal MCP keys"])


class KeyCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=100)
    scopes: list[str] = Field(min_length=1, max_length=32)
    expires_in_days: int = Field(default=90, ge=1, le=365)
    password: SecretStr = Field(min_length=1, max_length=256)
    two_factor_code: SecretStr | None = Field(default=None, max_length=32)

    @field_validator("name")
    @classmethod
    def name_not_blank(cls, value):
        if not value.strip():
            raise ValueError("Enter a key name.")
        return value.strip()


@router.get("")
def keys(user: CurrentUser, db: DBSession):
    allowed = mcp_keys.available_scopes(db, user)
    return {
        "keys": mcp_keys.list_keys(db, user),
        "permissions": [
            {"scope": scope, "description": description}
            for scope, description in mcp_keys.SCOPE_DESCRIPTIONS.items()
            if scope in allowed
        ],
        "requires_two_factor": bool(user.mfa_secret_encrypted),
    }


@router.post("", status_code=201)
@limiter.limit(settings.login_rate_limit)
def create(request: Request, payload: KeyCreate, user: CurrentUser, db: DBSession):
    del request
    if not verify_password(payload.password.get_secret_value(), user.password_hash):
        mcp_keys.fail(401, "Current password is incorrect.")
    two_factor.lock_account(db, user)
    if user.mfa_secret_encrypted:
        if not payload.two_factor_code:
            mcp_keys.fail(401, "Enter an authenticator code or an unused recovery code.")
        two_factor.verify_code(
            db,
            user,
            payload.two_factor_code.get_secret_value(),
            installation_store.decrypt,
        )
    return mcp_keys.create_key(
        db,
        user,
        payload.name,
        payload.scopes,
        payload.expires_in_days,
    )


@router.delete("/{key_id}")
def revoke(key_id: str, user: CurrentUser, db: DBSession):
    return mcp_keys.revoke_key(db, user, key_id)
