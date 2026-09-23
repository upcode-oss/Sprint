from pathlib import Path

from alembic.config import Config

from alembic import command


def upgrade_database(database_url: str) -> None:
    backend_root = Path(__file__).resolve().parents[2]
    configuration = Config(str(backend_root / "alembic.ini"))
    configuration.set_main_option("script_location", str(backend_root / "alembic"))
    configuration.set_main_option("sqlalchemy.url", database_url.replace("%", "%%"))
    command.upgrade(configuration, "head")
