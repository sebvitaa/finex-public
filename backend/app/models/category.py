from sqlalchemy import Boolean, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base
from backend.app.models.mixins import TimestampMixin


class Category(TimestampMixin, Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id", ondelete="SET NULL"), index=True)
    name: Mapped[str] = mapped_column(String(80), unique=True, nullable=False, index=True)
    color: Mapped[str] = mapped_column(String(7), nullable=False, default="#71717A")
    icon: Mapped[str] = mapped_column(String(40), nullable=False, default="circle")
    kind: Mapped[str] = mapped_column(String(20), nullable=False, default="expense", index=True)
    is_system: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    parent = relationship("Category", remote_side=[id])
    transactions = relationship("Transaction", back_populates="category")
    transaction_splits = relationship("TransactionSplit", back_populates="category")
    rules = relationship("ClassificationRule", back_populates="category")
