from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Literal
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

Money = Annotated[Decimal, Field(max_digits=18, decimal_places=2)]
AccountKind = Literal["cash", "bank", "e_wallet", "savings", "credit_card"]


class AccountCreate(BaseModel):
    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
    kind: AccountKind
    currency_code: str = Field(min_length=3, max_length=3, pattern=r"^[A-Za-z]{3}$")
    bank_name: Annotated[str | None, StringConstraints(strip_whitespace=True, max_length=100)] = None
    opening_balance: Money = Field(default=Decimal(0), ge=0)
    allow_negative: bool = False
    credit_limit: Money | None = Field(default=None, ge=0)
    billing_day: int | None = Field(default=None, ge=1, le=28)
    due_day: int | None = Field(default=None, ge=1, le=28)

    @field_validator("currency_code")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        return value.upper()

    @model_validator(mode="after")
    def validate_card_rules(self) -> "AccountCreate":
        if self.kind == "credit_card":
            self.allow_negative = True
            if self.credit_limit is None or self.credit_limit < Decimal(0):
                raise ValueError("credit_limit is required for credit cards")
            if self.billing_day is None:
                raise ValueError("billing_day is required for credit cards (between 1 and 28)")
            if self.due_day is None:
                raise ValueError("due_day is required for credit cards (between 1 and 28)")
        else:
            if self.credit_limit is not None:
                raise ValueError("credit_limit is only allowed for credit_card accounts")
            if self.billing_day is not None or self.due_day is not None:
                raise ValueError("billing_day and due_day are only allowed for credit_card accounts")
        return self


class AccountUpdate(BaseModel):
    name: Annotated[str | None, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)] = None
    bank_name: Annotated[str | None, StringConstraints(strip_whitespace=True, max_length=100)] = None
    kind: AccountKind | None = None
    currency_code: str | None = None
    opening_balance: Money | None = None
    is_archived: bool | None = None
    credit_limit: Money | None = Field(default=None, ge=0)
    billing_day: int | None = Field(default=None, ge=1, le=28)
    due_day: int | None = Field(default=None, ge=1, le=28)


class AccountRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    name: str
    kind: str
    currency_code: str
    bank_name: str | None
    opening_balance: Decimal
    current_balance: Decimal
    balance_base: Decimal | None = None
    allow_negative: bool
    credit_limit: Decimal | None
    billing_day: int | None
    due_day: int | None
    is_archived: bool
    created_at: datetime
    updated_at: datetime


class AccountSummaryResponse(BaseModel):
    default_currency: str
    total_assets_base: Decimal
    total_liabilities_base: Decimal
    net_worth_base: Decimal
    accounts: list[AccountRead]


class AccountBalanceHistoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    account_id: UUID
    snapshot_date: date
    balance: Decimal
    created_at: datetime
