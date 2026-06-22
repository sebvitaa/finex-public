from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from backend.app.schemas.transaction import TransactionType


RuleField = Literal[
    "source_text",
    "sender_email",
    "sender_name",
    "subject",
    "body_preview",
    "merchant_name",
    "counterparty",
    "description",
    "detected_account_institution",
    "detected_account_type",
    "detected_account_last_four",
    "item_text",
]
RuleOperator = Literal["contains", "equals", "starts_with", "regex"]


class ClassificationRuleBase(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    field: RuleField = "source_text"
    operator: RuleOperator = "contains"
    pattern: str = Field(min_length=1, max_length=240)
    category_id: int | None = None
    transaction_type: TransactionType | None = None
    financial_account_id: int | None = None
    investment_account_id: int | None = None
    priority: int = Field(default=100, ge=0, le=1000)
    confidence: float = Field(default=0.75, ge=0, le=1)
    is_active: bool = True
    created_from_correction: bool = False
    notes: str | None = None

    @model_validator(mode="after")
    def validate_target(self) -> "ClassificationRuleBase":
        if not any([self.category_id, self.transaction_type, self.financial_account_id, self.investment_account_id]):
            raise ValueError("A rule must set at least one target")
        return self


class ClassificationRuleCreate(ClassificationRuleBase):
    pass


class ClassificationRuleUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    field: RuleField | None = None
    operator: RuleOperator | None = None
    pattern: str | None = Field(default=None, min_length=1, max_length=240)
    category_id: int | None = None
    transaction_type: TransactionType | None = None
    financial_account_id: int | None = None
    investment_account_id: int | None = None
    priority: int | None = Field(default=None, ge=0, le=1000)
    confidence: float | None = Field(default=None, ge=0, le=1)
    is_active: bool | None = None
    created_from_correction: bool | None = None
    notes: str | None = None


class ClassificationRuleRead(ClassificationRuleBase):
    id: int
    category_name: str | None = None
    financial_account_name: str | None = None
    investment_account_name: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RuleMatchRead(BaseModel):
    rule_id: int
    rule_name: str
    field: str
    operator: str
    pattern: str
    confidence: float
    reason: str


class RuleClassificationRead(BaseModel):
    category_id: int | None = None
    category_name: str | None = None
    transaction_type: str | None = None
    financial_account_id: int | None = None
    financial_account_name: str | None = None
    investment_account_id: int | None = None
    investment_account_name: str | None = None
    confidence: float | None = None
    reason: str | None = None
    matched_rules: list[RuleMatchRead] = Field(default_factory=list)


class RuleTestRequest(BaseModel):
    raw_text: str | None = None
    email_message_id: int | None = None
    transaction_id: int | None = None

    @model_validator(mode="after")
    def validate_source(self) -> "RuleTestRequest":
        if not any([self.raw_text, self.email_message_id, self.transaction_id]):
            raise ValueError("Provide raw_text, email_message_id or transaction_id")
        return self


class RuleTestResponse(RuleClassificationRead):
    input_preview: str


class ClassificationFeedbackRead(BaseModel):
    id: int
    transaction_id: int | None = None
    field: str
    pattern: str
    merchant_name: str | None = None
    sender_email: str | None = None
    subject: str | None = None
    new_category_id: int | None = None
    new_category_name: str | None = None
    new_financial_account_id: int | None = None
    new_financial_account_name: str | None = None
    new_investment_account_id: int | None = None
    new_investment_account_name: str | None = None
    new_transaction_type: str | None = None
    confidence: float
    created_at: datetime


class RuleSuggestionRead(BaseModel):
    field: str
    pattern: str
    count: int
    category_id: int | None = None
    category_name: str | None = None
    financial_account_id: int | None = None
    financial_account_name: str | None = None
    investment_account_id: int | None = None
    investment_account_name: str | None = None
    transaction_type: str | None = None
    confidence: float
    reason: str
