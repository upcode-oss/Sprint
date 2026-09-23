from sqlalchemy import create_mock_engine

import app.models  # noqa: F401
from app.db.base import Base
from app.schemas.setup import DatabaseConfiguration
from app.services.setup_service import build_database_url


def test_schema_compiles_for_all_supported_dialects() -> None:
    for url in (
        "sqlite://",
        "postgresql+psycopg://user:password@localhost/harbor",
        "mysql+pymysql://user:password@localhost/harbor",
    ):
        statements: list[str] = []

        def capture(sql, *_args, captured=statements, **_kwargs) -> None:
            captured.append(str(sql))

        engine = create_mock_engine(url, capture)
        Base.metadata.create_all(engine)
        assert statements


def test_database_urls_hide_no_fields_from_driver_and_enable_ssl() -> None:
    postgres = build_database_url(
        DatabaseConfiguration(
            engine="postgresql",
            host="database.example",
            port=5432,
            database="harbor",
            username="harbor",
            password="special:p@ssword",
            ssl=True,
        )
    )
    mysql = build_database_url(
        DatabaseConfiguration(
            engine="mysql",
            host="database.example",
            port=3306,
            database="harbor",
            username="harbor",
            password="special:p@ssword",
            ssl=True,
        )
    )
    assert "sslmode=require" in postgres
    assert "ssl_check_hostname=false" in mysql
    assert "special%3Ap%40ssword" in postgres
