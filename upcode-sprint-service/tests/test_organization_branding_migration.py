from pathlib import Path

from sqlalchemy import create_engine, inspect, text

from app.db.migrations import upgrade_database


def test_organization_branding_migration_preserves_existing_organization(tmp_path: Path) -> None:
    database = tmp_path / "legacy-branding.db"
    url = f"sqlite:///{database}"
    engine = create_engine(url)
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                CREATE TABLE organizations (
                    id VARCHAR(36) PRIMARY KEY,
                    name VARCHAR(200) NOT NULL
                )
                """
            )
        )
        connection.execute(
            text("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL PRIMARY KEY)")
        )
        connection.execute(
            text("INSERT INTO alembic_version (version_num) VALUES ('20260817_0002')")
        )
        connection.execute(
            text(
                "INSERT INTO organizations (id, name) "
                "VALUES ('00000000-0000-4000-8000-000000000001', 'Existing Organization')"
            )
        )
    engine.dispose()

    upgrade_database(url)

    engine = create_engine(url)
    with engine.connect() as connection:
        columns = {column["name"] for column in inspect(connection).get_columns("organizations")}
        assert {"logo_key", "logo_mime_type"}.issubset(columns)
        assert connection.scalar(text("SELECT name FROM organizations")) == "Existing Organization"
        assert connection.scalar(text("SELECT logo_key FROM organizations")) is None
    engine.dispose()
