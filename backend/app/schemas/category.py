from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


CategoryKind = Literal["expense", "income", "both"]


class CategoryBase(BaseModel):
    parent_id: int | None = None
    name: str = Field(min_length=2, max_length=80)
    color: str = Field(default="#71717A", pattern=r"^#[0-9A-Fa-f]{6}$")
    icon: str = Field(default="circle", min_length=1, max_length=40)
    kind: CategoryKind = "expense"
    sort_order: int = Field(default=0, ge=0)


class CategoryCreate(CategoryBase):
    pass


class CategoryUpdate(BaseModel):
    parent_id: int | None = None
    name: str | None = Field(default=None, min_length=2, max_length=80)
    color: str | None = Field(default=None, pattern=r"^#[0-9A-Fa-f]{6}$")
    icon: str | None = Field(default=None, min_length=1, max_length=40)
    kind: CategoryKind | None = None
    sort_order: int | None = Field(default=None, ge=0)


class CategoryRead(CategoryBase):
    id: int
    is_system: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
