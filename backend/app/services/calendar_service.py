from datetime import datetime

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.core.errors import APIError
from app.models.associations import project_teams, team_members
from app.models.collaboration import CalendarEvent
from app.models.identity import User
from app.models.project import Project, Team
from app.schemas.collaboration import CalendarEventCreate, CalendarEventUpdate
from app.services.access_service import can_access_project, can_access_team
from app.services.meeting_service import list_meetings


def _team_ids(user_id: str):
    return select(team_members.c.team_id).where(team_members.c.user_id == user_id)


def _project_ids(user_id: str):
    return (
        select(project_teams.c.project_id)
        .join(team_members, team_members.c.team_id == project_teams.c.team_id)
        .where(team_members.c.user_id == user_id)
    )


def visible_event_condition(user: User):
    return or_(
        and_(CalendarEvent.scope_type == "personal", CalendarEvent.owner_id == user.id),
        and_(
            CalendarEvent.scope_type == "organization",
            CalendarEvent.organization_id == user.organization_id,
        ),
        and_(CalendarEvent.scope_type == "team", CalendarEvent.scope_id.in_(_team_ids(user.id))),
        and_(
            CalendarEvent.scope_type == "project",
            CalendarEvent.scope_id.in_(_project_ids(user.id)),
        ),
    )


def calendar_feed(
    db: Session,
    user: User,
    start: datetime,
    end: datetime,
    sources: set[str] | None = None,
) -> tuple[list[CalendarEvent], list, list[dict[str, str]]]:
    statement = (
        select(CalendarEvent)
        .where(
            visible_event_condition(user),
            CalendarEvent.end >= start,
            CalendarEvent.start <= end,
        )
        .order_by(CalendarEvent.start)
    )
    events = list(db.scalars(statement))
    meetings = list_meetings(db, user, start, end)
    available: dict[str, dict[str, str]] = {
        "personal": {"key": "personal", "label": "Personal", "type": "personal"},
        "organization": {
            "key": "organization",
            "label": "Organization",
            "type": "organization",
        },
        "meetings": {"key": "meetings", "label": "Meetings", "type": "meetings"},
    }
    for team in db.scalars(select(Team).where(Team.id.in_(_team_ids(user.id))).order_by(Team.name)):
        key = f"team:{team.id}"
        available[key] = {"key": key, "label": team.name, "type": "team"}
    for project in db.scalars(
        select(Project).where(Project.id.in_(_project_ids(user.id))).order_by(Project.name)
    ):
        key = f"project:{project.id}"
        available[key] = {"key": key, "label": project.name, "type": "project"}

    if sources:
        events = [
            event
            for event in events
            if (event.scope_type in sources or f"{event.scope_type}:{event.scope_id}" in sources)
        ]
        if "meetings" not in sources:
            meetings = []
    return events, meetings, list(available.values())


def create_event(db: Session, user: User, payload: CalendarEventCreate) -> CalendarEvent:
    owner_id = None
    if payload.scope_type == "personal":
        owner_id = user.id
    elif payload.scope_type == "team":
        if not payload.scope_id or not can_access_team(db, user, payload.scope_id):
            raise APIError(404, "team_not_found", "Team not found")
    elif payload.scope_type == "project" and (
        not payload.scope_id or not can_access_project(db, user, payload.scope_id)
    ):
        raise APIError(404, "project_not_found", "Project not found")
    event = CalendarEvent(
        organization_id=user.organization_id,
        creator_id=user.id,
        owner_id=owner_id,
        **payload.model_dump(),
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


def get_visible_event(db: Session, user: User, event_id: str) -> CalendarEvent:
    event = db.scalar(
        select(CalendarEvent).where(CalendarEvent.id == event_id, visible_event_condition(user))
    )
    if event is None:
        raise APIError(404, "event_not_found", "Calendar event not found")
    return event


def update_event(
    db: Session, user: User, event: CalendarEvent, payload: CalendarEventUpdate
) -> CalendarEvent:
    if event.creator_id != user.id:
        raise APIError(403, "event_owner_required", "Only the creator can edit this event")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(event, key, value)
    if event.end <= event.start:
        raise APIError(422, "invalid_dates", "Event end must be after start")
    db.commit()
    db.refresh(event)
    return event
