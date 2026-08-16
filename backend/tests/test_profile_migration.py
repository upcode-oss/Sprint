from pathlib import Path

from sqlalchemy import create_engine, inspect, text

from app.db.migrations import upgrade_database


def test_profile_migration_backfills_existing_users(tmp_path: Path) -> None:
    database = tmp_path / "legacy.db"
    url = f"sqlite:///{database}"
    engine = create_engine(url)
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                CREATE TABLE users (
                    id VARCHAR(36) PRIMARY KEY,
                    first_name VARCHAR(100) NOT NULL,
                    last_name VARCHAR(100) NOT NULL
                )
                """
            )
        )
        connection.execute(
            text("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL PRIMARY KEY)")
        )
        connection.execute(
            text("INSERT INTO alembic_version (version_num) VALUES ('20260816_0001')")
        )
        connection.execute(
            text(
                "INSERT INTO users (id, first_name, last_name) "
                "VALUES ('00000000-0000-4000-8000-000000000001', 'Legacy', 'User')"
            )
        )
    engine.dispose()

    upgrade_database(url)

    engine = create_engine(url)
    with engine.connect() as connection:
        assert {"user_profiles", "user_contacts", "user_presences"}.issubset(
            inspect(connection).get_table_names()
        )
        assert connection.scalar(text("SELECT COUNT(*) FROM user_profiles")) == 1
        assert connection.scalar(text("SELECT timezone FROM user_profiles")) == "UTC"
        assert connection.scalar(text("SELECT COUNT(*) FROM user_presences")) == 1
        assert connection.scalar(text("SELECT first_name FROM users")) == "Legacy"
    engine.dispose()
