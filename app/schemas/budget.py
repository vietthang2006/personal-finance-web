from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator


class BudgetCreate(BaseModel):
    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
    period_type: Literal["monthly", "weekly", "custom"]
    start_date: date
    end_date: date
    total_limit: Decimal = Field(gt=0, max_digits=18, decimal_places=2)

    @model_validator(mode="after")
    def validate_dates(self) -> "BudgetCreate":
        if self.end_date < self.start_date:
            raise ValueError("end_date must not be before start_date")
        return self


class BudgetRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    period_type: str
    start_date: date
    end_date: date
    total_limit: Decimal
    status: str
    created_at: datetime