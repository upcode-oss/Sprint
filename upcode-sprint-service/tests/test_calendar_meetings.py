from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.schemas.collaboration import CalendarEventCreate, MeetingCreate
from app.services.calendar_service import calendar_feed, create_event
from app.services.meeting_service import create_meeting, list_meetings


def test_calendar_visibility_aggregates_authorized_sources(
    db: Session, workspace: dict[str, object]
) -> None:
    member = workspace["member"]
    outsider = workspace["outsider"]
    team = workspace["team"]
    project = workspace["project"]
    now = datetime.now(UTC)
    create_event(
        db,
        member,
        CalendarEventCreate(
            title="Private focus",
            start=now,
            end=now + timedelta(hours=1),
            scope_type="personal",
        ),
    )
    create_event(
        db,
        member,
        CalendarEventCreate(
            title="Organization town hall",
            start=now,
            end=now + timedelta(hours=1),
            scope_type="organization",
        ),
    )
    create_event(
        db,
        member,
        CalendarEventCreate(
            title="Team sync",
            start=now,
            end=now + timedelta(hours=1),
            scope_type="team",
            scope_id=team.id,
        ),
    )
    create_event(
        db,
        member,
        CalendarEventCreate(
            title="Project release",
            start=now,
            end=now + timedelta(hours=1),
            scope_type="project",
            scope_id=project.id,
        ),
    )

    member_events, _, sources = calendar_feed(
        db, member, now - timedelta(days=1), now + timedelta(days=1)
    )
    outsider_events, _, _ = calendar_feed(
        db, outsider, now - timedelta(days=1), now + timedelta(days=1)
    )
    assert {item.title for item in member_events} == {
        "Private focus",
        "Organization town hall",
        "Team sync",
        "Project release",
    }
    assert {item.title for item in outsider_events} == {"Organization town hall"}
    assert {source["label"] for source in sources} >= {"Delivery", "sprint", "Meetings"}


def test_meetings_are_visible_by_participant_without_copies(
    db: Session, workspace: dict[str, object]
) -> None:
    member = workspace["member"]
    outsider = workspace["outsider"]
    project = workspace["project"]
    now = datetime.now(UTC)
    meeting = create_meeting(
        db,
        member,
        MeetingCreate(
            title="Sprint planning",
            start=now,
            end=now + timedelta(hours=1),
            scope_type="project",
            scope_id=project.id,
            participant_ids=[],
        ),
    )
    assert len(meeting.participants) == 1
    assert [item.id for item in list_meetings(db, member)] == [meeting.id]
    assert list_meetings(db, outsider) == []
