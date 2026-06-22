from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base


class ImportRun(Base):
    __tablename__ = "import_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    source: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="pending", index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    messages_seen: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    messages_imported: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    transactions_created: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    errors_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_summary: Mapped[str | None] = mapped_column(Text)

    email_messages = relationship("EmailMessage", back_populates="import_run")

