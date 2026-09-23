from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.errors import APIError
from app.models.identity import User
from app.models.project import (
    KanbanColumn,
    Project,
    Sprint,
    Task,
    TaskActivity,
    TaskComment,
)
from app.repositories.pagination import paginate
from app.schemas.common import PaginationMeta
from app.schemas.project import (
    KanbanColumnCreate,
    TaskCommentCreate,
    TaskCreate,
    TaskMove,
    TaskUpdate,
)
from app.services.team_project_service import project_members

ActivityValue = str | int | float | bool | None
ActivityChanges = dict[str, dict[str, ActivityValue]]


def _activity_value(db: Session, field: str, value: object) -> ActivityValue:
    if value is None or isinstance(value, (str, int, float, bool)):
        if field == "assignee_id" and value:
            user = db.get(User, value)
            return user.display_name if user else str(value)
        if field == "sprint_id" and value:
            sprint = db.get(Sprint, value)
            return sprint.name if sprint else str(value)
        if field == "parent_task_id" and value:
            parent = db.get(Task, value)
            return parent.reference if parent else str(value)
        return value
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    return str(value)


def record_task_activity(
    db: Session,
    task: Task,
    actor_id: str | None,
    action: str,
    changes: ActivityChanges | None = None,
) -> None:
    db.add(
        TaskActivity(
            project_id=task.project_id,
            task_id=task.id,
            task_reference=task.reference,
            task_title=task.title,
            actor_id=actor_id,
            action=action,
            changes=changes or {},
        )
    )


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


def create_task(
    db: Session,
    project: Project,
    reporter_id: str,
    payload: TaskCreate,
    parent: Task | None = None,
) -> Task:
    _validate_task_relations(db, project.id, payload.assignee_id, payload.sprint_id)
    if parent and parent.project_id != project.id:
        raise APIError(422, "invalid_parent_task", "Parent ticket belongs to another project")
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
        tracked_seconds=payload.tracked_seconds,
        parent_task_id=parent.id if parent else None,
        kanban_column_id=default_column.id if default_column else None,
        status=default_column.key if default_column else "backlog",
        position=Decimal(max_position or 0) + Decimal("1000"),
    )
    db.add(task)
    db.flush()
    initial_values = {
        "title": task.title,
        "description": task.description,
        "type": task.type,
        "priority": task.priority,
        "assignee_id": task.assignee_id,
        "sprint_id": task.sprint_id,
        "status": task.status,
        "due_date": task.due_date,
        "tracked_seconds": task.tracked_seconds,
        "parent_task_id": task.parent_task_id,
    }
    record_task_activity(
        db,
        task,
        reporter_id,
        "created",
        {
            field: {"before": None, "after": _activity_value(db, field, value)}
            for field, value in initial_values.items()
            if value is not None
        },
    )
    db.commit()
    return get_task(db, project.id, task.id)


def update_task(db: Session, task: Task, payload: TaskUpdate, actor_id: str) -> Task:
    assignee_id = (
        payload.assignee_id if "assignee_id" in payload.model_fields_set else task.assignee_id
    )
    sprint_id = payload.sprint_id if "sprint_id" in payload.model_fields_set else task.sprint_id
    _validate_task_relations(db, task.project_id, assignee_id, sprint_id)
    changes: ActivityChanges = {}
    for key, value in payload.model_dump(exclude_unset=True).items():
        previous = getattr(task, key)
        if previous == value:
            continue
        changes[key] = {
            "before": _activity_value(db, key, previous),
            "after": _activity_value(db, key, value),
        }
        setattr(task, key, value)
    if changes:
        record_task_activity(db, task, actor_id, "updated", changes)
    db.commit()
    return get_task(db, task.project_id, task.id)


def list_task_comments(db: Session, task_id: str) -> list[TaskComment]:
    return list(
        db.scalars(
            select(TaskComment)
            .options(selectinload(TaskComment.author))
            .where(TaskComment.task_id == task_id)
            .order_by(TaskComment.created_at)
        )
    )


def list_subtasks(db: Session, project_id: str, parent_task_id: str) -> list[Task]:
    return list(
        db.scalars(
            select(Task)
            .options(
                selectinload(Task.project),
                selectinload(Task.assignee),
                selectinload(Task.reporter),
            )
            .where(Task.project_id == project_id, Task.parent_task_id == parent_task_id)
            .order_by(Task.created_at)
        )
    )


def create_task_comment(
    db: Session, task: Task, author_id: str, payload: TaskCommentCreate
) -> TaskComment:
    comment = TaskComment(task_id=task.id, author_id=author_id, body=payload.body)
    db.add(comment)
    record_task_activity(
        db,
        task,
        author_id,
        "commented",
        {"comment": {"before": None, "after": payload.body}},
    )
    db.commit()
    created = db.scalar(
        select(TaskComment)
        .options(selectinload(TaskComment.author))
        .where(TaskComment.id == comment.id)
    )
    if created is None:
        raise RuntimeError("Created task comment could not be loaded")
    return created


def move_task(db: Session, task: Task, payload: TaskMove, actor_id: str) -> Task:
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
    previous_column = db.get(KanbanColumn, task.kanban_column_id)
    previous_position = Decimal(task.position)
    previous_status = task.status
    task.kanban_column_id = column.id
    task.status = column.key
    task.position = position
    if column.is_done and not (previous_column and previous_column.is_done):
        task.completed_at = datetime.now(UTC)
    elif not column.is_done:
        task.completed_at = None
    changes: ActivityChanges = {
        "column": {
            "before": previous_column.name if previous_column else None,
            "after": column.name,
        }
    }
    if previous_status != task.status:
        changes["status"] = {"before": previous_status, "after": task.status}
    if previous_column and previous_column.id == column.id and previous_position != task.position:
        changes["order"] = {"before": "Previous position", "after": "New position"}
    record_task_activity(db, task, actor_id, "moved", changes)
    db.commit()
    return get_task(db, task.project_id, task.id)


def delete_task(db: Session, task: Task, actor_id: str) -> None:
    delete_task_activity(db, task, actor_id)
    db.delete(task)
    db.commit()


def delete_task_activity(db: Session, task: Task, actor_id: str) -> None:
    for subtask in list(task.subtasks):
        delete_task_activity(db, subtask, actor_id)
    record_task_activity(db, task, actor_id, "deleted")


def list_project_task_activity(
    db: Session, project_id: str, page: int, page_size: int
) -> tuple[list[TaskActivity], PaginationMeta]:
    statement = (
        select(TaskActivity)
        .options(selectinload(TaskActivity.actor))
        .where(TaskActivity.project_id == project_id)
        .order_by(TaskActivity.created_at.desc())
    )
    return paginate(db, statement, page, page_size)


def board(db: Session, project_id: str) -> tuple[list[KanbanColumn], list[Task]]:
    columns = list(
        db.scalars(
            select(KanbanColumn)
            .where(KanbanColumn.project_id == project_id)
            .order_by(KanbanColumn.position)
        )
    )
    project = db.get(Project, project_id)
    if project is None:
        raise APIError(404, "project_not_found", "Project not found")
    done_column_ids = [column.id for column in columns if column.is_done]
    statement = (
        select(Task)
        .options(
            selectinload(Task.project),
            selectinload(Task.assignee),
            selectinload(Task.reporter),
        )
        .where(Task.project_id == project_id)
    )
    if done_column_ids:
        cutoff = datetime.now(UTC) - timedelta(days=project.done_task_retention_days)
        statement = statement.where(
            (Task.kanban_column_id.not_in(done_column_ids))
            | Task.completed_at.is_(None)
            | (Task.completed_at > cutoff)
        )
    tasks = list(db.scalars(statement.order_by(Task.position, Task.created_at)))
    return columns, tasks


def create_column(db: Session, project_id: str, payload: KanbanColumnCreate) -> KanbanColumn:
    column = KanbanColumn(project_id=project_id, **payload.model_dump())
    db.add(column)
    db.commit()
    db.refresh(column)
    return column
