from fastapi import APIRouter, Depends, Query, status

from app.api.dependencies import CurrentUser, DBSession, require_permission
from app.models.identity import User
from app.models.project import Task
from app.permissions.catalog import PermissionKey
from app.schemas.common import MessageResponse, UUIDString
from app.schemas.project import TaskCreate, TaskResponse, TaskUpdate
from app.services.access_service import require_project_access
from app.services.task_service import create_task, get_task, list_tasks, update_task

router = APIRouter(prefix="/projects/{project_id}/tasks", tags=["tasks"])


@router.get("", response_model=list[TaskResponse])
def tasks_list(
    project_id: UUIDString,
    db: DBSession,
    current: CurrentUser,
    _: User = Depends(require_permission(PermissionKey.KANBAN_VIEW)),
    task_status: str | None = Query(default=None, alias="status"),
    sprint_id: UUIDString | None = None,
    assignee_id: UUIDString | None = None,
) -> list[Task]:
    require_project_access(db, current, project_id)
    return list_tasks(db, project_id, task_status, sprint_id, assignee_id)


@router.post("", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
def task_create(
    project_id: UUIDString,
    payload: TaskCreate,
    db: DBSession,
    current: CurrentUser,
    _: User = Depends(require_permission(PermissionKey.KANBAN_MANAGE)),
) -> Task:
    project = require_project_access(db, current, project_id)
    return create_task(db, project, current.id, payload)


@router.get("/{task_id}", response_model=TaskResponse)
def task_detail(
    project_id: UUIDString,
    task_id: UUIDString,
    db: DBSession,
    current: CurrentUser,
    _: User = Depends(require_permission(PermissionKey.KANBAN_VIEW)),
) -> Task:
    require_project_access(db, current, project_id)
    return get_task(db, project_id, task_id)


@router.patch("/{task_id}", response_model=TaskResponse)
def task_update(
    project_id: UUIDString,
    task_id: UUIDString,
    payload: TaskUpdate,
    db: DBSession,
    current: CurrentUser,
    _: User = Depends(require_permission(PermissionKey.KANBAN_MANAGE)),
) -> Task:
    require_project_access(db, current, project_id)
    return update_task(db, get_task(db, project_id, task_id), payload)


@router.delete("/{task_id}", response_model=MessageResponse)
def task_delete(
    project_id: UUIDString,
    task_id: UUIDString,
    db: DBSession,
    current: CurrentUser,
    _: User = Depends(require_permission(PermissionKey.KANBAN_MANAGE)),
) -> MessageResponse:
    require_project_access(db, current, project_id)
    task = get_task(db, project_id, task_id)
    db.delete(task)
    db.commit()
    return MessageResponse(message="Task deleted")
