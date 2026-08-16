from collections.abc import Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import APIError
from app.models.identity import Organization, Permission, Role, User
from app.permissions.catalog import ALL_PERMISSIONS, PERMISSION_DESCRIPTIONS


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
    return permissions


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
