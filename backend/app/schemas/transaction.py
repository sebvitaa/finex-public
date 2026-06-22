from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from backend.app.schemas.category import CategoryRead
from backend.app.schemas.money import normalize_currency, validate_money_scale


Source = Literal["manual", "gmail", "csv", "demo"]
TransactionType = Literal[
    "expense",
    "income",
    "transfer_out",
    "transfer_in",
    "internal_transfer",
    "loan_out",
    "receivable_payment",
    "payable_payment",
    "investment",
    "disinvestment",
    "subscription",
    "refund",
    "unknown",
]
TransactionStatus = Literal[
    "classified",
    "needs_review",
    "ignored",
    "duplicate",
    "pending_payment",
    "partially_paid",
    "paid",
    "overdue",
]
TransactionRelationshipCategory = Literal["ninguna", "amigos", "trabajo", "mi", "novia"]


class PersonReadLite(BaseModel):
    id: int
    name: str
    alias: str | None = None

    model_config = ConfigDict(from_attributes=True)


class ReceivableReadLite(BaseModel):
    id: int
    title: str
    remaining_amount: Decimal
    status: str

    model_config = ConfigDict(from_attributes=True)


class PayableReadLite(BaseModel):
    id: int
    title: str
    remaining_amount: Decimal
    status: str

    model_config = ConfigDict(from_attributes=True)


class FinancialAccountReadLite(BaseModel):
    id: int
    name: str
    institution: str | None = None
    account_type: str
    last_four: str | None = None
    currency: str = "CLP"
    credit_limit_amount: Decimal | None = None
    credit_limit_currency: str | None = None
    card_art_variant: str | None = None
    visual_group: str | None = None

    model_config = ConfigDict(from_attributes=True)


class InvestmentAccountReadLite(BaseModel):
    id: int
    name: str
    institution: str | None = None
    account_type: str

    model_config = ConfigDict(from_attributes=True)


class InternalReceivableCreate(BaseModel):
    person_id: int
    title: str = Field(min_length=2, max_length=160)
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    due_at: datetime | None = None
    notes: str | None = None


class InternalPayableCreate(BaseModel):
    person_id: int
    title: str = Field(min_length=2, max_length=160)
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    due_at: datetime | None = None
    notes: str | None = None


class TransactionSplitBase(BaseModel):
    category_id: int | None = None
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    currency: str = Field(default="CLP", min_length=3, max_length=3)
    label: str | None = Field(default=None, max_length=120)
    quantity: Decimal | None = Field(default=None, gt=0, max_digits=10, decimal_places=2)
    notes: str | None = None

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        return normalize_currency(value) or "CLP"

    @model_validator(mode="after")
    def validate_amount_scale(self) -> "TransactionSplitBase":
        validate_money_scale(self.amount, self.currency, "split amount")
        return self


class TransactionSplitCreate(TransactionSplitBase):
    pass


class TransactionSplitRead(TransactionSplitBase):
    id: int
    transaction_id: int
    category: CategoryRead | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TransactionCreate(BaseModel):
    occurred_at: datetime
    posted_at: datetime | None = None
    amount: Decimal = Field(gt=0, max_digits=14, decimal_places=2)
    signed_amount: Decimal | None = Field(default=None, max_digits=14, decimal_places=2)
    currency: str = Field(default="CLP", min_length=3, max_length=3)
    original_amount: Decimal | None = Field(default=None, gt=0, max_digits=14, decimal_places=2)
    original_currency: str | None = Field(default=None, min_length=3, max_length=3)
    amount_clp: Decimal | None = Field(default=None, ge=0, max_digits=14, decimal_places=2)
    exchange_rate: Decimal | None = Field(default=None, gt=0, max_digits=14, decimal_places=6)
    exchange_rate_source: str | None = Field(default=None, max_length=80)
    exchange_rate_date: datetime | None = None
    currency_detection_confidence: float | None = Field(default=None, ge=0, le=1)
    currency_detection_reason: str | None = Field(default=None, max_length=240)
    merchant_name: str | None = Field(default=None, max_length=160)
    counterparty: str | None = Field(default=None, max_length=160)
    relationship_category: TransactionRelationshipCategory = "mi"
    financial_account_id: int | None = None
    destination_account_id: int | None = None
    destination_amount: Decimal | None = Field(default=None, gt=0, max_digits=14, decimal_places=2)
    destination_currency: str | None = Field(default=None, min_length=3, max_length=3)
    investment_account_id: int | None = None
    person_id: int | None = None
    receivable_id: int | None = None
    payable_id: int | None = None
    description: str | None = None
    subject: str | None = Field(default=None, max_length=240)
    category_id: int | None = None
    source: Source = "manual"
    source_message_id: str | None = Field(default=None, max_length=160)
    payment_method: str | None = Field(default=None, max_length=80)
    transaction_type: TransactionType = "expense"
    status: TransactionStatus = "needs_review"
    confidence: float | None = Field(default=None, ge=0, le=1)
    classification_method: str | None = Field(default=None, max_length=40)
    classification_reason: str | None = Field(default=None, max_length=240)
    account_detection_method: str | None = Field(default=None, max_length=40)
    account_detection_confidence: float | None = Field(default=None, ge=0, le=1)
    account_detection_reason: str | None = Field(default=None, max_length=240)
    notes: str | None = None
    splits: list[TransactionSplitCreate] = Field(default_factory=list)
    internal_receivables: list[InternalReceivableCreate] = Field(default_factory=list)
    internal_payables: list[InternalPayableCreate] = Field(default_factory=list)

    @field_validator("currency", "original_currency", "destination_currency")
    @classmethod
    def normalize_currency(cls, value: str | None) -> str | None:
        return normalize_currency(value)

    @model_validator(mode="after")
    def validate_money_scales(self) -> "TransactionCreate":
        currency = self.currency or "CLP"
        original_currency = self.original_currency or currency
        validate_money_scale(self.amount, currency, "amount")
        validate_money_scale(self.signed_amount, currency, "signed_amount")
        validate_money_scale(self.original_amount, original_currency, "original_amount")
        validate_money_scale(self.amount_clp, "CLP", "amount_clp")
        return self


class TransactionUpdate(BaseModel):
    occurred_at: datetime | None = None
    posted_at: datetime | None = None
    amount: Decimal | None = Field(default=None, gt=0, max_digits=14, decimal_places=2)
    signed_amount: Decimal | None = Field(default=None, max_digits=14, decimal_places=2)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    original_amount: Decimal | None = Field(default=None, gt=0, max_digits=14, decimal_places=2)
    original_currency: str | None = Field(default=None, min_length=3, max_length=3)
    amount_clp: Decimal | None = Field(default=None, ge=0, max_digits=14, decimal_places=2)
    exchange_rate: Decimal | None = Field(default=None, gt=0, max_digits=14, decimal_places=6)
    exchange_rate_source: str | None = Field(default=None, max_length=80)
    exchange_rate_date: datetime | None = None
    currency_detection_confidence: float | None = Field(default=None, ge=0, le=1)
    currency_detection_reason: str | None = Field(default=None, max_length=240)
    merchant_name: str | None = Field(default=None, max_length=160)
    counterparty: str | None = Field(default=None, max_length=160)
    relationship_category: TransactionRelationshipCategory | None = None
    financial_account_id: int | None = None
    destination_account_id: int | None = None
    destination_amount: Decimal | None = Field(default=None, gt=0, max_digits=14, decimal_places=2)
    destination_currency: str | None = Field(default=None, min_length=3, max_length=3)
    investment_account_id: int | None = None
    person_id: int | None = None
    receivable_id: int | None = None
    payable_id: int | None = None
    description: str | None = None
    subject: str | None = Field(default=None, max_length=240)
    category_id: int | None = None
    source: Source | None = None
    source_message_id: str | None = Field(default=None, max_length=160)
    payment_method: str | None = Field(default=None, max_length=80)
    transaction_type: TransactionType | None = None
    status: TransactionStatus | None = None
    confidence: float | None = Field(default=None, ge=0, le=1)
    classification_method: str | None = Field(default=None, max_length=40)
    classification_reason: str | None = Field(default=None, max_length=240)
    account_detection_method: str | None = Field(default=None, max_length=40)
    account_detection_confidence: float | None = Field(default=None, ge=0, le=1)
    account_detection_reason: str | None = Field(default=None, max_length=240)
    notes: str | None = None
    splits: list[TransactionSplitCreate] | None = None

    @field_validator("currency", "original_currency", "destination_currency")
    @classmethod
    def normalize_currency(cls, value: str | None) -> str | None:
        return normalize_currency(value)

    @model_validator(mode="after")
    def validate_money_scales(self) -> "TransactionUpdate":
        currency = self.currency
        original_currency = self.original_currency or currency
        validate_money_scale(self.amount, currency, "amount")
        validate_money_scale(self.signed_amount, currency, "signed_amount")
        validate_money_scale(self.original_amount, original_currency, "original_amount")
        validate_money_scale(self.amount_clp, "CLP", "amount_clp")
        return self


class TransactionRead(TransactionCreate):
    id: int
    category: CategoryRead | None = None
    financial_account: FinancialAccountReadLite | None = None
    destination_account: FinancialAccountReadLite | None = None
    investment_account: InvestmentAccountReadLite | None = None
    person: PersonReadLite | None = None
    receivable: ReceivableReadLite | None = None
    payable: PayableReadLite | None = None
    splits: list[TransactionSplitRead] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
