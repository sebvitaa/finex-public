from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Float, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base
from backend.app.models.mixins import TimestampMixin


class Transaction(TimestampMixin, Base):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    posted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    signed_amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="CLP")
    original_amount: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    original_currency: Mapped[str] = mapped_column(String(3), nullable=False, default="CLP")
    amount_clp: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    exchange_rate: Mapped[Decimal | None] = mapped_column(Numeric(14, 6))
    exchange_rate_source: Mapped[str | None] = mapped_column(String(80))
    exchange_rate_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    currency_detection_confidence: Mapped[float | None] = mapped_column(Float)
    currency_detection_reason: Mapped[str | None] = mapped_column(String(240))
    merchant_name: Mapped[str | None] = mapped_column(String(160), index=True)
    counterparty: Mapped[str | None] = mapped_column(String(160))
    relationship_category: Mapped[str] = mapped_column(String(40), nullable=False, default="mi", index=True)
    financial_account_id: Mapped[int | None] = mapped_column(
        ForeignKey("financial_accounts.id", ondelete="SET NULL"),
        index=True,
    )
    destination_account_id: Mapped[int | None] = mapped_column(
        ForeignKey("financial_accounts.id", ondelete="SET NULL"),
        index=True,
    )
    destination_amount: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    destination_currency: Mapped[str | None] = mapped_column(String(3))
    investment_account_id: Mapped[int | None] = mapped_column(
        ForeignKey("investment_accounts.id", ondelete="SET NULL"),
        index=True,
    )
    person_id: Mapped[int | None] = mapped_column(ForeignKey("people.id", ondelete="SET NULL"), index=True)
    receivable_id: Mapped[int | None] = mapped_column(ForeignKey("receivables.id", ondelete="SET NULL"), index=True)
    payable_id: Mapped[int | None] = mapped_column(ForeignKey("payables.id", ondelete="SET NULL"), index=True)
    description: Mapped[str | None] = mapped_column(Text)
    subject: Mapped[str | None] = mapped_column(String(240))
    category_id: Mapped[int | None] = mapped_column(
        ForeignKey("categories.id", ondelete="SET NULL"),
        index=True,
    )
    source: Mapped[str] = mapped_column(String(40), nullable=False, default="manual", index=True)
    source_message_id: Mapped[str | None] = mapped_column(String(160), index=True)
    payment_method: Mapped[str | None] = mapped_column(String(80))
    transaction_type: Mapped[str] = mapped_column(String(40), nullable=False, default="expense", index=True)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="needs_review", index=True)
    confidence: Mapped[float | None] = mapped_column(Float)
    classification_method: Mapped[str | None] = mapped_column(String(40))
    classification_reason: Mapped[str | None] = mapped_column(String(240))
    account_detection_method: Mapped[str | None] = mapped_column(String(40))
    account_detection_confidence: Mapped[float | None] = mapped_column(Float)
    account_detection_reason: Mapped[str | None] = mapped_column(String(240))
    notes: Mapped[str | None] = mapped_column(Text)

    category = relationship("Category", back_populates="transactions")
    financial_account = relationship(
        "FinancialAccount",
        foreign_keys=[financial_account_id],
        back_populates="transactions",
    )
    destination_account = relationship(
        "FinancialAccount",
        foreign_keys=[destination_account_id],
    )
    investment_account = relationship("InvestmentAccount", back_populates="transactions")
    person = relationship("Person", back_populates="transactions")
    receivable = relationship("Receivable", back_populates="transactions")
    payable = relationship("Payable", back_populates="transactions")
    splits = relationship("TransactionSplit", back_populates="transaction", cascade="all, delete-orphan")


class TransactionSplit(TimestampMixin, Base):
    __tablename__ = "transaction_splits"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    transaction_id: Mapped[int] = mapped_column(
        ForeignKey("transactions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    category_id: Mapped[int | None] = mapped_column(
        ForeignKey("categories.id", ondelete="SET NULL"),
        index=True,
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="CLP")
    label: Mapped[str | None] = mapped_column(String(120))
    quantity: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    notes: Mapped[str | None] = mapped_column(Text)

    transaction = relationship("Transaction", back_populates="splits")
    category = relationship("Category", back_populates="transaction_splits")
