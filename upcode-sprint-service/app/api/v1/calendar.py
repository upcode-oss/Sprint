from datetime import datetime

from fastapi import APIRouter, Depends, Query, status

from app.api.dependencies import CurrentUser, DBSession, require_permission
from app.core.errors import APIError
from app.models.collaboration import CalendarEvent
from app.models.identity import User
from app.permissions.catalog import PermissionKey
from app.schemas.collaboration import (
    CalendarEventCreate,
    CalendarEventResponse,
    CalendarEventUpdate,
    CalendarFeedResponse,
    CalendarMeetingResponse,
)
from app.schemas.common import MessageResponse, UUIDString
from app.services.calendar_service import (
    calendar_feed,
    create_event,
    get_visible_event,
    update_event,
)

router = APIRouter(prefix="/calendar", tags=["calendar"])


@router.get("", response_model=CalendarFeedResponse)
def calendar(
    start: datetime,
    end: datetime,
    db: DBSession,
    current: CurrentUser,
    _: User = Depends(require_permission(PermissionKey.CALENDAR_VIEW)),
    sources: list[str] | None = Query(default=None),
) -> CalendarFeedResponse:
    if end <= start:
        raise APIError(422, "invalid_dates", "End must be after start")
    events, meetings, available = calendar_feed(db, current, start, end, set(sources or []))
    items = [CalendarEventResponse.model_validate(event) for event in events]
    items.extend(CalendarMeetingResponse.model_validate(meeting) for meeting in meetings)
    items.sort(key=lambda item: item.start)
    return CalendarFeedResponse(items=items, available_sources=available)


@router.post("/events", response_model=CalendarEventResponse, status_code=status.HTTP_201_CREATED)
def event_create(
    payload: CalendarEventCreate,
    db: DBSession,
    current: CurrentUser,
    _: User = Depends(require_permission(PermissionKey.CALENDAR_MANAGE)),
) -> CalendarEvent:
    return create_event(db, current, payload)


@router.get("/events/{event_id}", response_model=CalendarEventResponse)
def event_detail(
    event_id: UUIDString,
    db: DBSession,
    current: CurrentUser,
    _: User = Depends(require_permission(PermissionKey.CALENDAR_VIEW)),
) -> CalendarEvent:
    return get_visible_event(db, current, event_id)


@router.patch("/events/{event_id}", response_model=CalendarEventResponse)
def event_update(
    event_id: UUIDString,
    payload: CalendarEventUpdate,
    db: DBSession,
    current: CurrentUser,
    _: User = Depends(require_permission(PermissionKey.CALENDAR_MANAGE)),
) -> CalendarEvent:
    return update_event(db, current, get_visible_event(db, current, event_id), payload)


@router.delete("/events/{event_id}", response_model=MessageResponse)
def event_delete(
    event_id: UUIDString,
    db: DBSession,
    current: CurrentUser,
    _: User = Depends(require_permission(PermissionKey.CALENDAR_MANAGE)),
) -> MessageResponse:
    event = get_visible_event(db, current, event_id)
    if event.creator_id != current.id:
        raise APIError(403, "event_owner_required", "Only the creator can delete this event")
    db.delete(event)
    db.commit()
    return MessageResponse(message="Calendar event deleted")
