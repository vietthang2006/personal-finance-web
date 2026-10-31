from datetime import date, datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Annotated
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    computed_field,
)

Money = Annotated[Decimal, Field(max_digits=18, decimal_places=2)]


def calculate_goal_progress(
    target_amount: Decimal,
    current_amount: Decimal,
    deadline: date | None,
    status: str,
    as_of: date | None = None,
) -> tuple[Decimal, Decimal, Decimal | None]:
    """Calculates dynamic progress indicators according to Formula F7:
    - remaining = max(0, target_amount - current_amount)
    - progress_percent = round(100 * current_amount / target_amount, 1)
    - monthly_needed = round(remaining / max(1, months_left), 2)

    Edge case rules:
    - If deadline is None or status != 'active': monthly_needed is None.
    - If remaining <= 0: monthly_needed is Decimal('0.00').
    - months_left from today to deadline: kẹp max(1, months_left) to prevent division by 0.
    """
    remaining = max(Decimal("0.00"), target_amount - current_amount)

    if target_amount > Decimal("0.00"):
        progress_percent = (
            (Decimal("100.0") * current_amount) / target_amount
        ).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
    else:
        progress_percent = Decimal("0.0")

    if deadline is None or status != "active":
        monthly_needed = None
    elif remaining <= Decimal("0.00"):
        monthly_needed = Decimal("0.00")
    else:
        today = as_of or datetime.now(timezone.utc).date()
        months_left = (deadline.year - today.year) * 12 + (deadline.month - today.month)
        if deadline.day > today.day and months_left == 0:
            months_left = 1
        months_left = max(1, months_left)
        monthly_needed = (remaining / Decimal(months_left)).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

    return remaining, progress_percent, monthly_needed


class GoalCreate(BaseModel):
    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
    description: Annotated[str | None, StringConstraints(strip_whitespace=True, max_length=1000)] = None
    target_amount: Money = Field(gt=0)
    deadline: date | None = None


class GoalUpdate(BaseModel):
    name: Annotated[str | None, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)] = None
    description: Annotated[str | None, StringConstraints(strip_whitespace=True, max_length=1000)] = None
    target_amount: Money | None = Field(default=None, gt=0)
    deadline: date | None = None


class GoalContributionCreate(BaseModel):
    account_id: UUID
    amount: Money = Field(gt=0)


class GoalContributionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    goal_id: UUID
    transaction_id: UUID
    amount: Decimal
    contributed_at: datetime


class GoalRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    name: str
    description: str | None = None
    target_amount: Decimal
    current_amount: Decimal
    deadline: date | None = None
    status: str
    achieved_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    @computed_field
    @property
    def remaining(self) -> Decimal:
        rem, _, _ = calculate_goal_progress(
            self.target_amount, self.current_amount, self.deadline, self.status
        )
        return rem

    @computed_field
    @property
    def progress_percent(self) -> Decimal:
        _, pct, _ = calculate_goal_progress(
            self.target_amount, self.current_amount, self.deadline, self.status
        )
        return pct

    @computed_field
    @property
    def monthly_needed(self) -> Decimal | None:
        _, _, needed = calculate_goal_progress(
            self.target_amount, self.current_amount, self.deadline, self.status
        )
        return needed


class GoalDetailRead(GoalRead):
    contributions: list[GoalContributionRead] = Field(default_factory=list)


class GoalContributeAccountSummary(BaseModel):
    id: UUID
    new_balance: Decimal


class GoalContributeResponse(BaseModel):
    contribution: GoalContributionRead
    goal: GoalRead
    account: GoalContributeAccountSummary
