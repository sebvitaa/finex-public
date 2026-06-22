from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base
from backend.app.models.mixins import TimestampMixin


class Person(TimestampMixin, Base):
    __tablename__ = "people"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    alias: Mapped[str | None] = mapped_column(String(80))
    email: Mapped[str | None] = mapped_column(String(240))
    phone: Mapped[str | None] = mapped_column(String(80))
    notes: Mapped[str | None] = mapped_column(Text)

    transactions = relationship("Transaction", back_populates="person")
    receivables = relationship("Receivable", back_populates="person", cascade="all, delete-orphan")
    payables = relationship("Payable", back_populates="person", cascade="all, delete-orphan")
