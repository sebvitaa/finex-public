from datetime import datetime, timezone
from decimal import Decimal
from hashlib import sha256

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.api.deps import get_db
from backend.app.models import CreditCardStatement, FinancialAccount, FinancialAccountSnapshot, Transaction
from backend.app.schemas import (
    CreditCardStatementCreate,
    CreditCardStatementRead,
    FinancialAccountCreate,
    FinancialAccountRead,
    FinancialAccountSnapshotCreate,
    FinancialAccountSnapshotRead,
    FinancialAccountUpdate,
)


router = APIRouter(prefix="/financial-accounts", tags=["financial-accounts"])
CARD_ART_VARIANTS = ("white", "red", "green", "black", "blue")


def _as_comparable_datetime(value: datetime | None) -> datetime | None:
    if value is None or value.tzinfo is None:
        return value
    return value.astimezone(timezone.utc).replace(tzinfo=None)


def _get_account_or_404(account_id: int, db: Session) -> FinancialAccount:
    account = db.get(FinancialAccount, account_id)
    if account is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Financial account not found")
    return account


def _card_variant(seed: str) -> str:
    index = int(sha256(seed.encode("utf-8")).hexdigest(), 16) % len(CARD_ART_VARIANTS)
    return CARD_ART_VARIANTS[index]


def _prepare_account_data(data: dict, existing: FinancialAccount | None = None) -> dict:
    currency = data.get("currency") or (existing.currency if existing else "CLP")
    account_type = data.get("account_type") or (existing.account_type if existing else "unknown")
    if data.get("credit_limit_currency") is None and data.get("credit_limit_amount") is not None:
        data["credit_limit_currency"] = currency
    if data.get("statement_currency") is None and data.get("statement_amount") is not None:
        data["statement_currency"] = currency
    if account_type == "credit_card":
        data.setdefault("credit_limit_currency", currency)
        data.setdefault("statement_currency", currency)
        if not data.get("card_art_variant") and (existing is None or not existing.card_art_variant):
            seed_name = data.get("name") or (existing.name if existing else "")
            seed_last_four = data.get("last_four") or (existing.last_four if existing else "")
            seed = f"{seed_name}:{seed_last_four}:{currency}"
            data["card_art_variant"] = _card_variant(seed)
        if not data.get("visual_group") and (existing is None or not existing.visual_group):
            last_four = data.get("last_four") or (existing.last_four if existing else None)
            data["visual_group"] = f"Credito {last_four}" if last_four else data.get("name")
    return data


@router.get("", response_model=list[FinancialAccountRead])
def list_financial_accounts(active_only: bool = True, db: Session = Depends(get_db)) -> list[FinancialAccount]:
    query = select(FinancialAccount).order_by(FinancialAccount.name)
    if active_only:
        query = query.where(FinancialAccount.is_active.is_(True))
    return list(db.scalars(query).all())


@router.post("", response_model=FinancialAccountRead, status_code=status.HTTP_201_CREATED)
def create_financial_account(payload: FinancialAccountCreate, db: Session = Depends(get_db)) -> FinancialAccount:
    account = FinancialAccount(**_prepare_account_data(payload.model_dump()))
    db.add(account)
    db.commit()
    db.refresh(account)
    return account


@router.get("/{account_id}", response_model=FinancialAccountRead)
def get_financial_account(account_id: int, db: Session = Depends(get_db)) -> FinancialAccount:
    return _get_account_or_404(account_id, db)


@router.patch("/{account_id}", response_model=FinancialAccountRead)
def update_financial_account(
    account_id: int,
    payload: FinancialAccountUpdate,
    db: Session = Depends(get_db),
) -> FinancialAccount:
    account = _get_account_or_404(account_id, db)
    data = _prepare_account_data(payload.model_dump(exclude_unset=True), existing=account)
    for key, value in data.items():
        setattr(account, key, value)
    db.add(account)
    db.commit()
    db.refresh(account)
    return account


@router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_financial_account(account_id: int, db: Session = Depends(get_db)) -> Response:
    account = _get_account_or_404(account_id, db)
    account.is_active = False
    db.add(account)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{account_id}/snapshots", response_model=list[FinancialAccountSnapshotRead])
def list_snapshots(account_id: int, db: Session = Depends(get_db)) -> list[FinancialAccountSnapshot]:
    _get_account_or_404(account_id, db)
    query = (
        select(FinancialAccountSnapshot)
        .where(FinancialAccountSnapshot.financial_account_id == account_id)
        .order_by(FinancialAccountSnapshot.captured_at.desc(), FinancialAccountSnapshot.id.desc())
    )
    return list(db.scalars(query).all())


@router.post("/{account_id}/snapshots", response_model=FinancialAccountSnapshotRead, status_code=status.HTTP_201_CREATED)
def create_snapshot(
    account_id: int,
    payload: FinancialAccountSnapshotCreate,
    db: Session = Depends(get_db),
) -> FinancialAccountSnapshot:
    account = _get_account_or_404(account_id, db)
    data = payload.model_dump()
    if "currency" not in payload.model_fields_set:
        data["currency"] = account.currency
    snapshot = FinancialAccountSnapshot(financial_account_id=account_id, **data)
    db.add(snapshot)
    db.commit()
    db.refresh(snapshot)
    return snapshot


@router.get("/{account_id}/statements", response_model=list[CreditCardStatementRead])
def list_credit_card_statements(account_id: int, db: Session = Depends(get_db)) -> list[CreditCardStatement]:
    _get_account_or_404(account_id, db)
    query = (
        select(CreditCardStatement)
        .where(CreditCardStatement.financial_account_id == account_id)
        .order_by(CreditCardStatement.period_end.desc(), CreditCardStatement.id.desc())
    )
    return list(db.scalars(query).all())


@router.post("/{account_id}/statements", response_model=CreditCardStatementRead, status_code=status.HTTP_201_CREATED)
def create_credit_card_statement(
    account_id: int,
    payload: CreditCardStatementCreate,
    db: Session = Depends(get_db),
) -> CreditCardStatement:
    account = _get_account_or_404(account_id, db)
    if account.account_type != "credit_card":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Statements are only available for credit cards")
    statement = CreditCardStatement(financial_account_id=account_id, **payload.model_dump())
    db.add(statement)
    db.commit()
    db.refresh(statement)
    return statement


@router.get("/{account_id}/balance")
def account_balance(account_id: int, at: datetime | None = None, db: Session = Depends(get_db)) -> dict[str, str | int]:
    account = _get_account_or_404(account_id, db)
    comparable_at = _as_comparable_datetime(at)
    snapshots = list(
        db.scalars(
            select(FinancialAccountSnapshot)
            .where(FinancialAccountSnapshot.financial_account_id == account.id)
            .order_by(FinancialAccountSnapshot.captured_at.desc(), FinancialAccountSnapshot.id.desc())
        )
    )
    if comparable_at is not None:
        snapshots = [
            snapshot
            for snapshot in snapshots
            if (_as_comparable_datetime(snapshot.captured_at) or datetime.min) <= comparable_at
        ]
    snapshot = snapshots[0] if snapshots else None
    base = snapshot.balance if snapshot else account.opening_balance
    since = _as_comparable_datetime(snapshot.captured_at) if snapshot else None

    transactions = db.scalars(
        select(Transaction).where(
            Transaction.financial_account_id == account.id,
            Transaction.status.notin_(["ignored", "duplicate"]),
        )
    )
    movement_total = Decimal("0")
    for transaction in transactions:
        occurred_at = _as_comparable_datetime(transaction.occurred_at)
        if comparable_at is not None and (occurred_at is None or occurred_at > comparable_at):
            continue
        if since is not None and (occurred_at is None or occurred_at <= since):
            continue
        if (transaction.currency or account.currency) != account.currency:
            continue
        movement_total += transaction.signed_amount or Decimal("0")
    quantizer = Decimal("1") if account.currency == "CLP" else Decimal("0.01")
    balance = (base + movement_total).quantize(quantizer)
    result: dict[str, str | int] = {"account_id": account.id, "balance": str(balance), "currency": account.currency}
    if account.account_type == "credit_card":
        used_credit = abs(balance) if balance < Decimal("0") else Decimal("0")
        if account.credit_limit_amount is not None:
            available_credit = max(account.credit_limit_amount - used_credit, Decimal("0"))
            result["used_credit_amount"] = str(used_credit.quantize(quantizer))
            result["available_credit_amount"] = str(available_credit.quantize(quantizer))
    return result
