from collections.abc import Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.errors import APIError
from app.models.identity import Organization, Permission, Role, User
from app.permissions.catalog import ALL_PERMISSIONS, PERMISSION_DESCRIPTIONS, PermissionKey

DEFAULT_USER_PERMISSION_KEYS = {
    PermissionKey.USERS_PROFILE_VIEW.value,
    PermissionKey.TEAMS_VIEW.value,
    PermissionKey.PROJECTS_VIEW.value,
    PermissionKey.DOCUMENTS_VIEW.value,
    PermissionKey.KANBAN_VIEW.value,
    PermissionKey.SCRUM_VIEW.value,
    PermissionKey.MEETINGS_VIEW.value,
    PermissionKey.CALENDAR_VIEW.value,
}


def sync_permission_catalog(db: Session) -> list[Permission]:
    existing = {item.key: item for item in db.scalars(select(Permission)).all()}
    for key in ALL_PERMISSIONS:
        if key.value not in existing:
            permission = Permission(key=key.value, description=PERMISSION_DESCRIPTIONS[key])
            db.add(permission)
            existing[key.value] = permission
    db.flush()

    permissions = list(existing.values())
    admin_roles = db.scalars(select(Role).where(Role.is_system.is_(True), Role.name == "Admin"))
    for role in admin_roles:
        role.permissions = permissions.copy()
    db.flush()

    default_permissions = [
        permission for permission in permissions if permission.key in DEFAULT_USER_PERMISSION_KEYS
    ]
    default_roles: dict[str, Role] = {}
    for organization in db.scalars(select(Organization)):
        role = db.scalar(
            select(Role).where(
                Role.organization_id == organization.id,
                Role.name == "User",
            )
        )
        if role is None:
            role = Role(organization_id=organization.id, name="User")
            db.add(role)
        role.description = "Standard workspace access for organization users"
        role.is_system = True
        role.permissions = default_permissions.copy()
        default_roles[organization.id] = role
    db.flush()

    users = db.scalars(select(User).options(selectinload(User.roles)))
    for user in users:
        default_role = default_roles.get(user.organization_id)
        if (
            default_role
            and not any(role.is_system and role.name == "Admin" for role in user.roles)
            and default_role not in user.roles
        ):
            user.roles.append(default_role)
    db.flush()
    return permissions


def get_default_user_role(db: Session, organization_id: str) -> Role:
    role = db.scalar(
        select(Role).where(
            Role.organization_id == organization_id,
            Role.is_system.is_(True),
            Role.name == "User",
        )
    )
    if role is None:
        sync_permission_catalog(db)
        role = db.scalar(
            select(Role).where(
                Role.organization_id == organization_id,
                Role.is_system.is_(True),
                Role.name == "User",
            )
        )
    if role is None:
        raise RuntimeError("Default User role could not be created")
    return role


def create_admin_role(db: Session, organization: Organization) -> Role:
    permissions = sync_permission_catalog(db)
    role = Role(
        organization_id=organization.id,
        name="Admin",
        description="System administrator with every available permission",
        is_system=True,
        permissions=permissions.copy(),
    )
    db.add(role)
    db.flush()
    return role


def effective_permission_keys(user: User) -> set[str]:
    return {permission.key for role in user.roles for permission in role.permissions}


def is_admin(user: User) -> bool:
    return any(role.is_system and role.name == "Admin" for role in user.roles)


def require_permissions(user: User, required: Iterable[str]) -> None:
    required_set = set(required)
    if not required_set.issubset(effective_permission_keys(user)):
        raise APIError(403, "permission_denied", "You do not have permission for this action")
