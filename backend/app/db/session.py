from collections.abc import Generator
from threading import RLock

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.core.installation import installation_store

_lock = RLock()
_engine: Engine | None = None
_session_factory: sessionmaker[Session] | None = None
_database_url: str | None = None


def _engine_options(url: str) -> dict[str, object]:
    options: dict[str, object] = {"pool_pre_ping": True}
    if url.startswith("sqlite"):
        options["connect_args"] = {"check_same_thread": False}
    return options


def configure_engine(url: str) -> Engine:
    global _database_url, _engine, _session_factory
    with _lock:
        if _engine is not None and _database_url == url:
            return _engine
        new_engine = create_engine(url, **_engine_options(url))
        if url.startswith("sqlite"):

            @event.listens_for(new_engine, "connect")
            def enable_sqlite_foreign_keys(dbapi_connection: object, _: object) -> None:
                cursor = dbapi_connection.cursor()  # type: ignore[attr-defined]
                cursor.execute("PRAGMA foreign_keys=ON")
                cursor.close()

        old_engine = _engine
        _engine = new_engine
        _database_url = url
        _session_factory = sessionmaker(bind=new_engine, expire_on_commit=False)
        if old_engine is not None:
            old_engine.dispose()
        return new_engine


def current_database_url() -> str:
    return installation_store.configured_database_url() or settings.database_url


def get_engine() -> Engine:
    return configure_engine(current_database_url())


def get_session_factory() -> sessionmaker[Session]:
    get_engine()
    assert _session_factory is not None
    return _session_factory


def get_db() -> Generator[Session, None, None]:
    session = get_session_factory()()
    try:
        yield session
    finally:
        session.close()
