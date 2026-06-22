from collections.abc import Generator
from typing import Annotated

from fastapi import Header
from sqlalchemy.orm import Session

from backend.app.db.session import VALID_SESSIONS, get_session


def get_db(x_finex_session: Annotated[str | None, Header()] = None) -> Generator[Session, None, None]:
    session_name = x_finex_session if x_finex_session in VALID_SESSIONS else "personal"
    yield from get_session(session_name)
