import uuid
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID as UUIDType

from sqlalchemy import (
    CheckConstraint, Date, DateTime, ForeignKey, ForeignKeyConstraint, Numeric,
    String, Text, UniqueConstraint, func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class SavingsGoal(Base):
    __tablename__ = "savings_goals"
    __table_args__ = (
        ForeignKeyConstraint(
            ["account_id", "user_id"], ["accounts.id", "accounts.user_id"],
            ondelete="RESTRICT", name="fk_savings_goals_account_owner",
        ),
        CheckConstraint("target_amount > 0", name="ck_savings_goals_positive_target"),
        CheckConstraint("current_amount >= 0", name="ck_savings_goals_nonnegative_current"),
        CheckConstraint("status IN ('active', 'completed', 'cancelled')", name="ck_savings_goals_status"),
    )

    id: Mapped[UUIDType] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[UUIDType] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    account_id: Mapped[UUIDType | None] = mapped_column(UUID(as_uuid=True))
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    target_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    current_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, server_default="0")
    target_date: Mapped[date | None] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(10), nullable=False, server_default="active")
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now(), nullable=False)


class GoalContribution(Base):
    __tablename__ = "goal_contributions"
    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_goal_contributions_positive_amount"),
    )

    id: Mapped[UUIDType] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    goal_id: Mapped[UUIDType] = mapped_column(
        UUID(as_uuid=True), ForeignKey("savings_goals.id", ondelete="CASCADE"), nullable=False, index=True
    )
    transaction_id: Mapped[UUIDType] = mapped_column(
        UUID(as_uuid=True), ForeignKey("transactions.id", ondelete="RESTRICT"), unique=True, nullable=False
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    contributed_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)