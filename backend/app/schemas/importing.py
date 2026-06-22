from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator, model_validator

from backend.app.schemas.money import normalize_currency, validate_money_scale

from backend.app.schemas.transaction import (
    InternalPayableCreate,
    InternalReceivableCreate,
    TransactionRead,
    TransactionRelationshipCategory,
    TransactionSplitCreate,
    TransactionStatus,
    TransactionType,
)
from backend.app.schemas.receivable import ReceivablePaymentAllocationCreate
from backend.app.schemas.payable import PayablePaymentAllocationCreate


class ImportTextRequest(BaseModel):
    raw_text: str = Field(min_length=1)


class ImportDemoRequest(BaseModel):
    sample_id: str | None = None


class ImportDiscardRequest(BaseModel):
    email_message_id: int
    import_run_id: int | None = None


class ImportCandidateSplit(BaseModel):
    category_id: int | None = None
    category_name: str | None = None
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    currency: str = Field(default="CLP", min_length=3, max_length=3)
    label: str | None = Field(default=None, max_length=120)
    notes: str | None = None

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        return normalize_currency(value) or "CLP"

    @model_validator(mode="after")
    def validate_amount_scale(self) -> "ImportCandidateSplit":
        validate_money_scale(self.amount, self.currency, "split amount")
        return self


class ImportCandidateRead(BaseModel):
    email_message_id: int
    import_run_id: int
    subject: str
    body_preview: str | None = None
    body_text: str | None = None
    body_html: str | None = None
    received_at: datetime
    sender_name: str | None = None
    sender_email: str | None = None
    amount: Decimal
    currency: str = "CLP"
    original_amount: Decimal | None = None
    original_currency: str | None = None
    amount_clp: Decimal | None = None
    exchange_rate: Decimal | None = None
    exchange_rate_source: str | None = None
    exchange_rate_date: datetime | None = None
    currency_detection_confidence: float | None = Field(default=None, ge=0, le=1)
    currency_detection_reason: str | None = None
    merchant_name: str | None = None
    counterparty: str | None = None
    description: str | None = None
    suggested_category_id: int | None = None
    suggested_category_name: str | None = None
    suggested_category_color: str | None = None
    suggested_transaction_type: TransactionType
    cashflow_direction: str
    suggested_financial_account_id: int | None = None
    suggested_financial_account_name: str | None = None
    detected_account_institution: str | None = None
    detected_account_type: str | None = None
    detected_account_last_four: str | None = None
    account_detection_confidence: float | None = None
    account_detection_reason: str | None = None
    status: TransactionStatus
    confidence: float | None = None
    classification_reason: str | None = None
    classification_method: str | None = None
    needs_split: bool = False
    suggested_splits: list[ImportCandidateSplit] = Field(default_factory=list)
    suggested_investment_account_id: int | None = None
    suggested_investment_account_name: str | None = None


class ImportCandidateConfirm(BaseModel):
    email_message_id: int
    import_run_id: int | None = None
    occurred_at: datetime
    posted_at: datetime | None = None
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
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
    payment_method: str | None = Field(default=None, max_length=80)
    transaction_type: TransactionType = "expense"
    status: TransactionStatus = "classified"
    confidence: float | None = Field(default=None, ge=0, le=1)
    classification_reason: str | None = Field(default=None, max_length=240)
    classification_method: str | None = Field(default=None, max_length=40)
    account_detection_method: str | None = Field(default=None, max_length=40)
    account_detection_confidence: float | None = Field(default=None, ge=0, le=1)
    account_detection_reason: str | None = Field(default=None, max_length=240)
    notes: str | None = None
    splits: list[TransactionSplitCreate] = Field(default_factory=list)
    receivable_payments: list[ReceivablePaymentAllocationCreate] = Field(default_factory=list)
    payable_payments: list[PayablePaymentAllocationCreate] = Field(default_factory=list)
    internal_receivables: list[InternalReceivableCreate] = Field(default_factory=list)
    internal_payables: list[InternalPayableCreate] = Field(default_factory=list)

    @field_validator("currency", "original_currency", "destination_currency")
    @classmethod
    def normalize_currency(cls, value: str | None) -> str | None:
        return normalize_currency(value)

    @model_validator(mode="after")
    def validate_money_scales(self) -> "ImportCandidateConfirm":
        currency = self.currency or "CLP"
        original_currency = self.original_currency or currency
        validate_money_scale(self.amount, currency, "amount")
        validate_money_scale(self.original_amount, original_currency, "original_amount")
        validate_money_scale(self.amount_clp, "CLP", "amount_clp")
        return self


class ImportConfirmResponse(BaseModel):
    transaction: TransactionRead
    email_message_id: int
    import_run_id: int | None = None


class ImportDiscardResponse(BaseModel):
    email_message_id: int
    import_run_id: int | None = None
    status: str
