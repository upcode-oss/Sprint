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
    assert client.get(PATH + "/identity").json()["product"] == "sprint"
    app.dependency_overrides[get_current_user] = lambda: workspace["member"]
    assert client.get(PATH).status_code == 403
    assert client.get(PATH + "/identity").status_code == 403
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


def test_sprint_callback_url_is_saved_and_pending_pairing_can_retry(client, tmp_path, monkeypatch):
    from app import instance_link
    from app.core.installation import InstallationStore, installation_store
    from app.instance_link import PeerStatus

    client, _ = client
    monkeypatch.setattr(installation_store, "path", tmp_path / "installation.json")
    encrypted_database = installation_store.encrypt("sqlite:////data/sprint.db")
    installation_store.save({"setup_completed": True, "database_url_encrypted": encrypted_database})

    def unreachable(*args, **kwargs):
        raise HTTPException(502, "Cannot reach peer")

    monkeypatch.setattr(instance_link, "request_peer", unreachable)
    values = {
        "url": "http://192.168.122.45:3001",
        "callback_url": "http://192.168.122.45:3000/",
        "username": "admin",
        "password": "AdminPassword123",
    }
    assert client.post(PATH, json=values).status_code == 502
    assert installation_store.load()["database_url_encrypted"] == encrypted_database
    assert installation_store.is_complete
    assert InstallationStore(installation_store.path).public_app_url == "http://192.168.122.45:3000"
    assert client.get(PATH + "/identity").json()["url"] == "http://192.168.122.45:3000"
    connection_id = client.get(PATH).json()["connection_id"]

    def paired(url, method, path, **kwargs):
        assert kwargs["payload"]["identity"]["url"] == "http://192.168.122.45:3000"
        return PeerStatus(
            product="forge", name="Forge", url=url, connection_id=connection_id, state="connected"
        )

    monkeypatch.setattr(instance_link, "request_peer", paired)
    assert client.post(PATH, json=values).status_code == 200
    assert client.get(PATH).json()["connection_id"] == connection_id


def test_sprint_preserves_callback_failure_marker(client, monkeypatch):
    from app import instance_link

    client, _ = client

    def unreachable(*args, **kwargs):
        raise HTTPException(502, "Cannot reach initiating instance")

    monkeypatch.setattr(instance_link, "request_peer", unreachable)
    response = client.post(
        PATH + "/pair",
        json={
            "identity": {"product": "forge", "name": "Forge", "url": "https://forge.test"},
            "connection_id": str(uuid4()),
            "secret": "x" * 64,
            "username": "admin",
            "password": "AdminPassword123",
        },
    )
    assert response.status_code == 502
    assert response.headers["X-Instance-Link-Failure"] == "callback"
    assert (
        "Verification callback to https://forge.test failed" in response.json()["error"]["message"]
    )
