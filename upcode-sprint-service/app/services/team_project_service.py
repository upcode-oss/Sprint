from sqlalchemy import asc, desc, or_, select
from sqlalchemy.orm import Session, selectinload

from app.core.errors import APIError
from app.models.associations import project_teams, team_members
from app.models.identity import User
from app.models.project import Project, Team
from app.repositories.pagination import paginate
from app.schemas.common import PaginationMeta
from app.schemas.project import ProjectCreate, ProjectUpdate, TeamCreate, TeamUpdate
from app.services.access_service import accessible_project_ids_statement
from app.services.permission_service import is_admin
from app.services.setup_service import create_default_columns


def _members_for_ids(db: Session, organization_id: str, ids: list[str]) -> list[User]:
    if not ids:
        return []
    users = list(
        db.scalars(select(User).where(User.organization_id == organization_id, User.id.in_(ids)))
    )
    if len(users) != len(set(ids)):
        raise APIError(422, "invalid_members", "One or more users are invalid")
    return users


def list_teams(
    db: Session, user: User, page: int, page_size: int, search: str | None
) -> tuple[list[Team], PaginationMeta]:
    statement = (
        select(Team)
        .options(selectinload(Team.members))
        .where(Team.organization_id == user.organization_id)
    )
    if not is_admin(user):
        statement = statement.join(team_members).where(team_members.c.user_id == user.id)
    if search:
        statement = statement.where(Team.name.ilike(f"%{search.strip()}%"))
    return paginate(db, statement.order_by(Team.name), page, page_size)


def get_team(db: Session, organization_id: str, team_id: str) -> Team:
    team = db.scalar(
        select(Team)
        .options(selectinload(Team.members))
        .where(Team.id == team_id, Team.organization_id == organization_id)
    )
    if team is None:
        raise APIError(404, "team_not_found", "Team not found")
    return team


def create_team(db: Session, organization_id: str, payload: TeamCreate) -> Team:
    team = Team(
        organization_id=organization_id,
        name=payload.name.strip(),
        description=payload.description,
        members=_members_for_ids(db, organization_id, payload.member_ids),
    )
    db.add(team)
    db.commit()
    return get_team(db, organization_id, team.id)


def update_team(db: Session, team: Team, payload: TeamUpdate) -> Team:
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(team, key, value)
    db.commit()
    return get_team(db, team.organization_id, team.id)


def set_team_members(db: Session, team: Team, member_ids: list[str]) -> Team:
    team.members = _members_for_ids(db, team.organization_id, member_ids)
    db.commit()
    return get_team(db, team.organization_id, team.id)


def list_projects(
    db: Session,
    user: User,
    page: int,
    page_size: int,
    search: str | None,
    status: str | None,
    sort: str,
    direction: str,
) -> tuple[list[Project], PaginationMeta]:
    columns = {"name": Project.name, "key": Project.key, "created_at": Project.created_at}
    order = columns.get(sort, Project.name)
    statement = (
        select(Project)
        .options(selectinload(Project.teams))
        .where(Project.organization_id == user.organization_id)
    )
    if not is_admin(user):
        statement = statement.where(Project.id.in_(accessible_project_ids_statement(user)))
    if search:
        term = f"%{search.strip()}%"
        statement = statement.where(or_(Project.name.ilike(term), Project.key.ilike(term)))
    if status:
        statement = statement.where(Project.status == status)
    return paginate(
        db, statement.order_by(desc(order) if direction == "desc" else asc(order)), page, page_size
    )


def get_project(db: Session, organization_id: str, project_id: str) -> Project:
    project = db.scalar(
        select(Project)
        .options(selectinload(Project.teams))
        .where(Project.id == project_id, Project.organization_id == organization_id)
    )
    if project is None:
        raise APIError(404, "project_not_found", "Project not found")
    return project


def _teams_for_ids(db: Session, organization_id: str, ids: list[str]) -> list[Team]:
    if not ids:
        return []
    teams = list(
        db.scalars(select(Team).where(Team.organization_id == organization_id, Team.id.in_(ids)))
    )
    if len(teams) != len(set(ids)):
        raise APIError(422, "invalid_teams", "One or more teams are invalid")
    return teams


def create_project(db: Session, organization_id: str, payload: ProjectCreate) -> Project:
    project = Project(
        organization_id=organization_id,
        name=payload.name.strip(),
        key=payload.key,
        description=payload.description,
        status=payload.status,
        start_date=payload.start_date,
        end_date=payload.end_date,
        done_task_retention_days=payload.done_task_retention_days,
        teams=_teams_for_ids(db, organization_id, payload.team_ids),
    )
    db.add(project)
    db.flush()
    project.columns = create_default_columns(project.id)
    db.commit()
    return get_project(db, organization_id, project.id)


def update_project(db: Session, project: Project, payload: ProjectUpdate) -> Project:
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(project, key, value)
    if project.start_date and project.end_date and project.start_date > project.end_date:
        raise APIError(422, "invalid_dates", "End date cannot precede start date")
    db.commit()
    return get_project(db, project.organization_id, project.id)


def set_project_teams(db: Session, project: Project, team_ids: list[str]) -> Project:
    project.teams = _teams_for_ids(db, project.organization_id, team_ids)
    db.commit()
    return get_project(db, project.organization_id, project.id)


def project_members(db: Session, project_id: str) -> list[User]:
    return list(
        db.scalars(
            select(User)
            .join(team_members, team_members.c.user_id == User.id)
            .join(project_teams, project_teams.c.team_id == team_members.c.team_id)
            .where(project_teams.c.project_id == project_id, User.is_active.is_(True))
            .order_by(User.first_name, User.last_name)
            .distinct()
        )
    )
