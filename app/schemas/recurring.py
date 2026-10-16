from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator


class RecurringCreate(BaseModel):
    account_id: UUID
    kind: Literal["income", "expense"]
    category_id: int | None = Field(default=None, gt=0)
    subcategory_id: int | None = Field(default=None, gt=0)
    amount: Decimal = Field(gt=0, max_digits=18, decimal_places=2)
    description: Annotated[str | None, StringConstraints(strip_whitespace=True, max_length=2000)] = None
    frequency: Literal["daily", "weekly", "monthly", "yearly"]
    interval: int = Field(default=1, ge=1, le=365)
    start_date: date
    end_date: date | None = None

    @model_validator(mode="after")
    def validate_dates_and_category(self) -> "RecurringCreate":
        if self.end_date is not None and self.end_date < self.start_date:
            raise ValueError("end_date must not be before start_date")
        if (self.category_id is None) != (self.subcategory_id is None):
            raise ValueError("category_id and subcategory_id must be provided together")
        return self


class RecurringRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    account_id: UUID
    kind: str
    category_id: int | None
    subcategory_id: int | None
    amount: Decimal
    description: str | None
    frequency: str
    interval: int
    start_date: date
    next_run_at: date
    end_date: date | None
    last_generated_date: date | None
    status: str
    created_at: datetime


class RecurringStatusUpdate(BaseModel):
    status: Literal["active", "paused"]
