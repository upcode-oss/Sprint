from datetime import datetime

from fastapi import APIRouter, Depends, Query, status

from app.api.dependencies import CurrentUser, DBSession, require_permission
from app.core.errors import APIError
from app.models.collaboration import Meeting
from app.models.identity import User
from app.permissions.catalog import PermissionKey
from app.schemas.collaboration import MeetingCreate, MeetingResponse, MeetingUpdate
from app.schemas.common import MessageResponse, UUIDString
from app.schemas.identity import UserBrief
from app.services.meeting_service import (
    allowed_scope_participants,
    create_meeting,
    get_meeting,
    list_meetings,
    update_meeting,
)
from app.services.permission_service import is_admin

router = APIRouter(prefix="/meetings", tags=["meetings"])


@router.get("", response_model=list[MeetingResponse])
def meetings_list(
    db: DBSession,
    current: CurrentUser,
    _: User = Depends(require_permission(PermissionKey.MEETINGS_VIEW)),
    start: datetime | None = None,
    end: datetime | None = None,
    scope_type: str | None = Query(default=None, pattern=r"^(personal|organization|team|project)$"),
) -> list[Meeting]:
    return list_meetings(db, current, start, end, scope_type)


@router.get("/available-participants", response_model=list[UserBrief])
def available_participants(
    db: DBSession,
    current: CurrentUser,
    _: User = Depends(require_permission(PermissionKey.MEETINGS_CREATE)),
    scope_type: str = Query(pattern=r"^(personal|organization|team|project)$"),
    scope_id: UUIDString | None = None,
) -> list[User]:
    return allowed_scope_participants(db, current, scope_type, scope_id)


@router.post("", response_model=MeetingResponse, status_code=status.HTTP_201_CREATED)
def meeting_create(
    payload: MeetingCreate,
    db: DBSession,
    current: CurrentUser,
    _: User = Depends(require_permission(PermissionKey.MEETINGS_CREATE)),
) -> Meeting:
    return create_meeting(db, current, payload)


@router.get("/{meeting_id}", response_model=MeetingResponse)
def meeting_detail(
    meeting_id: UUIDString,
    db: DBSession,
    current: CurrentUser,
    _: User = Depends(require_permission(PermissionKey.MEETINGS_VIEW)),
) -> Meeting:
    return get_meeting(db, current, meeting_id)


@router.patch("/{meeting_id}", response_model=MeetingResponse)
def meeting_update(
    meeting_id: UUIDString,
    payload: MeetingUpdate,
    db: DBSession,
    current: CurrentUser,
    _: User = Depends(require_permission(PermissionKey.MEETINGS_EDIT)),
) -> Meeting:
    return update_meeting(db, current, get_meeting(db, current, meeting_id), payload)


@router.delete("/{meeting_id}", response_model=MessageResponse)
def meeting_delete(
    meeting_id: UUIDString,
    db: DBSession,
    current: CurrentUser,
    _: User = Depends(require_permission(PermissionKey.MEETINGS_DELETE)),
) -> MessageResponse:
    meeting = get_meeting(db, current, meeting_id)
    if meeting.creator_id != current.id and not is_admin(current):
        raise APIError(403, "meeting_owner_required", "Only the creator can delete this meeting")
    db.delete(meeting)
    db.commit()
    return MessageResponse(message="Meeting deleted")
