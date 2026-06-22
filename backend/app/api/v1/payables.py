from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from backend.app.api.deps import get_db
from backend.app.models import Payable, PayablePayment, Person
from backend.app.schemas import (
    PayableCreate,
    PayablePaymentAllocationCreate,
    PayablePaymentBatchCreate,
    PayablePaymentCreate,
    PayablePaymentRead,
    PayableRead,
    PayableUpdate,
)
from backend.app.services.payables import apply_payable_payments, refresh_payable_status


router = APIRouter(prefix="/payables", tags=["payables"])


def _get_payable_or_404(payable_id: int, db: Session) -> Payable:
    query = (
        select(Payable)
        .options(selectinload(Payable.person), selectinload(Payable.payments))
        .where(Payable.id == payable_id)
    )
    payable = db.scalar(query)
    if payable is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payable not found")
    return payable


def _validate_person(person_id: int, db: Session) -> None:
    if db.get(Person, person_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Person not found")


@router.get("", response_model=list[PayableRead])
def list_payables(
    person_id: int | None = None,
    status_: Annotated[str | None, Query(alias="status")] = None,
    from_: Annotated[datetime | None, Query(alias="from")] = None,
    to: datetime | None = None,
    q: str | None = None,
    db: Session = Depends(get_db),
) -> list[Payable]:
    query = select(Payable).options(selectinload(Payable.person), selectinload(Payable.payments))
    if person_id is not None:
        query = query.where(Payable.person_id == person_id)
    if status_ is not None:
        query = query.where(Payable.status == status_)
    if from_ is not None:
        query = query.where(Payable.issued_at >= from_)
    if to is not None:
        query = query.where(Payable.issued_at <= to)
    if q is not None:
        query = query.where(or_(Payable.title.ilike(f"%{q}%"), Payable.notes.ilike(f"%{q}%")))
    query = query.order_by(Payable.issued_at.desc(), Payable.id.desc())
    return list(db.scalars(query).all())


@router.post("", response_model=PayableRead, status_code=status.HTTP_201_CREATED)
def create_payable(payload: PayableCreate, db: Session = Depends(get_db)) -> Payable:
    _validate_person(payload.person_id, db)
    payable = Payable(**payload.model_dump())
    refresh_payable_status(payable)
    db.add(payable)
    db.commit()
    return _get_payable_or_404(payable.id, db)


@router.post("/payments", response_model=list[PayablePaymentRead], status_code=status.HTTP_201_CREATED)
def create_payments(
    payload: PayablePaymentBatchCreate,
    db: Session = Depends(get_db),
) -> list[PayablePayment]:
    payments = apply_payable_payments(
        db,
        payload.payments,
        paid_at=payload.paid_at,
        transaction_id=payload.transaction_id,
        default_notes=payload.notes or "Pago asignado desde UI",
    )
    db.commit()
    for payment in payments:
        db.refresh(payment)
    return payments


@router.get("/{payable_id}", response_model=PayableRead)
def get_payable(payable_id: int, db: Session = Depends(get_db)) -> Payable:
    return _get_payable_or_404(payable_id, db)


@router.patch("/{payable_id}", response_model=PayableRead)
def update_payable(
    payable_id: int,
    payload: PayableUpdate,
    db: Session = Depends(get_db),
) -> Payable:
    payable = _get_payable_or_404(payable_id, db)
    data = payload.model_dump(exclude_unset=True)
    if "person_id" in data:
        _validate_person(data["person_id"], db)
    for key, value in data.items():
        setattr(payable, key, value)
    if "status" not in data:
        refresh_payable_status(payable)
    db.add(payable)
    db.commit()
    return _get_payable_or_404(payable.id, db)


@router.delete("/{payable_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_payable(payable_id: int, db: Session = Depends(get_db)) -> Response:
    payable = _get_payable_or_404(payable_id, db)
    db.delete(payable)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{payable_id}/payments", response_model=PayablePaymentRead, status_code=status.HTTP_201_CREATED)
def create_payment(
    payable_id: int,
    payload: PayablePaymentCreate,
    db: Session = Depends(get_db),
) -> PayablePayment:
    _get_payable_or_404(payable_id, db)
    payments = apply_payable_payments(
        db,
        [PayablePaymentAllocationCreate(payable_id=payable_id, amount=payload.amount, notes=payload.notes)],
        paid_at=payload.paid_at,
        transaction_id=payload.transaction_id,
        default_notes="Pago registrado desde UI",
    )
    db.commit()
    payment = payments[0]
    db.refresh(payment)
    return payment
