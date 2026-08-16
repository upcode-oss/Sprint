from fastapi import APIRouter, Depends, status

from app.api.dependencies import CurrentUser, DBSession, require_permission
from app.models.identity import Role, User
from app.permissions.catalog import PermissionKey
from app.schemas.common import MessageResponse, UUIDString
from app.schemas.identity import RoleCreate, RoleResponse, RoleUpdate
from app.services.identity_service import (
    create_role,
    delete_role,
    get_role,
    list_roles,
    update_role,
)

router = APIRouter(prefix="/roles", tags=["roles"])


@router.get("", response_model=list[RoleResponse])
def roles_list(
    db: DBSession,
    current: CurrentUser,
    _: User = Depends(require_permission(PermissionKey.ROLES_VIEW)),
) -> list[Role]:
    return list_roles(db, current.organization_id)


@router.post("", response_model=RoleResponse, status_code=status.HTTP_201_CREATED)
def role_create(
    payload: RoleCreate,
    db: DBSession,
    current: CurrentUser,
    _: User = Depends(require_permission(PermissionKey.ROLES_CREATE)),
) -> Role:
    return create_role(db, current.organization_id, payload)


@router.get("/{role_id}", response_model=RoleResponse)
def role_detail(
    role_id: UUIDString,
    db: DBSession,
    current: CurrentUser,
    _: User = Depends(require_permission(PermissionKey.ROLES_VIEW)),
) -> Role:
    return get_role(db, current.organization_id, role_id)


@router.patch("/{role_id}", response_model=RoleResponse)
def role_update(
    role_id: UUIDString,
    payload: RoleUpdate,
    db: DBSession,
    current: CurrentUser,
    _: User = Depends(require_permission(PermissionKey.ROLES_EDIT)),
) -> Role:
    return update_role(db, get_role(db, current.organization_id, role_id), payload)


@router.delete("/{role_id}", response_model=MessageResponse)
def role_delete(
    role_id: UUIDString,
    db: DBSession,
    current: CurrentUser,
    _: User = Depends(require_permission(PermissionKey.ROLES_DELETE)),
) -> MessageResponse:
    delete_role(db, get_role(db, current.organization_id, role_id))
    return MessageResponse(message="Role deleted")
