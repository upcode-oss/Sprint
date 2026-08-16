from collections.abc import Generator

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session

import app.models  # noqa: F401
from app.core.security import hash_password
from app.db.base import Base
from app.models.identity import Organization, Role, User
from app.models.project import Project, Team
from app.services.permission_service import create_admin_role
from app.services.setup_service import create_default_columns


@pytest.fixture
def db(tmp_path) -> Generator[Session, None, None]:
    engine = create_engine(
        f"sqlite:///{tmp_path / 'test.db'}", connect_args={"check_same_thread": False}
    )

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection, _) -> None:
        cursor = connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    with Session(engine, expire_on_commit=False) as session:
        yield session
        session.rollback()
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def workspace(db: Session) -> dict[str, object]:
    organization = Organization(name="Test Organization")
    db.add(organization)
    db.flush()
    admin_role = create_admin_role(db, organization)
    viewer_role = Role(
        organization_id=organization.id,
        name="Viewer",
        description="Project viewer",
        permissions=[],
    )
    admin = User(
        organization_id=organization.id,
        username="admin",
        email="admin@example.test",
        first_name="Ada",
        last_name="Admin",
        password_hash=hash_password("AdminPassword123"),
        roles=[admin_role],
    )
    member = User(
        organization_id=organization.id,
        username="member",
        email="member@example.test",
        first_name="Mira",
        last_name="Member",
        password_hash=hash_password("MemberPassword123"),
        roles=[viewer_role],
    )
    outsider = User(
        organization_id=organization.id,
        username="outsider",
        email="outsider@example.test",
        first_name="Otto",
        last_name="Outside",
        password_hash=hash_password("OutsidePassword123"),
        roles=[viewer_role],
    )
    db.add_all([viewer_role, admin, member, outsider])
    db.flush()
    team = Team(
        organization_id=organization.id,
        name="Delivery",
        description="Delivery team",
        members=[member],
    )
    db.add(team)
    db.flush()
    project = Project(
        organization_id=organization.id,
        name="sprint",
        key="sprint",
        status="active",
        teams=[team],
    )
    db.add(project)
    db.flush()
    project.columns = create_default_columns(project.id)
    db.commit()
    return {
        "organization": organization,
        "admin_role": admin_role,
        "viewer_role": viewer_role,
        "admin": admin,
        "member": member,
        "outsider": outsider,
        "team": team,
        "project": project,
    }
