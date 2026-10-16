from uuid import uuid4

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from app.api.dependencies import get_current_user
from app.api.v1.integrations import router
from app.core.errors import APIError, api_error_handler
from app.core.rate_limit import limiter
from app.db.session import get_db
from app.models.integration import InstanceConnection

PATH = "/api/v1/integrations/instance"


@pytest.fixture
def client(db, workspace):
    app = FastAPI()
    app.state.limiter = limiter
    app.add_exception_handler(APIError, api_error_handler)
    app.include_router(router, prefix="/api/v1")
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: workspace["admin"]
    with TestClient(app) as client:
        yield client, app


def test_sprint_settings_permission(client, workspace):
    client, app = client
    assert client.get(PATH).status_code == 200
    assert client.get(PATH).json() is None
    app.dependency_overrides[get_current_user] = lambda: workspace["member"]
    assert client.get(PATH).status_code == 403
    assert client.delete(PATH + "?force=true").status_code == 403
    assert client.post(PATH + "/test").status_code == 403


def test_sprint_pair_requires_remote_settings_permission(client):
    client, _ = client
    response = client.post(
        PATH + "/pair",
        json={
            "identity": {"product": "forge", "name": "Forge", "url": "https://forge.test"},
            "connection_id": str(uuid4()),
            "secret": "x" * 64,
            "username": "member",
            "password": "MemberPassword123",
        },
    )
    assert response.status_code == 403
    assert client.get(PATH).json() is None


def test_sprint_credentials_checked_before_callback(client):
    client, _ = client
    response = client.post(
        PATH + "/pair",
        json={
            "identity": {"product": "forge", "name": "Forge", "url": "https://forge.test"},
            "connection_id": str(uuid4()),
            "secret": "x" * 64,
            "username": "admin",
            "password": "wrong-password",
        },
    )
    assert response.status_code == 401
    assert "wrong-password" not in response.text


def test_sprint_pair_encrypts_key_and_uses_organization_identity(client, db, monkeypatch):
    from app import instance_link
    from app.core.installation import installation_store
    from app.instance_link import PeerStatus

    client, _ = client
    connection_id = str(uuid4())
    secret = "x" * 64
    identity = {"product": "forge", "name": "Test Forge", "url": "https://forge.test"}

    def remote(url, method, path, **kwargs):
        assert url == identity["url"]
        assert method == "GET" and path == "/peer"
        assert kwargs["secret"] == secret
        return PeerStatus(**identity, connection_id=connection_id, state="pending")

    monkeypatch.setattr(instance_link, "request_peer", remote)
    response = client.post(
        PATH + "/pair",
        json={
            "identity": identity,
            "connection_id": connection_id,
            "secret": secret,
            "username": "admin",
            "password": "AdminPassword123",
        },
    )
    assert response.status_code == 200, response.text
    assert response.json()["product"] == "sprint"
    assert response.json()["name"] == "Test Organization"
    assert response.json()["state"] == "connected"
    row = db.get(InstanceConnection, 1)
    assert row.secret_encrypted != secret
    assert installation_store.decrypt(row.secret_encrypted) == secret
    assert secret not in client.get(PATH).text


def test_sprint_connection_errors_stay_in_api_error_format(client, monkeypatch):
    from app import instance_link

    client, _ = client

    def unreachable(*args, **kwargs):
        raise HTTPException(502, "Cannot verify the other instance")

    monkeypatch.setattr(instance_link, "request_peer", unreachable)
    response = client.post(
        PATH,
        json={
            "url": "https://forge.test",
            "username": "admin",
            "password": "AdminPassword123",
        },
    )
    assert response.status_code == 502
    assert response.json()["error"]["message"] == "Cannot verify the other instance"
