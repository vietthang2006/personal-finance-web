from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator


class BudgetCategoryCreate(BaseModel):
    category_id: int
    limit_amount: Decimal = Field(gt=0, max_digits=18, decimal_places=2)
    warn_percent: int = Field(default=80, ge=1, le=100)


class BudgetCategoryUpdate(BaseModel):
    limit_amount: Decimal | None = Field(default=None, gt=0, max_digits=18, decimal_places=2)
    warn_percent: int | None = Field(default=None, ge=1, le=100)


class BudgetCategoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    budget_id: UUID
    category_id: int
    category_kind: str = "expense"
    limit_amount: Decimal
    warn_percent: int


class BudgetCategoryProgressRead(BaseModel):
    category_id: int
    category_name: str
    limit_amount: Decimal
    spent_amount: Decimal
    remaining_amount: Decimal
    percent_used: Decimal
    warn_percent: int
    is_warning: bool
    is_exceeded: bool


class BudgetCreate(BaseModel):
    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
    period_type: Literal["monthly", "quarterly", "yearly", "custom"]
    start_date: date
    end_date: date
    total_limit: Decimal = Field(gt=0, max_digits=18, decimal_places=2)
    categories: list[BudgetCategoryCreate] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_dates(self) -> "BudgetCreate":
        if self.end_date < self.start_date:
            raise ValueError("end_date must not be before start_date")
        return self


class BudgetUpdate(BaseModel):
    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)] | None = None
    period_type: Literal["monthly", "quarterly", "yearly", "custom"] | None = None
    start_date: date | None = None
    end_date: date | None = None
    total_limit: Decimal | None = Field(default=None, gt=0, max_digits=18, decimal_places=2)
    status: Literal["active", "archived"] | None = None

    @model_validator(mode="after")
    def validate_dates(self) -> "BudgetUpdate":
        if self.start_date is not None and self.end_date is not None:
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
    updated_at: datetime


class BudgetDetailRead(BudgetRead):
    categories: list[BudgetCategoryRead] = Field(default_factory=list)


class BudgetProgressRead(BaseModel):
    budget_id: UUID
    name: str
    period_type: str
    start_date: date
    end_date: date
    total_limit: Decimal
    total_spent: Decimal
    total_remaining: Decimal
    overall_percent_used: Decimal
    categories: list[BudgetCategoryProgressRead] = Field(default_factory=list)


class BudgetAlertEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    budget_category_id: UUID
    level: str
    spent_amount: Decimal
    percent_used: Decimal
    triggered_at: datetime
    notification_id: UUID | None = None
