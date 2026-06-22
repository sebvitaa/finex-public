from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base
from backend.app.models.mixins import TimestampMixin, utc_now


class Receivable(TimestampMixin, Base):
    __tablename__ = "receivables"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    person_id: Mapped[int] = mapped_column(ForeignKey("people.id", ondelete="CASCADE"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    original_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    remaining_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="CLP")
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now, index=True)
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="pending_payment", index=True)
    notes: Mapped[str | None] = mapped_column(Text)

    person = relationship("Person", back_populates="receivables")
    payments = relationship("ReceivablePayment", back_populates="receivable", cascade="all, delete-orphan")
    transactions = relationship("Transaction", back_populates="receivable")


class ReceivablePayment(Base):
    __tablename__ = "receivable_payments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    receivable_id: Mapped[int] = mapped_column(
        ForeignKey("receivables.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    transaction_id: Mapped[int | None] = mapped_column(ForeignKey("transactions.id", ondelete="SET NULL"), index=True)
    paid_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now, index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)

    receivable = relationship("Receivable", back_populates="payments")
