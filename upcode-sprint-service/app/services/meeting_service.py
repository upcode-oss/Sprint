from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from app.core.errors import APIError
from app.models.associations import team_members
from app.models.collaboration import Meeting, MeetingParticipant
from app.models.identity import User
from app.schemas.collaboration import MeetingCreate, MeetingUpdate
from app.services.access_service import can_access_project, can_access_team
from app.services.permission_service import is_admin
from app.services.team_project_service import project_members


def _meeting_options():
    return (
        selectinload(Meeting.creator),
        selectinload(Meeting.participants).selectinload(MeetingParticipant.user),
    )


def allowed_scope_participants(
    db: Session, current_user: User, scope_type: str, scope_id: str | None
) -> list[User]:
    if scope_type == "personal":
        return [current_user]
    if scope_type == "organization":
        return list(
            db.scalars(
                select(User)
                .where(
                    User.organization_id == current_user.organization_id, User.is_active.is_(True)
                )
                .order_by(User.first_name, User.last_name)
            )
        )
    if scope_type == "team" and scope_id:
        if not can_access_team(db, current_user, scope_id):
            raise APIError(404, "team_not_found", "Team not found")
        return list(
            db.scalars(
                select(User)
                .join(team_members, team_members.c.user_id == User.id)
                .where(team_members.c.team_id == scope_id, User.is_active.is_(True))
                .order_by(User.first_name, User.last_name)
            )
        )
    if scope_type == "project" and scope_id:
        if not can_access_project(db, current_user, scope_id):
            raise APIError(404, "project_not_found", "Project not found")
        return project_members(db, scope_id)
    raise APIError(422, "invalid_scope", "Meeting scope is invalid")


def _validate_participants(
    allowed: list[User], participant_ids: list[str], creator: User
) -> list[User]:
    by_id = {user.id: user for user in allowed}
    by_id.setdefault(creator.id, creator)
    requested = set(participant_ids)
    requested.add(creator.id)
    if not requested.issubset(by_id):
        raise APIError(
            422, "invalid_participants", "One or more participants are outside the meeting scope"
        )
    return [by_id[user_id] for user_id in requested]


def create_meeting(db: Session, creator: User, payload: MeetingCreate) -> Meeting:
    allowed = allowed_scope_participants(db, creator, payload.scope_type, payload.scope_id)
    participants = _validate_participants(allowed, payload.participant_ids, creator)
    meeting = Meeting(
        organization_id=creator.organization_id,
        creator_id=creator.id,
        title=payload.title.strip(),
        description=payload.description,
        start=payload.start,
        end=payload.end,
        location=payload.location,
        meeting_url=str(payload.meeting_url) if payload.meeting_url else None,
        scope_type=payload.scope_type,
        scope_id=payload.scope_id,
        participants=[MeetingParticipant(user_id=user.id) for user in participants],
    )
    db.add(meeting)
    db.commit()
    return get_meeting(db, creator, meeting.id)


def visible_meeting_condition(user: User):
    participant = select(MeetingParticipant.meeting_id).where(MeetingParticipant.user_id == user.id)
    if is_admin(user):
        return or_(Meeting.organization_id == user.organization_id, Meeting.id.in_(participant))
    return Meeting.id.in_(participant)


def list_meetings(
    db: Session, user: User, start=None, end=None, scope_type: str | None = None
) -> list[Meeting]:
    statement = select(Meeting).options(*_meeting_options()).where(visible_meeting_condition(user))
    if start:
        statement = statement.where(Meeting.end >= start)
    if end:
        statement = statement.where(Meeting.start <= end)
    if scope_type:
        statement = statement.where(Meeting.scope_type == scope_type)
    return list(db.scalars(statement.order_by(Meeting.start)))


def get_meeting(db: Session, user: User, meeting_id: str) -> Meeting:
    meeting = db.scalar(
        select(Meeting)
        .options(*_meeting_options())
        .where(Meeting.id == meeting_id, visible_meeting_condition(user))
    )
    if meeting is None:
        raise APIError(404, "meeting_not_found", "Meeting not found")
    return meeting


def update_meeting(
    db: Session, current_user: User, meeting: Meeting, payload: MeetingUpdate
) -> Meeting:
    if meeting.creator_id != current_user.id and not is_admin(current_user):
        raise APIError(403, "meeting_owner_required", "Only the creator can edit this meeting")
    for key in ("title", "description", "start", "end", "location"):
        if key in payload.model_fields_set:
            setattr(meeting, key, getattr(payload, key))
    if "meeting_url" in payload.model_fields_set:
        meeting.meeting_url = str(payload.meeting_url) if payload.meeting_url else None
    if meeting.end <= meeting.start:
        raise APIError(422, "invalid_dates", "Meeting end must be after start")
    if payload.participant_ids is not None:
        allowed = allowed_scope_participants(db, current_user, meeting.scope_type, meeting.scope_id)
        users = _validate_participants(allowed, payload.participant_ids, meeting.creator)
        meeting.participants = [MeetingParticipant(user_id=user.id) for user in users]
    db.commit()
    return get_meeting(db, current_user, meeting.id)
