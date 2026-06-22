from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from backend.app.api.deps import get_db
from backend.app.models import Category, ClassificationFeedback, ClassificationRule, EmailMessage, FinancialAccount, InvestmentAccount, Transaction
from backend.app.schemas import (
    ClassificationFeedbackRead,
    ClassificationRuleCreate,
    ClassificationRuleRead,
    ClassificationRuleUpdate,
    RuleMatchRead,
    RuleSuggestionRead,
    RuleTestRequest,
    RuleTestResponse,
)
from backend.app.services.rule_classifier import (
    RuleClassification,
    classify_context,
    classify_raw_text,
    classification_names,
    context_from_email_message,
    context_from_transaction,
    load_active_rules,
)


router = APIRouter(prefix="/rules", tags=["rules"])


def _rule_options():
    return (
        selectinload(ClassificationRule.category),
        selectinload(ClassificationRule.financial_account),
        selectinload(ClassificationRule.investment_account),
    )


def _get_rule_or_404(rule_id: int, db: Session) -> ClassificationRule:
    rule = db.scalar(select(ClassificationRule).options(*_rule_options()).where(ClassificationRule.id == rule_id))
    if rule is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rule not found")
    return rule


def _validate_targets(payload: ClassificationRuleCreate | ClassificationRuleUpdate, db: Session) -> None:
    if getattr(payload, "category_id", None) is not None and db.get(Category, payload.category_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")
    if getattr(payload, "financial_account_id", None) is not None and db.get(FinancialAccount, payload.financial_account_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Financial account not found")
    if getattr(payload, "investment_account_id", None) is not None and db.get(InvestmentAccount, payload.investment_account_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Investment account not found")


def _to_rule_read(rule: ClassificationRule) -> ClassificationRuleRead:
    return ClassificationRuleRead(
        id=rule.id,
        name=rule.name,
        field=rule.field,
        operator=rule.operator,
        pattern=rule.pattern,
        category_id=rule.category_id,
        category_name=rule.category.name if rule.category else None,
        transaction_type=rule.transaction_type,
        financial_account_id=rule.financial_account_id,
        financial_account_name=rule.financial_account.name if rule.financial_account else None,
        investment_account_id=rule.investment_account_id,
        investment_account_name=rule.investment_account.name if rule.investment_account else None,
        priority=rule.priority,
        confidence=rule.confidence,
        is_active=rule.is_active,
        created_from_correction=rule.created_from_correction,
        notes=rule.notes,
        created_at=rule.created_at,
        updated_at=rule.updated_at,
    )


def _to_match_read(match) -> RuleMatchRead:
    rule = match.rule
    return RuleMatchRead(
        rule_id=rule.id,
        rule_name=rule.name,
        field=rule.field,
        operator=rule.operator,
        pattern=rule.pattern,
        confidence=rule.confidence,
        reason=match.reason,
    )


def _to_test_response(classification: RuleClassification, db: Session, input_preview: str) -> RuleTestResponse:
    names = classification_names(classification, db)
    return RuleTestResponse(
        input_preview=input_preview[:500],
        category_id=classification.category_id,
        category_name=names["category_name"],
        transaction_type=classification.transaction_type,
        financial_account_id=classification.financial_account_id,
        financial_account_name=names["financial_account_name"],
        investment_account_id=classification.investment_account_id,
        investment_account_name=names["investment_account_name"],
        confidence=classification.confidence,
        reason=classification.reason,
        matched_rules=[_to_match_read(match) for match in classification.matched_rules],
    )


@router.get("", response_model=list[ClassificationRuleRead])
def list_rules(active_only: bool = False, db: Session = Depends(get_db)) -> list[ClassificationRuleRead]:
    query = select(ClassificationRule).options(*_rule_options()).order_by(ClassificationRule.priority, ClassificationRule.id)
    if active_only:
        query = query.where(ClassificationRule.is_active.is_(True))
    return [_to_rule_read(rule) for rule in db.scalars(query).all()]


@router.post("", response_model=ClassificationRuleRead, status_code=status.HTTP_201_CREATED)
def create_rule(payload: ClassificationRuleCreate, db: Session = Depends(get_db)) -> ClassificationRuleRead:
    _validate_targets(payload, db)
    rule = ClassificationRule(**payload.model_dump())
    db.add(rule)
    db.commit()
    return _to_rule_read(_get_rule_or_404(rule.id, db))


@router.patch("/{rule_id:int}", response_model=ClassificationRuleRead)
def update_rule(rule_id: int, payload: ClassificationRuleUpdate, db: Session = Depends(get_db)) -> ClassificationRuleRead:
    rule = _get_rule_or_404(rule_id, db)
    _validate_targets(payload, db)
    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(rule, key, value)
    if not any([rule.category_id, rule.transaction_type, rule.financial_account_id, rule.investment_account_id]):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="A rule must set at least one target")
    db.add(rule)
    db.commit()
    return _to_rule_read(_get_rule_or_404(rule.id, db))


@router.delete("/{rule_id:int}", status_code=status.HTTP_204_NO_CONTENT)
def delete_rule(rule_id: int, db: Session = Depends(get_db)) -> Response:
    rule = _get_rule_or_404(rule_id, db)
    db.delete(rule)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/test", response_model=RuleTestResponse)
def test_rule(payload: RuleTestRequest, db: Session = Depends(get_db)) -> RuleTestResponse:
    if payload.raw_text:
        _, classification = classify_raw_text(payload.raw_text, db)
        return _to_test_response(classification, db, payload.raw_text)
    if payload.email_message_id:
        message = db.get(EmailMessage, payload.email_message_id)
        if message is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Email message not found")
        context = context_from_email_message(message)
        classification = classify_context(context, load_active_rules(db))
        return _to_test_response(classification, db, context.source_text)
    transaction = db.get(Transaction, payload.transaction_id)
    if transaction is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found")
    context = context_from_transaction(transaction)
    classification = classify_context(context, load_active_rules(db))
    return _to_test_response(classification, db, context.source_text)


@router.get("/feedback", response_model=list[ClassificationFeedbackRead])
def list_feedback(limit: int = Query(default=50, ge=1, le=200), db: Session = Depends(get_db)) -> list[ClassificationFeedbackRead]:
    feedback = db.scalars(select(ClassificationFeedback).order_by(ClassificationFeedback.created_at.desc(), ClassificationFeedback.id.desc()).limit(limit)).all()
    return [_feedback_read(item, db) for item in feedback]


@router.get("/suggestions", response_model=list[RuleSuggestionRead])
def rule_suggestions(min_count: int = Query(default=2, ge=2, le=10), db: Session = Depends(get_db)) -> list[RuleSuggestionRead]:
    feedback_items = db.scalars(select(ClassificationFeedback)).all()
    grouped: dict[tuple, list[ClassificationFeedback]] = defaultdict(list)
    for item in feedback_items:
        key = (
            item.field,
            item.pattern,
            item.new_category_id,
            item.new_financial_account_id,
            item.new_investment_account_id,
            item.new_transaction_type,
        )
        grouped[key].append(item)

    suggestions: list[RuleSuggestionRead] = []
    for (field, pattern, category_id, financial_account_id, investment_account_id, transaction_type), items in grouped.items():
        if len(items) < min_count:
            continue
        if _rule_exists(db, field, pattern, category_id, financial_account_id, investment_account_id, transaction_type):
            continue
        category = db.get(Category, category_id) if category_id else None
        financial_account = db.get(FinancialAccount, financial_account_id) if financial_account_id else None
        investment_account = db.get(InvestmentAccount, investment_account_id) if investment_account_id else None
        suggestions.append(
            RuleSuggestionRead(
                field=field,
                pattern=pattern,
                count=len(items),
                category_id=category_id,
                category_name=category.name if category else None,
                financial_account_id=financial_account_id,
                financial_account_name=financial_account.name if financial_account else None,
                investment_account_id=investment_account_id,
                investment_account_name=investment_account.name if investment_account else None,
                transaction_type=transaction_type,
                confidence=min(0.9, 0.6 + len(items) * 0.08),
                reason=f"{len(items)} correcciones repetidas sobre '{pattern}'",
            )
        )
    return sorted(suggestions, key=lambda item: item.count, reverse=True)


def _rule_exists(
    db: Session,
    field: str,
    pattern: str,
    category_id: int | None,
    financial_account_id: int | None,
    investment_account_id: int | None,
    transaction_type: str | None,
) -> bool:
    return (
        db.scalar(
            select(ClassificationRule).where(
                ClassificationRule.field == field,
                ClassificationRule.pattern == pattern,
                ClassificationRule.category_id == category_id,
                ClassificationRule.financial_account_id == financial_account_id,
                ClassificationRule.investment_account_id == investment_account_id,
                ClassificationRule.transaction_type == transaction_type,
            )
        )
        is not None
    )


def _feedback_read(item: ClassificationFeedback, db: Session) -> ClassificationFeedbackRead:
    category = db.get(Category, item.new_category_id) if item.new_category_id else None
    financial_account = db.get(FinancialAccount, item.new_financial_account_id) if item.new_financial_account_id else None
    investment_account = db.get(InvestmentAccount, item.new_investment_account_id) if item.new_investment_account_id else None
    return ClassificationFeedbackRead(
        id=item.id,
        transaction_id=item.transaction_id,
        field=item.field,
        pattern=item.pattern,
        merchant_name=item.merchant_name,
        sender_email=item.sender_email,
        subject=item.subject,
        new_category_id=item.new_category_id,
        new_category_name=category.name if category else None,
        new_financial_account_id=item.new_financial_account_id,
        new_financial_account_name=financial_account.name if financial_account else None,
        new_investment_account_id=item.new_investment_account_id,
        new_investment_account_name=investment_account.name if investment_account else None,
        new_transaction_type=item.new_transaction_type,
        confidence=item.confidence,
        created_at=item.created_at,
    )
