from datetime import datetime
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from backend.app.api.deps import get_db
from backend.app.models import (
    Category,
    ClassificationFeedback,
    EmailMessage,
    FinancialAccount,
    InvestmentAccount,
    InvestmentMovement,
    Payable,
    Person,
    Receivable,
    Transaction,
    TransactionSplit,
)
from backend.app.schemas import TransactionCreate, TransactionRead, TransactionSplitCreate, TransactionSplitRead, TransactionUpdate
from backend.app.schemas.money import normalize_currency, validate_money_scale


router = APIRouter(prefix="/transactions", tags=["transactions"])


def _transaction_options():
    return (
        selectinload(Transaction.category),
        selectinload(Transaction.financial_account),
        selectinload(Transaction.destination_account),
        selectinload(Transaction.investment_account),
        selectinload(Transaction.person),
        selectinload(Transaction.receivable),
        selectinload(Transaction.payable),
        selectinload(Transaction.splits).selectinload(TransactionSplit.category),
    )


def _get_transaction_or_404(transaction_id: int, db: Session) -> Transaction:
    query = (
        select(Transaction)
        .options(*_transaction_options())
        .where(Transaction.id == transaction_id)
    )
    transaction = db.scalar(query)
    if transaction is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found")
    return transaction


def _validate_category(category_id: int | None, db: Session) -> None:
    if category_id is None:
        return
    if db.get(Category, category_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")


def _validate_person(person_id: int | None, db: Session) -> None:
    if person_id is None:
        return
    if db.get(Person, person_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Person not found")


def _validate_financial_account(financial_account_id: int | None, db: Session) -> FinancialAccount | None:
    if financial_account_id is None:
        return None
    account = db.get(FinancialAccount, financial_account_id)
    if account is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Financial account not found")
    return account


def _validate_investment_account(investment_account_id: int | None, db: Session) -> None:
    if investment_account_id is None:
        return
    if db.get(InvestmentAccount, investment_account_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Investment account not found")


def _validate_receivable(receivable_id: int | None, db: Session) -> None:
    if receivable_id is None:
        return
    if db.get(Receivable, receivable_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Receivable not found")


def _validate_payable(payable_id: int | None, db: Session) -> None:
    if payable_id is None:
        return
    if db.get(Payable, payable_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payable not found")


def _signed_amount(amount: Decimal, transaction_type: str) -> Decimal:
    if transaction_type in {"expense", "transfer_out", "internal_transfer", "loan_out", "subscription", "payable_payment", "investment"}:
        return -abs(amount)
    return abs(amount)


def _resolve_internal_transfer(
    transaction_type: str,
    origin_account_id: int | None,
    currency: str,
    amount: Decimal,
    destination_account_id: int | None,
    destination_amount: Decimal | None,
    db: Session,
) -> tuple[int | None, Decimal | None, str | None]:
    """Validate and normalize the destination leg of an internal transfer.

    Returns ``(destination_account_id, destination_amount, destination_currency)``.
    For any non-transfer type the destination fields are cleared.
    """
    if transaction_type != "internal_transfer":
        return None, None, None
    if origin_account_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="El traspaso entre cuentas requiere una cuenta de origen")
    if destination_account_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="El traspaso entre cuentas requiere una cuenta de destino")
    if destination_account_id == origin_account_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="La cuenta de destino debe ser distinta a la de origen")
    destination = db.get(FinancialAccount, destination_account_id)
    if destination is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Destination account not found")

    dest_currency = destination.currency
    if dest_currency == currency:
        resolved_amount = destination_amount if destination_amount is not None else abs(amount)
    elif destination_amount is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Indica el monto recibido en {dest_currency} para un traspaso entre monedas distintas",
        )
    else:
        resolved_amount = destination_amount

    try:
        validate_money_scale(resolved_amount, dest_currency, "destination_amount")
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return destination_account_id, abs(resolved_amount), dest_currency


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


def _validate_splits(amount: Decimal, splits: list[TransactionSplitCreate], db: Session, currency: str = "CLP") -> None:
    if not splits:
        return
    for split in splits:
        _validate_category(split.category_id, db)
        if split.currency != currency:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Split currency must match transaction currency",
            )
    total = sum((split.amount for split in splits), Decimal("0"))
    if total != amount:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Split amounts must equal transaction amount",
        )


def _replace_splits(
    transaction: Transaction,
    splits: list[TransactionSplitCreate],
    db: Session,
) -> None:
    transaction.splits.clear()
    for split in splits:
        transaction.splits.append(TransactionSplit(**split.model_dump()))
    db.add(transaction)


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


def _create_internal_receivables(payload: TransactionCreate, amount: Decimal, db: Session) -> Decimal:
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


def _create_internal_payables(payload: TransactionCreate, amount: Decimal, db: Session) -> Decimal:
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


def _investment_movement_for_transaction(transaction_id: int, db: Session) -> InvestmentMovement | None:
    return db.scalar(
        select(InvestmentMovement)
        .where(InvestmentMovement.transaction_id == transaction_id)
        .order_by(InvestmentMovement.id.desc())
    )


def _apply_investment_delta(
    investment_account_id: int,
    movement_type: str,
    amount: Decimal,
    db: Session,
    direction: int = 1,
) -> None:
    account = db.get(InvestmentAccount, investment_account_id)
    if account is None:
        return
    signed_amount = amount * Decimal(direction)
    if movement_type == "investment":
        account.current_value += signed_amount
    elif movement_type == "disinvestment":
        account.current_value -= signed_amount
    db.add(account)


def _sync_investment_movement(transaction: Transaction, db: Session) -> None:
    existing = _investment_movement_for_transaction(transaction.id, db)
    if existing is not None:
        _apply_investment_delta(existing.investment_account_id, existing.movement_type, existing.amount, db, direction=-1)

    if transaction.transaction_type not in {"investment", "disinvestment"} or transaction.investment_account_id is None:
        if existing is not None:
            db.delete(existing)
        return

    if db.get(InvestmentAccount, transaction.investment_account_id) is None:
        if existing is not None:
            db.delete(existing)
        return

    movement = existing or InvestmentMovement(transaction_id=transaction.id)
    movement.investment_account_id = transaction.investment_account_id
    movement.occurred_at = transaction.occurred_at
    movement.movement_type = transaction.transaction_type
    movement.amount = transaction.amount
    movement.currency = transaction.currency
    movement.source = transaction.source
    movement.notes = transaction.notes
    _apply_investment_delta(transaction.investment_account_id, transaction.transaction_type, transaction.amount, db)
    db.add(movement)


def _delete_investment_movement(transaction: Transaction, db: Session) -> None:
    existing = _investment_movement_for_transaction(transaction.id, db)
    if existing is None:
        return
    _apply_investment_delta(existing.investment_account_id, existing.movement_type, existing.amount, db, direction=-1)
    db.delete(existing)


def _source_email(transaction: Transaction, db: Session) -> EmailMessage | None:
    if not transaction.source_message_id or not transaction.source_message_id.startswith("email:"):
        return None
    try:
        email_id = int(transaction.source_message_id.split(":", 1)[1])
    except ValueError:
        return None
    return db.get(EmailMessage, email_id)


def _feedback_field_and_pattern(transaction: Transaction, email_message: EmailMessage | None) -> tuple[str, str]:
    if transaction.merchant_name:
        return "merchant_name", transaction.merchant_name
    if transaction.counterparty:
        return "counterparty", transaction.counterparty
    if email_message and email_message.sender_email:
        return "sender_email", email_message.sender_email
    if transaction.subject:
        return "subject", transaction.subject
    return "description", transaction.description or "movimiento"


def _record_feedback(transaction: Transaction, data: dict, db: Session) -> None:
    tracked_fields = {"category_id", "financial_account_id", "investment_account_id", "transaction_type"}
    if not tracked_fields.intersection(data):
        return
    changed = any(
        key in data and getattr(transaction, key) != data[key]
        for key in tracked_fields
    )
    if not changed:
        return

    email_message = _source_email(transaction, db)
    field, pattern = _feedback_field_and_pattern(transaction, email_message)
    feedback = ClassificationFeedback(
        transaction_id=transaction.id,
        source_message_id=transaction.source_message_id,
        field=field,
        pattern=pattern[:240],
        merchant_name=transaction.merchant_name,
        sender_email=email_message.sender_email if email_message else None,
        subject=transaction.subject or (email_message.subject if email_message else None),
        previous_category_id=transaction.category_id,
        new_category_id=data.get("category_id", transaction.category_id),
        previous_financial_account_id=transaction.financial_account_id,
        new_financial_account_id=data.get("financial_account_id", transaction.financial_account_id),
        previous_investment_account_id=transaction.investment_account_id,
        new_investment_account_id=data.get("investment_account_id", transaction.investment_account_id),
        previous_transaction_type=transaction.transaction_type,
        new_transaction_type=data.get("transaction_type", transaction.transaction_type),
        confidence=0.72,
    )
    db.add(feedback)


@router.get("", response_model=list[TransactionRead])
def list_transactions(
    from_: Annotated[datetime | None, Query(alias="from")] = None,
    to: datetime | None = None,
    category_id: int | None = None,
    source: str | None = None,
    status: str | None = None,
    transaction_type: str | None = None,
    relationship_category: str | None = None,
    person_id: int | None = None,
    merchant: str | None = None,
    min_amount: Decimal | None = None,
    max_amount: Decimal | None = None,
    q: str | None = None,
    db: Session = Depends(get_db),
) -> list[Transaction]:
    query = select(Transaction).options(*_transaction_options())

    if from_ is not None:
        query = query.where(Transaction.occurred_at >= from_)
    if to is not None:
        query = query.where(Transaction.occurred_at <= to)
    if category_id is not None:
        query = query.where(Transaction.category_id == category_id)
    if source is not None:
        query = query.where(Transaction.source == source)
    if status is not None:
        query = query.where(Transaction.status == status)
    if transaction_type is not None:
        query = query.where(Transaction.transaction_type == transaction_type)
    if relationship_category is not None:
        query = query.where(Transaction.relationship_category == relationship_category)
    if person_id is not None:
        query = query.where(Transaction.person_id == person_id)
    if merchant is not None:
        query = query.where(Transaction.merchant_name.ilike(f"%{merchant}%"))
    if min_amount is not None:
        query = query.where(Transaction.amount >= min_amount)
    if max_amount is not None:
        query = query.where(Transaction.amount <= max_amount)
    if q is not None:
        query = query.where(
            or_(
                Transaction.merchant_name.ilike(f"%{q}%"),
                Transaction.counterparty.ilike(f"%{q}%"),
                Transaction.description.ilike(f"%{q}%"),
                Transaction.subject.ilike(f"%{q}%"),
            )
        )

    query = query.order_by(Transaction.occurred_at.desc(), Transaction.id.desc())
    return list(db.scalars(query).all())


@router.post("", response_model=TransactionRead, status_code=status.HTTP_201_CREATED)
def create_transaction(
    payload: TransactionCreate,
    db: Session = Depends(get_db),
) -> Transaction:
    _validate_category(payload.category_id, db)
    financial_account = _validate_financial_account(payload.financial_account_id, db)
    _validate_investment_account(payload.investment_account_id, db)
    _validate_person(payload.person_id, db)
    _validate_receivable(payload.receivable_id, db)
    _validate_payable(payload.payable_id, db)
    transaction_amount = _create_internal_receivables(payload, payload.amount, db)
    transaction_amount = _create_internal_payables(payload, transaction_amount, db)
    splits = _adjust_splits_for_amount(payload.amount, transaction_amount, payload.splits)
    data = payload.model_dump(exclude={"splits", "internal_receivables", "internal_payables"})
    data["amount"] = transaction_amount
    data["signed_amount"] = _signed_amount(transaction_amount, payload.transaction_type)
    data = _normalize_money_fields(data, payload.amount, transaction_amount)
    _validate_account_currency(financial_account, data["currency"])
    data["destination_account_id"], data["destination_amount"], data["destination_currency"] = _resolve_internal_transfer(
        payload.transaction_type,
        payload.financial_account_id,
        data["currency"],
        transaction_amount,
        payload.destination_account_id,
        payload.destination_amount,
        db,
    )
    _validate_splits(transaction_amount, splits, db, data["currency"])
    transaction = Transaction(**data)
    for split in splits:
        transaction.splits.append(TransactionSplit(**split.model_dump()))
    db.add(transaction)
    db.flush()
    _sync_investment_movement(transaction, db)
    db.commit()
    db.refresh(transaction)
    return _get_transaction_or_404(transaction.id, db)


@router.get("/{transaction_id}", response_model=TransactionRead)
def get_transaction(transaction_id: int, db: Session = Depends(get_db)) -> Transaction:
    return _get_transaction_or_404(transaction_id, db)


@router.patch("/{transaction_id}", response_model=TransactionRead)
def update_transaction(
    transaction_id: int,
    payload: TransactionUpdate,
    db: Session = Depends(get_db),
) -> Transaction:
    transaction = _get_transaction_or_404(transaction_id, db)
    data = payload.model_dump(exclude_unset=True)

    if "category_id" in data:
        _validate_category(data["category_id"], db)
    if "financial_account_id" in data:
        _validate_financial_account(data["financial_account_id"], db)
    if "investment_account_id" in data:
        _validate_investment_account(data["investment_account_id"], db)
    if "person_id" in data:
        _validate_person(data["person_id"], db)
    if "receivable_id" in data:
        _validate_receivable(data["receivable_id"], db)
    if "payable_id" in data:
        _validate_payable(data["payable_id"], db)
    splits = data.pop("splits", None)
    _record_feedback(transaction, data, db)
    amount_was_updated = "amount" in data
    currency_was_updated = "currency" in data
    original_amount_was_updated = "original_amount" in data
    original_currency_was_updated = "original_currency" in data

    for key, value in data.items():
        setattr(transaction, key, value)

    if amount_was_updated and not original_amount_was_updated:
        transaction.original_amount = transaction.amount
    if currency_was_updated and not original_currency_was_updated:
        transaction.original_currency = transaction.currency

    transaction.signed_amount = _signed_amount(transaction.amount, transaction.transaction_type)
    money_data = {
        "amount": transaction.amount,
        "signed_amount": transaction.signed_amount,
        "currency": transaction.currency,
        "original_amount": transaction.original_amount,
        "original_currency": transaction.original_currency,
        "amount_clp": transaction.amount_clp,
        "exchange_rate": transaction.exchange_rate,
    }
    money_data = _normalize_money_fields(money_data, transaction.amount, transaction.amount)
    for key, value in money_data.items():
        setattr(transaction, key, value)
    account = db.get(FinancialAccount, transaction.financial_account_id) if transaction.financial_account_id else None
    _validate_account_currency(account, transaction.currency)
    (
        transaction.destination_account_id,
        transaction.destination_amount,
        transaction.destination_currency,
    ) = _resolve_internal_transfer(
        transaction.transaction_type,
        transaction.financial_account_id,
        transaction.currency,
        transaction.amount,
        transaction.destination_account_id,
        transaction.destination_amount,
        db,
    )
    _sync_investment_movement(transaction, db)
    if splits is not None:
        split_payloads = [TransactionSplitCreate.model_validate(split) for split in splits]
        _validate_splits(transaction.amount, split_payloads, db, transaction.currency)
        _replace_splits(transaction, split_payloads, db)

    db.add(transaction)
    db.commit()
    db.refresh(transaction)
    return _get_transaction_or_404(transaction.id, db)


@router.delete("/{transaction_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_transaction(transaction_id: int, db: Session = Depends(get_db)) -> Response:
    transaction = _get_transaction_or_404(transaction_id, db)
    _delete_investment_movement(transaction, db)
    db.delete(transaction)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{transaction_id}/splits", response_model=list[TransactionSplitRead])
def list_transaction_splits(transaction_id: int, db: Session = Depends(get_db)) -> list[TransactionSplit]:
    transaction = _get_transaction_or_404(transaction_id, db)
    return transaction.splits


@router.put("/{transaction_id}/splits", response_model=TransactionRead)
def replace_transaction_splits(
    transaction_id: int,
    payload: list[TransactionSplitCreate],
    db: Session = Depends(get_db),
) -> Transaction:
    transaction = _get_transaction_or_404(transaction_id, db)
    _validate_splits(transaction.amount, payload, db, transaction.currency)
    _replace_splits(transaction, payload, db)
    db.commit()
    db.refresh(transaction)
    return _get_transaction_or_404(transaction.id, db)
