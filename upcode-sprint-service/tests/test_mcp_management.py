import json

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session
from test_mcp import KEYS, call, checked, create_key, rpc
from test_mcp import base_client as base_client
from test_mcp import mcp_client as mcp_client
from test_mcp import projects as projects
from test_mcp_oauth import approve, exchange, start
from test_mcp_oauth import oauth_client as oauth_client

from app.core.installation import installation_store
from app.core.security import verify_password
from app.mcp_tools import SCOPE_DESCRIPTIONS, TOOLS
from app.models.identity import Organization, Role, SMTPConfiguration, User
from app.models.project import Team
from app.permissions.catalog import ALL_PERMISSIONS

SCOPES = sorted(SCOPE_DESCRIPTIONS)
WINDOW = {"start": "2027-01-01T00:00:00Z", "end": "2027-01-02T00:00:00Z"}
SCHEDULE = {"start": "2027-01-01T10:00:00Z", "end": "2027-01-01T11:00:00Z"}


def grant(client, password, kind, scopes):
    if kind == "personal":
        return create_key(client, password, scopes)["key"]
    registration, verifier, request_id = start(client)
    code = approve(client, password, request_id, scopes=scopes)
    response = exchange(client, registration, verifier, code)
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


@pytest.fixture(params=["personal", "oauth"])
def management(oauth_client, request):
    client, password, engine = oauth_client
    raw = grant(client, password, request.param, SCOPES)

    def use(name, arguments=None, status=200):
        result = call(client, raw, name, arguments)
        assert result["status"] == status, (name, result)
        return result["data"]

    return client, password, engine, raw, use, request.param


def test_all_application_permissions_have_explicit_mcp_tools():
    assert set(SCOPE_DESCRIPTIONS) == {str(key) for key in ALL_PERMISSIONS} | {"profile.read"}
    assert len(TOOLS) == len({tool.name for tool in TOOLS})
    assert all(
        not tool.path.startswith(("/auth/", "/setup", "/oauth/"))
        for tool in TOOLS
        if tool.name != "get_current_user"
    )


def test_full_permission_grants_are_available_only_after_explicit_consent(management):
    client, _, _, raw, use, _ = management
    assert len(SCOPES) > 32
    names = {tool["name"] for tool in rpc(client, raw, "tools/list").json()["result"]["tools"]}
    assert names == {tool.name for tool in TOOLS}
    assert {permission["key"] for permission in use("list_permissions")} == {
        str(key) for key in ALL_PERMISSIONS
    }
    listed = client.get(KEYS).json()["keys"]
    assert set(listed[0]["scopes"]) == set(SCOPES)
    assert raw not in json.dumps(listed)


def test_user_role_team_and_project_administration_preserves_secrets_and_guards(management):
    _, _, engine, _, use, _ = management
    owner_id = use("get_current_user")["id"]
    role = use(
        "create_role",
        {"payload": {"name": "MCP managed role", "permission_keys": ["calendar.view"]}},
        201,
    )
    assert use("get_role", {"role_id": role["id"]})["name"] == role["name"]
    role = use(
        "update_role",
        {
            "role_id": role["id"],
            "payload": {
                "description": "Edited through MCP",
                "permission_keys": ["calendar.view", "projects.view"],
            },
        },
    )
    assert {permission["key"] for permission in role["permissions"]} == {
        "calendar.view",
        "projects.view",
    }
    admin_role = next(
        role for role in use("list_roles") if role["is_system"] and role["name"] == "Admin"
    )
    use("delete_role", {"role_id": admin_role["id"]}, 409)
    use("update_role", {"role_id": admin_role["id"], "payload": {"permission_keys": []}}, 409)

    initial_password = "McpCreatedPassword123"
    user = use(
        "create_user",
        {
            "payload": {
                "username": "mcp-created",
                "email": "mcp-created@example.com",
                "first_name": "MCP",
                "last_name": "Created",
                "password": initial_password,
                "role_ids": [role["id"]],
            }
        },
        201,
    )
    target = {"target_user_id": user["id"]}
    assert initial_password not in json.dumps(user)
    with Session(engine()) as db:
        assert verify_password(initial_password, db.get(User, user["id"]).password_hash)
    assert any(
        item["id"] == user["id"] for item in use("list_users", {"search": "mcp-created"})["items"]
    )
    updated = use("update_user", {**target, "payload": {"last_name": "Edited"}})
    assert updated["last_name"] == "Edited"
    assert use("get_user", target)["id"] == user["id"]
    profile = use(
        "update_user_profile",
        {**target, "payload": {"bio": "Profile through MCP", "job_title": "Tester"}},
    )
    assert profile["bio"] == "Profile through MCP"
    assert use("get_user_profile", target)["job_title"] == "Tester"
    use("delete_user_avatar", target)

    contact = use(
        "create_user_contact",
        {
            **target,
            "payload": {
                "type": "email",
                "label": "Private",
                "value": "private@example.com",
                "visibility": "private",
            },
        },
        201,
    )
    assert use("list_user_contacts", target)[0]["id"] == contact["id"]
    changed = use(
        "update_user_contact",
        {**target, "contact_id": contact["id"], "payload": {"label": "Changed"}},
    )
    assert changed["label"] == "Changed"
    use(
        "update_user_contact",
        {
            "target_user_id": owner_id,
            "contact_id": contact["id"],
            "payload": {"label": "Wrong owner"},
        },
        404,
    )
    use("delete_user_contact", {**target, "contact_id": contact["id"]})
    assert use("list_user_contacts", target) == []
    presence = use(
        "update_user_presence",
        {**target, "payload": {"status": "do_not_disturb", "status_message": "Testing MCP"}},
    )
    assert presence["manual_status"] == "do_not_disturb"
    assert use("get_user_presence", target)["status_message"] == "Testing MCP"

    team = use(
        "create_team", {"payload": {"name": "MCP managed team", "member_ids": [user["id"]]}}, 201
    )
    assert any(
        item["id"] == team["id"] for item in use("list_teams", {"search": "MCP managed"})["items"]
    )
    assert use("get_team", {"team_id": team["id"]})["members"][0]["id"] == user["id"]
    assert (
        use("update_team", {"team_id": team["id"], "payload": {"description": "MCP team"}})[
            "description"
        ]
        == "MCP team"
    )
    project = use(
        "create_project",
        {"payload": {"name": "MCP managed project", "key": "MCPTEAM", "team_ids": [team["id"]]}},
        201,
    )
    assert [
        member["id"] for member in use("get_project_members", {"project_id": project["id"]})
    ] == [user["id"]]
    use("set_project_teams", {"project_id": project["id"], "payload": {"ids": []}})
    assert use("get_project_members", {"project_id": project["id"]}) == []
    use("set_project_teams", {"project_id": project["id"], "payload": {"ids": [team["id"]]}})
    use("set_team_members", {"team_id": team["id"], "payload": {"ids": []}})
    assert use("get_project_members", {"project_id": project["id"]}) == []
    use("delete_project", {"project_id": project["id"]})
    use("delete_team", {"team_id": team["id"]})
    use("delete_role", {"role_id": role["id"]})
    use("delete_user", target)
    with Session(engine()) as db:
        assert db.get(User, user["id"]).is_active is False
    use("delete_user", {"target_user_id": owner_id}, 409)
    use("update_user", {"target_user_id": owner_id, "payload": {"role_ids": []}}, 409)
    assert use("get_current_user")["id"] == owner_id


def test_calendar_and_meeting_workflows_include_time_filters_and_partial_edits(management):
    _, _, _, _, use, _ = management
    event = use(
        "create_calendar_event",
        {"payload": {"title": "MCP event", "scope_type": "personal", **SCHEDULE}},
        201,
    )
    event_id = {"event_id": event["id"]}
    assert use("get_calendar_event", event_id)["title"] == "MCP event"
    event = use("update_calendar_event", {**event_id, "payload": {"start": "2027-01-01T10:15:00Z"}})
    assert "10:15:00" in event["start"]
    use("update_calendar_event", {**event_id, "payload": {"end": "2027-01-01T09:00:00Z"}}, 422)
    eligible = use("list_meeting_participants", {"scope_type": "personal"})
    assert len(eligible) == 1
    meeting = use(
        "create_meeting",
        {
            "payload": {
                "title": "MCP meeting",
                "scope_type": "personal",
                "participant_ids": [eligible[0]["id"]],
                **SCHEDULE,
            }
        },
        201,
    )
    meeting_id = {"meeting_id": meeting["id"]}
    assert use("get_meeting", meeting_id)["title"] == "MCP meeting"
    meeting = use("update_meeting", {**meeting_id, "payload": {"start": "2027-01-01T10:30:00Z"}})
    assert "10:30:00" in meeting["start"]
    use("update_meeting", {**meeting_id, "payload": {"end": "2027-01-01T09:00:00Z"}}, 422)
    assert any(
        item["id"] == meeting["id"]
        for item in use("list_meetings", {**WINDOW, "scope_type": "personal"})
    )
    feed = use("get_calendar", {**WINDOW, "sources": ["personal", "meetings"]})
    assert {item["id"] for item in feed["items"]} == {event["id"], meeting["id"]}
    assert {
        item["id"] for item in use("get_calendar", {**WINDOW, "sources": ["meetings"]})["items"]
    } == {meeting["id"]}
    use("delete_calendar_event", event_id)
    use("delete_meeting", meeting_id)
    assert use("get_calendar", WINDOW)["items"] == []


def test_settings_preserve_secret_values_and_smtp_tests_are_explicit_and_mocked(
    management, monkeypatch
):
    _, _, engine, _, use, _ = management
    assert use("get_organization")["name"] == "MCP test"
    organization = use(
        "update_organization",
        {"payload": {"name": "MCP managed organization", "timezone": "Europe/Berlin"}},
    )
    assert organization["timezone"] == "Europe/Berlin"
    assert "Europe/Berlin" in use("list_timezones")
    use("delete_organization_logo")
    assert use("get_system_info")["setup_completed"] is True
    assert use("get_mcp_settings") == {"enabled": True}
    assert use("update_mcp_settings", {"payload": {"enabled": True}}) == {"enabled": True}
    assert use("get_smtp_settings") is None
    password = "McpSmtpSecret123"
    payload = {
        "host": "mail.example.com",
        "port": 587,
        "username": "sprint",
        "password": password,
        "encryption": "starttls",
        "from_address": "sprint@example.com",
        "from_name": "Sprint MCP",
    }
    saved = use("update_smtp_settings", {"payload": payload})
    assert saved["has_password"] is True
    assert password not in json.dumps(saved)
    assert "password" not in use("get_smtp_settings")
    with Session(engine()) as db:
        stored = db.scalar(select(SMTPConfiguration))
        assert installation_store.decrypt(stored.password_encrypted) == password
    del payload["password"]
    use("update_smtp_settings", {"payload": {**payload, "from_name": "Changed"}})
    with Session(engine()) as db:
        assert (
            installation_store.decrypt(db.scalar(select(SMTPConfiguration)).password_encrypted)
            == password
        )
    sent = []
    monkeypatch.setattr(
        "app.api.v1.settings.send_email",
        lambda _configuration, recipient, _subject, _body: sent.append(recipient),
    )
    use("test_smtp_settings", {"recipient": "recipient@example.com"})
    assert sent == ["recipient@example.com"]
    annotation = (
        next(tool for tool in TOOLS if tool.name == "test_smtp_settings").definition().annotations
    )
    assert annotation.open_world_hint is True


def test_existing_narrow_grants_do_not_gain_administration_tools(management):
    client, password, _, _, _, kind = management
    raw = grant(client, password, kind, ["roles.view", "calendar.view"])
    names = {tool["name"] for tool in rpc(client, raw, "tools/list").json()["result"]["tools"]}
    assert "list_roles" in names and "get_calendar" in names
    for name in (
        "create_role",
        "create_user",
        "update_organization",
        "set_team_members",
        "update_smtp_settings",
    ):
        assert name not in names
        assert call(client, raw, name)["status"] == 403


@pytest.mark.parametrize("kind", ["personal", "oauth"])
def test_private_meetings_events_and_foreign_organization_objects_remain_inaccessible(
    projects, oauth_client, kind
):
    ctx = projects
    checked(
        ctx["admin"].patch(
            f"/api/v1/roles/{ctx['role_id']}",
            json={"permission_keys": [str(key) for key in ALL_PERMISSIONS]},
        ),
        200,
    )
    raw = grant(ctx["alice"], "AlicePassword123", kind, SCOPES)
    private_event = checked(
        ctx["admin"].post(
            "/api/v1/calendar/events",
            json={"title": "Private admin event", "scope_type": "personal", **SCHEDULE},
        )
    )
    private_meeting = checked(
        ctx["admin"].post(
            "/api/v1/meetings",
            json={"title": "Private admin meeting", "scope_type": "personal", **SCHEDULE},
        )
    )
    for name, arguments in [
        ("get_calendar_event", {"event_id": private_event["id"]}),
        ("get_meeting", {"meeting_id": private_meeting["id"]}),
        ("list_meeting_participants", {"scope_type": "project", "scope_id": ctx["foreign"]}),
        (
            "create_meeting",
            {
                "payload": {
                    "title": "Denied",
                    "scope_type": "project",
                    "scope_id": ctx["foreign"],
                    **SCHEDULE,
                }
            },
        ),
        (
            "create_calendar_event",
            {
                "payload": {
                    "title": "Denied",
                    "scope_type": "project",
                    "scope_id": ctx["foreign"],
                    **SCHEDULE,
                }
            },
        ),
    ]:
        assert call(ctx["admin"], raw, name, arguments)["status"] == 404
    assert call(ctx["admin"], raw, "get_calendar", WINDOW)["data"]["items"] == []
    with Session(ctx["engine"]()) as db:
        foreign = Organization(name="Foreign organization")
        db.add(foreign)
        db.flush()
        user = User(
            organization_id=foreign.id,
            username="foreign",
            email="foreign@example.com",
            first_name="Foreign",
            last_name="Secret",
            password_hash="unusable",
        )
        role = Role(organization_id=foreign.id, name="Foreign secret role", permissions=[])
        team = Team(organization_id=foreign.id, name="Foreign secret team", members=[])
        db.add_all([user, role, team])
        db.commit()
        foreign_user, foreign_role, foreign_team = user.id, role.id, team.id
    for name, arguments in [
        ("get_user", {"target_user_id": foreign_user}),
        ("get_user_profile", {"target_user_id": foreign_user}),
        ("list_user_contacts", {"target_user_id": foreign_user}),
        ("get_user_presence", {"target_user_id": foreign_user}),
        ("get_role", {"role_id": foreign_role}),
        ("get_team", {"team_id": foreign_team}),
    ]:
        result = call(ctx["admin"], raw, name, arguments)
        assert result["status"] == 404, (name, result)
        assert "secret" not in json.dumps(result).lower()
