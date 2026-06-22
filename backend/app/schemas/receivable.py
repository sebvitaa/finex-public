from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from backend.app.schemas.person import PersonRead


ReceivableStatus = Literal["pending_payment", "partially_paid", "paid", "overdue", "forgiven"]


class ReceivableBase(BaseModel):
    person_id: int
    title: str = Field(min_length=2, max_length=160)
    original_amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    remaining_amount: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    currency: str = Field(default="CLP", min_length=3, max_length=3)
    issued_at: datetime
    due_at: datetime | None = None
    status: ReceivableStatus = "pending_payment"
    notes: str | None = None

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        return value.upper()

    @model_validator(mode="after")
    def default_remaining_amount(self) -> "ReceivableBase":
        if self.remaining_amount is None:
            self.remaining_amount = self.original_amount
        return self


class ReceivableCreate(ReceivableBase):
    pass


class ReceivableUpdate(BaseModel):
    person_id: int | None = None
    title: str | None = Field(default=None, min_length=2, max_length=160)
    original_amount: Decimal | None = Field(default=None, gt=0, max_digits=12, decimal_places=2)
    remaining_amount: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    issued_at: datetime | None = None
    due_at: datetime | None = None
    status: ReceivableStatus | None = None
    notes: str | None = None

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str | None) -> str | None:
        return value.upper() if value else value


class ReceivablePaymentCreate(BaseModel):
    transaction_id: int | None = None
    paid_at: datetime
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    notes: str | None = None


class ReceivablePaymentAllocationCreate(BaseModel):
    receivable_id: int
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    force_close_with_adjustment: bool = False
    notes: str | None = None


class ReceivablePaymentBatchCreate(BaseModel):
    transaction_id: int | None = None
    paid_at: datetime
    payments: list[ReceivablePaymentAllocationCreate] = Field(min_length=1)
    notes: str | None = None


class ReceivablePaymentRead(ReceivablePaymentCreate):
    id: int
    receivable_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ReceivableRead(ReceivableBase):
    id: int
    person: PersonRead
    payments: list[ReceivablePaymentRead] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
