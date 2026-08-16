from fastapi import APIRouter, Depends, Query, status

from app.api.dependencies import CurrentUser, DBSession, require_permission
from app.core.errors import APIError
from app.models.identity import User
from app.permissions.catalog import PermissionKey
from app.schemas.common import MessageResponse, PaginatedResponse, UUIDString
from app.schemas.identity import UserCreate, UserResponse, UserUpdate
from app.services.identity_service import (
    create_user,
    delete_user,
    get_user,
    list_users,
    protect_last_active_admin,
    update_user,
)

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=PaginatedResponse[UserResponse])
def users_list(
    db: DBSession,
    current: CurrentUser,
    _: User = Depends(require_permission(PermissionKey.USERS_VIEW)),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    search: str | None = Query(default=None, max_length=200),
    active: bool | None = None,
    sort: str = Query("username", pattern=r"^(username|email|created_at|last_login)$"),
    direction: str = Query("asc", pattern=r"^(asc|desc)$"),
) -> PaginatedResponse[UserResponse]:
    items, meta = list_users(
        db, current.organization_id, page, page_size, search, active, sort, direction
    )
    return PaginatedResponse(items=items, meta=meta)


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def user_create(
    payload: UserCreate,
    db: DBSession,
    current: CurrentUser,
    _: User = Depends(require_permission(PermissionKey.USERS_CREATE)),
) -> User:
    return create_user(db, current.organization_id, payload)


@router.get("/{user_id}", response_model=UserResponse)
def user_detail(
    user_id: UUIDString,
    db: DBSession,
    current: CurrentUser,
    _: User = Depends(require_permission(PermissionKey.USERS_VIEW)),
) -> User:
    return get_user(db, current.organization_id, user_id)


@router.patch("/{user_id}", response_model=UserResponse)
def user_update(
    user_id: UUIDString,
    payload: UserUpdate,
    db: DBSession,
    current: CurrentUser,
    _: User = Depends(require_permission(PermissionKey.USERS_EDIT)),
) -> User:
    target = get_user(db, current.organization_id, user_id)
    if target.id == current.id and payload.is_active is False:
        raise APIError(409, "cannot_disable_self", "You cannot disable your own account")
    protect_last_active_admin(db, target, payload.is_active, payload.role_ids)
    return update_user(db, target, payload)


@router.delete("/{user_id}", response_model=MessageResponse)
def user_delete(
    user_id: UUIDString,
    db: DBSession,
    current: CurrentUser,
    _: User = Depends(require_permission(PermissionKey.USERS_DELETE)),
) -> MessageResponse:
    target = get_user(db, current.organization_id, user_id)
    if target.id == current.id:
        raise APIError(409, "cannot_delete_self", "You cannot delete your own account")
    delete_user(db, target)
    return MessageResponse(message="User deactivated")
