from fastapi import APIRouter, Depends
from sqlalchemy import select

from app.api.dependencies import DBSession, require_permission
from app.models.identity import Permission, User
from app.permissions.catalog import PermissionKey
from app.schemas.identity import PermissionResponse

router = APIRouter(prefix="/permissions", tags=["permissions"])


@router.get("", response_model=list[PermissionResponse])
def permissions_list(
    db: DBSession,
    _: User = Depends(require_permission(PermissionKey.ROLES_VIEW)),
) -> list[Permission]:
    return list(db.scalars(select(Permission).order_by(Permission.key)))
