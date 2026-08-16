from fastapi import APIRouter, Depends, Query, status

from app.api.dependencies import CurrentUser, DBSession, require_permission
from app.models.identity import User
from app.models.project import Project
from app.permissions.catalog import PermissionKey
from app.schemas.common import IDListRequest, MessageResponse, PaginatedResponse, UUIDString
from app.schemas.dashboard import ProjectOverviewResponse
from app.schemas.identity import UserBrief
from app.schemas.project import ProjectCreate, ProjectResponse, ProjectUpdate
from app.services.access_service import require_project_access
from app.services.dashboard_service import project_overview
from app.services.team_project_service import (
    create_project,
    get_project,
    list_projects,
    project_members,
    set_project_teams,
    update_project,
)

router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("", response_model=PaginatedResponse[ProjectResponse])
def projects_list(
    db: DBSession,
    current: CurrentUser,
    _: User = Depends(require_permission(PermissionKey.PROJECTS_VIEW)),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    search: str | None = Query(default=None, max_length=200),
    status_filter: str | None = Query(default=None, alias="status"),
    sort: str = Query("name", pattern=r"^(name|key|created_at)$"),
    direction: str = Query("asc", pattern=r"^(asc|desc)$"),
) -> PaginatedResponse[ProjectResponse]:
    items, meta = list_projects(
        db, current, page, page_size, search, status_filter, sort, direction
    )
    return PaginatedResponse(items=items, meta=meta)


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
def project_create(
    payload: ProjectCreate,
    db: DBSession,
    current: CurrentUser,
    _: User = Depends(require_permission(PermissionKey.PROJECTS_CREATE)),
) -> Project:
    return create_project(db, current.organization_id, payload)


@router.get("/{project_id}", response_model=ProjectResponse)
def project_detail(
    project_id: UUIDString,
    db: DBSession,
    current: CurrentUser,
    _: User = Depends(require_permission(PermissionKey.PROJECTS_VIEW)),
) -> Project:
    require_project_access(db, current, project_id)
    return get_project(db, current.organization_id, project_id)


@router.get("/{project_id}/overview", response_model=ProjectOverviewResponse)
def overview(
    project_id: UUIDString,
    db: DBSession,
    current: CurrentUser,
    _: User = Depends(require_permission(PermissionKey.PROJECTS_VIEW)),
) -> dict:
    require_project_access(db, current, project_id)
    return project_overview(db, project_id)


@router.patch("/{project_id}", response_model=ProjectResponse)
def project_update(
    project_id: UUIDString,
    payload: ProjectUpdate,
    db: DBSession,
    current: CurrentUser,
    _: User = Depends(require_permission(PermissionKey.PROJECTS_EDIT)),
) -> Project:
    require_project_access(db, current, project_id)
    return update_project(db, get_project(db, current.organization_id, project_id), payload)


@router.put("/{project_id}/teams", response_model=ProjectResponse)
def project_teams_update(
    project_id: UUIDString,
    payload: IDListRequest,
    db: DBSession,
    current: CurrentUser,
    _: User = Depends(require_permission(PermissionKey.PROJECTS_MANAGE_MEMBERS)),
) -> Project:
    require_project_access(db, current, project_id)
    project = get_project(db, current.organization_id, project_id)
    return set_project_teams(db, project, payload.ids)


@router.get("/{project_id}/members", response_model=list[UserBrief])
def members(
    project_id: UUIDString,
    db: DBSession,
    current: CurrentUser,
    _: User = Depends(require_permission(PermissionKey.PROJECTS_VIEW)),
) -> list[User]:
    require_project_access(db, current, project_id)
    return project_members(db, project_id)


@router.delete("/{project_id}", response_model=MessageResponse)
def project_delete(
    project_id: UUIDString,
    db: DBSession,
    current: CurrentUser,
    _: User = Depends(require_permission(PermissionKey.PROJECTS_DELETE)),
) -> MessageResponse:
    require_project_access(db, current, project_id)
    project = get_project(db, current.organization_id, project_id)
    db.delete(project)
    db.commit()
    return MessageResponse(message="Project deleted")
