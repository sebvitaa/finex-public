from typing import Annotated

from fastapi import APIRouter, Header
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.app.api.deps import get_db
from backend.app.db.session import VALID_SESSIONS, dispose_engine

router = APIRouter(prefix="/session", tags=["session"])


def _resolve_session(x_finex_session: str | None) -> str:
    return x_finex_session if x_finex_session in VALID_SESSIONS else "personal"


@router.get("/info")
def session_info(x_finex_session: Annotated[str | None, Header()] = None) -> dict:
    session_name = _resolve_session(x_finex_session)
    labels = {
        "personal": "Personal",
        "demo": "Demo · Presentación",
    }
    return {
        "session": session_name,
        "label": labels.get(session_name, session_name),
        "is_demo": session_name == "demo",
    }


@router.post("/demo/reset", status_code=200)
def reset_demo_session() -> dict:
    """Wipe and re-seed the demo database with fresh RANDOM data.

    Does NOT touch the personal DB. A new random seed is generated on every call,
    so each "Reiniciar datos" press reshuffles the fictional dataset.
    """
    import secrets
    from pathlib import Path

    from backend.app.core.config import PROJECT_ROOT
    from backend.app.db.init_db import init_demo_db
    from backend.app.db.session import db_url_for

    # Resolve the demo DB file path
    demo_url = db_url_for("demo")
    raw_path = demo_url.removeprefix("sqlite:///")
    db_path = Path(raw_path)
    if not db_path.is_absolute():
        db_path = PROJECT_ROOT / db_path

    # Dispose any cached engine so the file can be deleted cleanly
    dispose_engine("demo")

    # Delete the file if it exists
    if db_path.exists():
        db_path.unlink()

    # Re-init migrations + seeds + demo data with a fresh random seed
    init_demo_db(seed=secrets.randbelow(2**31 - 1) + 1)

    return {"status": "ok", "message": "Demo session reset successfully"}
