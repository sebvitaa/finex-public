from sqlalchemy import Boolean, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base
from backend.app.models.mixins import TimestampMixin


class ClassificationRule(TimestampMixin, Base):
    __tablename__ = "classification_rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    field: Mapped[str] = mapped_column(String(60), nullable=False)
    operator: Mapped[str] = mapped_column(String(40), nullable=False)
    pattern: Mapped[str] = mapped_column(String(240), nullable=False)
    category_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id", ondelete="SET NULL"), index=True)
    transaction_type: Mapped[str | None] = mapped_column(String(40), index=True)
    financial_account_id: Mapped[int | None] = mapped_column(ForeignKey("financial_accounts.id", ondelete="SET NULL"), index=True)
    investment_account_id: Mapped[int | None] = mapped_column(ForeignKey("investment_accounts.id", ondelete="SET NULL"), index=True)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.75)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_from_correction: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    notes: Mapped[str | None] = mapped_column(Text)

    category = relationship("Category", back_populates="rules")
    financial_account = relationship("FinancialAccount")
    investment_account = relationship("InvestmentAccount")
