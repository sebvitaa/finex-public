from sqlalchemy import Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base
from backend.app.models.mixins import TimestampMixin


class ClassificationFeedback(TimestampMixin, Base):
    __tablename__ = "classification_feedback"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    transaction_id: Mapped[int | None] = mapped_column(ForeignKey("transactions.id", ondelete="SET NULL"), index=True)
    source_message_id: Mapped[str | None] = mapped_column(String(160), index=True)
    field: Mapped[str] = mapped_column(String(60), nullable=False)
    pattern: Mapped[str] = mapped_column(String(240), nullable=False, index=True)
    merchant_name: Mapped[str | None] = mapped_column(String(160), index=True)
    sender_email: Mapped[str | None] = mapped_column(String(240), index=True)
    subject: Mapped[str | None] = mapped_column(String(240))
    previous_category_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id", ondelete="SET NULL"))
    new_category_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id", ondelete="SET NULL"), index=True)
    previous_financial_account_id: Mapped[int | None] = mapped_column(ForeignKey("financial_accounts.id", ondelete="SET NULL"))
    new_financial_account_id: Mapped[int | None] = mapped_column(ForeignKey("financial_accounts.id", ondelete="SET NULL"), index=True)
    previous_investment_account_id: Mapped[int | None] = mapped_column(ForeignKey("investment_accounts.id", ondelete="SET NULL"))
    new_investment_account_id: Mapped[int | None] = mapped_column(ForeignKey("investment_accounts.id", ondelete="SET NULL"), index=True)
    previous_transaction_type: Mapped[str | None] = mapped_column(String(40))
    new_transaction_type: Mapped[str | None] = mapped_column(String(40), index=True)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.7)

    transaction = relationship("Transaction")
    previous_category = relationship("Category", foreign_keys=[previous_category_id])
    new_category = relationship("Category", foreign_keys=[new_category_id])
    previous_financial_account = relationship("FinancialAccount", foreign_keys=[previous_financial_account_id])
    new_financial_account = relationship("FinancialAccount", foreign_keys=[new_financial_account_id])
    previous_investment_account = relationship("InvestmentAccount", foreign_keys=[previous_investment_account_id])
    new_investment_account = relationship("InvestmentAccount", foreign_keys=[new_investment_account_id])
