from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base
from backend.app.models.mixins import utc_now


class ObligationOffset(Base):
    __tablename__ = "obligation_offsets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    person_id: Mapped[int] = mapped_column(ForeignKey("people.id", ondelete="CASCADE"), nullable=False, index=True)
    receivable_id: Mapped[int | None] = mapped_column(
        ForeignKey("receivables.id", ondelete="SET NULL"),
        index=True,
    )
    payable_id: Mapped[int | None] = mapped_column(ForeignKey("payables.id", ondelete="SET NULL"), index=True)
    offset_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now, index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    resulting_direction: Mapped[str] = mapped_column(String(40), nullable=False, default="settled")
    resulting_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=Decimal("0.00"))
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)

    person = relationship("Person")
    receivable = relationship("Receivable")
    payable = relationship("Payable")
