from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from app.schemas.transaction import Money


class TransferCreate(BaseModel):
    from_account_id: UUID
    to_account_id: UUID
    amount: Money
    to_amount: Money | None = None
    exchange_rate: Annotated[Decimal, Field(gt=0, max_digits=18, decimal_places=8)] | None = None
    transaction_date: date
    purpose: Literal["internal", "credit_card_payment"] = "internal"
    description: Annotated[str | None, StringConstraints(strip_whitespace=True, max_length=2000)] = None
    idempotency_key: Annotated[str | None, StringConstraints(strip_whitespace=True, max_length=100)] = None

    @model_validator(mode="after")
    def validate_distinct_accounts(self) -> "TransferCreate":
        if self.from_account_id == self.to_account_id:
            raise ValueError("from_account_id and to_account_id must be distinct")
        return self


class TransferRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    from_account_id: UUID
    to_account_id: UUID
    amount: Decimal
    to_amount: Decimal
    exchange_rate: Decimal
    transaction_date: date
    purpose: str
    description: str | None
    idempotency_key: str | None
    created_at: datetime
