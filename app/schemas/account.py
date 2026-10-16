from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator, model_validator
from typing import Annotated, Literal


Money = Annotated[Decimal, Field(max_digits=18, decimal_places=2)]
AccountKind = Literal["cash", "bank", "e_wallet", "savings", "credit_card"]


class AccountCreate(BaseModel):
    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
    kind: AccountKind
    currency_code: str = Field(min_length=3, max_length=3, pattern=r"^[A-Za-z]{3}$")
    opening_balance: Money = Field(default=Decimal("0"), ge=0)
    allow_negative: bool = False
    credit_limit: Money | None = Field(default=None, ge=0)
    billing_day: int | None = Field(default=None, ge=1, le=31)
    due_day: int | None = Field(default=None, ge=1, le=31)

    @field_validator("currency_code")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        return value.upper()

    @model_validator(mode="after")
    def validate_credit_card_fields(self) -> "AccountCreate":
        if self.kind == "credit_card" and self.credit_limit is None:
            raise ValueError("credit_limit is required for credit card accounts")
        return self

class AccountRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    kind: str
    currency_code: str
    opening_balance: Decimal
    current_balance: Decimal
    allow_negative: bool
    credit_limit: Decimal | None
    billing_day: int | None
    due_day: int | None
    created_at: datetime