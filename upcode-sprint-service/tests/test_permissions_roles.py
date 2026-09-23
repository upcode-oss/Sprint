import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import APIError
from app.models.identity import Permission, Role
from app.permissions.catalog import ALL_PERMISSIONS, PermissionKey
from app.services.identity_service import delete_role, protect_last_active_admin
from app.services.permission_service import (
    effective_permission_keys,
    require_permissions,
    sync_permission_catalog,
)


def test_effective_permissions_are_role_union(db: Session, workspace: dict[str, object]) -> None:
    member = workspace["member"]
    viewer = workspace["viewer_role"]
    permissions = {item.key: item for item in db.scalars(select(Permission)).all()}
    viewer.permissions = [permissions[PermissionKey.PROJECTS_VIEW]]
    editor = Role(
        organization_id=member.organization_id,
        name="Editor",
        permissions=[permissions[PermissionKey.PROJECTS_EDIT]],
    )
    member.roles.append(editor)
    db.add(editor)
    db.commit()

    assert effective_permission_keys(member) == {
        PermissionKey.PROJECTS_VIEW,
        PermissionKey.PROJECTS_EDIT,
    }
    require_permissions(member, [PermissionKey.PROJECTS_VIEW])
    with pytest.raises(APIError) as error:
        require_permissions(member, [PermissionKey.PROJECTS_DELETE])
    assert error.value.status_code == 403


def test_admin_role_is_synced_and_cannot_be_deleted(
    db: Session, workspace: dict[str, object]
) -> None:
    admin_role = workspace["admin_role"]
    sync_permission_catalog(db)
    db.commit()
    assert {item.key for item in admin_role.permissions} == {item.value for item in ALL_PERMISSIONS}
    with pytest.raises(APIError) as error:
        delete_role(db, admin_role)
    assert error.value.code == "system_role_immutable"


def test_last_active_admin_cannot_be_demoted(db: Session, workspace: dict[str, object]) -> None:
    admin = workspace["admin"]
    viewer_role = workspace["viewer_role"]
    with pytest.raises(APIError) as error:
        protect_last_active_admin(db, admin, next_role_ids=[viewer_role.id])
    assert error.value.code == "last_admin_required"
