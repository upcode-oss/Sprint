from pathlib import Path

from sqlalchemy import URL, create_engine, func, select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.errors import APIError
from app.core.installation import installation_store
from app.core.security import hash_password
from app.db.migrations import upgrade_database
from app.db.session import configure_engine
from app.models.identity import (
    Organization,
    SMTPConfiguration,
    User,
    UserPresence,
    UserProfile,
)
from app.models.project import KanbanColumn
from app.schemas.setup import DatabaseConfiguration, SetupCompleteRequest
from app.services.permission_service import create_admin_role


def build_database_url(configuration: DatabaseConfiguration) -> str:
    if configuration.engine == "sqlite":
        raw_path = Path(configuration.sqlite_path or "sprint.db")
        path = raw_path if raw_path.is_absolute() else Path("/data") / raw_path
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise APIError(
                400, "invalid_database_path", "SQLite directory is not writable"
            ) from exc
        return f"sqlite:///{path}"

    driver = "postgresql+psycopg" if configuration.engine == "postgresql" else "mysql+pymysql"
    query = (
        {"sslmode": "require"} if configuration.ssl and configuration.engine == "postgresql" else {}
    )
    if configuration.ssl and configuration.engine in {"mysql", "mariadb"}:
        # SQLAlchemy collects ssl_* URL arguments into PyMySQL's SSL mapping.
        # This enables transport encryption even when no custom CA path is supplied.
        query = {"ssl_check_hostname": "false"}
    url = URL.create(
        drivername=driver,
        username=configuration.username,
        password=configuration.password.get_secret_value() if configuration.password else None,
        host=configuration.host,
        port=configuration.port,
        database=configuration.database,
        query=query,
    )
    return url.render_as_string(hide_password=False)


def test_database_connection(configuration: DatabaseConfiguration) -> None:
    url = build_database_url(configuration)
    engine = create_engine(url, pool_pre_ping=True)
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        raise APIError(400, "database_connection_failed", "Database connection failed") from exc
    finally:
        engine.dispose()


def complete_setup(payload: SetupCompleteRequest) -> tuple[Organization, User]:
    if installation_store.is_complete:
        raise APIError(409, "setup_already_completed", "Initial setup is already complete")

    url = build_database_url(payload.database)
    test_database_connection(payload.database)
    engine = configure_engine(url)
    upgrade_database(url)
    # The installation store is deliberately written only after the transaction
    # succeeds, so bind this bootstrap session directly to the selected engine.
    db = Session(engine, expire_on_commit=False)
    try:
        if (db.scalar(select(func.count(Organization.id))) or 0) > 0:
            raise APIError(
                409, "database_not_empty", "The selected database is already initialized"
            )

        organization = Organization(name=payload.organization_name.strip())
        db.add(organization)
        db.flush()
        admin_role = create_admin_role(db, organization)
        admin = User(
            organization_id=organization.id,
            username=payload.admin.username.strip(),
            email=str(payload.admin.email).lower(),
            first_name=payload.admin.first_name.strip(),
            last_name=payload.admin.last_name.strip(),
            password_hash=hash_password(payload.admin.password.get_secret_value()),
            roles=[admin_role],
            profile=UserProfile(timezone="UTC"),
            presence=UserPresence(),
        )
        db.add(admin)

        smtp = payload.smtp
        if smtp and smtp.enabled:
            db.add(
                SMTPConfiguration(
                    organization_id=organization.id,
                    host=smtp.host or "",
                    port=smtp.port or 0,
                    username=smtp.username,
                    password_encrypted=(
                        installation_store.encrypt(smtp.password.get_secret_value())
                        if smtp.password
                        else None
                    ),
                    encryption=smtp.encryption,
                    from_address=str(smtp.from_address),
                    from_name=smtp.from_name or payload.organization_name,
                )
            )
        db.commit()
        db.refresh(organization)
        db.refresh(admin)
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

    installation_store.save(
        {
            "setup_completed": True,
            "organization_id": organization.id,
            "database_engine": payload.database.engine,
            "database_url_encrypted": installation_store.encrypt(url),
        }
    )
    return organization, admin


DEFAULT_KANBAN_COLUMNS = (
    ("Backlog", "backlog", False),
    ("To Do", "todo", False),
    ("In Progress", "in_progress", False),
    ("Review", "review", False),
    ("Done", "done", True),
)


def create_default_columns(project_id: str) -> list[KanbanColumn]:
    return [
        KanbanColumn(project_id=project_id, name=name, key=key, position=index, is_done=is_done)
        for index, (name, key, is_done) in enumerate(DEFAULT_KANBAN_COLUMNS)
    ]
