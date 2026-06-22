from collections.abc import Generator
from pathlib import Path

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from backend.app.core.config import PROJECT_ROOT, get_settings


settings = get_settings()

VALID_SESSIONS = {"personal", "demo"}

_SESSION_DB_PATHS: dict[str, str] = {
    "personal": settings.database_url,
    "demo": settings.database_url.replace("finex.db", "finex_demo.db"),
}

_engines: dict[str, Engine] = {}
_factories: dict[str, sessionmaker] = {}


def _ensure_sqlite_parent(database_url: str) -> None:
    if not database_url.startswith("sqlite:///"):
        return

    raw_path = database_url.removeprefix("sqlite:///")
    if raw_path == ":memory:":
        return

    db_path = Path(raw_path)
    if not db_path.is_absolute():
        db_path = PROJECT_ROOT / db_path
    db_path.parent.mkdir(parents=True, exist_ok=True)


def _connect_args(database_url: str) -> dict[str, bool]:
    if database_url.startswith("sqlite"):
        return {"check_same_thread": False}
    return {}


def _get_or_create_engine(session_name: str) -> Engine:
    if session_name not in _engines:
        url = _SESSION_DB_PATHS.get(session_name, _SESSION_DB_PATHS["personal"])
        _ensure_sqlite_parent(url)
        eng = create_engine(url, connect_args=_connect_args(url), future=True)
        _engines[session_name] = eng
        _factories[session_name] = sessionmaker(
            bind=eng,
            autoflush=False,
            autocommit=False,
            expire_on_commit=False,
        )
    return _engines[session_name]


def db_url_for(session_name: str) -> str:
    return _SESSION_DB_PATHS.get(session_name, _SESSION_DB_PATHS["personal"])


def dispose_engine(session_name: str) -> None:
    """Dispose and remove a cached engine (used when resetting demo DB)."""
    if session_name in _engines:
        _engines[session_name].dispose()
        del _engines[session_name]
        del _factories[session_name]


# Bootstrap the personal engine at import time (keeps existing behaviour)
_get_or_create_engine("personal")

# Backwards-compatible aliases used by existing code
engine = _engines["personal"]
SessionLocal = _factories["personal"]


def get_session(session_name: str = "personal") -> Generator[Session, None, None]:
    _get_or_create_engine(session_name)
    with _factories[session_name]() as session:
        yield session
