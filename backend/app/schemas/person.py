from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class PersonBase(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    alias: str | None = Field(default=None, max_length=80)
    email: str | None = Field(default=None, max_length=240)
    phone: str | None = Field(default=None, max_length=80)
    notes: str | None = None


class PersonCreate(PersonBase):
    pass


class PersonUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    alias: str | None = Field(default=None, max_length=80)
    email: str | None = Field(default=None, max_length=240)
    phone: str | None = Field(default=None, max_length=80)
    notes: str | None = None


class PersonRead(PersonBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
