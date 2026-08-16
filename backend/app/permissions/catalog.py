from enum import StrEnum


class PermissionKey(StrEnum):
    USERS_VIEW = "users.view"
    USERS_CREATE = "users.create"
    USERS_EDIT = "users.edit"
    USERS_DELETE = "users.delete"
    ROLES_VIEW = "roles.view"
    ROLES_CREATE = "roles.create"
    ROLES_EDIT = "roles.edit"
    ROLES_DELETE = "roles.delete"
    TEAMS_VIEW = "teams.view"
    TEAMS_CREATE = "teams.create"
    TEAMS_EDIT = "teams.edit"
    TEAMS_DELETE = "teams.delete"
    TEAMS_MANAGE_MEMBERS = "teams.manage_members"
    PROJECTS_VIEW = "projects.view"
    PROJECTS_CREATE = "projects.create"
    PROJECTS_EDIT = "projects.edit"
    PROJECTS_DELETE = "projects.delete"
    PROJECTS_MANAGE_MEMBERS = "projects.manage_members"
    DOCUMENTS_VIEW = "documents.view"
    DOCUMENTS_CREATE = "documents.create"
    DOCUMENTS_EDIT = "documents.edit"
    DOCUMENTS_DELETE = "documents.delete"
    KANBAN_VIEW = "kanban.view"
    KANBAN_MANAGE = "kanban.manage"
    SCRUM_VIEW = "scrum.view"
    SCRUM_MANAGE = "scrum.manage"
    MEETINGS_VIEW = "meetings.view"
    MEETINGS_CREATE = "meetings.create"
    MEETINGS_EDIT = "meetings.edit"
    MEETINGS_DELETE = "meetings.delete"
    CALENDAR_VIEW = "calendar.view"
    CALENDAR_MANAGE = "calendar.manage"
    ORGANIZATION_MANAGE = "organization.manage"
    SETTINGS_MANAGE = "settings.manage"


PERMISSION_DESCRIPTIONS: dict[PermissionKey, str] = {
    key: key.value.replace(".", " ").replace("_", " ").title() for key in PermissionKey
}
ALL_PERMISSIONS = tuple(PermissionKey)
