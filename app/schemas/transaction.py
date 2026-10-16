from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator


Money = Annotated[Decimal, Field(gt=0, max_digits=18, decimal_places=2)]


class TransactionCreate(BaseModel):
    account_id: UUID
    kind: Literal["income", "expense"]
    category_id: int | None = Field(default=None, gt=0)
    subcategory_id: int | None = Field(default=None, gt=0)
    amount: Money
    transaction_date: date
    description: Annotated[str | None, StringConstraints(strip_whitespace=True, max_length=2000)] = None
    merchant: Annotated[str | None, StringConstraints(strip_whitespace=True, max_length=150)] = None
    dedup_hash: str | None = Field(default=None, min_length=64, max_length=64, pattern=r"^[a-fA-F0-9]{64}$")

    @model_validator(mode="after")
    def validate_category_pair(self) -> "TransactionCreate":
        if (self.category_id is None) != (self.subcategory_id is None):
            raise ValueError("category_id and subcategory_id must be provided together")
        return self


class TransactionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    account_id: UUID
    kind: str
    category_id: int | None
    subcategory_id: int | None
    amount: Decimal
    transaction_date: date
    description: str | None
    merchant: str | None
    source: str
    created_at: datetime