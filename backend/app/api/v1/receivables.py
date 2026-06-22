from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from backend.app.api.deps import get_db
from backend.app.models import Person, Receivable, ReceivablePayment
from backend.app.schemas import (
    ObligationOffsetCreate,
    ObligationOffsetRead,
    ReceivableCreate,
    ReceivablePaymentAllocationCreate,
    ReceivablePaymentBatchCreate,
    ReceivablePaymentCreate,
    ReceivablePaymentRead,
    ReceivableRead,
    ReceivableUpdate,
)
from backend.app.services.obligations import offset_receivable_payable
from backend.app.services.receivables import apply_receivable_payments, refresh_receivable_status


router = APIRouter(prefix="/receivables", tags=["receivables"])


def _get_receivable_or_404(receivable_id: int, db: Session) -> Receivable:
    query = (
        select(Receivable)
        .options(selectinload(Receivable.person), selectinload(Receivable.payments))
        .where(Receivable.id == receivable_id)
    )
    receivable = db.scalar(query)
    if receivable is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Receivable not found")
    return receivable


def _validate_person(person_id: int, db: Session) -> None:
    if db.get(Person, person_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Person not found")


@router.get("", response_model=list[ReceivableRead])
def list_receivables(
    person_id: int | None = None,
    status_: Annotated[str | None, Query(alias="status")] = None,
    from_: Annotated[datetime | None, Query(alias="from")] = None,
    to: datetime | None = None,
    q: str | None = None,
    db: Session = Depends(get_db),
) -> list[Receivable]:
    query = select(Receivable).options(selectinload(Receivable.person), selectinload(Receivable.payments))
    if person_id is not None:
        query = query.where(Receivable.person_id == person_id)
    if status_ is not None:
        query = query.where(Receivable.status == status_)
    if from_ is not None:
        query = query.where(Receivable.issued_at >= from_)
    if to is not None:
        query = query.where(Receivable.issued_at <= to)
    if q is not None:
        query = query.where(
            or_(
                Receivable.title.ilike(f"%{q}%"),
                Receivable.notes.ilike(f"%{q}%"),
            )
        )
    query = query.order_by(Receivable.issued_at.desc(), Receivable.id.desc())
    return list(db.scalars(query).all())


@router.post("", response_model=ReceivableRead, status_code=status.HTTP_201_CREATED)
def create_receivable(payload: ReceivableCreate, db: Session = Depends(get_db)) -> Receivable:
    _validate_person(payload.person_id, db)
    receivable = Receivable(**payload.model_dump())
    refresh_receivable_status(receivable)
    db.add(receivable)
    db.commit()
    return _get_receivable_or_404(receivable.id, db)


@router.post("/payments", response_model=list[ReceivablePaymentRead], status_code=status.HTTP_201_CREATED)
def create_payments(
    payload: ReceivablePaymentBatchCreate,
    db: Session = Depends(get_db),
) -> list[ReceivablePayment]:
    payments = apply_receivable_payments(
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


@router.post("/offsets", response_model=ObligationOffsetRead, status_code=status.HTTP_201_CREATED)
def create_obligation_offset(
    payload: ObligationOffsetCreate,
    db: Session = Depends(get_db),
):
    offset = offset_receivable_payable(db, payload)
    db.commit()
    db.refresh(offset)
    return offset


@router.get("/{receivable_id}", response_model=ReceivableRead)
def get_receivable(receivable_id: int, db: Session = Depends(get_db)) -> Receivable:
    return _get_receivable_or_404(receivable_id, db)


@router.patch("/{receivable_id}", response_model=ReceivableRead)
def update_receivable(
    receivable_id: int,
    payload: ReceivableUpdate,
    db: Session = Depends(get_db),
) -> Receivable:
    receivable = _get_receivable_or_404(receivable_id, db)
    data = payload.model_dump(exclude_unset=True)
    if "person_id" in data:
        _validate_person(data["person_id"], db)
    for key, value in data.items():
        setattr(receivable, key, value)
    if "status" not in data:
        refresh_receivable_status(receivable)
    db.add(receivable)
    db.commit()
    return _get_receivable_or_404(receivable.id, db)


@router.delete("/{receivable_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_receivable(receivable_id: int, db: Session = Depends(get_db)) -> Response:
    receivable = _get_receivable_or_404(receivable_id, db)
    db.delete(receivable)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{receivable_id}/payments", response_model=ReceivablePaymentRead, status_code=status.HTTP_201_CREATED)
def create_payment(
    receivable_id: int,
    payload: ReceivablePaymentCreate,
    db: Session = Depends(get_db),
) -> ReceivablePayment:
    _get_receivable_or_404(receivable_id, db)
    payments = apply_receivable_payments(
        db,
        [ReceivablePaymentAllocationCreate(receivable_id=receivable_id, amount=payload.amount, notes=payload.notes)],
        paid_at=payload.paid_at,
        transaction_id=payload.transaction_id,
        default_notes="Pago registrado desde UI",
    )
    db.commit()
    payment = payments[0]
    db.refresh(payment)
    return payment
