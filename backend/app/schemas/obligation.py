from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


ResultingDirection = Literal["receivable", "payable", "settled"]


class ObligationOffsetCreate(BaseModel):
    person_id: int
    receivable_id: int
    payable_id: int
    offset_at: datetime
    amount: Decimal | None = Field(default=None, gt=0, max_digits=12, decimal_places=2)
    notes: str | None = None


class ObligationOffsetRead(BaseModel):
    id: int
    person_id: int
    receivable_id: int | None = None
    payable_id: int | None = None
    offset_at: datetime
    amount: Decimal
    resulting_direction: ResultingDirection
    resulting_amount: Decimal
    notes: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
