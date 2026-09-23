from fastapi import APIRouter, Depends, File, Query, Response, UploadFile, status

from app.api.dependencies import CurrentUser, DBSession, require_permission
from app.core.config import settings
from app.core.errors import APIError
from app.models.identity import User
from app.permissions.catalog import PermissionKey
from app.schemas.common import MessageResponse, PaginatedResponse, UUIDString
from app.schemas.identity import (
    AuthUserResponse,
    AvatarResponse,
    ContactCreate,
    ContactResponse,
    ContactUpdate,
    PresenceResponse,
    PresenceUpdate,
    ProfileUpdate,
    UserCreate,
    UserProfileResponse,
    UserResponse,
    UserUpdate,
)
from app.services.identity_service import (
    create_user,
    delete_user,
    get_user,
    list_users,
    protect_last_active_admin,
    update_user,
)
from app.services.permission_service import effective_permission_keys
from app.services.presence_service import (
    expire_temporary_presence,
    presence_summary,
    update_presence,
)
from app.services.profile_service import (
    create_contact,
    delete_contact,
    get_contact,
    remove_avatar,
    save_avatar,
    update_contact,
    update_profile,
    user_teams_and_projects,
    visible_contacts,
)
from app.storage.local import avatar_storage

router = APIRouter(prefix="/users", tags=["users"])


def _has_permission(user: User, *keys: str) -> bool:
    return bool(set(keys).intersection(effective_permission_keys(user)))


def _require_target_access(current: User, target: User, *keys: str) -> None:
    if current.id != target.id and not _has_permission(current, *keys):
        raise APIError(403, "permission_denied", "You do not have permission for this action")


def _auth_response(user: User) -> AuthUserResponse:
    data = UserResponse.model_validate(user).model_dump()
    data.update(
        {
            "bio": user.bio,
            "timezone": user.timezone,
            "locale": user.locale,
            "permissions": sorted(effective_permission_keys(user)),
        }
    )
    return AuthUserResponse.model_validate(data)


def _profile_response(db: DBSession, viewer: User, target: User) -> UserProfileResponse:
    teams, projects = user_teams_and_projects(db, viewer, target)
    return UserProfileResponse.model_validate(
        {
            **target.__dict__,
            "display_name": target.display_name,
            "avatar_url": target.avatar_url,
            "job_title": target.job_title,
            "department": target.department,
            "presence_summary": presence_summary(target.presence),
            "bio": target.bio,
            "contacts": visible_contacts(db, viewer, target),
            "teams": teams,
            "projects": projects,
        }
    )


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


@router.get("/me", response_model=AuthUserResponse)
def own_profile(current: CurrentUser) -> AuthUserResponse:
    return _auth_response(current)


@router.patch("/me", response_model=AuthUserResponse)
def own_profile_update(
    payload: ProfileUpdate, db: DBSession, current: CurrentUser
) -> AuthUserResponse:
    update_profile(db, current, payload)
    return _auth_response(current)


@router.get("/me/contacts", response_model=list[ContactResponse])
def own_contacts(db: DBSession, current: CurrentUser) -> list:
    return visible_contacts(db, current, current)


@router.post("/me/contacts", response_model=ContactResponse, status_code=status.HTTP_201_CREATED)
def own_contact_create(payload: ContactCreate, db: DBSession, current: CurrentUser):
    return create_contact(db, current, payload)


@router.patch("/me/contacts/{contact_id}", response_model=ContactResponse)
def own_contact_update(
    contact_id: UUIDString,
    payload: ContactUpdate,
    db: DBSession,
    current: CurrentUser,
):
    return update_contact(db, current, get_contact(db, current, contact_id), payload)


@router.delete("/me/contacts/{contact_id}", response_model=MessageResponse)
def own_contact_delete(
    contact_id: UUIDString, db: DBSession, current: CurrentUser
) -> MessageResponse:
    delete_contact(db, get_contact(db, current, contact_id))
    return MessageResponse(message="Contact information deleted")


@router.post("/me/avatar", response_model=AvatarResponse)
async def own_avatar_upload(
    db: DBSession,
    current: CurrentUser,
    avatar: UploadFile = File(...),
) -> AvatarResponse:
    content = await avatar.read(settings.avatar_max_bytes + 1)
    save_avatar(db, current, content, avatar.content_type, avatar_storage)
    return AvatarResponse(avatar_url=current.avatar_url or "")


@router.delete("/me/avatar", response_model=MessageResponse)
def own_avatar_delete(db: DBSession, current: CurrentUser) -> MessageResponse:
    remove_avatar(db, current, avatar_storage)
    return MessageResponse(message="Avatar deleted")


@router.get("/me/presence", response_model=PresenceResponse)
def own_presence(db: DBSession, current: CurrentUser) -> PresenceResponse:
    presence = expire_temporary_presence(db, current)
    return PresenceResponse.model_validate(presence_summary(presence))


@router.patch("/me/presence", response_model=PresenceResponse)
def own_presence_update(
    payload: PresenceUpdate, db: DBSession, current: CurrentUser
) -> PresenceResponse:
    presence = update_presence(db, current, payload)
    return PresenceResponse.model_validate(presence_summary(presence))


@router.get("/{user_id}/avatar")
def avatar_download(user_id: UUIDString, db: DBSession, current: CurrentUser) -> Response:
    target = get_user(db, current.organization_id, user_id)
    if not target.profile or not target.profile.avatar_key or not target.profile.avatar_mime_type:
        raise APIError(404, "avatar_not_found", "Avatar not found")
    return Response(
        content=avatar_storage.read(target.profile.avatar_key),
        media_type=target.profile.avatar_mime_type,
        headers={"Cache-Control": "private, max-age=86400", "X-Content-Type-Options": "nosniff"},
    )


@router.get("/{user_id}", response_model=UserProfileResponse)
def user_detail(user_id: UUIDString, db: DBSession, current: CurrentUser) -> UserProfileResponse:
    target = get_user(db, current.organization_id, user_id)
    _require_target_access(
        current,
        target,
        PermissionKey.USERS_VIEW.value,
        PermissionKey.USERS_PROFILE_VIEW.value,
    )
    return _profile_response(db, current, target)


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


@router.patch("/{user_id}/profile", response_model=UserProfileResponse)
def managed_profile_update(
    user_id: UUIDString,
    payload: ProfileUpdate,
    db: DBSession,
    current: CurrentUser,
    _: User = Depends(require_permission(PermissionKey.USERS_PROFILE_EDIT)),
) -> UserProfileResponse:
    target = get_user(db, current.organization_id, user_id)
    update_profile(db, target, payload)
    return _profile_response(db, current, target)


@router.get("/{user_id}/contacts", response_model=list[ContactResponse])
def managed_contacts(
    user_id: UUIDString,
    db: DBSession,
    current: CurrentUser,
    _: User = Depends(require_permission(PermissionKey.USERS_CONTACTS_VIEW)),
) -> list:
    target = get_user(db, current.organization_id, user_id)
    return visible_contacts(db, current, target)


@router.post(
    "/{user_id}/contacts", response_model=ContactResponse, status_code=status.HTTP_201_CREATED
)
def managed_contact_create(
    user_id: UUIDString,
    payload: ContactCreate,
    db: DBSession,
    current: CurrentUser,
    _: User = Depends(require_permission(PermissionKey.USERS_CONTACTS_EDIT)),
):
    target = get_user(db, current.organization_id, user_id)
    return create_contact(db, target, payload)


@router.patch("/{user_id}/contacts/{contact_id}", response_model=ContactResponse)
def managed_contact_update(
    user_id: UUIDString,
    contact_id: UUIDString,
    payload: ContactUpdate,
    db: DBSession,
    current: CurrentUser,
    _: User = Depends(require_permission(PermissionKey.USERS_CONTACTS_EDIT)),
):
    target = get_user(db, current.organization_id, user_id)
    return update_contact(db, target, get_contact(db, target, contact_id), payload)


@router.delete("/{user_id}/contacts/{contact_id}", response_model=MessageResponse)
def managed_contact_delete(
    user_id: UUIDString,
    contact_id: UUIDString,
    db: DBSession,
    current: CurrentUser,
    _: User = Depends(require_permission(PermissionKey.USERS_CONTACTS_EDIT)),
) -> MessageResponse:
    target = get_user(db, current.organization_id, user_id)
    delete_contact(db, get_contact(db, target, contact_id))
    return MessageResponse(message="Contact information deleted")


@router.get("/{user_id}/presence", response_model=PresenceResponse)
def managed_presence(
    user_id: UUIDString,
    db: DBSession,
    current: CurrentUser,
    _: User = Depends(require_permission(PermissionKey.USERS_PRESENCE_VIEW)),
) -> PresenceResponse:
    target = get_user(db, current.organization_id, user_id)
    presence = expire_temporary_presence(db, target)
    return PresenceResponse.model_validate(presence_summary(presence))


@router.patch("/{user_id}/presence", response_model=PresenceResponse)
def managed_presence_update(
    user_id: UUIDString,
    payload: PresenceUpdate,
    db: DBSession,
    current: CurrentUser,
    _: User = Depends(require_permission(PermissionKey.USERS_PRESENCE_EDIT)),
) -> PresenceResponse:
    target = get_user(db, current.organization_id, user_id)
    presence = update_presence(db, target, payload)
    return PresenceResponse.model_validate(presence_summary(presence))


@router.post("/{user_id}/avatar", response_model=AvatarResponse)
async def managed_avatar_upload(
    user_id: UUIDString,
    db: DBSession,
    current: CurrentUser,
    _: User = Depends(require_permission(PermissionKey.USERS_PROFILE_EDIT)),
    avatar: UploadFile = File(...),
) -> AvatarResponse:
    target = get_user(db, current.organization_id, user_id)
    content = await avatar.read(settings.avatar_max_bytes + 1)
    save_avatar(db, target, content, avatar.content_type, avatar_storage)
    return AvatarResponse(avatar_url=target.avatar_url or "")


@router.delete("/{user_id}/avatar", response_model=MessageResponse)
def managed_avatar_delete(
    user_id: UUIDString,
    db: DBSession,
    current: CurrentUser,
    _: User = Depends(require_permission(PermissionKey.USERS_PROFILE_EDIT)),
) -> MessageResponse:
    target = get_user(db, current.organization_id, user_id)
    remove_avatar(db, target, avatar_storage)
    return MessageResponse(message="Avatar deleted")


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
