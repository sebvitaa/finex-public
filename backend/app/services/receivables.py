from datetime import datetime, timezone
from decimal import Decimal
from typing import Protocol, Sequence

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from backend.app.models import Receivable, ReceivablePayment, Transaction


class ReceivablePaymentAllocation(Protocol):
    receivable_id: int
    amount: Decimal
    force_close_with_adjustment: bool
    notes: str | None


def refresh_receivable_status(receivable: Receivable) -> None:
    if receivable.remaining_amount <= Decimal("0"):
        receivable.remaining_amount = Decimal("0")
        receivable.status = "paid"
        return
    if receivable.remaining_amount < receivable.original_amount:
        receivable.status = "partially_paid"
        return
    if receivable.due_at and receivable.due_at < datetime.now(timezone.utc):
        receivable.status = "overdue"
        return
    receivable.status = "pending_payment"


def apply_receivable_payments(
    db: Session,
    allocations: Sequence[ReceivablePaymentAllocation],
    *,
    paid_at: datetime,
    transaction_id: int | None = None,
    total_cap: Decimal | None = None,
    default_notes: str | None = None,
) -> list[ReceivablePayment]:
    if not allocations:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="At least one receivable payment is required")

    total = sum((allocation.amount for allocation in allocations), Decimal("0"))
    if total <= Decimal("0"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Payment amount must be greater than zero")

    if total_cap is not None and total > total_cap:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Payment allocations exceed received amount")

    if transaction_id is not None:
        transaction = db.get(Transaction, transaction_id)
        if transaction is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found")
        if total > transaction.amount:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Payment allocations exceed transaction amount")

    totals_by_receivable: dict[int, Decimal] = {}
    for allocation in allocations:
        totals_by_receivable[allocation.receivable_id] = totals_by_receivable.get(allocation.receivable_id, Decimal("0")) + allocation.amount

    receivables: dict[int, Receivable] = {}
    for receivable_id, amount in totals_by_receivable.items():
        receivable = db.get(Receivable, receivable_id)
        if receivable is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Receivable not found")
        if amount > receivable.remaining_amount:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Payment exceeds remaining amount")
        receivables[receivable_id] = receivable

    payments: list[ReceivablePayment] = []
    for allocation in allocations:
        receivable = receivables[allocation.receivable_id]
        payment = ReceivablePayment(
            receivable_id=receivable.id,
            transaction_id=transaction_id,
            paid_at=paid_at,
            amount=allocation.amount,
            notes=allocation.notes or default_notes,
        )
        receivable.remaining_amount -= allocation.amount
        if getattr(allocation, "force_close_with_adjustment", False):
            receivable.remaining_amount = Decimal("0")
        refresh_receivable_status(receivable)
        db.add(payment)
        db.add(receivable)
        payments.append(payment)

    return payments
