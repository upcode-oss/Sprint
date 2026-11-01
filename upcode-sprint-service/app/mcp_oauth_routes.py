"""OAuth discovery, SDK protocol handlers, and authenticated user consent."""

import base64
import json
import secrets
from datetime import timedelta
from urllib.parse import unquote

from fastapi import APIRouter, Depends, Request, Response
from mcp.server.auth.handlers.authorize import AuthorizationHandler
from mcp.server.auth.handlers.register import RegistrationHandler
from mcp.server.auth.handlers.revoke import RevocationHandler
from mcp.server.auth.handlers.token import TokenHandler
from mcp.server.auth.middleware.client_auth import ClientAuthenticator
from mcp.server.auth.provider import AuthorizationCode, construct_redirect_uri
from mcp.server.auth.routes import build_metadata, validate_issuer_url
from mcp.server.auth.settings import ClientRegistrationOptions, RevocationOptions
from mcp.server.transport_security import RequestBodyLimitMiddleware
from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field, SecretStr
from sqlalchemy import update
from starlette.datastructures import FormData
from starlette.responses import JSONResponse

from app import mcp_keys
from app import mcp_oauth as oauth
from app.api.dependencies import CurrentUser, DBSession, require_setup_completed
from app.core.config import settings
from app.core.errors import APIError
from app.core.installation import installation_store
from app.core.rate_limit import limiter
from app.core.security import verify_password
from app.models.mcp import MCPKey
from app.models.mcp_oauth import MCPOAuthClient, MCPOAuthCode, MCPOAuthRequest
from app.services import two_factor_service as two_factor

router = APIRouter(
    prefix="/oauth", tags=["MCP OAuth"], dependencies=[Depends(require_setup_completed)]
)
discovery_router = APIRouter(
    tags=["MCP OAuth discovery"], dependencies=[Depends(require_setup_completed)]
)
registration = ClientRegistrationOptions(
    enabled=True, valid_scopes=oauth.SCOPES, default_scopes=oauth.SCOPES
)
client_auth = ClientAuthenticator(oauth.provider)


class OAuthBodyLimitMiddleware:
    def __init__(self, app):
        self.app = app
        self.limited = RequestBodyLimitMiddleware(app, 16384)

    async def __call__(self, scope, receive, send):
        app = self.limited if scope.get("path", "").startswith("/api/v1/oauth/") else self.app
        await app(scope, receive, send)


def enabled(db):
    mcp_keys.require_enabled(db)
    validate_issuer_url(AnyHttpUrl(oauth.issuer()))


def no_store(response):
    response.headers["Cache-Control"] = "no-store"
    response.headers["Pragma"] = "no-cache"
    response.headers["Referrer-Policy"] = "no-referrer"
    return response


@discovery_router.get("/.well-known/oauth-authorization-server")
@discovery_router.get("/.well-known/oauth-authorization-server/api/v1/oauth")
@router.get("/.well-known/oauth-authorization-server")
def authorization_metadata(db: DBSession):
    enabled(db)
    metadata = build_metadata(
        AnyHttpUrl(oauth.issuer()), None, registration, RevocationOptions(enabled=True)
    )
    return no_store(
        JSONResponse(
            {
                **metadata.model_dump(mode="json", exclude_none=True),
                "authorization_response_iss_parameter_supported": True,
                "token_endpoint_auth_methods_supported": [
                    "none",
                    "client_secret_post",
                    "client_secret_basic",
                ],
            },
            headers={"Access-Control-Allow-Origin": "*"},
        )
    )


@discovery_router.get("/.well-known/oauth-protected-resource")
@discovery_router.get("/.well-known/oauth-protected-resource/api/v1/mcp")
def resource_metadata(db: DBSession):
    enabled(db)
    return no_store(
        JSONResponse(
            {
                "resource": oauth.resource(),
                "authorization_servers": [oauth.issuer()],
                "scopes_supported": oauth.SCOPES,
                "bearer_methods_supported": ["header"],
                "resource_name": "Upcode Sprint MCP",
            },
            headers={"Access-Control-Allow-Origin": "*"},
        )
    )


@router.post("/register")
@limiter.limit("10/hour")
async def register_client(request: Request, db: DBSession):
    enabled(db)
    return no_store(await RegistrationHandler(oauth.provider, registration).handle(request))


@router.api_route("/authorize", methods=["GET", "POST"])
@limiter.limit("30/minute")
async def authorize(request: Request, db: DBSession):
    enabled(db)
    response = await AuthorizationHandler(oauth.provider).handle(request)
    location = response.headers.get("Location")
    if location and not location.startswith(oauth.origin() + "/oauth/authorize?"):
        # RFC 9207 issuer identification also applies to OAuth error redirects.
        response.headers["Location"] = construct_redirect_uri(location, iss=oauth.issuer())
    return no_store(response)


async def normalize_client_form(request):
    form = dict(await request.form())
    # The SDK expects client_id in the form, including for HTTP Basic clients.
    if "client_id" not in form and request.headers.get("authorization", "").startswith("Basic "):
        try:
            value = base64.b64decode(request.headers["authorization"][6:], validate=True).decode()
            form["client_id"] = unquote(value.split(":", 1)[0])
        except (ValueError, UnicodeDecodeError):
            pass  # The SDK returns invalid_client for malformed authentication.
    form.setdefault("client_secret", "")
    request._form = FormData(form)
    return form


@router.post("/token")
@limiter.limit("30/minute")
async def token(request: Request, db: DBSession):
    enabled(db)
    form = await normalize_client_form(request)
    if form.get("resource") != oauth.resource():
        return no_store(
            JSONResponse(
                {
                    "error": "invalid_target",
                    "error_description": "Use this instance's MCP resource URL.",
                },
                status_code=400,
            )
        )
    return no_store(await TokenHandler(oauth.provider, client_auth).handle(request))


@router.post("/revoke")
@limiter.limit("30/minute")
async def revoke(request: Request, db: DBSession):
    enabled(db)
    await normalize_client_form(request)
    return no_store(await RevocationHandler(oauth.provider, client_auth).handle(request))


def pending_request(db, request_id):
    pending = (
        db.get(MCPOAuthRequest, mcp_keys.digest(request_id)) if len(request_id) <= 128 else None
    )
    if pending is None or pending.consumed_at or not oauth.valid_until(pending.expires_at):
        raise APIError(
            410,
            "oauth_request_expired",
            "This connection request expired. Start again in your MCP client.",
        )
    return pending


@router.get("/consent/{request_id}")
def consent_details(request_id: str, user: CurrentUser, db: DBSession, response: Response):
    enabled(db)
    no_store(response)
    pending = pending_request(db, request_id)
    client = db.get(MCPOAuthClient, pending.client_id)
    metadata = json.loads(installation_store.decrypt(client.metadata_encrypted))
    csrf = secrets.token_urlsafe(32)
    pending.user_id, pending.csrf_digest = user.id, mcp_keys.digest(csrf)
    db.commit()
    allowed = mcp_keys.available_scopes(db, user)
    return {
        "client_name": metadata.get("client_name") or "MCP client",
        "redirect_uri": json.loads(pending.data)["redirect_uri"],
        "username": user.username,
        "csrf_token": csrf,
        "requires_two_factor": bool(user.mfa_secret_encrypted),
        "expires_in_days": oauth.GRANT_DAYS,
        "permissions": [
            {"scope": scope, "description": description}
            for scope, description in mcp_keys.SCOPE_DESCRIPTIONS.items()
            if scope in allowed
        ],
    }


class ConsentDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")
    approved: bool = Field(strict=True)
    csrf_token: str = Field(min_length=43, max_length=43)
    scopes: list[str] = Field(default_factory=list, max_length=32)
    password: SecretStr | None = Field(default=None, max_length=256)
    two_factor_code: SecretStr | None = Field(default=None, max_length=32)


@router.post("/consent/{request_id}")
@limiter.limit(settings.login_rate_limit)
def consent(
    request: Request,
    request_id: str,
    payload: ConsentDecision,
    user: CurrentUser,
    db: DBSession,
    response: Response,
):
    enabled(db)
    no_store(response)
    if request.headers.get("origin") not in {None, oauth.origin()}:
        raise APIError(403, "oauth_consent_invalid", "Untrusted consent origin.")
    pending = pending_request(db, request_id)
    if pending.user_id != user.id or not secrets.compare_digest(
        pending.csrf_digest or "", mcp_keys.digest(payload.csrf_token)
    ):
        raise APIError(403, "oauth_consent_invalid", "Reload the authorization page and try again.")
    params = json.loads(pending.data)
    if payload.approved:
        scopes = set(payload.scopes)
        if not scopes or not scopes.issubset(mcp_keys.available_scopes(db, user)):
            raise APIError(
                403, "oauth_scope_invalid", "Select permissions available to your account."
            )
        if not payload.password or not verify_password(
            payload.password.get_secret_value(), user.password_hash
        ):
            mcp_keys.fail(401, "Current password is incorrect.")
        two_factor.lock_account(db, user)
        if user.mfa_secret_encrypted:
            if not payload.two_factor_code:
                mcp_keys.fail(401, "Enter an authenticator code or an unused recovery code.")
            two_factor.verify_code(
                db, user, payload.two_factor_code.get_secret_value(), installation_store.decrypt
            )
    consumed = db.execute(
        update(MCPOAuthRequest)
        .where(
            MCPOAuthRequest.digest == pending.digest,
            MCPOAuthRequest.user_id == user.id,
            MCPOAuthRequest.csrf_digest == mcp_keys.digest(payload.csrf_token),
            MCPOAuthRequest.consumed_at.is_(None),
            MCPOAuthRequest.expires_at > mcp_keys.now(),
        )
        .values(consumed_at=mcp_keys.now())
        .execution_options(synchronize_session=False)
    )
    if consumed.rowcount != 1:
        raise APIError(
            410, "oauth_request_expired", "Start a new connection request in your MCP client."
        )
    redirect = {"state": params.get("state"), "iss": oauth.issuer()}
    if payload.approved:
        client = db.get(MCPOAuthClient, pending.client_id)
        metadata = json.loads(installation_store.decrypt(client.metadata_encrypted))
        grant = MCPKey(
            user_id=user.id,
            name=("OAuth: " + (metadata.get("client_name") or "MCP client"))[:100],
            digest=mcp_keys.digest(secrets.token_urlsafe(32)),
            scopes=json.dumps(sorted(scopes)),
            password_digest=mcp_keys.credential_digest(user),
            expires_at=mcp_keys.now() + timedelta(days=oauth.GRANT_DAYS),
        )
        db.add(grant)
        db.flush()
        raw = secrets.token_urlsafe(32)
        expiry = mcp_keys.now() + timedelta(minutes=2)
        code = AuthorizationCode(
            code=raw,
            scopes=oauth.SCOPES,
            expires_at=expiry.timestamp(),
            client_id=pending.client_id,
            code_challenge=params["code_challenge"],
            redirect_uri=params["redirect_uri"],
            redirect_uri_provided_explicitly=params["redirect_uri_provided_explicitly"],
            resource=params["resource"],
            subject=user.id,
        )
        db.add(
            MCPOAuthCode(
                digest=mcp_keys.digest(raw),
                client_id=pending.client_id,
                key_id=grant.id,
                data=code.model_dump_json(exclude={"code"}),
                expires_at=expiry,
            )
        )
        redirect["code"] = raw
    else:
        redirect["error"] = "access_denied"
    db.commit()
    return {"redirect_uri": construct_redirect_uri(params["redirect_uri"], **redirect)}
