from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


InvestmentAccountType = Literal["brokerage", "mutual_fund", "pension", "crypto", "savings", "other"]
InvestmentMovementType = Literal["investment", "disinvestment", "valuation"]


class InvestmentAccountBase(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    institution: str | None = Field(default=None, max_length=120)
    account_type: InvestmentAccountType = "brokerage"
    currency: str = Field(default="CLP", min_length=3, max_length=3)
    current_value: Decimal = Field(default=Decimal("0.00"), max_digits=14, decimal_places=2)
    notes: str | None = None
    is_active: bool = True

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        return value.upper()


class InvestmentAccountCreate(InvestmentAccountBase):
    pass


class InvestmentAccountUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    institution: str | None = Field(default=None, max_length=120)
    account_type: InvestmentAccountType | None = None
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    current_value: Decimal | None = Field(default=None, max_digits=14, decimal_places=2)
    notes: str | None = None
    is_active: bool | None = None

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str | None) -> str | None:
        return value.upper() if value else value


class InvestmentMovementCreate(BaseModel):
    transaction_id: int | None = None
    occurred_at: datetime
    movement_type: InvestmentMovementType
    amount: Decimal = Field(gt=0, max_digits=14, decimal_places=2)
    currency: str = Field(default="CLP", min_length=3, max_length=3)
    units: Decimal | None = Field(default=None, gt=0, max_digits=18, decimal_places=6)
    unit_price: Decimal | None = Field(default=None, gt=0, max_digits=14, decimal_places=4)
    source: str = Field(default="manual", max_length=40)
    notes: str | None = None

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        return value.upper()


class InvestmentMovementRead(InvestmentMovementCreate):
    id: int
    investment_account_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class InvestmentAccountRead(InvestmentAccountBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
