from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.api.deps import get_db
from backend.app.models import InvestmentAccount, InvestmentMovement, Transaction
from backend.app.schemas import (
    InvestmentAccountCreate,
    InvestmentAccountRead,
    InvestmentAccountUpdate,
    InvestmentMovementCreate,
    InvestmentMovementRead,
)


router = APIRouter(prefix="/investment-accounts", tags=["investment-accounts"])


def _get_account_or_404(account_id: int, db: Session) -> InvestmentAccount:
    account = db.get(InvestmentAccount, account_id)
    if account is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Investment account not found")
    return account


def _validate_transaction(transaction_id: int | None, db: Session) -> None:
    if transaction_id is not None and db.get(Transaction, transaction_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found")


@router.get("", response_model=list[InvestmentAccountRead])
def list_investment_accounts(active_only: bool = True, db: Session = Depends(get_db)) -> list[InvestmentAccount]:
    query = select(InvestmentAccount).order_by(InvestmentAccount.name)
    if active_only:
        query = query.where(InvestmentAccount.is_active.is_(True))
    return list(db.scalars(query).all())


@router.post("", response_model=InvestmentAccountRead, status_code=status.HTTP_201_CREATED)
def create_investment_account(payload: InvestmentAccountCreate, db: Session = Depends(get_db)) -> InvestmentAccount:
    account = InvestmentAccount(**payload.model_dump())
    db.add(account)
    db.commit()
    db.refresh(account)
    return account


@router.get("/{account_id}", response_model=InvestmentAccountRead)
def get_investment_account(account_id: int, db: Session = Depends(get_db)) -> InvestmentAccount:
    return _get_account_or_404(account_id, db)


@router.patch("/{account_id}", response_model=InvestmentAccountRead)
def update_investment_account(
    account_id: int,
    payload: InvestmentAccountUpdate,
    db: Session = Depends(get_db),
) -> InvestmentAccount:
    account = _get_account_or_404(account_id, db)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(account, key, value)
    db.add(account)
    db.commit()
    db.refresh(account)
    return account


@router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_investment_account(account_id: int, db: Session = Depends(get_db)) -> Response:
    account = _get_account_or_404(account_id, db)
    account.is_active = False
    db.add(account)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{account_id}/movements", response_model=list[InvestmentMovementRead])
def list_movements(account_id: int, db: Session = Depends(get_db)) -> list[InvestmentMovement]:
    _get_account_or_404(account_id, db)
    query = (
        select(InvestmentMovement)
        .where(InvestmentMovement.investment_account_id == account_id)
        .order_by(InvestmentMovement.occurred_at.desc(), InvestmentMovement.id.desc())
    )
    return list(db.scalars(query).all())


@router.post("/{account_id}/movements", response_model=InvestmentMovementRead, status_code=status.HTTP_201_CREATED)
def create_movement(
    account_id: int,
    payload: InvestmentMovementCreate,
    db: Session = Depends(get_db),
) -> InvestmentMovement:
    account = _get_account_or_404(account_id, db)
    _validate_transaction(payload.transaction_id, db)
    movement = InvestmentMovement(investment_account_id=account.id, **payload.model_dump())
    if payload.movement_type == "investment":
        account.current_value += payload.amount
    elif payload.movement_type == "disinvestment":
        account.current_value -= payload.amount
    db.add(account)
    db.add(movement)
    db.commit()
    db.refresh(movement)
    return movement
