from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from backend.app.models import Category, ClassificationRule, EmailMessage, FinancialAccount, InvestmentAccount, Transaction
from backend.app.services.email_parser import ParsedEmailCandidate


@dataclass(frozen=True)
class RuleContext:
    sender_name: str | None = None
    sender_email: str | None = None
    subject: str | None = None
    body_preview: str | None = None
    merchant_name: str | None = None
    counterparty: str | None = None
    description: str | None = None
    detected_account_institution: str | None = None
    detected_account_type: str | None = None
    detected_account_last_four: str | None = None
    item_text: str | None = None

    @property
    def source_text(self) -> str:
        return " ".join(
            value
            for value in (
                self.sender_name,
                self.sender_email,
                self.subject,
                self.body_preview,
                self.merchant_name,
                self.counterparty,
                self.description,
                self.detected_account_institution,
                self.detected_account_type,
                self.detected_account_last_four,
                self.item_text,
            )
            if value
        )


@dataclass(frozen=True)
class RuleMatch:
    rule: ClassificationRule
    reason: str


@dataclass
class RuleClassification:
    category_id: int | None = None
    transaction_type: str | None = None
    financial_account_id: int | None = None
    investment_account_id: int | None = None
    confidence: float | None = None
    reason: str | None = None
    matched_rules: list[RuleMatch] = field(default_factory=list)


def context_from_parsed(parsed: ParsedEmailCandidate) -> RuleContext:
    return RuleContext(
        sender_name=parsed.sender_name,
        sender_email=parsed.sender_email,
        subject=parsed.subject,
        body_preview=parsed.body_preview,
        merchant_name=parsed.merchant_name,
        counterparty=parsed.counterparty,
        description=parsed.description,
        detected_account_institution=parsed.detected_account_institution,
        detected_account_type=parsed.detected_account_type,
        detected_account_last_four=parsed.detected_account_last_four,
    )


def context_from_email_message(email_message: EmailMessage) -> RuleContext:
    return RuleContext(
        sender_name=email_message.sender_name,
        sender_email=email_message.sender_email,
        subject=email_message.subject,
        body_preview=email_message.body_preview,
    )


def context_from_transaction(transaction: Transaction) -> RuleContext:
    sender_name = None
    sender_email = None
    body_preview = None
    if transaction.source_message_id and transaction.source_message_id.startswith("email:"):
        # The caller may not always eager load the email; keep this context local to stored transaction fields.
        pass
    return RuleContext(
        sender_name=sender_name,
        sender_email=sender_email,
        subject=transaction.subject,
        body_preview=body_preview,
        merchant_name=transaction.merchant_name,
        counterparty=transaction.counterparty,
        description=transaction.description,
        detected_account_institution=transaction.financial_account.institution if transaction.financial_account else None,
        detected_account_type=transaction.financial_account.account_type if transaction.financial_account else None,
        detected_account_last_four=transaction.financial_account.last_four if transaction.financial_account else None,
    )


def load_active_rules(db: Session) -> list[ClassificationRule]:
    query = (
        select(ClassificationRule)
        .options(
            selectinload(ClassificationRule.category),
            selectinload(ClassificationRule.financial_account),
            selectinload(ClassificationRule.investment_account),
        )
        .where(ClassificationRule.is_active.is_(True))
        .order_by(ClassificationRule.priority, ClassificationRule.confidence.desc(), ClassificationRule.id)
    )
    return list(db.scalars(query).all())


def classify_context(context: RuleContext, rules: list[ClassificationRule]) -> RuleClassification:
    classification = RuleClassification()
    best_confidence = 0.0
    reasons: list[str] = []

    for rule in rules:
        reason = _match_reason(rule, context)
        if reason is None:
            continue
        classification.matched_rules.append(RuleMatch(rule=rule, reason=reason))
        best_confidence = max(best_confidence, rule.confidence)
        if rule.category_id is not None and classification.category_id is None:
            classification.category_id = rule.category_id
            reasons.append(reason)
        if rule.transaction_type and classification.transaction_type is None:
            classification.transaction_type = rule.transaction_type
            reasons.append(reason)
        if rule.financial_account_id is not None and classification.financial_account_id is None:
            classification.financial_account_id = rule.financial_account_id
            reasons.append(reason)
        if rule.investment_account_id is not None and classification.investment_account_id is None:
            classification.investment_account_id = rule.investment_account_id
            reasons.append(reason)

    if classification.matched_rules:
        classification.confidence = best_confidence
        classification.reason = "; ".join(dict.fromkeys(reasons or [match.reason for match in classification.matched_rules]))
    return classification


def classify_parsed_candidate(parsed: ParsedEmailCandidate, db: Session) -> RuleClassification:
    return classify_context(context_from_parsed(parsed), load_active_rules(db))


def classify_raw_text(raw_text: str, db: Session) -> tuple[RuleContext, RuleClassification]:
    context = RuleContext(subject=raw_text[:240], body_preview=raw_text[:1000], description=raw_text[:240])
    classification = classify_context(context, load_active_rules(db))
    return context, classification


def classification_names(classification: RuleClassification, db: Session) -> dict[str, str | None]:
    category = db.get(Category, classification.category_id) if classification.category_id else None
    financial_account = db.get(FinancialAccount, classification.financial_account_id) if classification.financial_account_id else None
    investment_account = db.get(InvestmentAccount, classification.investment_account_id) if classification.investment_account_id else None
    return {
        "category_name": category.name if category else None,
        "financial_account_name": financial_account.name if financial_account else None,
        "investment_account_name": investment_account.name if investment_account else None,
    }


def _match_reason(rule: ClassificationRule, context: RuleContext) -> str | None:
    field_value = getattr(context, rule.field, None)
    if rule.field == "source_text":
        field_value = context.source_text
    if not field_value:
        return None

    value = _normalize(str(field_value))
    pattern = _normalize(rule.pattern)
    matched = False
    if rule.operator == "contains":
        matched = pattern in value
    elif rule.operator == "equals":
        matched = pattern == value
    elif rule.operator == "starts_with":
        matched = value.startswith(pattern)
    elif rule.operator == "regex":
        try:
            matched = re.search(rule.pattern, str(field_value), flags=re.IGNORECASE) is not None
        except re.error:
            matched = False
    if not matched:
        return None
    return f"{rule.name}: {rule.field} {rule.operator} '{rule.pattern}'"


def _normalize(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value)
    ascii_value = "".join(char for char in decomposed if not unicodedata.combining(char))
    return " ".join(ascii_value.lower().split())
