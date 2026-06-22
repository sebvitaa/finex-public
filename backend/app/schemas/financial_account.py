from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from backend.app.schemas.money import normalize_currency, validate_money_scale


FinancialAccountType = Literal["checking", "savings", "debit_card", "credit_card", "cash", "wallet", "unknown"]


class FinancialAccountBase(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    institution: str | None = Field(default=None, max_length=120)
    account_type: FinancialAccountType = "unknown"
    product_name: str | None = Field(default=None, max_length=120)
    last_four: str | None = Field(default=None, min_length=4, max_length=4)
    currency: str = Field(default="CLP", min_length=3, max_length=3)
    opening_balance: Decimal = Field(default=Decimal("0.00"), max_digits=14, decimal_places=2)
    credit_limit_amount: Decimal | None = Field(default=None, gt=0, max_digits=14, decimal_places=2)
    credit_limit_currency: str | None = Field(default=None, min_length=3, max_length=3)
    available_credit_amount: Decimal | None = Field(default=None, ge=0, max_digits=14, decimal_places=2)
    used_credit_amount: Decimal | None = Field(default=None, ge=0, max_digits=14, decimal_places=2)
    billing_cycle_day: int | None = Field(default=None, ge=1, le=31)
    payment_due_day: int | None = Field(default=None, ge=1, le=31)
    statement_amount: Decimal | None = Field(default=None, ge=0, max_digits=14, decimal_places=2)
    statement_currency: str | None = Field(default=None, min_length=3, max_length=3)
    statement_amount_overridden: bool = False
    statement_override_reason: str | None = None
    card_art_variant: str | None = Field(default=None, max_length=20)
    visual_group: str | None = Field(default=None, max_length=120)
    notes: str | None = None
    is_active: bool = True

    @field_validator("currency", "credit_limit_currency", "statement_currency")
    @classmethod
    def normalize_currency(cls, value: str | None) -> str | None:
        return normalize_currency(value)

    @model_validator(mode="after")
    def validate_money_scales(self) -> "FinancialAccountBase":
        currency = self.currency or "CLP"
        credit_currency = self.credit_limit_currency or currency
        statement_currency = self.statement_currency or currency
        validate_money_scale(self.opening_balance, currency, "opening_balance")
        validate_money_scale(self.credit_limit_amount, credit_currency, "credit_limit_amount")
        validate_money_scale(self.available_credit_amount, credit_currency, "available_credit_amount")
        validate_money_scale(self.used_credit_amount, credit_currency, "used_credit_amount")
        validate_money_scale(self.statement_amount, statement_currency, "statement_amount")
        return self


class FinancialAccountCreate(FinancialAccountBase):
    pass


class FinancialAccountUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    institution: str | None = Field(default=None, max_length=120)
    account_type: FinancialAccountType | None = None
    product_name: str | None = Field(default=None, max_length=120)
    last_four: str | None = Field(default=None, min_length=4, max_length=4)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    opening_balance: Decimal | None = Field(default=None, max_digits=14, decimal_places=2)
    credit_limit_amount: Decimal | None = Field(default=None, gt=0, max_digits=14, decimal_places=2)
    credit_limit_currency: str | None = Field(default=None, min_length=3, max_length=3)
    available_credit_amount: Decimal | None = Field(default=None, ge=0, max_digits=14, decimal_places=2)
    used_credit_amount: Decimal | None = Field(default=None, ge=0, max_digits=14, decimal_places=2)
    billing_cycle_day: int | None = Field(default=None, ge=1, le=31)
    payment_due_day: int | None = Field(default=None, ge=1, le=31)
    statement_amount: Decimal | None = Field(default=None, ge=0, max_digits=14, decimal_places=2)
    statement_currency: str | None = Field(default=None, min_length=3, max_length=3)
    statement_amount_overridden: bool | None = None
    statement_override_reason: str | None = None
    card_art_variant: str | None = Field(default=None, max_length=20)
    visual_group: str | None = Field(default=None, max_length=120)
    notes: str | None = None
    is_active: bool | None = None

    @field_validator("currency", "credit_limit_currency", "statement_currency")
    @classmethod
    def normalize_currency(cls, value: str | None) -> str | None:
        return normalize_currency(value)

    @model_validator(mode="after")
    def validate_money_scales(self) -> "FinancialAccountUpdate":
        currency = self.currency
        credit_currency = self.credit_limit_currency or currency
        statement_currency = self.statement_currency or currency
        validate_money_scale(self.opening_balance, currency, "opening_balance")
        validate_money_scale(self.credit_limit_amount, credit_currency, "credit_limit_amount")
        validate_money_scale(self.available_credit_amount, credit_currency, "available_credit_amount")
        validate_money_scale(self.used_credit_amount, credit_currency, "used_credit_amount")
        validate_money_scale(self.statement_amount, statement_currency, "statement_amount")
        return self


class FinancialAccountSnapshotCreate(BaseModel):
    captured_at: datetime
    balance: Decimal = Field(max_digits=14, decimal_places=2)
    currency: str = Field(default="CLP", min_length=3, max_length=3)
    source: str = Field(default="manual", max_length=40)
    notes: str | None = None

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        return normalize_currency(value) or "CLP"

    @model_validator(mode="after")
    def validate_money_scales(self) -> "FinancialAccountSnapshotCreate":
        validate_money_scale(self.balance, self.currency, "balance")
        return self


class FinancialAccountSnapshotRead(FinancialAccountSnapshotCreate):
    id: int
    financial_account_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class FinancialAccountRead(FinancialAccountBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CreditCardStatementBase(BaseModel):
    period_start: datetime
    period_end: datetime
    due_at: datetime | None = None
    statement_amount: Decimal = Field(default=Decimal("0.00"), ge=0, max_digits=14, decimal_places=2)
    statement_currency: str = Field(default="CLP", min_length=3, max_length=3)
    calculated_amount: Decimal = Field(default=Decimal("0.00"), ge=0, max_digits=14, decimal_places=2)
    is_overridden: bool = False
    override_reason: str | None = None
    source: str = Field(default="calculated", max_length=40)

    @field_validator("statement_currency")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        return normalize_currency(value) or "CLP"

    @model_validator(mode="after")
    def validate_money_scales(self) -> "CreditCardStatementBase":
        validate_money_scale(self.statement_amount, self.statement_currency, "statement_amount")
        validate_money_scale(self.calculated_amount, self.statement_currency, "calculated_amount")
        return self


class CreditCardStatementCreate(CreditCardStatementBase):
    pass


class CreditCardStatementRead(CreditCardStatementBase):
    id: int
    financial_account_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
