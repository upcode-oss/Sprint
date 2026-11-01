"""MCP SDK OAuth provider backed by persistent, revocable personal grants."""

import json
import re
import secrets
from contextlib import contextmanager
from datetime import UTC, timedelta
from urllib.parse import parse_qs, urlencode, urlsplit

from mcp.server.auth.provider import (
    AccessToken,
    AuthorizationCode,
    AuthorizeError,
    RefreshToken,
    RegistrationError,
    TokenError,
)
from mcp.shared.auth import OAuthClientInformationFull, OAuthToken
from sqlalchemy import delete, update

from app import mcp_keys
from app.core.errors import APIError
from app.core.installation import installation_store
from app.db.session import get_db
from app.models.mcp import MCPKey
from app.models.mcp_oauth import MCPOAuthClient, MCPOAuthCode, MCPOAuthRequest, MCPOAuthToken

ACCESS_PREFIX = "sprint_oauth_access_"
REFRESH_PREFIX = "sprint_oauth_refresh_"
ACCESS_SECONDS = 1800
GRANT_DAYS = 90
SCOPES = ["mcp"]


def origin():
    return installation_store.public_app_url.rstrip("/")


def issuer():
    return origin() + "/api/v1/oauth"


def resource():
    return origin() + "/api/v1/mcp"


def metadata_url():
    return origin() + "/.well-known/oauth-protected-resource/api/v1/mcp"


def valid_until(value):
    return value.replace(tzinfo=UTC) > mcp_keys.now()


def authenticate(db, raw, *, touch=False):
    if len(raw) > 128 or not raw.startswith(ACCESS_PREFIX):
        mcp_keys.fail(401, "A valid MCP OAuth access token is required.")
    token = db.get(MCPOAuthToken, mcp_keys.digest(raw))
    if (
        token is None
        or token.kind != "access"
        or token.consumed_at is not None
        or not valid_until(token.expires_at)
        or token.resource != resource()
    ):
        mcp_keys.fail(401, "The MCP OAuth token is invalid, expired, or revoked.")
    return mcp_keys.authenticate_record(db, db.get(MCPKey, token.key_id), touch=touch)


class SprintOAuthProvider:
    async def get_client(self, client_id):
        if len(client_id) > 128:
            return None
        with contextmanager(get_db)() as db:
            record = db.get(MCPOAuthClient, client_id)
            if record is None:
                return None
            return OAuthClientInformationFull.model_validate_json(
                installation_store.decrypt(record.metadata_encrypted)
            )

    async def register_client(self, client_info):
        if not client_info.redirect_uris or len(client_info.redirect_uris) > 10:
            raise RegistrationError("invalid_redirect_uri", "Register 1 to 10 redirect URIs.")
        for uri in client_info.redirect_uris:
            parsed = urlsplit(str(uri))
            if (
                len(str(uri)) > 2048
                or parsed.fragment
                or parsed.username
                or parsed.password
                or {"code", "state", "error", "iss"}.intersection(parse_qs(parsed.query))
                or not parsed.hostname
                or not (
                    parsed.scheme == "https"
                    or (
                        parsed.scheme == "http"
                        and parsed.hostname in {"localhost", "127.0.0.1", "::1"}
                    )
                )
            ):
                raise RegistrationError(
                    "invalid_redirect_uri", "Use HTTPS or an HTTP loopback URI."
                )
        if not set(client_info.grant_types).issubset({"authorization_code", "refresh_token"}):
            raise RegistrationError("invalid_client_metadata", "Unsupported grant type.")
        if client_info.response_types != ["code"] or len(client_info.client_name or "") > 100:
            raise RegistrationError(
                "invalid_client_metadata", "Invalid client name or response type."
            )
        if client_info.token_endpoint_auth_method not in {
            "none",
            "client_secret_post",
            "client_secret_basic",
        }:
            raise RegistrationError("invalid_client_metadata", "Unsupported client authentication.")
        with contextmanager(get_db)() as db:
            mcp_keys.require_enabled(db)
            db.add(
                MCPOAuthClient(
                    id=client_info.client_id,
                    metadata_encrypted=installation_store.encrypt(client_info.model_dump_json()),
                )
            )
            db.commit()

    async def authorize(self, client, params):
        if params.resource != resource():
            raise AuthorizeError("invalid_target", "Use this Sprint instance's MCP resource URL.")
        if set(params.scopes or []) != set(SCOPES):
            raise AuthorizeError("invalid_scope", "Request the mcp scope.")
        if not re.fullmatch(r"[A-Za-z0-9_-]{43}", params.code_challenge):
            raise AuthorizeError("invalid_request", "A valid S256 PKCE challenge is required.")
        raw = secrets.token_urlsafe(32)
        with contextmanager(get_db)() as db:
            mcp_keys.require_enabled(db)
            # Requests expire quickly; opportunistically remove abandoned consent requests.
            db.execute(
                delete(MCPOAuthRequest)
                .where(MCPOAuthRequest.expires_at < mcp_keys.now())
                .execution_options(synchronize_session=False)
            )
            db.add(
                MCPOAuthRequest(
                    digest=mcp_keys.digest(raw),
                    client_id=client.client_id,
                    data=params.model_dump_json(),
                    expires_at=mcp_keys.now() + timedelta(minutes=10),
                )
            )
            db.commit()
        return origin() + "/oauth/authorize?" + urlencode({"request": raw})

    async def load_authorization_code(self, client, authorization_code):
        if len(authorization_code) > 128:
            return None
        with contextmanager(get_db)() as db:
            record = db.get(MCPOAuthCode, mcp_keys.digest(authorization_code))
            if record is None or record.client_id != client.client_id:
                return None
            if record.consumed_at is not None:
                grant = db.get(MCPKey, record.key_id)
                grant.revoked_at = mcp_keys.now()
                db.commit()
                return None
            if not valid_until(record.expires_at):
                return None
            return AuthorizationCode.model_validate(
                {"code": authorization_code, **json.loads(record.data)}
            )

    def issue_tokens(self, db, client_id, key_id):
        grant = db.get(MCPKey, key_id)
        try:
            mcp_keys.authenticate_record(db, grant)
        except APIError as exc:
            raise TokenError("invalid_grant", "The authorization is no longer valid.") from exc
        access = ACCESS_PREFIX + secrets.token_urlsafe(32)
        refresh = REFRESH_PREFIX + secrets.token_urlsafe(32)
        access_expiry = min(
            mcp_keys.now() + timedelta(seconds=ACCESS_SECONDS),
            grant.expires_at.replace(tzinfo=UTC),
        )
        for raw, kind, expiry in [
            (access, "access", access_expiry),
            (refresh, "refresh", grant.expires_at),
        ]:
            db.add(
                MCPOAuthToken(
                    digest=mcp_keys.digest(raw),
                    kind=kind,
                    client_id=client_id,
                    key_id=key_id,
                    resource=resource(),
                    expires_at=expiry,
                )
            )
        db.commit()
        return OAuthToken(
            access_token=access,
            token_type="Bearer",
            expires_in=max(1, int((access_expiry - mcp_keys.now()).total_seconds())),
            refresh_token=refresh,
            scope="mcp",
        )

    async def exchange_authorization_code(self, client, authorization_code):
        with contextmanager(get_db)() as db:
            record = db.get(MCPOAuthCode, mcp_keys.digest(authorization_code.code))
            if (
                record is None
                or record.client_id != client.client_id
                or authorization_code.resource != resource()
            ):
                raise TokenError("invalid_grant", "Invalid authorization code.")
            consumed = db.execute(
                update(MCPOAuthCode)
                .where(
                    MCPOAuthCode.digest == record.digest,
                    MCPOAuthCode.consumed_at.is_(None),
                    MCPOAuthCode.expires_at > mcp_keys.now(),
                )
                .values(consumed_at=mcp_keys.now())
                .execution_options(synchronize_session=False)
            )
            if consumed.rowcount != 1:
                raise TokenError("invalid_grant", "Authorization code was already used or expired.")
            return self.issue_tokens(db, client.client_id, record.key_id)

    async def load_refresh_token(self, client, refresh_token):
        if len(refresh_token) > 128 or not refresh_token.startswith(REFRESH_PREFIX):
            return None
        with contextmanager(get_db)() as db:
            record = db.get(MCPOAuthToken, mcp_keys.digest(refresh_token))
            if record is None or record.kind != "refresh" or record.client_id != client.client_id:
                return None
            if record.consumed_at is not None:
                # Reusing a rotated refresh token revokes the complete authorization family.
                grant = db.get(MCPKey, record.key_id)
                grant.revoked_at = mcp_keys.now()
                db.commit()
                return None
            if not valid_until(record.expires_at) or record.resource != resource():
                return None
            try:
                user, _, _ = mcp_keys.authenticate_record(db, db.get(MCPKey, record.key_id))
            except APIError:
                return None
            return RefreshToken(
                token=refresh_token,
                client_id=client.client_id,
                scopes=SCOPES,
                expires_at=int(record.expires_at.replace(tzinfo=UTC).timestamp()),
                resource=record.resource,
                subject=user.id,
            )

    async def exchange_refresh_token(self, client, refresh_token, scopes):
        if scopes != SCOPES:
            raise TokenError("invalid_scope", "Request the mcp scope.")
        with contextmanager(get_db)() as db:
            record = db.get(MCPOAuthToken, mcp_keys.digest(refresh_token.token))
            if (
                record is None
                or record.client_id != client.client_id
                or record.resource != resource()
            ):
                raise TokenError("invalid_grant", "Invalid refresh token.")
            consumed = db.execute(
                update(MCPOAuthToken)
                .where(
                    MCPOAuthToken.digest == record.digest,
                    MCPOAuthToken.kind == "refresh",
                    MCPOAuthToken.consumed_at.is_(None),
                    MCPOAuthToken.expires_at > mcp_keys.now(),
                )
                .values(consumed_at=mcp_keys.now())
                .execution_options(synchronize_session=False)
            )
            if consumed.rowcount != 1:
                raise TokenError("invalid_grant", "Refresh token was already used or expired.")
            return self.issue_tokens(db, client.client_id, record.key_id)

    async def load_access_token(self, token):
        with contextmanager(get_db)() as db:
            try:
                user, _, _ = authenticate(db, token)
            except APIError:
                return None
            record = db.get(MCPOAuthToken, mcp_keys.digest(token))
            return AccessToken(
                token=token,
                client_id=record.client_id,
                scopes=SCOPES,
                expires_at=int(record.expires_at.replace(tzinfo=UTC).timestamp()),
                resource=record.resource,
                subject=user.id,
                claims={"iss": issuer()},
            )

    async def revoke_token(self, token):
        with contextmanager(get_db)() as db:
            record = db.get(MCPOAuthToken, mcp_keys.digest(token.token))
            if record is not None:
                grant = db.get(MCPKey, record.key_id)
                grant.revoked_at = mcp_keys.now()
                db.commit()


provider = SprintOAuthProvider()
