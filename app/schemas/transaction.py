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
    tag_ids: list[int] = Field(default_factory=list)
    dedup_hash: str | None = Field(default=None, min_length=64, max_length=64, pattern=r"^[a-fA-F0-9]{64}$")

    @model_validator(mode="after")
    def validate_rules(self) -> "TransactionCreate":
        if self.subcategory_id is not None and self.category_id is None:
            raise ValueError("category_id must be provided when subcategory_id is specified")
        if self.transaction_date > date.today():
            raise ValueError("transaction_date cannot be in the future")
        return self


class TransactionUpdate(BaseModel):
    account_id: UUID | None = None
    kind: Literal["income", "expense"] | None = None
    category_id: int | None = Field(default=None, gt=0)
    subcategory_id: int | None = Field(default=None, gt=0)
    amount: Money | None = None
    transaction_date: date | None = None
    description: Annotated[str | None, StringConstraints(strip_whitespace=True, max_length=2000)] = None
    merchant: Annotated[str | None, StringConstraints(strip_whitespace=True, max_length=150)] = None
    tag_ids: list[int] | None = None

    @model_validator(mode="after")
    def validate_patch_fields(self) -> "TransactionUpdate":
        supplied = self.model_fields_set
        if not supplied:
            raise ValueError("At least one field must be provided")
        for field_name in ("kind", "amount", "transaction_date"):
            if field_name in supplied and getattr(self, field_name) is None:
                raise ValueError(f"{field_name} cannot be null")
        if self.transaction_date is not None and self.transaction_date > date.today():
            raise ValueError("transaction_date cannot be in the future")
        if self.subcategory_id is not None and self.category_id is None and "category_id" in supplied:
            raise ValueError("category_id must be provided when subcategory_id is specified")
        return self


class TransactionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    account_id: UUID
    user_id: UUID | None = None
    kind: str
    category_id: int | None = None
    subcategory_id: int | None = None
    amount: Decimal
    transaction_date: date
    description: str | None = None
    merchant: str | None = None
    source: str = "manual"
    created_at: datetime
    updated_at: datetime | None = None
