import asyncio
import base64
import hashlib
import json
import secrets
from datetime import UTC, datetime, timedelta
from urllib.parse import parse_qs, urlsplit

import pyotp
import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session
from test_mcp import KEYS, MCP, call, rpc
from test_mcp import base_client as base_client
from test_mcp import mcp_client as mcp_client

from app import mcp_oauth as oauth
from app.core.config import settings
from app.core.installation import installation_store
from app.models.identity import User
from app.models.mcp import MCPKey
from app.models.mcp_oauth import MCPOAuthClient, MCPOAuthCode, MCPOAuthRequest, MCPOAuthToken

ROOT = "/api/v1/oauth"
PUBLIC = "https://testserver"
RESOURCE = PUBLIC + MCP
CALLBACK = "https://chatgpt.com/connector_platform_oauth_redirect"


@pytest.fixture
def oauth_client(mcp_client, monkeypatch):
    monkeypatch.setattr(settings, "public_app_url", PUBLIC)
    stored = installation_store.load()
    installation_store.save({**stored, "public_app_url": PUBLIC})
    return mcp_client


def register(client, method="none", **extra):
    response = client.post(
        ROOT + "/register",
        json={
            "client_name": "ChatGPT",
            "redirect_uris": [CALLBACK],
            "token_endpoint_auth_method": method,
            "grant_types": ["authorization_code", "refresh_token"],
            "response_types": ["code"],
            "scope": "mcp",
            **extra,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def start(client, registration=None, **extra):
    registration = registration or register(client)
    verifier = secrets.token_urlsafe(48)
    challenge = (
        base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip("=")
    )
    params = {
        "client_id": registration["client_id"],
        "redirect_uri": CALLBACK,
        "response_type": "code",
        "code_challenge_method": "S256",
        "code_challenge": challenge,
        "state": "client-state",
        "scope": "mcp",
        "resource": RESOURCE,
        **extra,
    }
    response = client.get(ROOT + "/authorize", params=params, follow_redirects=False)
    assert response.status_code == 302, response.text
    request_id = parse_qs(urlsplit(response.headers["location"]).query)["request"][0]
    return registration, verifier, request_id


def approve(client, password, request_id, **extra):
    response = client.get(ROOT + "/consent/" + request_id)
    assert response.status_code == 200, response.text
    details = response.json()
    response = client.post(
        ROOT + "/consent/" + request_id,
        json={
            "approved": True,
            "csrf_token": details["csrf_token"],
            "scopes": ["profile.read"],
            "password": password,
            **extra,
        },
    )
    assert response.status_code == 200, response.text
    query = parse_qs(urlsplit(response.json()["redirect_uri"]).query)
    assert query["state"] == ["client-state"]
    assert query["iss"] == [PUBLIC + ROOT]
    return query["code"][0]


def exchange(client, registration, verifier, code, **extra):
    return client.post(
        ROOT + "/token",
        data={
            "grant_type": "authorization_code",
            "client_id": registration["client_id"],
            "client_secret": registration.get("client_secret") or "",
            "code": code,
            "code_verifier": verifier,
            "redirect_uri": CALLBACK,
            "resource": RESOURCE,
            **extra,
        },
    )


def connect(oauth_client, method="none"):
    client, password, _ = oauth_client
    registration, verifier, request_id = start(client, register(client, method))
    code = approve(client, password, request_id)
    response = exchange(client, registration, verifier, code)
    assert response.status_code == 200, response.text
    return registration, response.json()


def refresh(client, registration, raw, **extra):
    return client.post(
        ROOT + "/token",
        data={
            "grant_type": "refresh_token",
            "client_id": registration["client_id"],
            "client_secret": registration.get("client_secret") or "",
            "refresh_token": raw,
            "resource": RESOURCE,
            **extra,
        },
    )


def test_discovery_advertises_public_urls_pkce_and_authentication_challenge(oauth_client):
    client, _, _ = oauth_client
    metadata = client.get("/.well-known/oauth-protected-resource" + MCP)
    assert metadata.status_code == 200
    assert metadata.json()["resource"] == RESOURCE
    assert metadata.json()["authorization_servers"] == [PUBLIC + ROOT]
    auth = client.get("/.well-known/oauth-authorization-server" + ROOT).json()
    assert auth["issuer"] == PUBLIC + ROOT
    assert auth["authorization_endpoint"] == PUBLIC + ROOT + "/authorize"
    assert auth["token_endpoint"] == PUBLIC + ROOT + "/token"
    assert auth["registration_endpoint"] == PUBLIC + ROOT + "/register"
    assert auth["code_challenge_methods_supported"] == ["S256"]
    assert auth["authorization_response_iss_parameter_supported"] is True
    response = client.post(MCP, json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
    assert response.status_code == 401
    assert oauth.metadata_url() in response.headers["www-authenticate"]


@pytest.mark.parametrize("method", ["none", "client_secret_post", "client_secret_basic"])
def test_full_flow_keeps_owner_permissions_and_secrets_out_of_storage(oauth_client, method):
    client, password, engine = oauth_client
    registration, verifier, request_id = start(client, register(client, method))
    code = approve(client, password, request_id)
    if method == "client_secret_basic":
        response = client.post(
            ROOT + "/token",
            auth=(registration["client_id"], registration["client_secret"]),
            data={
                "grant_type": "authorization_code",
                "code": code,
                "code_verifier": verifier,
                "redirect_uri": CALLBACK,
                "resource": RESOURCE,
            },
        )
    else:
        response = exchange(client, registration, verifier, code)
    assert response.status_code == 200, response.text
    tokens = response.json()
    assert response.headers["cache-control"] == "no-store"
    assert tokens["scope"] == "mcp"
    assert 0 < tokens["expires_in"] <= 1800
    client.cookies.clear()
    assert (
        client.get(
            "/api/v1/auth/me", headers={"Authorization": "Bearer " + tokens["access_token"]}
        ).status_code
        == 401
    )
    assert call(client, tokens["access_token"], "get_current_user")["data"]["username"] == "admin"
    listed = rpc(client, tokens["access_token"], "tools/list").json()["result"]["tools"]
    assert [tool["name"] for tool in listed] == ["get_current_user"]
    assert listed[0]["_meta"]["securitySchemes"] == [{"type": "oauth2", "scopes": ["mcp"]}]
    assert rpc(client, tokens["refresh_token"], "tools/list").status_code == 401
    with Session(engine()) as db:
        grant = db.scalar(select(MCPKey))
        assert grant.name == "OAuth: ChatGPT"
        assert json.loads(grant.scopes) == ["profile.read"]
        stored = db.scalar(select(MCPOAuthClient))
        assert (
            registration.get("client_secret") not in stored.metadata_encrypted
            if registration.get("client_secret")
            else True
        )
        assert db.get(MCPOAuthCode, hashlib.sha256(code.encode()).hexdigest()) is not None
        for raw in [tokens["access_token"], tokens["refresh_token"]]:
            assert db.get(MCPOAuthToken, hashlib.sha256(raw.encode()).hexdigest()) is not None
        assert code not in db.scalar(select(MCPOAuthCode)).data
    assert (
        asyncio.run(oauth.SprintOAuthProvider().load_access_token(tokens["access_token"]))
        is not None
    )


def test_consent_requires_login_csrf_password_and_available_scopes(oauth_client):
    client, password, _ = oauth_client
    _, _, request_id = start(client)
    details = client.get(ROOT + "/consent/" + request_id).json()
    payload = {
        "approved": True,
        "csrf_token": details["csrf_token"],
        "password": password,
        "scopes": ["profile.read"],
    }
    assert (
        client.post(
            ROOT + "/consent/" + request_id, json={**payload, "csrf_token": "a" * 43}
        ).status_code
        == 403
    )
    assert (
        client.post(
            ROOT + "/consent/" + request_id, json={**payload, "scopes": ["auth.tokens.issue"]}
        ).status_code
        == 403
    )
    assert (
        client.post(
            ROOT + "/consent/" + request_id, json={**payload, "password": "wrong"}
        ).status_code
        == 401
    )
    assert (
        client.post(
            ROOT + "/consent/" + request_id,
            json=payload,
            headers={"Origin": "https://attacker.example"},
        ).status_code
        == 403
    )
    client.cookies.clear()
    assert client.get(ROOT + "/consent/" + request_id).status_code == 401
    assert client.post(ROOT + "/consent/" + request_id, json=payload).status_code == 401


def test_denial_does_not_issue_a_grant_or_code(oauth_client):
    client, _, engine = oauth_client
    _, _, request_id = start(client)
    details = client.get(ROOT + "/consent/" + request_id).json()
    response = client.post(
        ROOT + "/consent/" + request_id,
        json={"approved": False, "csrf_token": details["csrf_token"]},
    )
    assert response.status_code == 200
    query = parse_qs(urlsplit(response.json()["redirect_uri"]).query)
    assert query == {"error": ["access_denied"], "state": ["client-state"], "iss": [PUBLIC + ROOT]}
    with Session(engine()) as db:
        assert db.scalar(select(MCPKey)) is None
        assert db.scalar(select(MCPOAuthCode)) is None
    assert client.get(ROOT + "/consent/" + request_id).status_code == 410


@pytest.mark.parametrize("wrong", ["pkce", "resource", "client", "redirect"])
def test_authorization_code_cannot_be_exchanged_with_changed_bindings(oauth_client, wrong):
    client, password, _ = oauth_client
    registration, verifier, request_id = start(client)
    code = approve(client, password, request_id)
    overrides = {
        "pkce": {"code_verifier": "incorrect"},
        "resource": {"resource": "https://other.example/api/v1/mcp"},
        "client": {"client_id": register(client)["client_id"]},
        "redirect": {"redirect_uri": "https://attacker.example/callback"},
    }
    response = exchange(client, registration, verifier, code, **overrides[wrong])
    assert response.status_code == 400, response.text
    assert exchange(client, registration, verifier, code).status_code == 200


def test_codes_are_single_use_and_replay_revokes_issued_tokens(oauth_client):
    client, password, _ = oauth_client
    registration, verifier, request_id = start(client)
    code = approve(client, password, request_id)
    tokens = exchange(client, registration, verifier, code).json()
    assert exchange(client, registration, verifier, code).status_code == 400
    assert rpc(client, tokens["access_token"], "tools/list").status_code == 401


def test_refresh_rotation_replay_and_profile_revocation(oauth_client):
    client, _, _ = oauth_client
    registration, tokens = connect(oauth_client)
    response = refresh(client, registration, tokens["refresh_token"])
    assert response.status_code == 200, response.text
    rotated = response.json()
    assert rotated["refresh_token"] != tokens["refresh_token"]
    assert call(client, rotated["access_token"], "get_current_user")["status"] == 200
    assert refresh(client, registration, tokens["refresh_token"]).status_code == 400
    assert rpc(client, rotated["access_token"], "tools/list").status_code == 401
    registration, tokens = connect(oauth_client)
    grant = client.get(KEYS).json()["keys"][0]
    assert client.delete(KEYS + "/" + grant["id"]).status_code == 200
    assert rpc(client, tokens["access_token"], "tools/list").status_code == 401
    assert refresh(client, registration, tokens["refresh_token"]).status_code == 400


def test_token_expiry_and_oauth_revocation(oauth_client):
    client, _, engine = oauth_client
    registration, tokens = connect(oauth_client)
    with Session(engine()) as db:
        token = db.get(MCPOAuthToken, hashlib.sha256(tokens["access_token"].encode()).hexdigest())
        token.expires_at = datetime.now(UTC) - timedelta(seconds=1)
        db.commit()
    assert rpc(client, tokens["access_token"], "tools/list").status_code == 401
    response = client.post(
        ROOT + "/revoke",
        data={"client_id": registration["client_id"], "token": tokens["refresh_token"]},
    )
    assert response.status_code == 200, response.text
    assert refresh(client, registration, tokens["refresh_token"]).status_code == 400


def test_expired_consent_and_authorization_codes_cannot_be_used(oauth_client):
    client, password, engine = oauth_client
    _, _, request_id = start(client)
    with Session(engine()) as db:
        db.get(MCPOAuthRequest, hashlib.sha256(request_id.encode()).hexdigest()).expires_at = (
            datetime.now(UTC) - timedelta(seconds=1)
        )
        db.commit()
    assert client.get(ROOT + "/consent/" + request_id).status_code == 410
    registration, verifier, request_id = start(client)
    code = approve(client, password, request_id)
    with Session(engine()) as db:
        db.get(MCPOAuthCode, hashlib.sha256(code.encode()).hexdigest()).expires_at = datetime.now(
            UTC
        ) - timedelta(seconds=1)
        db.commit()
    assert exchange(client, registration, verifier, code).status_code == 400


def test_disabling_mcp_closes_discovery_and_existing_oauth_connections(oauth_client):
    client, _, _ = oauth_client
    registration, tokens = connect(oauth_client)
    assert client.put("/api/v1/settings/mcp", json={"enabled": False}).status_code == 200
    assert client.get("/.well-known/oauth-protected-resource").status_code == 404
    assert client.get("/.well-known/oauth-authorization-server").status_code == 404
    assert client.post(ROOT + "/register", json={}).status_code == 404
    assert rpc(client, tokens["access_token"], "tools/list").status_code == 404
    assert refresh(client, registration, tokens["refresh_token"]).status_code == 404


def test_registration_rejects_unsafe_callbacks_and_limits_request_bodies(oauth_client):
    client, _, _ = oauth_client
    for uri in [
        "https://example.com/#fragment",
        "https://user:secret@example.com/callback",
        "http://example.com/callback",
        "javascript:alert(1)",
    ]:
        response = client.post(ROOT + "/register", json={"redirect_uris": [uri]})
        assert response.status_code == 400, response.text
    response = client.post(
        ROOT + "/register", content=b"x" * 16385, headers={"Content-Type": "application/json"}
    )
    assert response.status_code == 413


def test_two_factor_is_required_before_issuing_an_oauth_grant(oauth_client):
    client, password, engine = oauth_client
    secret = pyotp.random_base32()
    with Session(engine()) as db:
        user = db.scalar(select(User).where(User.username == "admin"))
        user.mfa_secret_encrypted = installation_store.encrypt(secret)
        db.commit()
    registration, verifier, request_id = start(client)
    details = client.get(ROOT + "/consent/" + request_id).json()
    assert details["requires_two_factor"] is True
    response = client.post(
        ROOT + "/consent/" + request_id,
        json={
            "approved": True,
            "csrf_token": details["csrf_token"],
            "password": password,
            "scopes": ["profile.read"],
        },
    )
    assert response.status_code == 401
    with Session(engine()) as db:
        assert db.scalar(select(MCPKey)) is None
    code = approve(client, password, request_id, two_factor_code=pyotp.TOTP(secret).now())
    tokens = exchange(client, registration, verifier, code).json()
    assert call(client, tokens["access_token"], "get_current_user")["status"] == 200


@pytest.mark.parametrize("change", ["password", "two_factor", "inactive"])
def test_account_security_changes_invalidate_access_and_refresh_tokens(oauth_client, change):
    client, _, engine = oauth_client
    registration, tokens = connect(oauth_client)
    with Session(engine()) as db:
        user = db.scalar(select(User).where(User.username == "admin"))
        if change == "password":
            user.password_hash += "-changed"
        elif change == "two_factor":
            user.mfa_secret_encrypted = installation_store.encrypt(pyotp.random_base32())
        else:
            user.is_active = False
        db.commit()
    assert rpc(client, tokens["access_token"], "tools/list").status_code == 401
    assert refresh(client, registration, tokens["refresh_token"]).status_code == 400


def test_invalid_authorization_callbacks_never_receive_codes(oauth_client):
    client, _, _ = oauth_client
    registration = register(client)
    response = client.get(
        ROOT + "/authorize",
        params={
            "client_id": registration["client_id"],
            "redirect_uri": "https://attacker.example/callback",
            "response_type": "code",
            "code_challenge": "A" * 43,
            "scope": "mcp",
            "resource": RESOURCE,
        },
        follow_redirects=False,
    )
    assert response.status_code == 400
    assert "location" not in response.headers
    response = client.get(
        ROOT + "/authorize",
        params={
            "client_id": registration["client_id"],
            "redirect_uri": CALLBACK,
            "response_type": "code",
            "code_challenge": "A" * 43,
            "scope": "mcp",
            "resource": "https://attacker.example/mcp",
            "state": "check-state",
        },
        follow_redirects=False,
    )
    assert response.status_code == 302
    query = parse_qs(urlsplit(response.headers["location"]).query)
    assert query == {
        "state": ["check-state"],
        "error": ["invalid_target"],
        "error_description": ["Use this Sprint instance's MCP resource URL."],
        "iss": [PUBLIC + ROOT],
    }
