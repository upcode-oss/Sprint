from pathlib import Path

import pytest
from alembic.config import Config
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect, text

from alembic import command
from app.api.dependencies import get_current_user
from app.api.v1.settings import router
from app.core.errors import APIError, api_error_handler
from app.db.session import get_db


@pytest.fixture
def client(db, workspace):
    app = FastAPI()
    app.include_router(router)
    app.add_exception_handler(APIError, api_error_handler)
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: workspace["admin"]
    with TestClient(app) as client:
        yield client


def test_timezone_is_persisted_and_name_only_update_preserves_it(client, db, workspace):
    response = client.patch("/organization", json={"name": "Delivery", "timezone": "Europe/Vienna"})
    assert response.status_code == 200
    db.expire_all()
    assert workspace["organization"].timezone == "Europe/Vienna"
    assert client.get("/organization").json()["timezone"] == "Europe/Vienna"
    response = client.patch("/organization", json={"name": "Renamed"})
    assert response.status_code == 200
    assert response.json()["timezone"] == "Europe/Vienna"


@pytest.mark.parametrize("timezone", ["Mars/Olympus", "", None])
def test_invalid_timezone_does_not_change_organization(client, timezone):
    response = client.patch("/organization", json={"name": "Changed", "timezone": timezone})
    assert response.status_code == 422
    organization = client.get("/organization").json()
    assert organization["timezone"] == "UTC"
    assert organization["name"] == "Test Organization"


def test_member_can_read_timezones_but_cannot_change_organization(client, workspace):
    client.app.dependency_overrides[get_current_user] = lambda: workspace["member"]
    response = client.get("/settings/timezones")
    assert response.status_code == 200
    assert {"UTC", "Europe/Vienna", "Asia/Kathmandu"} <= set(response.json())
    response = client.patch("/organization", json={"name": "Changed", "timezone": "Europe/Vienna"})
    assert response.status_code == 403
    assert client.get("/organization").json()["timezone"] == "UTC"


@pytest.mark.parametrize("legacy_schema", [True, False])
def test_timezone_migration_preserves_existing_organization(tmp_path, legacy_schema):
    backend = Path(__file__).resolve().parents[1]
    config = Config(str(backend / "alembic.ini"))
    config.set_main_option("script_location", str(backend / "alembic"))
    url = f"sqlite:///{tmp_path / 'timezone.db'}"
    config.set_main_option("sqlalchemy.url", url)
    command.upgrade(config, "20260830_0008")
    engine = create_engine(url)
    with engine.begin() as connection:
        # The initial migration uses current model metadata, so simulate the
        # older schema explicitly as well as checking a fresh installation.
        if legacy_schema:
            connection.execute(text("ALTER TABLE organizations DROP COLUMN timezone"))
        connection.execute(
            text(
                "INSERT INTO organizations (id, name, created_at, updated_at) "
                "VALUES ('legacy', 'Existing Organization', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
            )
        )
    command.upgrade(config, "head")
    with engine.connect() as connection:
        assert connection.execute(text("SELECT name, timezone FROM organizations")).one() == (
            "Existing Organization",
            "UTC",
        )
    command.downgrade(config, "20260830_0008")
    with engine.connect() as connection:
        assert "timezone" not in {
            column["name"] for column in inspect(connection).get_columns("organizations")
        }
        assert connection.scalar(text("SELECT name FROM organizations")) == "Existing Organization"
    engine.dispose()
