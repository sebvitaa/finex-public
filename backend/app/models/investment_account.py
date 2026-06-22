from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base
from backend.app.models.mixins import TimestampMixin, utc_now


class InvestmentAccount(TimestampMixin, Base):
    __tablename__ = "investment_accounts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    institution: Mapped[str | None] = mapped_column(String(120), index=True)
    account_type: Mapped[str] = mapped_column(String(40), nullable=False, default="brokerage", index=True)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="CLP")
    current_value: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=Decimal("0.00"))
    notes: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)

    movements = relationship("InvestmentMovement", back_populates="account", cascade="all, delete-orphan")
    transactions = relationship("Transaction", back_populates="investment_account")


class InvestmentMovement(Base):
    __tablename__ = "investment_movements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    investment_account_id: Mapped[int] = mapped_column(
        ForeignKey("investment_accounts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    transaction_id: Mapped[int | None] = mapped_column(ForeignKey("transactions.id", ondelete="SET NULL"), index=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now, index=True)
    movement_type: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="CLP")
    units: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    unit_price: Mapped[Decimal | None] = mapped_column(Numeric(14, 4))
    source: Mapped[str] = mapped_column(String(40), nullable=False, default="manual")
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)

    account = relationship("InvestmentAccount", back_populates="movements")
