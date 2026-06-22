from datetime import datetime, timezone
from decimal import Decimal
from typing import Protocol, Sequence

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from backend.app.models import Payable, PayablePayment, Transaction


class PayablePaymentAllocation(Protocol):
    payable_id: int
    amount: Decimal
    force_close_with_adjustment: bool
    notes: str | None


def refresh_payable_status(payable: Payable) -> None:
    if payable.remaining_amount <= Decimal("0"):
        payable.remaining_amount = Decimal("0")
        payable.status = "paid"
        return
    if payable.remaining_amount < payable.original_amount:
        payable.status = "partially_paid"
        return
    if payable.due_at and payable.due_at < datetime.now(timezone.utc):
        payable.status = "overdue"
        return
    payable.status = "pending_payment"


def apply_payable_payments(
    db: Session,
    allocations: Sequence[PayablePaymentAllocation],
    *,
    paid_at: datetime,
    transaction_id: int | None = None,
    total_cap: Decimal | None = None,
    default_notes: str | None = None,
) -> list[PayablePayment]:
    if not allocations:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="At least one payable payment is required")

    total = sum((allocation.amount for allocation in allocations), Decimal("0"))
    if total <= Decimal("0"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Payment amount must be greater than zero")

    if total_cap is not None and total > total_cap:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Payment allocations exceed transferred amount")

    if transaction_id is not None:
        transaction = db.get(Transaction, transaction_id)
        if transaction is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found")
        if total > transaction.amount:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Payment allocations exceed transaction amount")

    totals_by_payable: dict[int, Decimal] = {}
    for allocation in allocations:
        totals_by_payable[allocation.payable_id] = totals_by_payable.get(allocation.payable_id, Decimal("0")) + allocation.amount

    payables: dict[int, Payable] = {}
    for payable_id, amount in totals_by_payable.items():
        payable = db.get(Payable, payable_id)
        if payable is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payable not found")
        if amount > payable.remaining_amount:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Payment exceeds remaining amount")
        payables[payable_id] = payable

    payments: list[PayablePayment] = []
    for allocation in allocations:
        payable = payables[allocation.payable_id]
        payment = PayablePayment(
            payable_id=payable.id,
            transaction_id=transaction_id,
            paid_at=paid_at,
            amount=allocation.amount,
            notes=allocation.notes or default_notes,
        )
        payable.remaining_amount -= allocation.amount
        if getattr(allocation, "force_close_with_adjustment", False):
            payable.remaining_amount = Decimal("0")
        refresh_payable_status(payable)
        db.add(payment)
        db.add(payable)
        payments.append(payment)

    return payments
