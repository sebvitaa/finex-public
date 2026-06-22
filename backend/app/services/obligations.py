from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from backend.app.models import ObligationOffset, Payable, Receivable
from backend.app.schemas.obligation import ObligationOffsetCreate
from backend.app.services.payables import refresh_payable_status
from backend.app.services.receivables import refresh_receivable_status


def offset_receivable_payable(db: Session, payload: ObligationOffsetCreate) -> ObligationOffset:
    receivable = db.get(Receivable, payload.receivable_id)
    payable = db.get(Payable, payload.payable_id)
    if receivable is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Receivable not found")
    if payable is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payable not found")
    if receivable.person_id != payload.person_id or payable.person_id != payload.person_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Obligations must belong to the same person")
    if receivable.remaining_amount <= Decimal("0") or payable.remaining_amount <= Decimal("0"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only open obligations can be offset")

    max_offset = min(receivable.remaining_amount, payable.remaining_amount)
    amount = payload.amount or max_offset
    if amount > max_offset:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Offset exceeds available balance")

    receivable.remaining_amount -= amount
    payable.remaining_amount -= amount
    refresh_receivable_status(receivable)
    refresh_payable_status(payable)

    if receivable.remaining_amount > Decimal("0"):
        resulting_direction = "receivable"
        resulting_amount = receivable.remaining_amount
    elif payable.remaining_amount > Decimal("0"):
        resulting_direction = "payable"
        resulting_amount = payable.remaining_amount
    else:
        resulting_direction = "settled"
        resulting_amount = Decimal("0")

    offset = ObligationOffset(
        person_id=payload.person_id,
        receivable_id=receivable.id,
        payable_id=payable.id,
        offset_at=payload.offset_at,
        amount=amount,
        resulting_direction=resulting_direction,
        resulting_amount=resulting_amount,
        notes=payload.notes,
    )
    db.add(receivable)
    db.add(payable)
    db.add(offset)
    return offset
