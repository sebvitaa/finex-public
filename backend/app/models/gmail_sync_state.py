from datetime import datetime

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.base import Base
from backend.app.models.mixins import TimestampMixin


class GmailSyncState(TimestampMixin, Base):
    __tablename__ = "gmail_sync_state"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    label_id: Mapped[str] = mapped_column(String(160), unique=True, nullable=False, index=True)
    history_id: Mapped[str | None] = mapped_column(String(160), index=True)
    watch_expiration_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_poll_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_push_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
