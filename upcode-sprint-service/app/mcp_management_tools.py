"""Fixed MCP tools for the existing calendar and workspace administration APIs."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.mcp_toolkit import APITool
from app.schemas.collaboration import (
    CalendarEventCreate,
    CalendarEventUpdate,
    MeetingCreate,
    MeetingUpdate,
    ScopeType,
)
from app.schemas.common import IDListRequest, UUIDString
from app.schemas.identity import (
    ContactCreate,
    ContactUpdate,
    PresenceUpdate,
    ProfileUpdate,
    RoleCreate,
    RoleUpdate,
    UserCreate,
    UserUpdate,
)
from app.schemas.project import TeamCreate, TeamUpdate
from app.schemas.settings import OrganizationUpdate, SMTPConfigurationUpdate

USER = {"target_user_id": UUIDString}
CONTACT = {**USER, "contact_id": UUIDString}
TEAM = {"team_id": UUIDString}
ROLE = {"role_id": UUIDString}
MEETING = {"meeting_id": UUIDString}
EVENT = {"event_id": UUIDString}
PAGING = {
    "page": (int, Field(default=1, ge=1)),
    "page_size": (int, Field(default=25, ge=1, le=100)),
}
SEARCH = (str | None, Field(default=None, max_length=200))


class MCPSettingsUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    enabled: bool = Field(strict=True)


TOOLS = [
    APITool(
        "get_calendar",
        "Read visible calendar events and meetings within a time range. "
        "Optional sources filter by the source keys returned in available_sources.",
        "calendar.view",
        "GET",
        "/calendar",
        query_fields={
            "start": (datetime, ...),
            "end": (datetime, ...),
            "sources": (list[str] | None, Field(default=None, max_length=100)),
        },
    ),
    APITool(
        "get_calendar_event",
        "Read a calendar event visible to the acting user.",
        "calendar.view",
        "GET",
        "/calendar/events/{event_id}",
        EVENT,
    ),
    APITool(
        "create_calendar_event",
        "Create a personal, organization, team, or project calendar event within your access.",
        "calendar.manage",
        "POST",
        "/calendar/events",
        payload=CalendarEventCreate,
    ),
    APITool(
        "update_calendar_event",
        "Update a visible calendar event owned by the acting user.",
        "calendar.manage",
        "PATCH",
        "/calendar/events/{event_id}",
        EVENT,
        payload=CalendarEventUpdate,
    ),
    APITool(
        "delete_calendar_event",
        "Delete a visible calendar event owned by the acting user.",
        "calendar.manage",
        "DELETE",
        "/calendar/events/{event_id}",
        EVENT,
    ),
    APITool(
        "list_meetings",
        "List meetings visible to the acting user, optionally filtered by time and scope.",
        "meetings.view",
        "GET",
        "/meetings",
        query_fields={
            "start": (datetime | None, None),
            "end": (datetime | None, None),
            "scope_type": (ScopeType | None, None),
        },
    ),
    APITool(
        "get_meeting",
        "Read an accessible meeting and its participants.",
        "meetings.view",
        "GET",
        "/meetings/{meeting_id}",
        MEETING,
    ),
    APITool(
        "list_meeting_participants",
        "List users eligible for a meeting's scope; project and team access is checked.",
        "meetings.create",
        "GET",
        "/meetings/available-participants",
        query_fields={
            "scope_type": (ScopeType, ...),
            "scope_id": (UUIDString | None, None),
        },
    ),
    APITool(
        "create_meeting",
        "Create a meeting with eligible participants in an accessible scope.",
        "meetings.create",
        "POST",
        "/meetings",
        payload=MeetingCreate,
    ),
    APITool(
        "update_meeting",
        "Update an accessible meeting; creator or administrator rules still apply.",
        "meetings.edit",
        "PATCH",
        "/meetings/{meeting_id}",
        MEETING,
        payload=MeetingUpdate,
    ),
    APITool(
        "delete_meeting",
        "Delete an accessible meeting; creator or administrator rules still apply.",
        "meetings.delete",
        "DELETE",
        "/meetings/{meeting_id}",
        MEETING,
    ),
    APITool(
        "list_teams",
        "List teams in the acting user's organization.",
        "teams.view",
        "GET",
        "/teams",
        query_fields={**PAGING, "search": SEARCH},
    ),
    APITool(
        "get_team",
        "Read a team and its members in the acting user's organization.",
        "teams.view",
        "GET",
        "/teams/{team_id}",
        TEAM,
    ),
    APITool(
        "create_team",
        "Create a team in your organization, optionally with members.",
        "teams.create",
        "POST",
        "/teams",
        payload=TeamCreate,
    ),
    APITool(
        "update_team",
        "Update a team's name or description in your organization.",
        "teams.edit",
        "PATCH",
        "/teams/{team_id}",
        TEAM,
        payload=TeamUpdate,
    ),
    APITool(
        "set_team_members",
        "Replace the complete team membership with payload.ids. "
        "Read get_team first; an empty list removes every member.",
        "teams.manage_members",
        "PUT",
        "/teams/{team_id}/members",
        TEAM,
        payload=IDListRequest,
    ),
    APITool(
        "delete_team",
        "Delete a team in your organization, removing its memberships.",
        "teams.delete",
        "DELETE",
        "/teams/{team_id}",
        TEAM,
    ),
    APITool(
        "list_permissions",
        "Read the application's permission catalog for configuring roles.",
        "roles.view",
        "GET",
        "/permissions",
    ),
    APITool(
        "list_roles",
        "List roles and their permissions in your organization.",
        "roles.view",
        "GET",
        "/roles",
    ),
    APITool(
        "get_role",
        "Read a role and its permissions in your organization.",
        "roles.view",
        "GET",
        "/roles/{role_id}",
        ROLE,
    ),
    APITool(
        "create_role",
        "Create a role using permission keys from list_permissions.",
        "roles.create",
        "POST",
        "/roles",
        payload=RoleCreate,
    ),
    APITool(
        "update_role",
        "Update a role; system role names and permissions remain protected.",
        "roles.edit",
        "PATCH",
        "/roles/{role_id}",
        ROLE,
        payload=RoleUpdate,
    ),
    APITool(
        "delete_role",
        "Delete a role; protected system roles cannot be deleted.",
        "roles.delete",
        "DELETE",
        "/roles/{role_id}",
        ROLE,
    ),
    APITool(
        "list_users",
        "List user accounts in your organization. "
        "Passwords and authentication secrets are never returned.",
        "users.view",
        "GET",
        "/users",
        query_fields={
            **PAGING,
            "search": SEARCH,
            "active": (bool | None, None),
        },
    ),
    APITool(
        "get_user",
        "Read a user profile in your organization, including contacts and memberships "
        "visible to the acting user.",
        "users.view",
        "GET",
        "/users/{target_user_id}",
        USER,
    ),
    APITool(
        "create_user",
        "Create a user account and assign organization roles. "
        "The supplied initial password is never returned.",
        "users.create",
        "POST",
        "/users",
        payload=UserCreate,
    ),
    APITool(
        "update_user",
        "Update account details, active status, or role assignments. "
        "Self-deactivation and removal of the last active administrator are blocked.",
        "users.edit",
        "PATCH",
        "/users/{target_user_id}",
        USER,
        payload=UserUpdate,
    ),
    APITool(
        "delete_user",
        "Deactivate a user account while retaining historical authorship. "
        "Self-deletion and deactivation of the last active administrator are blocked.",
        "users.delete",
        "DELETE",
        "/users/{target_user_id}",
        USER,
    ),
    APITool(
        "get_user_profile",
        "Read a user profile in your organization, including contacts and memberships "
        "visible to the acting user.",
        "users.profile.view",
        "GET",
        "/users/{target_user_id}",
        USER,
    ),
    APITool(
        "update_user_profile",
        "Update another user's profile in your organization "
        "without changing account roles or credentials.",
        "users.profile.edit",
        "PATCH",
        "/users/{target_user_id}/profile",
        USER,
        payload=ProfileUpdate,
    ),
    APITool(
        "delete_user_avatar",
        "Remove a user's avatar in your organization.",
        "users.profile.edit",
        "DELETE",
        "/users/{target_user_id}/avatar",
        USER,
    ),
    APITool(
        "list_user_contacts",
        "Read contact information visible to the acting user for an organization user.",
        "users.contacts.view",
        "GET",
        "/users/{target_user_id}/contacts",
        USER,
    ),
    APITool(
        "create_user_contact",
        "Add contact information for a user in your organization.",
        "users.contacts.edit",
        "POST",
        "/users/{target_user_id}/contacts",
        USER,
        payload=ContactCreate,
    ),
    APITool(
        "update_user_contact",
        "Update a contact belonging to the specified user in your organization.",
        "users.contacts.edit",
        "PATCH",
        "/users/{target_user_id}/contacts/{contact_id}",
        CONTACT,
        payload=ContactUpdate,
    ),
    APITool(
        "delete_user_contact",
        "Delete a contact belonging to the specified user in your organization.",
        "users.contacts.edit",
        "DELETE",
        "/users/{target_user_id}/contacts/{contact_id}",
        CONTACT,
    ),
    APITool(
        "get_user_presence",
        "Read an organization user's presence and status message.",
        "users.presence.view",
        "GET",
        "/users/{target_user_id}/presence",
        USER,
    ),
    APITool(
        "update_user_presence",
        "Update an organization user's manual presence and status message.",
        "users.presence.edit",
        "PATCH",
        "/users/{target_user_id}/presence",
        USER,
        payload=PresenceUpdate,
    ),
    APITool(
        "get_organization",
        "Read your organization's name, timezone, and logo URL.",
        "organization.manage",
        "GET",
        "/organization",
    ),
    APITool(
        "update_organization",
        "Update your organization's name and optionally its timezone.",
        "organization.manage",
        "PATCH",
        "/organization",
        payload=OrganizationUpdate,
    ),
    APITool(
        "delete_organization_logo",
        "Remove the current organization's custom logo.",
        "organization.manage",
        "DELETE",
        "/organization/logo",
    ),
    APITool(
        "list_timezones",
        "List valid IANA timezone names for organization and profile settings.",
        "organization.manage",
        "GET",
        "/settings/timezones",
    ),
    APITool(
        "get_system_info",
        "Read the application version, environment, database engine, and setup state.",
        "settings.manage",
        "GET",
        "/settings/system",
    ),
    APITool(
        "get_smtp_settings",
        "Read SMTP settings; the stored password is never returned.",
        "settings.manage",
        "GET",
        "/settings/smtp",
    ),
    APITool(
        "update_smtp_settings",
        "Update SMTP delivery settings. Omit password to preserve the existing secret; "
        "it is never returned.",
        "settings.manage",
        "PUT",
        "/settings/smtp",
        payload=SMTPConfigurationUpdate,
    ),
    APITool(
        "test_smtp_settings",
        "Send an SMTP test email to the explicitly supplied recipient "
        "using the saved delivery settings.",
        "settings.manage",
        "POST",
        "/settings/smtp/test",
        query_fields={"recipient": (EmailStr, ...)},
        open_world=True,
    ),
    APITool(
        "get_mcp_settings",
        "Read whether MCP access is enabled for this instance.",
        "settings.manage",
        "GET",
        "/mcp-status",
    ),
    APITool(
        "update_mcp_settings",
        "Enable or disable MCP access. Disabling it immediately blocks subsequent MCP "
        "requests; re-enable it in Sprint's web administration.",
        "settings.manage",
        "PUT",
        "/settings/mcp",
        payload=MCPSettingsUpdate,
    ),
]
