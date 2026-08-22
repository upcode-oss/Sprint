from fastapi import APIRouter, Depends, status

from app.api.dependencies import CurrentUser, DBSession, require_permission
from app.models.identity import User
from app.models.project import KanbanColumn, Task
from app.permissions.catalog import PermissionKey
from app.schemas.common import UUIDString
from app.schemas.project import (
    BoardResponse,
    KanbanColumnCreate,
    KanbanColumnResponse,
    TaskMove,
    TaskResponse,
)
from app.services.access_service import require_project_access
from app.services.task_service import board, create_column, get_task, move_task

router = APIRouter(prefix="/projects/{project_id}/board", tags=["boards"])


@router.get("", response_model=BoardResponse)
def board_detail(
    project_id: UUIDString,
    db: DBSession,
    current: CurrentUser,
    _: User = Depends(require_permission(PermissionKey.KANBAN_VIEW)),
) -> BoardResponse:
    require_project_access(db, current, project_id)
    columns, tasks = board(db, project_id)
    return BoardResponse(columns=columns, tasks=tasks)


@router.post("/columns", response_model=KanbanColumnResponse, status_code=status.HTTP_201_CREATED)
def column_create(
    project_id: UUIDString,
    payload: KanbanColumnCreate,
    db: DBSession,
    current: CurrentUser,
    _: User = Depends(require_permission(PermissionKey.KANBAN_MANAGE)),
) -> KanbanColumn:
    require_project_access(db, current, project_id)
    return create_column(db, project_id, payload)


@router.post("/tasks/{task_id}/move", response_model=TaskResponse)
def task_move(
    project_id: UUIDString,
    task_id: UUIDString,
    payload: TaskMove,
    db: DBSession,
    current: CurrentUser,
    _: User = Depends(require_permission(PermissionKey.KANBAN_MANAGE)),
) -> Task:
    require_project_access(db, current, project_id)
    return move_task(db, get_task(db, project_id, task_id), payload, current.id)
