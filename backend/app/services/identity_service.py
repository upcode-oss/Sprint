from sqlalchemy import asc, desc, func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.core.errors import APIError
from app.core.security import hash_password
from app.models.associations import user_roles
from app.models.identity import Permission, Role, User, UserPresence, UserProfile
from app.repositories.pagination import paginate
from app.schemas.common import PaginationMeta
from app.schemas.identity import RoleCreate, RoleUpdate, UserCreate, UserUpdate


def list_users(
    db: Session,
    organization_id: str,
    page: int,
    page_size: int,
    search: str | None,
    active: bool | None,
    sort: str,
    direction: str,
) -> tuple[list[User], PaginationMeta]:
    columns = {
        "username": User.username,
        "email": User.email,
        "created_at": User.created_at,
        "last_login": User.last_login,
    }
    order = columns.get(sort, User.username)
    statement = (
        select(User)
        .options(selectinload(User.roles))
        .where(User.organization_id == organization_id)
    )
    if search:
        term = f"%{search.strip()}%"
        statement = statement.where(
            or_(
                User.username.ilike(term),
                User.email.ilike(term),
                User.first_name.ilike(term),
                User.last_name.ilike(term),
            )
        )
    if active is not None:
        statement = statement.where(User.is_active == active)
    return paginate(
        db, statement.order_by(desc(order) if direction == "desc" else asc(order)), page, page_size
    )


def _roles_for_ids(db: Session, organization_id: str, role_ids: list[str]) -> list[Role]:
    if not role_ids:
        return []
    roles = list(
        db.scalars(
            select(Role).where(Role.organization_id == organization_id, Role.id.in_(role_ids))
        )
    )
    if len(roles) != len(set(role_ids)):
        raise APIError(422, "invalid_roles", "One or more roles are invalid")
    return roles


def create_user(db: Session, organization_id: str, payload: UserCreate) -> User:
    duplicate = db.scalar(
        select(User.id).where(
            User.organization_id == organization_id,
            or_(User.username == payload.username, User.email == str(payload.email).lower()),
        )
    )
    if duplicate:
        raise APIError(409, "user_exists", "Username or email is already in use")
    user = User(
        organization_id=organization_id,
        username=payload.username.strip(),
        email=str(payload.email).lower(),
        first_name=payload.first_name.strip(),
        last_name=payload.last_name.strip(),
        password_hash=hash_password(payload.password.get_secret_value()),
        is_active=payload.is_active,
        roles=_roles_for_ids(db, organization_id, payload.role_ids),
        profile=UserProfile(timezone="UTC"),
        presence=UserPresence(),
    )
    db.add(user)
    db.commit()
    return get_user(db, organization_id, user.id)


def get_user(db: Session, organization_id: str, user_id: str) -> User:
    user = db.scalar(
        select(User)
        .options(selectinload(User.roles))
        .where(User.id == user_id, User.organization_id == organization_id)
    )
    if user is None:
        raise APIError(404, "user_not_found", "User not found")
    return user


def update_user(db: Session, user: User, payload: UserUpdate) -> User:
    values = payload.model_dump(exclude_unset=True, exclude={"role_ids"})
    if "email" in values:
        values["email"] = str(values["email"]).lower()
    for key, value in values.items():
        setattr(user, key, value)
    if payload.role_ids is not None:
        user.roles = _roles_for_ids(db, user.organization_id, payload.role_ids)
    db.commit()
    return get_user(db, user.organization_id, user.id)


def protect_last_active_admin(
    db: Session,
    user: User,
    next_active: bool | None = None,
    next_role_ids: list[str] | None = None,
) -> None:
    current_admin_role_ids = {role.id for role in user.roles if role.is_system}
    if not current_admin_role_ids:
        return
    removes_admin = next_role_ids is not None and not current_admin_role_ids.intersection(
        next_role_ids
    )
    disables_admin = next_active is False
    if not removes_admin and not disables_admin:
        return
    active_admins = int(
        db.scalar(
            select(func.count(func.distinct(User.id)))
            .join(user_roles, user_roles.c.user_id == User.id)
            .join(Role, Role.id == user_roles.c.role_id)
            .where(
                User.organization_id == user.organization_id,
                User.is_active.is_(True),
                Role.is_system.is_(True),
            )
        )
        or 0
    )
    if active_admins <= 1:
        raise APIError(
            409,
            "last_admin_required",
            "The organization must retain at least one active administrator",
        )


def delete_user(db: Session, user: User) -> None:
    protect_last_active_admin(db, user, next_active=False)
    # Historical task, document and meeting authorship must remain intact.
    # DELETE therefore means a recoverable account deactivation.
    user.is_active = False
    user.token_version += 1
    db.commit()


def list_roles(db: Session, organization_id: str) -> list[Role]:
    return list(
        db.scalars(
            select(Role)
            .options(selectinload(Role.permissions))
            .where(Role.organization_id == organization_id)
            .order_by(Role.name)
        )
    )


def get_role(db: Session, organization_id: str, role_id: str) -> Role:
    role = db.scalar(
        select(Role)
        .options(selectinload(Role.permissions))
        .where(Role.id == role_id, Role.organization_id == organization_id)
    )
    if role is None:
        raise APIError(404, "role_not_found", "Role not found")
    return role


def _permissions_for_keys(db: Session, keys: list[str]) -> list[Permission]:
    permissions = (
        list(db.scalars(select(Permission).where(Permission.key.in_(keys)))) if keys else []
    )
    if len(permissions) != len(set(keys)):
        raise APIError(422, "invalid_permissions", "One or more permission keys are invalid")
    return permissions


def create_role(db: Session, organization_id: str, payload: RoleCreate) -> Role:
    role = Role(
        organization_id=organization_id,
        name=payload.name.strip(),
        description=payload.description,
        permissions=_permissions_for_keys(db, payload.permission_keys),
    )
    db.add(role)
    db.commit()
    return get_role(db, organization_id, role.id)


def update_role(db: Session, role: Role, payload: RoleUpdate) -> Role:
    if role.is_system and (payload.name is not None or payload.permission_keys is not None):
        raise APIError(
            409,
            "system_role_immutable",
            "The Admin role permissions and name are managed by the system",
        )
    if payload.name is not None:
        role.name = payload.name.strip()
    if "description" in payload.model_fields_set:
        role.description = payload.description
    if payload.permission_keys is not None:
        role.permissions = _permissions_for_keys(db, payload.permission_keys)
    db.commit()
    return get_role(db, role.organization_id, role.id)


def delete_role(db: Session, role: Role) -> None:
    if role.is_system:
        raise APIError(409, "system_role_immutable", "The Admin role cannot be deleted")
    db.delete(role)
    db.commit()
