from sqlalchemy import exists, select
from sqlalchemy.orm import Session

from app.core.errors import APIError
from app.models.associations import project_teams, team_members
from app.models.identity import User
from app.models.project import Project, Team
from app.services.permission_service import is_admin


def accessible_project_ids_statement(user: User):
    return (
        select(project_teams.c.project_id)
        .join(team_members, team_members.c.team_id == project_teams.c.team_id)
        .where(team_members.c.user_id == user.id)
    )


def can_access_project(db: Session, user: User, project_id: str) -> bool:
    if is_admin(user):
        return bool(
            db.scalar(
                select(
                    exists().where(
                        Project.id == project_id, Project.organization_id == user.organization_id
                    )
                )
            )
        )
    membership = accessible_project_ids_statement(user).where(
        project_teams.c.project_id == project_id
    )
    return bool(db.scalar(select(membership.exists())))


def require_project_access(db: Session, user: User, project_id: str) -> Project:
    project = db.scalar(
        select(Project).where(
            Project.id == project_id, Project.organization_id == user.organization_id
        )
    )
    if project is None or not can_access_project(db, user, project_id):
        raise APIError(404, "project_not_found", "Project not found")
    return project


def can_access_team(db: Session, user: User, team_id: str) -> bool:
    if is_admin(user):
        return bool(
            db.scalar(
                select(
                    exists().where(Team.id == team_id, Team.organization_id == user.organization_id)
                )
            )
        )
    return bool(
        db.scalar(
            select(
                exists().where(team_members.c.team_id == team_id, team_members.c.user_id == user.id)
            )
        )
    )
