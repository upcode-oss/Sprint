import pytest
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.api import dependencies
from app.api.v1 import auth, setup
from app.core.errors import APIError, api_error_handler, validation_error_handler
from app.core.installation import InstallationStore
from app.core.rate_limit import limiter
from app.db import session
from app.models.identity import Organization, SMTPConfiguration, User
from app.services import mail_service, setup_service


@pytest.fixture
def setup_client(tmp_path, monkeypatch):
    store = InstallationStore(tmp_path / "installation.json", secret="setup-test-" + "x" * 40)
    for module in (setup, setup_service, session, dependencies):
        monkeypatch.setattr(module, "installation_store", store)
    for name in ("_engine", "_session_factory", "_database_url"):
        monkeypatch.setattr(session, name, None)
    monkeypatch.setattr(limiter, "enabled", False)

    def unexpected_email(*args, **kwargs):
        pytest.fail("Setup with SMTP disabled must not send email")

    monkeypatch.setattr(mail_service, "send_email", unexpected_email)
    monkeypatch.setattr(setup, "send_test_email", unexpected_email)
    app = FastAPI()
    app.state.limiter = limiter
    app.add_exception_handler(APIError, api_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.include_router(setup.router, prefix="/api/v1")
    app.include_router(auth.router, prefix="/api/v1")
    payload = {
        "organization_name": "Optional Email Sprint",
        "organization_logo_token": None,
        "database": {"engine": "sqlite", "sqlite_path": str(tmp_path / "sprint.db")},
        "admin": {
            "username": "admin",
            "email": "admin@example.com",
            "password": "AdminPassword123",
            "first_name": "Ada",
            "last_name": "Admin",
        },
    }
    try:
        with TestClient(app) as client:
            yield client, payload, store
    finally:
        if session._engine is not None:
            session._engine.dispose()


@pytest.mark.parametrize(
    "smtp",
    [
        "omitted",
        None,
        {"enabled": False},
        {
            "enabled": False,
            "host": "",
            "port": 587,
            "username": "",
            "password": "",
            "encryption": "starttls",
            "from_address": "",
            "from_name": "",
        },
        {
            "enabled": False,
            "host": "stale-host",
            "port": 0,
            "encryption": "invalid",
            "from_address": "invalid email",
            "from_name": "",
        },
    ],
)
def test_complete_setup_without_smtp_creates_login_and_no_email_configuration(setup_client, smtp):
    client, payload, store = setup_client
    if smtp != "omitted":
        payload["smtp"] = smtp
    response = client.post("/api/v1/setup/complete", json=payload)
    assert response.status_code == 201, response.text
    assert response.json()["completed"] is True
    assert store.is_complete
    assert client.get("/api/v1/setup/status").json() == {
        "completed": True,
        "organization_name": payload["organization_name"],
    }
    with session.get_session_factory()() as db:
        assert db.scalar(select(func.count(Organization.id))) == 1
        assert db.scalar(select(func.count(User.id))) == 1
        assert db.scalar(select(func.count(SMTPConfiguration.id))) == 0
    login = client.post(
        "/api/v1/auth/login",
        json={
            "username": "admin",
            "password": "AdminPassword123",
        },
    )
    assert login.status_code == 200, login.text
    assert client.get("/api/v1/auth/me").json()["username"] == "admin"


def test_enabled_smtp_still_requires_valid_configuration(setup_client):
    client, payload, store = setup_client
    payload["smtp"] = {"enabled": True, "from_address": ""}
    response = client.post("/api/v1/setup/complete", json=payload)
    assert response.status_code == 422
    assert "smtp.from_address" in response.json()["error"]["fields"]
    assert not store.is_complete


@pytest.mark.parametrize(
    "field,value",
    [
        ("password", "longlowercasepassword"),
        ("username", "invalid username"),
        ("email", "invalid-email"),
    ],
)
def test_setup_validation_identifies_the_actual_admin_field(setup_client, field, value):
    client, payload, store = setup_client
    payload["smtp"] = None
    payload["admin"][field] = value
    response = client.post("/api/v1/setup/complete", json=payload)
    assert response.status_code == 422
    errors = response.json()["error"]["fields"]
    assert f"admin.{field}" in errors
    assert all(not path.startswith("smtp") for path in errors)
    if field == "password":
        assert value not in response.text
    assert not store.is_complete
