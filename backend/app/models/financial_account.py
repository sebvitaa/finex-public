from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base
from backend.app.models.mixins import TimestampMixin, utc_now


class FinancialAccount(TimestampMixin, Base):
    __tablename__ = "financial_accounts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    institution: Mapped[str | None] = mapped_column(String(120), index=True)
    account_type: Mapped[str] = mapped_column(String(40), nullable=False, default="unknown", index=True)
    product_name: Mapped[str | None] = mapped_column(String(120))
    last_four: Mapped[str | None] = mapped_column(String(4), index=True)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="CLP")
    opening_balance: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=Decimal("0.00"))
    credit_limit_amount: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    credit_limit_currency: Mapped[str | None] = mapped_column(String(3))
    available_credit_amount: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    used_credit_amount: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    billing_cycle_day: Mapped[int | None] = mapped_column(Integer)
    payment_due_day: Mapped[int | None] = mapped_column(Integer)
    statement_amount: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    statement_currency: Mapped[str | None] = mapped_column(String(3))
    statement_amount_overridden: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    statement_override_reason: Mapped[str | None] = mapped_column(Text)
    card_art_variant: Mapped[str | None] = mapped_column(String(20))
    visual_group: Mapped[str | None] = mapped_column(String(120), index=True)
    notes: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)

    snapshots = relationship("FinancialAccountSnapshot", back_populates="account", cascade="all, delete-orphan")
    statements = relationship("CreditCardStatement", back_populates="account", cascade="all, delete-orphan")
    transactions = relationship(
        "Transaction",
        foreign_keys="Transaction.financial_account_id",
        back_populates="financial_account",
    )


class FinancialAccountSnapshot(Base):
    __tablename__ = "financial_account_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    financial_account_id: Mapped[int] = mapped_column(
        ForeignKey("financial_accounts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now, index=True)
    balance: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="CLP")
    source: Mapped[str] = mapped_column(String(40), nullable=False, default="manual")
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)

    account = relationship("FinancialAccount", back_populates="snapshots")


class CreditCardStatement(Base):
    __tablename__ = "credit_card_statements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    financial_account_id: Mapped[int] = mapped_column(
        ForeignKey("financial_accounts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    statement_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=Decimal("0.00"))
    statement_currency: Mapped[str] = mapped_column(String(3), nullable=False, default="CLP")
    calculated_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=Decimal("0.00"))
    is_overridden: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    override_reason: Mapped[str | None] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String(40), nullable=False, default="calculated")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now)

    account = relationship("FinancialAccount", back_populates="statements")
