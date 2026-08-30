from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models.associations import project_teams, team_members
from app.models.collaboration import Document, Meeting, MeetingParticipant
from app.models.identity import User
from app.models.project import Project, Sprint, Task, Team
from app.services.access_service import accessible_project_ids_statement
from app.services.calendar_service import calendar_feed
from app.services.permission_service import is_admin


def personal_dashboard(db: Session, user: User) -> dict:
    project_ids = (
        select(Project.id).where(Project.organization_id == user.organization_id)
        if is_admin(user)
        else accessible_project_ids_statement(user)
    )
    projects = list(
        db.scalars(
            select(Project)
            .options(selectinload(Project.teams))
            .where(Project.id.in_(project_ids), Project.status.in_(["planned", "active"]))
            .order_by(Project.name)
            .limit(8)
        )
    )
    teams = list(
        db.scalars(
            select(Team)
            .join(team_members, team_members.c.team_id == Team.id)
            .where(team_members.c.user_id == user.id)
            .order_by(Team.name)
        )
    )
    tasks = list(
        db.scalars(
            select(Task)
            .options(
                selectinload(Task.project), selectinload(Task.reporter), selectinload(Task.assignee)
            )
            .where(Task.assignee_id == user.id, Task.status != "done")
            .order_by(Task.due_date, Task.priority.desc())
            .limit(10)
        )
    )
    sprints = list(
        db.scalars(
            select(Sprint)
            .where(Sprint.project_id.in_(project_ids), Sprint.status == "active")
            .order_by(Sprint.end_date)
        )
    )
    now = datetime.now(UTC)
    meetings = list(
        db.scalars(
            select(Meeting)
            .join(MeetingParticipant)
            .where(MeetingParticipant.user_id == user.id, Meeting.end >= now)
            .order_by(Meeting.start)
            .limit(8)
        )
    )
    events, _, _ = calendar_feed(db, user, now, now + timedelta(days=30))
    return {
        "projects": projects,
        "teams": teams,
        "tasks": tasks,
        "active_sprints": sprints,
        "upcoming_meetings": meetings,
        "upcoming_events": events[:8],
    }


def project_overview(db: Session, project_id: str) -> dict:
    tasks = list(
        db.scalars(
            select(Task)
            .options(
                selectinload(Task.project), selectinload(Task.reporter), selectinload(Task.assignee)
            )
            .where(Task.project_id == project_id, Task.status != "done")
            .order_by(Task.updated_at.desc())
            .limit(8)
        )
    )
    sprint = db.scalar(
        select(Sprint).where(Sprint.project_id == project_id, Sprint.status == "active")
    )
    meetings = list(
        db.scalars(
            select(Meeting)
            .where(
                Meeting.scope_type == "project",
                Meeting.scope_id == project_id,
                Meeting.end >= datetime.now(UTC),
            )
            .order_by(Meeting.start)
            .limit(5)
        )
    )
    documents = list(
        db.scalars(
            select(Document)
            .where(Document.project_id == project_id)
            .order_by(Document.updated_at.desc())
            .limit(5)
        )
    )
    member_count = int(
        db.scalar(
            select(func.count(func.distinct(team_members.c.user_id)))
            .select_from(project_teams)
            .join(team_members, team_members.c.team_id == project_teams.c.team_id)
            .where(project_teams.c.project_id == project_id)
        )
        or 0
    )
    total_tracked_minutes = int(
        db.scalar(
            select(func.coalesce(func.sum(Task.tracked_minutes), 0)).where(
                Task.project_id == project_id
            )
        )
        or 0
    )
    return {
        "tasks": tasks,
        "active_sprint": sprint,
        "upcoming_meetings": meetings,
        "recent_documents": documents,
        "member_count": member_count,
        "total_tracked_minutes": total_tracked_minutes,
    }
