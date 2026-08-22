from fastapi import APIRouter, Depends, Query, status

from app.api.dependencies import CurrentUser, DBSession, require_permission
from app.models.identity import User
from app.models.project import Sprint
from app.permissions.catalog import PermissionKey
from app.schemas.common import UUIDString
from app.schemas.project import (
    SprintCompleteRequest,
    SprintCreate,
    SprintResponse,
    SprintUpdate,
)
from app.services.access_service import require_project_access
from app.services.sprint_service import (
    cancel_sprint,
    complete_sprint,
    create_sprint,
    get_sprint,
    list_sprints,
    start_sprint,
    update_sprint,
)

router = APIRouter(prefix="/projects/{project_id}/sprints", tags=["sprints"])


@router.get("", response_model=list[SprintResponse])
def sprints_list(
    project_id: UUIDString,
    db: DBSession,
    current: CurrentUser,
    _: User = Depends(require_permission(PermissionKey.SCRUM_VIEW)),
    sprint_status: str | None = Query(default=None, alias="status"),
) -> list[Sprint]:
    require_project_access(db, current, project_id)
    return list_sprints(db, project_id, sprint_status)


@router.post("", response_model=SprintResponse, status_code=status.HTTP_201_CREATED)
def sprint_create(
    project_id: UUIDString,
    payload: SprintCreate,
    db: DBSession,
    current: CurrentUser,
    _: User = Depends(require_permission(PermissionKey.SCRUM_MANAGE)),
) -> Sprint:
    require_project_access(db, current, project_id)
    return create_sprint(db, project_id, payload)


@router.patch("/{sprint_id}", response_model=SprintResponse)
def sprint_update(
    project_id: UUIDString,
    sprint_id: UUIDString,
    payload: SprintUpdate,
    db: DBSession,
    current: CurrentUser,
    _: User = Depends(require_permission(PermissionKey.SCRUM_MANAGE)),
) -> Sprint:
    require_project_access(db, current, project_id)
    return update_sprint(db, get_sprint(db, project_id, sprint_id), payload)


@router.post("/{sprint_id}/start", response_model=SprintResponse)
def sprint_start(
    project_id: UUIDString,
    sprint_id: UUIDString,
    db: DBSession,
    current: CurrentUser,
    _: User = Depends(require_permission(PermissionKey.SCRUM_MANAGE)),
) -> Sprint:
    require_project_access(db, current, project_id)
    return start_sprint(db, get_sprint(db, project_id, sprint_id))


@router.post("/{sprint_id}/complete", response_model=SprintResponse)
def sprint_complete(
    project_id: UUIDString,
    sprint_id: UUIDString,
    payload: SprintCompleteRequest,
    db: DBSession,
    current: CurrentUser,
    _: User = Depends(require_permission(PermissionKey.SCRUM_MANAGE)),
) -> Sprint:
    require_project_access(db, current, project_id)
    return complete_sprint(db, get_sprint(db, project_id, sprint_id), payload, current.id)


@router.post("/{sprint_id}/cancel", response_model=SprintResponse)
def sprint_cancel(
    project_id: UUIDString,
    sprint_id: UUIDString,
    db: DBSession,
    current: CurrentUser,
    _: User = Depends(require_permission(PermissionKey.SCRUM_MANAGE)),
) -> Sprint:
    require_project_access(db, current, project_id)
    return cancel_sprint(db, get_sprint(db, project_id, sprint_id), current.id)
