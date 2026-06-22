from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base


class EmailMessage(Base):
    __tablename__ = "email_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    gmail_message_id: Mapped[str | None] = mapped_column(String(240), unique=True, index=True)
    gmail_thread_id: Mapped[str | None] = mapped_column(String(240), index=True)
    gmail_history_id: Mapped[str | None] = mapped_column(String(160), index=True)
    internet_message_id: Mapped[str | None] = mapped_column(String(240), index=True)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    sender_name: Mapped[str | None] = mapped_column(String(160))
    sender_email: Mapped[str | None] = mapped_column(String(240))
    subject: Mapped[str] = mapped_column(String(240), nullable=False)
    body_preview: Mapped[str | None] = mapped_column(Text)
    body_text: Mapped[str | None] = mapped_column(Text)
    body_html: Mapped[str | None] = mapped_column(Text)
    body_hash: Mapped[str | None] = mapped_column(String(128), index=True)
    label_id: Mapped[str | None] = mapped_column(String(160), index=True)
    import_run_id: Mapped[int | None] = mapped_column(ForeignKey("import_runs.id"), index=True)
    parse_status: Mapped[str] = mapped_column(String(40), nullable=False, default="pending", index=True)
    is_visible: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)

    import_run = relationship("ImportRun", back_populates="email_messages")
