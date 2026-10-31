import hashlib
import json
from datetime import UTC, datetime, timedelta

import pyotp
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.installation import installation_store
from app.core.rate_limit import limiter
from app.db import session
from app.main import app
from app.models.mcp import MCPKey

KEYS = "/api/v1/auth/mcp-keys"
MCP = "/api/v1/mcp"


@pytest.fixture
def base_client(tmp_path, monkeypatch):
    monkeypatch.setattr(installation_store, "path", tmp_path / "installation.json")
    monkeypatch.setattr(limiter, "enabled", False)
    monkeypatch.setattr(settings, "public_app_url", "http://testserver")
    for name in ("_engine", "_session_factory", "_database_url"):
        monkeypatch.setattr(session, name, None)
    password = "AdminPassword123"
    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/setup/complete",
                json={
                    "organization_name": "MCP test",
                    "database": {"engine": "sqlite", "sqlite_path": str(tmp_path / "sprint.db")},
                    "admin": {
                        "username": "admin",
                        "email": "admin@example.com",
                        "password": password,
                        "first_name": "Test",
                        "last_name": "Admin",
                    },
                },
            )
            assert response.status_code == 201, response.text
            assert (
                client.post(
                    "/api/v1/auth/login", json={"username": "admin", "password": password}
                ).status_code
                == 200
            )
            yield client, password, session.get_engine
    finally:
        if session._engine is not None:
            session._engine.dispose()


@pytest.fixture
def mcp_client(base_client):
    client, _, _ = base_client
    assert client.get("/api/v1/mcp-status").json() == {"enabled": False}
    response = client.put("/api/v1/settings/mcp", json={"enabled": True})
    assert response.status_code == 200, response.text
    return base_client


def create_key(client, password, scopes=None, **extra):
    response = client.post(
        KEYS,
        json={
            "name": "Test MCP client",
            "scopes": scopes or ["profile.read"],
            "password": password,
            **extra,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def rpc(client, key, method, params=None, *, headers=None, path=MCP):
    return client.post(
        path,
        json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": method,
            "params": params or {},
        },
        headers={
            "Authorization": "Bearer " + key,
            "Accept": "application/json, text/event-stream",
            "MCP-Protocol-Version": "2025-11-25",
            **(headers or {}),
        },
    )


def call(client, key, name, arguments=None):
    response = rpc(client, key, "tools/call", {"name": name, "arguments": arguments or {}})
    assert response.status_code == 200, response.text
    value = response.json()
    assert "result" in value, value
    return value["result"]["structuredContent"]


def test_key_is_hashed_and_only_shown_once(mcp_client):
    client, password, engine = mcp_client
    created = create_key(client, password)
    raw = created["key"]
    assert raw.startswith("sprint_mcp_")
    assert client.get(KEYS).headers["cache-control"] == "no-store"
    listed = client.get(KEYS).json()
    assert len(listed["keys"]) == 1
    assert raw not in json.dumps(listed)
    assert "digest" not in listed["keys"][0]
    with Session(engine()) as db:
        stored = db.scalar(select(MCPKey))
        assert stored.digest == hashlib.sha256(raw.encode()).hexdigest()
        assert stored.scopes == '["profile.read"]'


def test_official_protocol_and_sessionless_owner_identity(mcp_client):
    client, password, _ = mcp_client
    raw = create_key(client, password)["key"]
    client.cookies.clear()
    assert client.get("/api/v1/auth/me").status_code == 401
    response = rpc(
        client,
        raw,
        "initialize",
        {
            "protocolVersion": "2025-11-25",
            "capabilities": {},
            "clientInfo": {"name": "integration-test", "version": "1.0"},
        },
    )
    assert response.status_code == 200, response.text
    assert response.json()["result"]["serverInfo"]["name"] == "Upcode Sprint"
    tools = rpc(client, raw, "tools/list").json()
    assert [tool["name"] for tool in tools["result"]["tools"]] == ["get_current_user"]
    result = call(client, raw, "get_current_user")
    assert result["status"] == 200, result
    assert result["data"]["username"] == "admin"
    assert client.get("/api/v1/auth/me").status_code == 401


def test_cookie_or_query_string_cannot_authenticate_mcp(mcp_client):
    client, password, _ = mcp_client
    raw = create_key(client, password)["key"]
    response = client.post(MCP, json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
    assert response.status_code == 401
    assert "Bearer" in response.headers["www-authenticate"]
    assert rpc(client, "wrong", "tools/list").status_code == 401
    assert rpc(client, raw, "tools/list", path=MCP + "?access_token=" + raw).status_code == 400
    assert (
        rpc(client, raw, "tools/list", headers={"Origin": "https://untrusted.example"}).status_code
        == 403
    )
    assert rpc(client, raw, "tools/list", headers={"Host": "untrusted.example"}).status_code == 403


def test_revocation_and_expiry_are_checked_on_every_request(mcp_client):
    client, password, engine = mcp_client
    created = create_key(client, password)
    raw, key_id = created["key"], created["record"]["id"]
    assert rpc(client, raw, "tools/list").status_code == 200
    assert client.delete(KEYS + "/" + key_id).status_code == 200
    assert rpc(client, raw, "tools/list").status_code == 401
    created = create_key(client, password)
    with Session(engine()) as db:
        db.get(MCPKey, created["record"]["id"]).expires_at = datetime.now(UTC) - timedelta(
            seconds=1
        )
        db.commit()
    assert rpc(client, created["key"], "tools/list").status_code == 401


def test_key_scopes_cannot_be_expanded_by_arguments(mcp_client):
    client, password, _ = mcp_client
    raw = create_key(client, password)["key"]
    result = call(client, raw, "create_project", {"payload": {"name": "Denied", "key": "denied"}})
    assert result["status"] == 403, result
    response = client.post(
        KEYS,
        json={
            "name": "Forged owner",
            "password": password,
            "scopes": ["profile.read"],
            "user_id": "other",
        },
    )
    assert response.status_code == 422
    assert call(client, raw, "create_mcp_key")["status"] == 404
    assert call(client, raw, "api_request", {"path": "/users", "method": "POST"})["status"] == 404


def test_password_change_invalidates_existing_mcp_keys(mcp_client):
    client, password, _ = mcp_client
    raw = create_key(client, password)["key"]
    response = client.post(
        "/api/v1/auth/change-password",
        json={
            "current_password": password,
            "password": "ChangedPassword123",
        },
    )
    assert response.status_code == 200, response.text
    assert rpc(client, raw, "tools/list").status_code == 401
    assert (
        client.post(
            "/api/v1/auth/login",
            json={
                "username": "admin",
                "password": "ChangedPassword123",
            },
        ).status_code
        == 200
    )
    assert client.get(KEYS).json()["keys"][0]["status"] == "credentials_changed"


def test_creation_requires_password_and_enrolled_second_factor(mcp_client):
    client, password, _ = mcp_client
    original = create_key(client, password)["key"]
    setup = client.post("/api/v1/auth/2fa/setup", json={"password": password}).json()
    enabled = client.post(
        "/api/v1/auth/2fa/enable",
        json={
            "password": password,
            "code": pyotp.TOTP(setup["secret"]).now(),
        },
    )
    assert enabled.status_code == 200, enabled.text
    assert rpc(client, original, "tools/list").status_code == 401
    codes = enabled.json()["recovery_codes"]
    assert client.get(KEYS).json()["requires_two_factor"] is True
    payload = {"name": "Proof test", "password": password, "scopes": ["profile.read"]}
    assert client.post(KEYS, json=payload).status_code == 401
    assert (
        client.post(
            KEYS,
            json={
                **payload,
                "password": "wrong",
                "two_factor_code": codes[0],
            },
        ).status_code
        == 401
    )
    raw = create_key(client, password, two_factor_code=codes[0])["key"]
    assert rpc(client, raw, "tools/list").status_code == 200
    assert (
        client.post(
            KEYS,
            json={
                **payload,
                "two_factor_code": codes[0],
            },
        ).status_code
        == 401
    )

    assert (
        client.post(
            "/api/v1/auth/2fa/disable",
            json={
                "password": password,
                "code": codes[1],
            },
        ).status_code
        == 200
    )
    assert rpc(client, raw, "tools/list").status_code == 401

    assert rpc(client, original, "tools/list").status_code == 401


def test_unknown_scopes_and_invalid_expiration_are_rejected(mcp_client):
    client, password, _ = mcp_client
    payload = {"name": "Rejected", "password": password, "scopes": ["*"]}
    assert client.post(KEYS, json=payload).status_code == 422
    assert client.post(KEYS, json={**payload, "scopes": []}).status_code == 422
    for days in (0, -1, 366):
        assert (
            client.post(
                KEYS,
                json={
                    **payload,
                    "scopes": ["profile.read"],
                    "expires_in_days": days,
                },
            ).status_code
            == 422
        )
    assert client.get(KEYS).json()["keys"] == []


def test_every_tool_has_a_closed_valid_input_schema():
    from app.mcp_tools import TOOLS

    for tool in TOOLS:
        schema = tool.definition().input_schema
        assert schema["additionalProperties"] is False
        assert "user_id" not in schema.get("properties", {})


def checked(response, status=201):
    assert response.status_code == status, response.text
    return response.json()


@pytest.fixture
def projects(mcp_client):
    admin, _password, engine = mcp_client
    permissions = [
        "projects.view",
        "projects.edit",
        "projects.delete",
        "kanban.view",
        "kanban.manage",
        "documents.view",
        "documents.create",
        "documents.edit",
        "documents.delete",
        "scrum.view",
        "scrum.manage",
    ]
    role = checked(
        admin.post(
            "/api/v1/roles",
            json={
                "name": "MCP Writer",
                "permission_keys": permissions,
            },
        )
    )
    alice = checked(
        admin.post(
            "/api/v1/users",
            json={
                "username": "alice",
                "email": "alice@example.com",
                "first_name": "Alice",
                "last_name": "Reader",
                "password": "AlicePassword123",
                "role_ids": [role["id"]],
            },
        )
    )
    team = checked(
        admin.post("/api/v1/teams", json={"name": "Alice team", "member_ids": [alice["id"]]})
    )
    own = checked(
        admin.post(
            "/api/v1/projects",
            json={
                "name": "Accessible project",
                "key": "own",
                "team_ids": [team["id"]],
            },
        )
    )
    foreign = checked(
        admin.post(
            "/api/v1/projects",
            json={
                "name": "Foreign secret project",
                "key": "secret",
                "team_ids": [],
            },
        )
    )
    foreign_task = checked(
        admin.post(
            f"/api/v1/projects/{foreign['id']}/tasks",
            json={
                "title": "Foreign secret task",
            },
        )
    )
    foreign_doc = checked(
        admin.post(
            f"/api/v1/projects/{foreign['id']}/documents",
            json={
                "title": "Foreign secret document",
                "slug": "secret",
                "markdown_content": "do not leak this content",
            },
        )
    )
    foreign_sprint = checked(
        admin.post(
            f"/api/v1/projects/{foreign['id']}/sprints",
            json={
                "name": "Foreign secret sprint",
            },
        )
    )
    own_task = checked(
        admin.post(
            f"/api/v1/projects/{own['id']}/tasks",
            json={
                "title": "Allowed task",
                "description": "Keep this description",
                "priority": "high",
                "assignee_id": alice["id"],
            },
        )
    )
    other = TestClient(app)
    checked(
        other.post(
            "/api/v1/auth/login",
            json={
                "username": "alice",
                "password": "AlicePassword123",
            },
        ),
        200,
    )
    key = create_key(other, "AlicePassword123", ["profile.read", *permissions])
    try:
        yield {
            "admin": admin,
            "alice": other,
            "alice_id": alice["id"],
            "engine": engine,
            "role_id": role["id"],
            "team_id": team["id"],
            "permissions": permissions,
            "own": own["id"],
            "foreign": foreign["id"],
            "key": key["key"],
            "own_task": own_task["id"],
            "task": foreign_task["id"],
            "doc": foreign_doc["id"],
            "sprint": foreign_sprint["id"],
        }
    finally:
        other.close()


def test_project_lists_and_identity_follow_key_owner_even_with_admin_cookie(projects):
    ctx = projects
    result = call(ctx["admin"], ctx["key"], "list_projects")
    assert result["status"] == 200, result
    assert [item["id"] for item in result["data"]["items"]] == [ctx["own"]]
    assert call(ctx["admin"], ctx["key"], "get_current_user")["data"]["username"] == "alice"


def test_foreign_projects_and_all_nested_resources_are_denied(projects):
    ctx = projects
    project_id = ctx["foreign"]
    requests = [
        ("get_project", {}),
        ("get_project_overview", {}),
        ("get_project_activity", {}),
        ("list_tasks", {}),
        ("get_task", {"task_id": ctx["task"]}),
        ("list_task_comments", {"task_id": ctx["task"]}),
        ("list_documents", {}),
        ("get_document", {"document_id": ctx["doc"]}),
        ("list_sprints", {}),
        ("update_project", {"payload": {"name": "Intrusion"}}),
        ("delete_project", {}),
        ("create_task", {"payload": {"title": "Intrusion"}}),
        ("update_task", {"task_id": ctx["task"], "payload": {"title": "Intrusion"}}),
        ("delete_task", {"task_id": ctx["task"]}),
        ("comment_on_task", {"task_id": ctx["task"], "payload": {"body": "Intrusion"}}),
        ("create_document", {"payload": {"title": "Intrusion", "slug": "intrusion"}}),
        ("update_document", {"document_id": ctx["doc"], "payload": {"title": "Intrusion"}}),
        ("delete_document", {"document_id": ctx["doc"]}),
        ("create_sprint", {"payload": {"name": "Intrusion"}}),
        ("update_sprint", {"sprint_id": ctx["sprint"], "payload": {"name": "Intrusion"}}),
        ("start_sprint", {"sprint_id": ctx["sprint"]}),
        (
            "complete_sprint",
            {"sprint_id": ctx["sprint"], "payload": {"incomplete_action": "backlog"}},
        ),
        ("cancel_sprint", {"sprint_id": ctx["sprint"]}),
    ]
    for name, arguments in requests:
        result = call(ctx["admin"], ctx["key"], name, {"project_id": project_id, **arguments})
        assert result["status"] == 404, (name, result)
        assert "secret" not in json.dumps(result).lower(), (name, result)
    assert (
        ctx["admin"].get(f"/api/v1/projects/{project_id}").json()["name"]
        == "Foreign secret project"
    )


def test_foreign_object_ids_cannot_be_reparented_to_accessible_project(projects):
    ctx = projects
    for name, arguments in [
        ("get_task", {"task_id": ctx["task"]}),
        ("update_task", {"task_id": ctx["task"], "payload": {"title": "Intrusion"}}),
        ("delete_task", {"task_id": ctx["task"]}),
        ("comment_on_task", {"task_id": ctx["task"], "payload": {"body": "Intrusion"}}),
        ("get_document", {"document_id": ctx["doc"]}),
        ("update_document", {"document_id": ctx["doc"], "payload": {"title": "Intrusion"}}),
        ("update_sprint", {"sprint_id": ctx["sprint"], "payload": {"name": "Intrusion"}}),
    ]:
        result = call(ctx["admin"], ctx["key"], name, {"project_id": ctx["own"], **arguments})
        assert result["status"] == 404, (name, result)


def test_allowed_task_updates_preserve_unspecified_fields(projects):
    ctx = projects
    result = call(
        ctx["admin"],
        ctx["key"],
        "update_task",
        {
            "project_id": ctx["own"],
            "task_id": ctx["own_task"],
            "payload": {"title": "Changed via MCP"},
        },
    )
    assert result["status"] == 200, result
    assert result["data"]["description"] == "Keep this description"
    assert result["data"]["priority"] == "high"
    assert result["data"]["assignee"]["id"] == ctx["alice_id"]


def test_membership_and_permission_removal_apply_to_existing_keys(projects):
    ctx = projects
    assert (
        call(ctx["admin"], ctx["key"], "get_project", {"project_id": ctx["own"]})["status"] == 200
    )
    checked(
        ctx["admin"].patch(
            f"/api/v1/roles/{ctx['role_id']}",
            json={
                "permission_keys": [
                    value for value in ctx["permissions"] if value != "kanban.manage"
                ],
            },
        ),
        200,
    )
    result = call(
        ctx["admin"],
        ctx["key"],
        "update_task",
        {
            "project_id": ctx["own"],
            "task_id": ctx["own_task"],
            "payload": {"title": "Denied"},
        },
    )
    assert result["status"] == 403, result
    tools = rpc(ctx["admin"], ctx["key"], "tools/list").json()["result"]["tools"]
    assert "update_task" not in [tool["name"] for tool in tools]
    checked(ctx["admin"].put(f"/api/v1/teams/{ctx['team_id']}/members", json={"ids": []}), 200)
    assert (
        call(ctx["admin"], ctx["key"], "get_project", {"project_id": ctx["own"]})["status"] == 404
    )
    assert call(ctx["admin"], ctx["key"], "list_projects")["data"]["items"] == []


def test_regular_user_cannot_mint_admin_or_unowned_permissions(projects):
    ctx = projects
    response = ctx["alice"].post(
        KEYS,
        json={
            "name": "Overgrant",
            "password": "AlicePassword123",
            "scopes": ["projects.create"],
        },
    )
    assert response.status_code == 403
    assert (
        ctx["alice"]
        .post(
            KEYS,
            json={
                "name": "Admin",
                "password": "AlicePassword123",
                "scopes": ["settings.manage"],
            },
        )
        .status_code
        == 422
    )
    admin_key = create_key(ctx["admin"], "AdminPassword123")
    assert ctx["alice"].delete(KEYS + "/" + admin_key["record"]["id"]).status_code == 404
    assert admin_key["record"]["id"] not in {
        key["id"] for key in ctx["alice"].get(KEYS).json()["keys"]
    }


def test_promoting_owner_does_not_add_new_scopes_to_existing_key(projects):
    ctx = projects
    readonly = create_key(ctx["alice"], "AlicePassword123", ["projects.view", "kanban.view"])["key"]
    # The account can already write, but this independently narrowed key cannot.
    result = call(
        ctx["admin"],
        readonly,
        "update_task",
        {
            "project_id": ctx["own"],
            "task_id": ctx["own_task"],
            "payload": {"title": "Denied"},
        },
    )
    assert result["status"] == 403, result


def test_inactive_key_owner_cannot_use_active_administrator_cookie(projects):
    ctx = projects
    checked(ctx["admin"].patch(f"/api/v1/users/{ctx['alice_id']}", json={"is_active": False}), 200)
    assert rpc(ctx["admin"], ctx["key"], "tools/list").status_code == 401


@pytest.mark.parametrize("mode", ["auto", "legacy"])
def test_official_sdk_client_over_http_with_bearer_key(mcp_client, mode):
    import asyncio

    import httpx2
    from mcp import Client
    from mcp.client.streamable_http import streamable_http_client

    client, password, _ = mcp_client
    raw = create_key(client, password)["key"]

    def transport(request):
        response = client.request(
            request.method,
            str(request.url),
            content=request.content,
            headers=dict(request.headers),
        )
        return httpx2.Response(
            response.status_code, headers=response.headers, content=response.content
        )

    async def exercise():
        async with (
            httpx2.AsyncClient(
                transport=httpx2.MockTransport(transport),
                headers={"Authorization": "Bearer " + raw},
            ) as http,
            Client(
                streamable_http_client("http://testserver" + MCP, http_client=http),
                mode=mode,
                cache=None,
            ) as sdk,
        ):
            tools = await sdk.list_tools()
            assert [tool.name for tool in tools.tools] == ["get_current_user"]
            result = await sdk.call_tool("get_current_user", {})
            assert not result.is_error
            assert result.structured_content["data"]["username"] == "admin"

    asyncio.run(exercise())


def test_mcp_migration_preserves_existing_users(tmp_path):
    from sqlalchemy import create_engine, inspect, text

    from app.db.migrations import upgrade_database

    url = f"sqlite:///{tmp_path / 'legacy-mcp.db'}"
    engine = create_engine(url)
    with engine.begin() as connection:
        connection.execute(
            text(
                "CREATE TABLE users (id VARCHAR(36) PRIMARY KEY, "
                "password_hash VARCHAR(255) NOT NULL)"
            )
        )
        connection.execute(
            text(
                "INSERT INTO users (id, password_hash) VALUES "
                "('00000000-0000-4000-8000-000000000001', 'existing-hash')"
            )
        )
        connection.execute(
            text("CREATE TABLE alembic_version (version_num VARCHAR(32) PRIMARY KEY)")
        )
        connection.execute(text("INSERT INTO alembic_version VALUES ('20261031_0011')"))
    upgrade_database(url)
    with engine.connect() as connection:
        assert connection.scalar(text("SELECT password_hash FROM users")) == "existing-hash"
        assert connection.scalar(text("SELECT COUNT(*) FROM mcp_keys")) == 0
        foreign_keys = inspect(connection).get_foreign_keys("mcp_keys")
        assert foreign_keys[0]["referred_table"] == "users"
        assert foreign_keys[0]["constrained_columns"] == ["user_id"]
    engine.dispose()


def test_mcp_is_disabled_by_default_and_cannot_generate_keys(base_client):
    client, password, _ = base_client
    assert client.get("/api/v1/mcp-status").json() == {"enabled": False}
    assert rpc(client, "not-a-key", "tools/list").status_code == 404
    assert client.get(KEYS).status_code == 404
    assert (
        client.post(
            KEYS,
            json={
                "name": "Blocked while disabled",
                "password": password,
                "scopes": ["profile.read"],
            },
        ).status_code
        == 404
    )


def test_administrative_disable_blocks_existing_keys_and_creation(mcp_client):
    client, password, _ = mcp_client
    created = create_key(client, password)
    key = created["key"]
    assert rpc(client, key, "tools/list").status_code == 200
    assert client.put("/api/v1/settings/mcp", json={"enabled": False}).status_code == 200
    assert client.get("/api/v1/mcp-status").json() == {"enabled": False}
    assert rpc(client, key, "tools/list").status_code == 404
    assert client.get(KEYS).status_code == 404
    assert (
        client.post(
            KEYS,
            json={
                "name": "Denied",
                "password": password,
                "scopes": ["profile.read"],
            },
        ).status_code
        == 404
    )
    # Revocation remains available so disabling the feature never prevents cleanup.
    assert client.delete(KEYS + "/" + created["record"]["id"]).status_code == 200
    assert client.put("/api/v1/settings/mcp", json={"enabled": True}).status_code == 200
    assert rpc(client, key, "tools/list").status_code == 401


def test_setting_rejects_implicit_string_activation(base_client):
    client, _, _ = base_client
    assert client.put("/api/v1/settings/mcp", json={"enabled": "true"}).status_code == 422
    assert client.get("/api/v1/mcp-status").json() == {"enabled": False}


def test_regular_users_cannot_change_instance_mcp_setting(projects):
    ctx = projects
    assert ctx["alice"].put("/api/v1/settings/mcp", json={"enabled": False}).status_code == 403
    assert ctx["admin"].get("/api/v1/mcp-status").json() == {"enabled": True}
