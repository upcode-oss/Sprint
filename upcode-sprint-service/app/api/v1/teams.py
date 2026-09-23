from fastapi import APIRouter, Depends, Query, status

from app.api.dependencies import CurrentUser, DBSession, require_permission
from app.models.identity import User
from app.models.project import Team
from app.permissions.catalog import PermissionKey
from app.schemas.common import IDListRequest, MessageResponse, PaginatedResponse, UUIDString
from app.schemas.project import TeamCreate, TeamResponse, TeamUpdate
from app.services.team_project_service import (
    create_team,
    get_team,
    list_teams,
    set_team_members,
    update_team,
)

router = APIRouter(prefix="/teams", tags=["teams"])


@router.get("", response_model=PaginatedResponse[TeamResponse])
def teams_list(
    db: DBSession,
    current: CurrentUser,
    _: User = Depends(require_permission(PermissionKey.TEAMS_VIEW)),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    search: str | None = Query(default=None, max_length=200),
) -> PaginatedResponse[TeamResponse]:
    items, meta = list_teams(db, current, page, page_size, search)
    return PaginatedResponse(items=items, meta=meta)


@router.post("", response_model=TeamResponse, status_code=status.HTTP_201_CREATED)
def team_create(
    payload: TeamCreate,
    db: DBSession,
    current: CurrentUser,
    _: User = Depends(require_permission(PermissionKey.TEAMS_CREATE)),
) -> Team:
    return create_team(db, current.organization_id, payload)


@router.get("/{team_id}", response_model=TeamResponse)
def team_detail(
    team_id: UUIDString,
    db: DBSession,
    current: CurrentUser,
    _: User = Depends(require_permission(PermissionKey.TEAMS_VIEW)),
) -> Team:
    return get_team(db, current.organization_id, team_id)


@router.patch("/{team_id}", response_model=TeamResponse)
def team_update(
    team_id: UUIDString,
    payload: TeamUpdate,
    db: DBSession,
    current: CurrentUser,
    _: User = Depends(require_permission(PermissionKey.TEAMS_EDIT)),
) -> Team:
    return update_team(db, get_team(db, current.organization_id, team_id), payload)


@router.put("/{team_id}/members", response_model=TeamResponse)
def team_members_update(
    team_id: UUIDString,
    payload: IDListRequest,
    db: DBSession,
    current: CurrentUser,
    _: User = Depends(require_permission(PermissionKey.TEAMS_MANAGE_MEMBERS)),
) -> Team:
    return set_team_members(db, get_team(db, current.organization_id, team_id), payload.ids)


@router.delete("/{team_id}", response_model=MessageResponse)
def team_delete(
    team_id: UUIDString,
    db: DBSession,
    current: CurrentUser,
    _: User = Depends(require_permission(PermissionKey.TEAMS_DELETE)),
) -> MessageResponse:
    team = get_team(db, current.organization_id, team_id)
    db.delete(team)
    db.commit()
    return MessageResponse(message="Team deleted")
