from sqlalchemy.orm import Session

from app.services.access_service import can_access_project
from app.services.team_project_service import project_members, set_team_members


def test_team_membership_is_many_to_many_and_replaceable(
    db: Session, workspace: dict[str, object]
) -> None:
    team = workspace["team"]
    member = workspace["member"]
    outsider = workspace["outsider"]
    updated = set_team_members(db, team, [member.id, outsider.id])
    assert {user.id for user in updated.members} == {member.id, outsider.id}
    assert team in member.teams
    assert team in outsider.teams


def test_project_access_and_member_view_follow_team_membership(
    db: Session, workspace: dict[str, object]
) -> None:
    project = workspace["project"]
    member = workspace["member"]
    outsider = workspace["outsider"]
    admin = workspace["admin"]
    assert can_access_project(db, member, project.id)
    assert not can_access_project(db, outsider, project.id)
    assert can_access_project(db, admin, project.id)
    assert [user.id for user in project_members(db, project.id)] == [member.id]
