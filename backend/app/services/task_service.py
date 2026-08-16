from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.errors import APIError
from app.models.project import KanbanColumn, Project, Task
from app.schemas.project import KanbanColumnCreate, TaskCreate, TaskMove, TaskUpdate
from app.services.team_project_service import project_members


def _validate_task_relations(
    db: Session,
    project_id: str,
    assignee_id: str | None,
    sprint_id: str | None,
) -> None:
    if assignee_id and assignee_id not in {user.id for user in project_members(db, project_id)}:
        raise APIError(422, "invalid_assignee", "Assignee must be a project member")
    if sprint_id:
        from app.models.project import Sprint

        if not db.scalar(
            select(Sprint.id).where(Sprint.id == sprint_id, Sprint.project_id == project_id)
        ):
            raise APIError(422, "invalid_sprint", "Sprint does not belong to this project")


def get_task(db: Session, project_id: str, task_id: str) -> Task:
    task = db.scalar(
        select(Task)
        .options(
            selectinload(Task.project),
            selectinload(Task.assignee),
            selectinload(Task.reporter),
        )
        .where(Task.id == task_id, Task.project_id == project_id)
    )
    if task is None:
        raise APIError(404, "task_not_found", "Task not found")
    return task


def list_tasks(
    db: Session,
    project_id: str,
    status: str | None = None,
    sprint_id: str | None = None,
    assignee_id: str | None = None,
) -> list[Task]:
    statement = (
        select(Task)
        .options(
            selectinload(Task.project),
            selectinload(Task.assignee),
            selectinload(Task.reporter),
        )
        .where(Task.project_id == project_id)
    )
    if status:
        statement = statement.where(Task.status == status)
    if sprint_id:
        statement = statement.where(Task.sprint_id == sprint_id)
    if assignee_id:
        statement = statement.where(Task.assignee_id == assignee_id)
    return list(db.scalars(statement.order_by(Task.position, Task.created_at)))


def create_task(db: Session, project: Project, reporter_id: str, payload: TaskCreate) -> Task:
    _validate_task_relations(db, project.id, payload.assignee_id, payload.sprint_id)
    locked_project = db.scalar(select(Project).where(Project.id == project.id).with_for_update())
    if locked_project is None:
        raise APIError(404, "project_not_found", "Project not found")
    default_column = db.scalar(
        select(KanbanColumn)
        .where(KanbanColumn.project_id == project.id)
        .order_by(KanbanColumn.position)
        .limit(1)
    )
    max_position = (
        db.scalar(select(func.max(Task.position)).where(Task.kanban_column_id == default_column.id))
        if default_column
        else None
    )
    locked_project.task_counter += 1
    task = Task(
        project_id=project.id,
        number=locked_project.task_counter,
        title=payload.title.strip(),
        description=payload.description,
        type=payload.type,
        priority=payload.priority,
        assignee_id=payload.assignee_id,
        reporter_id=reporter_id,
        sprint_id=payload.sprint_id,
        due_date=payload.due_date,
        kanban_column_id=default_column.id if default_column else None,
        status=default_column.key if default_column else "backlog",
        position=Decimal(max_position or 0) + Decimal("1000"),
    )
    db.add(task)
    db.commit()
    return get_task(db, project.id, task.id)


def update_task(db: Session, task: Task, payload: TaskUpdate) -> Task:
    assignee_id = (
        payload.assignee_id if "assignee_id" in payload.model_fields_set else task.assignee_id
    )
    sprint_id = payload.sprint_id if "sprint_id" in payload.model_fields_set else task.sprint_id
    _validate_task_relations(db, task.project_id, assignee_id, sprint_id)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(task, key, value)
    db.commit()
    return get_task(db, task.project_id, task.id)


def move_task(db: Session, task: Task, payload: TaskMove) -> Task:
    column = db.scalar(
        select(KanbanColumn).where(
            KanbanColumn.id == payload.column_id, KanbanColumn.project_id == task.project_id
        )
    )
    if column is None:
        raise APIError(422, "invalid_column", "Kanban column does not belong to this project")

    before = db.get(Task, payload.before_task_id) if payload.before_task_id else None
    after = db.get(Task, payload.after_task_id) if payload.after_task_id else None
    for neighbor in (before, after):
        if neighbor and (
            neighbor.project_id != task.project_id or neighbor.kanban_column_id != column.id
        ):
            raise APIError(422, "invalid_position", "Neighbor task is not in the target column")

    if before and after:
        position = (Decimal(before.position) + Decimal(after.position)) / 2
    elif before:
        previous_position = db.scalar(
            select(func.max(Task.position)).where(
                Task.kanban_column_id == column.id,
                Task.id != task.id,
                Task.position < before.position,
            )
        )
        position = (
            (Decimal(previous_position) + Decimal(before.position)) / 2
            if previous_position is not None
            else Decimal(before.position) - Decimal("1000")
        )
    elif after:
        next_position = db.scalar(
            select(func.min(Task.position)).where(
                Task.kanban_column_id == column.id,
                Task.id != task.id,
                Task.position > after.position,
            )
        )
        position = (
            (Decimal(after.position) + Decimal(next_position)) / 2
            if next_position is not None
            else Decimal(after.position) + Decimal("1000")
        )
    else:
        maximum = db.scalar(
            select(func.max(Task.position)).where(Task.kanban_column_id == column.id)
        )
        position = Decimal(maximum or 0) + Decimal("1000")
    task.kanban_column_id = column.id
    task.status = column.key
    task.position = position
    db.commit()
    return get_task(db, task.project_id, task.id)


def board(db: Session, project_id: str) -> tuple[list[KanbanColumn], list[Task]]:
    columns = list(
        db.scalars(
            select(KanbanColumn)
            .where(KanbanColumn.project_id == project_id)
            .order_by(KanbanColumn.position)
        )
    )
    return columns, list_tasks(db, project_id)


def create_column(db: Session, project_id: str, payload: KanbanColumnCreate) -> KanbanColumn:
    column = KanbanColumn(project_id=project_id, **payload.model_dump())
    db.add(column)
    db.commit()
    db.refresh(column)
    return column
