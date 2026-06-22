import json
import unicodedata
from datetime import datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from backend.app.api.deps import get_db
from backend.app.core.config import PROJECT_ROOT
from backend.app.models import (
    Category,
    EmailMessage,
    FinancialAccount,
    ImportRun,
    InvestmentAccount,
    InvestmentMovement,
    Payable,
    Person,
    Receivable,
    Transaction,
    TransactionSplit,
)
from backend.app.schemas import (
    ImportCandidateConfirm,
    ImportCandidateRead,
    ImportCandidateSplit,
    ImportConfirmResponse,
    ImportDemoRequest,
    ImportDiscardRequest,
    ImportDiscardResponse,
    ImportTextRequest,
    PayablePaymentAllocationCreate,
    ReceivablePaymentAllocationCreate,
    TransactionSplitCreate,
)
from backend.app.api.v1.transactions import _resolve_internal_transfer
from backend.app.schemas.money import normalize_currency, validate_money_scale
from backend.app.services.email_parser import EmailParseError, ParsedEmailCandidate, cashflow_direction_for_type, parse_email_text
from backend.app.services.payables import apply_payable_payments
from backend.app.services.receivables import apply_receivable_payments
from backend.app.services.rule_classifier import classify_parsed_candidate


router = APIRouter(prefix="/import", tags=["import"])

SAMPLE_EMAILS_PATH = PROJECT_ROOT / "data/demo/sample_emails.json"


def _transaction_options():
    return (
        selectinload(Transaction.category),
        selectinload(Transaction.financial_account),
        selectinload(Transaction.investment_account),
        selectinload(Transaction.person),
        selectinload(Transaction.receivable),
        selectinload(Transaction.payable),
        selectinload(Transaction.splits).selectinload(TransactionSplit.category),
    )


def _signed_amount(amount: Decimal, transaction_type: str) -> Decimal:
    if transaction_type in {"expense", "transfer_out", "internal_transfer", "loan_out", "subscription", "payable_payment", "investment"}:
        return -abs(amount)
    return abs(amount)


def _prefer_parser_transaction_type(
    parsed: ParsedEmailCandidate,
    rule_transaction_type: str | None,
    rule_confidence: float | None,
) -> bool:
    if not rule_transaction_type or parsed.suggested_transaction_type == rule_transaction_type:
        return False
    # An explicit own-account transfer detected by the parser should not be flipped
    # back to a generic in/out transfer (or expense) by a broad sender rule.
    if parsed.suggested_transaction_type == "internal_transfer" and rule_transaction_type in {"transfer_in", "transfer_out", "expense"}:
        return True
    parsed_direction = cashflow_direction_for_type(parsed.suggested_transaction_type)
    rule_direction = cashflow_direction_for_type(rule_transaction_type)
    if "neutral" in {parsed_direction, rule_direction} or parsed_direction == rule_direction:
        return False
    return (rule_confidence or 0) <= parsed.confidence


def _category_by_name(db: Session, name: str | None) -> Category | None:
    if not name:
        return None
    return db.scalar(select(Category).where(Category.name == name))


def _validate_category(category_id: int | None, db: Session) -> None:
    if category_id is not None and db.get(Category, category_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")


def _validate_financial_account(financial_account_id: int | None, db: Session) -> FinancialAccount | None:
    if financial_account_id is None:
        return None
    account = db.get(FinancialAccount, financial_account_id)
    if account is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Financial account not found")
    return account


def _validate_investment_account(investment_account_id: int | None, db: Session) -> InvestmentAccount | None:
    if investment_account_id is None:
        return None
    account = db.get(InvestmentAccount, investment_account_id)
    if account is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Investment account not found")
    return account


def _validate_person(person_id: int | None, db: Session) -> None:
    if person_id is not None and db.get(Person, person_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Person not found")


def _validate_receivable(receivable_id: int | None, db: Session) -> Receivable | None:
    if receivable_id is None:
        return None
    receivable = db.get(Receivable, receivable_id)
    if receivable is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Receivable not found")
    return receivable


def _validate_payable(payable_id: int | None, db: Session) -> Payable | None:
    if payable_id is None:
        return None
    payable = db.get(Payable, payable_id)
    if payable is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payable not found")
    return payable


def _validate_splits(amount: Decimal, splits: list[TransactionSplitCreate], db: Session, currency: str = "CLP") -> None:
    if not splits:
        return
    for split in splits:
        _validate_category(split.category_id, db)
        if split.currency != currency:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Split currency must match transaction currency")
    total = sum((split.amount for split in splits), Decimal("0"))
    if total != amount:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Split amounts must equal transaction amount")


def _adjust_splits_for_amount(
    original_amount: Decimal,
    adjusted_amount: Decimal,
    splits: list[TransactionSplitCreate],
) -> list[TransactionSplitCreate]:
    if not splits or adjusted_amount == original_amount:
        return splits
    split_total = sum((split.amount for split in splits), Decimal("0"))
    if split_total != original_amount:
        return splits

    adjusted: list[TransactionSplitCreate] = []
    allocated = Decimal("0")
    for index, split in enumerate(splits):
        amount = adjusted_amount - allocated if index == len(splits) - 1 else (split.amount * adjusted_amount / original_amount).quantize(Decimal("1"))
        allocated += amount
        adjusted.append(split.model_copy(update={"amount": amount}))
    return adjusted


def _scale_amount_clp(original_amount: Decimal, adjusted_amount: Decimal, amount_clp: Decimal | None) -> Decimal | None:
    if amount_clp is None or adjusted_amount == original_amount:
        return amount_clp
    return (amount_clp * adjusted_amount / original_amount).quantize(Decimal("1"))


def _normalize_money_fields(data: dict, original_amount: Decimal, adjusted_amount: Decimal) -> dict:
    try:
        currency = normalize_currency(data.get("currency") or "CLP") or "CLP"
        original_currency = normalize_currency(data.get("original_currency") or currency) or currency
        data["currency"] = currency
        data["original_currency"] = original_currency
        if data.get("original_amount") is None:
            data["original_amount"] = adjusted_amount
        if currency == "CLP":
            data["amount_clp"] = adjusted_amount
        else:
            data["amount_clp"] = _scale_amount_clp(original_amount, adjusted_amount, data.get("amount_clp"))
        if data.get("exchange_rate") is None and data.get("amount_clp") is not None and data["original_amount"] > Decimal("0") and original_currency != "CLP":
            data["exchange_rate"] = (data["amount_clp"] / data["original_amount"]).quantize(Decimal("0.000001"))
        validate_money_scale(data["amount"], currency, "amount")
        validate_money_scale(data.get("signed_amount"), currency, "signed_amount")
        validate_money_scale(data.get("original_amount"), original_currency, "original_amount")
        validate_money_scale(data.get("amount_clp"), "CLP", "amount_clp")
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return data


def _validate_account_currency(account: FinancialAccount | None, currency: str) -> None:
    if account is None:
        return
    if account.currency != currency:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Financial account currency is {account.currency}, but transaction currency is {currency}",
        )


def _ensure_category(db: Session, name: str, kind: str, color: str, icon: str, sort_order: int) -> Category:
    category = _category_by_name(db, name)
    if category is not None:
        return category
    category = Category(name=name, kind=kind, color=color, icon=icon, sort_order=sort_order, is_system=True)
    db.add(category)
    db.flush()
    return category


def _create_adjustment_transaction(
    db: Session,
    *,
    amount: Decimal,
    occurred_at: datetime,
    currency: str,
    source: str,
    source_message_id: str,
    person_id: int | None,
    counterparty: str | None,
    direction: str,
) -> Transaction | None:
    if amount <= Decimal("0"):
        return None
    if direction == "income":
        category = _ensure_category(db, "Ingreso por ajuste", "income", "#4ADE80", "badge-dollar-sign", 118)
        transaction_type = "income"
        description = "Diferencia positiva al asignar transferencia recibida a cuentas por cobrar"
    else:
        category = _ensure_category(db, "Costo por ajuste", "expense", "#FB7185", "badge-minus", 119)
        transaction_type = "expense"
        description = "Diferencia positiva al asignar transferencia enviada a cuentas por pagar"

    transaction = Transaction(
        occurred_at=occurred_at,
        amount=amount,
        signed_amount=_signed_amount(amount, transaction_type),
        currency=currency,
        original_amount=amount,
        original_currency=currency,
        amount_clp=amount if currency == "CLP" else None,
        counterparty=counterparty,
        person_id=person_id,
        description=description,
        category_id=category.id,
        source=source,
        source_message_id=source_message_id,
        transaction_type=transaction_type,
        status="classified",
        classification_method="obligation_adjustment",
        classification_reason=category.name,
    )
    db.add(transaction)
    return transaction


def _create_investment_movement(transaction: Transaction, db: Session) -> None:
    if transaction.transaction_type not in {"investment", "disinvestment"} or transaction.investment_account_id is None:
        return
    account = db.get(InvestmentAccount, transaction.investment_account_id)
    if account is None:
        return
    movement = InvestmentMovement(
        investment_account_id=account.id,
        transaction_id=transaction.id,
        occurred_at=transaction.occurred_at,
        movement_type=transaction.transaction_type,
        amount=transaction.amount,
        currency=transaction.currency,
        source=transaction.source,
        notes=transaction.notes,
    )
    if transaction.transaction_type == "investment":
        account.current_value += transaction.amount
    else:
        account.current_value -= transaction.amount
    db.add(account)
    db.add(movement)


def _normalize_match(value: str | None) -> str:
    if not value:
        return ""
    decomposed = unicodedata.normalize("NFKD", value)
    ascii_value = "".join(char for char in decomposed if not unicodedata.combining(char))
    return " ".join(ascii_value.lower().split())


def _same_institution(left: str | None, right: str | None) -> bool:
    left_normalized = _normalize_match(left)
    right_normalized = _normalize_match(right)
    if not left_normalized or not right_normalized:
        return False
    return left_normalized == right_normalized or left_normalized in right_normalized or right_normalized in left_normalized


def _match_financial_account(parsed: ParsedEmailCandidate, db: Session) -> FinancialAccount | None:
    if not parsed.detected_account_institution and not parsed.detected_account_type and not parsed.detected_account_last_four:
        return None
    candidates = list(db.scalars(select(FinancialAccount).where(FinancialAccount.is_active.is_(True))).all())
    scored: list[tuple[int, FinancialAccount]] = []
    for account in candidates:
        score = 0
        if parsed.currency:
            score += 4 if account.currency == parsed.currency else -6
        if parsed.detected_account_last_four:
            score += 6 if account.last_four == parsed.detected_account_last_four else -4 if account.last_four else 0
        if parsed.detected_account_type:
            score += 3 if account.account_type == parsed.detected_account_type else -2 if account.account_type != "unknown" else 0
        if parsed.detected_account_institution:
            score += 3 if _same_institution(account.institution, parsed.detected_account_institution) else -1 if account.institution else 0
        if score > 0:
            scored.append((score, account))

    if not scored:
        return None

    if parsed.detected_account_last_four:
        minimum_score = 5
    elif parsed.detected_account_institution and parsed.detected_account_type:
        minimum_score = 5
    elif parsed.detected_account_institution:
        minimum_score = 3
    else:
        return None

    score, account = max(scored, key=lambda item: (item[0], item[1].id))
    return account if score >= minimum_score else None


def _create_internal_receivables(payload: ImportCandidateConfirm, amount: Decimal, db: Session) -> Decimal:
    if not payload.internal_receivables:
        return amount
    if payload.transaction_type not in {"expense", "subscription"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Internal receivables are only valid for expenses")

    total_internal = Decimal("0")
    for internal in payload.internal_receivables:
        _validate_person(internal.person_id, db)
        total_internal += internal.amount
    if total_internal >= amount:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Internal receivables must be lower than transaction amount")

    for internal in payload.internal_receivables:
        receivable = Receivable(
            person_id=internal.person_id,
            title=internal.title,
            original_amount=internal.amount,
            remaining_amount=internal.amount,
            currency=payload.currency,
            issued_at=payload.occurred_at,
            due_at=internal.due_at,
            notes=internal.notes or f"Cuenta por cobrar interna desde compra: {payload.description or payload.merchant_name or 'sin detalle'}",
        )
        db.add(receivable)
    return amount - total_internal


def _create_internal_payables(payload: ImportCandidateConfirm, amount: Decimal, db: Session) -> Decimal:
    if not payload.internal_payables:
        return amount
    if payload.transaction_type not in {"income", "transfer_in", "refund", "disinvestment"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Internal payables are only valid for inflows")

    total_internal = Decimal("0")
    for internal in payload.internal_payables:
        _validate_person(internal.person_id, db)
        total_internal += internal.amount
    if total_internal >= amount:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Internal payables must be lower than transaction amount")

    for internal in payload.internal_payables:
        payable = Payable(
            person_id=internal.person_id,
            title=internal.title,
            original_amount=internal.amount,
            remaining_amount=internal.amount,
            currency=payload.currency,
            issued_at=payload.occurred_at,
            due_at=internal.due_at,
            notes=internal.notes or f"Cuenta por pagar interna desde ingreso: {payload.description or payload.counterparty or 'sin detalle'}",
        )
        db.add(payable)
    return amount - total_internal


def _create_import_run(db: Session, source: str, messages_seen: int = 1) -> ImportRun:
    import_run = ImportRun(
        source=source,
        status="previewed",
        started_at=datetime.now(timezone.utc),
        finished_at=datetime.now(timezone.utc),
        messages_seen=messages_seen,
        messages_imported=0,
        transactions_created=0,
    )
    db.add(import_run)
    db.flush()
    return import_run


def _create_email_message(db: Session, parsed: ParsedEmailCandidate, import_run: ImportRun) -> EmailMessage:
    email_message = EmailMessage(
        received_at=parsed.received_at,
        sender_name=parsed.sender_name,
        sender_email=parsed.sender_email,
        subject=parsed.subject,
        body_preview=parsed.body_preview,
        body_text=parsed.body_text,
        body_hash=parsed.body_hash,
        import_run_id=import_run.id,
        parse_status="parsed",
    )
    db.add(email_message)
    db.flush()
    import_run.messages_imported += 1
    return email_message


def _to_candidate_response(
    parsed: ParsedEmailCandidate,
    email_message: EmailMessage,
    import_run: ImportRun,
    db: Session,
) -> ImportCandidateRead:
    rule_classification = classify_parsed_candidate(parsed, db)
    prefer_parser_transaction = _prefer_parser_transaction_type(parsed, rule_classification.transaction_type, rule_classification.confidence)
    use_rule_classification = bool(rule_classification.matched_rules) and not prefer_parser_transaction
    category = (
        db.get(Category, rule_classification.category_id)
        if use_rule_classification and rule_classification.category_id
        else _category_by_name(db, parsed.suggested_category_name)
    )
    financial_account = (
        db.get(FinancialAccount, rule_classification.financial_account_id)
        if use_rule_classification and rule_classification.financial_account_id
        else _match_financial_account(parsed, db)
    )
    investment_account = (
        db.get(InvestmentAccount, rule_classification.investment_account_id)
        if use_rule_classification and rule_classification.investment_account_id
        else None
    )
    if use_rule_classification and rule_classification.transaction_type:
        suggested_transaction_type = rule_classification.transaction_type
    else:
        suggested_transaction_type = parsed.suggested_transaction_type
    confidence = rule_classification.confidence if use_rule_classification else parsed.confidence
    classification_reason = rule_classification.reason if use_rule_classification else parsed.classification_reason
    classification_method = "rule_engine" if use_rule_classification else "email_parser"
    splits: list[ImportCandidateSplit] = []
    for split in parsed.suggested_splits:
        split_category = _category_by_name(db, split.category_name)
        splits.append(
            ImportCandidateSplit(
                category_id=split_category.id if split_category else None,
                category_name=split.category_name,
                amount=split.amount,
                currency=parsed.currency,
                label=split.label,
            )
        )

    return ImportCandidateRead(
        email_message_id=email_message.id,
        import_run_id=import_run.id,
        subject=parsed.subject,
        body_preview=parsed.body_preview,
        body_text=email_message.body_text or parsed.body_text,
        body_html=email_message.body_html,
        received_at=parsed.received_at,
        sender_name=parsed.sender_name,
        sender_email=parsed.sender_email,
        amount=parsed.amount,
        currency=parsed.currency,
        original_amount=parsed.original_amount,
        original_currency=parsed.original_currency,
        amount_clp=parsed.amount_clp,
        exchange_rate=parsed.exchange_rate,
        exchange_rate_source=parsed.exchange_rate_source,
        exchange_rate_date=parsed.exchange_rate_date,
        currency_detection_confidence=parsed.currency_detection_confidence,
        currency_detection_reason=parsed.currency_detection_reason,
        merchant_name=parsed.merchant_name,
        counterparty=parsed.counterparty,
        description=parsed.description,
        suggested_category_id=category.id if category else None,
        suggested_category_name=category.name if category else parsed.suggested_category_name,
        suggested_category_color=category.color if category else None,
        suggested_transaction_type=suggested_transaction_type,
        cashflow_direction=cashflow_direction_for_type(suggested_transaction_type),
        suggested_financial_account_id=financial_account.id if financial_account else None,
        suggested_financial_account_name=financial_account.name if financial_account else None,
        suggested_investment_account_id=investment_account.id if investment_account else None,
        suggested_investment_account_name=investment_account.name if investment_account else None,
        detected_account_institution=parsed.detected_account_institution,
        detected_account_type=parsed.detected_account_type,
        detected_account_last_four=parsed.detected_account_last_four,
        account_detection_confidence=parsed.account_detection_confidence,
        account_detection_reason=parsed.account_detection_reason,
        status=parsed.status,
        confidence=confidence,
        classification_reason=classification_reason,
        classification_method=classification_method,
        needs_split=parsed.needs_split,
        suggested_splits=splits,
    )


def _get_transaction_or_404(transaction_id: int, db: Session) -> Transaction:
    query = select(Transaction).options(*_transaction_options()).where(Transaction.id == transaction_id)
    transaction = db.scalar(query)
    if transaction is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found")
    return transaction


def _load_samples() -> list[dict[str, str]]:
    if not SAMPLE_EMAILS_PATH.exists():
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Demo dataset not found")
    with SAMPLE_EMAILS_PATH.open(encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, list):
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Demo dataset must be a list")
    return data


@router.post("/text", response_model=ImportCandidateRead, status_code=status.HTTP_201_CREATED)
def preview_text_import(payload: ImportTextRequest, db: Session = Depends(get_db)) -> ImportCandidateRead:
    import_run = _create_import_run(db, "text")
    try:
        parsed = parse_email_text(payload.raw_text)
    except EmailParseError as exc:
        import_run.status = "failed"
        import_run.errors_count = 1
        import_run.error_summary = str(exc)
        db.add(import_run)
        db.commit()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    email_message = _create_email_message(db, parsed, import_run)
    db.commit()
    return _to_candidate_response(parsed, email_message, import_run, db)


@router.post("/demo", response_model=list[ImportCandidateRead], status_code=status.HTTP_201_CREATED)
def preview_demo_import(payload: ImportDemoRequest | None = None, db: Session = Depends(get_db)) -> list[ImportCandidateRead]:
    samples = _load_samples()
    sample_id = payload.sample_id if payload else None
    if sample_id:
        samples = [sample for sample in samples if sample.get("id") == sample_id]
        if not samples:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Demo sample not found")

    import_run = _create_import_run(db, "demo", messages_seen=len(samples))
    candidates: list[tuple[ParsedEmailCandidate, EmailMessage]] = []
    for sample in samples:
        raw_text = sample.get("raw_text", "")
        try:
            parsed = parse_email_text(raw_text)
        except EmailParseError as exc:
            import_run.errors_count += 1
            import_run.error_summary = str(exc)
            continue
        email_message = _create_email_message(db, parsed, import_run)
        candidates.append((parsed, email_message))

    if not candidates:
        import_run.status = "failed"
        db.add(import_run)
        db.commit()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="No demo candidates could be parsed")

    db.commit()
    return [_to_candidate_response(parsed, email_message, import_run, db) for parsed, email_message in candidates]


@router.post("/confirm", response_model=ImportConfirmResponse, status_code=status.HTTP_201_CREATED)
def confirm_import(payload: ImportCandidateConfirm, db: Session = Depends(get_db)) -> ImportConfirmResponse:
    email_message = db.get(EmailMessage, payload.email_message_id)
    if email_message is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Email message not found")

    import_run = db.get(ImportRun, payload.import_run_id or email_message.import_run_id) if payload.import_run_id or email_message.import_run_id else None
    _validate_category(payload.category_id, db)
    financial_account = _validate_financial_account(payload.financial_account_id, db)
    _validate_investment_account(payload.investment_account_id, db)
    _validate_person(payload.person_id, db)
    receivable = _validate_receivable(payload.receivable_id, db)
    payable = _validate_payable(payload.payable_id, db)
    receivable_allocations = payload.receivable_payments
    if receivable_allocations:
        for allocation in receivable_allocations:
            _validate_receivable(allocation.receivable_id, db)
    payable_allocations = payload.payable_payments
    if payable_allocations:
        for allocation in payable_allocations:
            _validate_payable(allocation.payable_id, db)

    transaction_receivable_id = payload.receivable_id
    if receivable_allocations:
        allocation_receivable_ids = {allocation.receivable_id for allocation in receivable_allocations}
        transaction_receivable_id = next(iter(allocation_receivable_ids)) if len(allocation_receivable_ids) == 1 else None

    transaction_payable_id = payload.payable_id
    if payable_allocations:
        allocation_payable_ids = {allocation.payable_id for allocation in payable_allocations}
        transaction_payable_id = next(iter(allocation_payable_ids)) if len(allocation_payable_ids) == 1 else None

    source = "demo" if import_run and import_run.source == "demo" else "gmail"
    source_message_id = f"email:{email_message.id}"
    transaction_amount = _create_internal_receivables(payload, payload.amount, db)
    transaction_amount = _create_internal_payables(payload, transaction_amount, db)
    if receivable_allocations:
        transaction_amount = sum((allocation.amount for allocation in receivable_allocations), Decimal("0"))
    if payable_allocations:
        transaction_amount = sum((allocation.amount for allocation in payable_allocations), Decimal("0"))

    if payload.transaction_type == "receivable_payment" and not receivable_allocations:
        if receivable is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Receivable payment requires receivable_id")
        payment_amount = min(payload.amount, receivable.remaining_amount)
        receivable_allocations = [
            ReceivablePaymentAllocationCreate(
                receivable_id=receivable.id,
                amount=payment_amount,
                notes="Pago confirmado desde importacion",
            )
        ]
        transaction_amount = payment_amount

    if payload.transaction_type == "payable_payment" and not payable_allocations:
        if payable is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Payable payment requires payable_id")
        payment_amount = min(payload.amount, payable.remaining_amount)
        payable_allocations = [
            PayablePaymentAllocationCreate(
                payable_id=payable.id,
                amount=payment_amount,
                notes="Pago confirmado desde importacion",
            )
        ]
        transaction_amount = payment_amount

    if transaction_amount <= Decimal("0"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Transaction amount must be greater than zero")

    effective_transaction_type = payload.transaction_type
    if receivable_allocations:
        effective_transaction_type = "receivable_payment"
    if payable_allocations:
        effective_transaction_type = "payable_payment"

    splits = _adjust_splits_for_amount(payload.amount, transaction_amount, payload.splits)
    money_data = _normalize_money_fields(
        {
            "amount": transaction_amount,
            "signed_amount": _signed_amount(transaction_amount, effective_transaction_type),
            "currency": payload.currency,
            "original_amount": payload.original_amount,
            "original_currency": payload.original_currency,
            "amount_clp": payload.amount_clp,
            "exchange_rate": payload.exchange_rate,
        },
        payload.amount,
        transaction_amount,
    )
    _validate_account_currency(financial_account, money_data["currency"])
    _validate_splits(transaction_amount, splits, db, money_data["currency"])

    destination_account_id, destination_amount, destination_currency = _resolve_internal_transfer(
        effective_transaction_type,
        payload.financial_account_id,
        money_data["currency"],
        transaction_amount,
        payload.destination_account_id,
        payload.destination_amount,
        db,
    )

    transaction = Transaction(
        occurred_at=payload.occurred_at,
        posted_at=payload.posted_at,
        amount=money_data["amount"],
        signed_amount=money_data["signed_amount"],
        currency=money_data["currency"],
        original_amount=money_data["original_amount"],
        original_currency=money_data["original_currency"],
        amount_clp=money_data["amount_clp"],
        exchange_rate=money_data["exchange_rate"],
        exchange_rate_source=payload.exchange_rate_source,
        exchange_rate_date=payload.exchange_rate_date,
        currency_detection_confidence=payload.currency_detection_confidence,
        currency_detection_reason=payload.currency_detection_reason,
        merchant_name=payload.merchant_name,
        counterparty=payload.counterparty,
        relationship_category=payload.relationship_category,
        financial_account_id=payload.financial_account_id,
        destination_account_id=destination_account_id,
        destination_amount=destination_amount,
        destination_currency=destination_currency,
        investment_account_id=payload.investment_account_id,
        person_id=payload.person_id,
        receivable_id=transaction_receivable_id,
        payable_id=transaction_payable_id,
        description=payload.description,
        subject=payload.subject or email_message.subject,
        category_id=payload.category_id,
        source=source,
        source_message_id=source_message_id,
        payment_method=payload.payment_method,
        transaction_type=effective_transaction_type,
        status=payload.status,
        confidence=payload.confidence,
        classification_method=payload.classification_method or "email_parser",
        classification_reason=payload.classification_reason,
        account_detection_method=payload.account_detection_method,
        account_detection_confidence=payload.account_detection_confidence,
        account_detection_reason=payload.account_detection_reason,
        notes=payload.notes,
    )
    for split in splits:
        transaction.splits.append(TransactionSplit(**split.model_dump()))
    db.add(transaction)
    db.flush()
    _create_investment_movement(transaction, db)

    if receivable_allocations:
        apply_receivable_payments(
            db,
            receivable_allocations,
            paid_at=payload.occurred_at,
            transaction_id=transaction.id,
            total_cap=payload.amount,
            default_notes="Pago confirmado desde importacion",
        )
        adjustment_amount = payload.amount - sum((allocation.amount for allocation in receivable_allocations), Decimal("0"))
        _create_adjustment_transaction(
            db,
            amount=adjustment_amount,
            occurred_at=payload.occurred_at,
            currency=payload.currency,
            source=source,
            source_message_id=source_message_id,
            person_id=payload.person_id,
            counterparty=payload.counterparty,
            direction="income",
        )

    if payable_allocations:
        apply_payable_payments(
            db,
            payable_allocations,
            paid_at=payload.occurred_at,
            transaction_id=transaction.id,
            total_cap=payload.amount,
            default_notes="Pago confirmado desde importacion",
        )
        adjustment_amount = payload.amount - sum((allocation.amount for allocation in payable_allocations), Decimal("0"))
        _create_adjustment_transaction(
            db,
            amount=adjustment_amount,
            occurred_at=payload.occurred_at,
            currency=payload.currency,
            source=source,
            source_message_id=source_message_id,
            person_id=payload.person_id,
            counterparty=payload.counterparty,
            direction="expense",
        )

    email_message.parse_status = "confirmed"
    db.add(email_message)
    if import_run is not None:
        import_run.status = "confirmed"
        import_run.transactions_created += 1
        db.add(import_run)
    db.commit()
    return ImportConfirmResponse(
        transaction=_get_transaction_or_404(transaction.id, db),
        email_message_id=email_message.id,
        import_run_id=import_run.id if import_run else None,
    )


@router.post("/discard", response_model=ImportDiscardResponse)
def discard_import(payload: ImportDiscardRequest, db: Session = Depends(get_db)) -> ImportDiscardResponse:
    email_message = db.get(EmailMessage, payload.email_message_id)
    if email_message is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Email message not found")

    import_run = db.get(ImportRun, payload.import_run_id or email_message.import_run_id) if payload.import_run_id or email_message.import_run_id else None
    email_message.parse_status = "discarded"
    db.add(email_message)
    if import_run is not None and import_run.transactions_created == 0:
        import_run.status = "discarded"
        db.add(import_run)
    db.commit()
    return ImportDiscardResponse(
        email_message_id=email_message.id,
        import_run_id=import_run.id if import_run else None,
        status=email_message.parse_status,
    )
