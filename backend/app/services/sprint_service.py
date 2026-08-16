from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.errors import APIError
from app.models.project import KanbanColumn, Sprint, Task
from app.schemas.project import SprintCompleteRequest, SprintCreate, SprintUpdate


def get_sprint(db: Session, project_id: str, sprint_id: str) -> Sprint:
    sprint = db.scalar(
        select(Sprint)
        .options(
            selectinload(Sprint.tasks).selectinload(Task.project),
            selectinload(Sprint.tasks).selectinload(Task.assignee),
            selectinload(Sprint.tasks).selectinload(Task.reporter),
        )
        .where(Sprint.id == sprint_id, Sprint.project_id == project_id)
        .execution_options(populate_existing=True)
    )
    if sprint is None:
        raise APIError(404, "sprint_not_found", "Sprint not found")
    return sprint


def list_sprints(db: Session, project_id: str, status: str | None = None) -> list[Sprint]:
    statement = (
        select(Sprint)
        .options(
            selectinload(Sprint.tasks).selectinload(Task.project),
            selectinload(Sprint.tasks).selectinload(Task.assignee),
            selectinload(Sprint.tasks).selectinload(Task.reporter),
        )
        .where(Sprint.project_id == project_id)
    )
    if status:
        statement = statement.where(Sprint.status == status)
    return list(db.scalars(statement.order_by(Sprint.created_at.desc())))


def create_sprint(db: Session, project_id: str, payload: SprintCreate) -> Sprint:
    if payload.start_date and payload.end_date and payload.start_date > payload.end_date:
        raise APIError(422, "invalid_dates", "End date cannot precede start date")
    sprint = Sprint(project_id=project_id, **payload.model_dump())
    db.add(sprint)
    db.commit()
    return get_sprint(db, project_id, sprint.id)


def update_sprint(db: Session, sprint: Sprint, payload: SprintUpdate) -> Sprint:
    if sprint.status in {"completed", "cancelled"}:
        raise APIError(409, "sprint_closed", "Closed sprints cannot be edited")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(sprint, key, value)
    if sprint.start_date and sprint.end_date and sprint.start_date > sprint.end_date:
        raise APIError(422, "invalid_dates", "End date cannot precede start date")
    db.commit()
    return get_sprint(db, sprint.project_id, sprint.id)


def start_sprint(db: Session, sprint: Sprint) -> Sprint:
    active = db.scalar(
        select(Sprint.id).where(
            Sprint.project_id == sprint.project_id,
            Sprint.status == "active",
            Sprint.id != sprint.id,
        )
    )
    if active:
        raise APIError(409, "active_sprint_exists", "This project already has an active sprint")
    if sprint.status != "planned":
        raise APIError(409, "invalid_sprint_state", "Only planned sprints can be started")
    sprint.status = "active"
    db.commit()
    return get_sprint(db, sprint.project_id, sprint.id)


def complete_sprint(db: Session, sprint: Sprint, payload: SprintCompleteRequest) -> Sprint:
    if sprint.status != "active":
        raise APIError(409, "invalid_sprint_state", "Only an active sprint can be completed")
    done_column_ids = set(
        db.scalars(
            select(KanbanColumn.id).where(
                KanbanColumn.project_id == sprint.project_id, KanbanColumn.is_done.is_(True)
            )
        )
    )
    incomplete = [task for task in sprint.tasks if task.kanban_column_id not in done_column_ids]
    if payload.incomplete_action == "sprint":
        target = get_sprint(db, sprint.project_id, payload.target_sprint_id or "")
        if target.id == sprint.id or target.status != "planned":
            raise APIError(422, "invalid_target_sprint", "Target must be another planned sprint")
        for task in incomplete:
            task.sprint_id = target.id
    else:
        for task in incomplete:
            task.sprint_id = None
    sprint.status = "completed"
    db.commit()
    return get_sprint(db, sprint.project_id, sprint.id)


def cancel_sprint(db: Session, sprint: Sprint) -> Sprint:
    if sprint.status in {"completed", "cancelled"}:
        raise APIError(409, "invalid_sprint_state", "Sprint is already closed")
    for task in sprint.tasks:
        task.sprint_id = None
    sprint.status = "cancelled"
    db.commit()
    return get_sprint(db, sprint.project_id, sprint.id)
