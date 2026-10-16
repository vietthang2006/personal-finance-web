import uuid
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID as UUIDType

from sqlalchemy import (
    CheckConstraint, Date, DateTime, ForeignKey, ForeignKeyConstraint, Integer,
    Numeric, String, UniqueConstraint, func, text,
)
from sqlalchemy.dialects.postgresql import UUID, ExcludeConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Budget(Base):
    __tablename__ = "budgets"
    __table_args__ = (
        CheckConstraint(
            "period_type IN ('monthly', 'weekly', 'custom')", name="ck_budgets_period_type"
        ),
        CheckConstraint("start_date <= end_date", name="ck_budgets_date_range"),
        CheckConstraint("total_limit > 0", name="ck_budgets_positive_limit"),
        CheckConstraint("status IN ('active', 'paused', 'completed')", name="ck_budgets_status"),
        ExcludeConstraint(
            ("user_id", "="),
            (text("daterange(start_date, end_date, '[]')"), "&&"),
            where=text("status = 'active'"),
            using="gist",
            name="ex_budgets_active_period_per_user",
        ),
    )

    id: Mapped[UUIDType] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[UUIDType] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    period_type: Mapped[str] = mapped_column(String(10), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    total_limit: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    status: Mapped[str] = mapped_column(String(10), nullable=False, server_default="active")
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now(), nullable=False)


class BudgetCategory(Base):
    __tablename__ = "budget_categories"
    __table_args__ = (
        CheckConstraint("limit_amount > 0", name="ck_budget_categories_positive_limit"),
        CheckConstraint("warn_percent BETWEEN 1 AND 100", name="ck_budget_categories_warn_percent"),
        UniqueConstraint("budget_id", "category_id", name="uq_budget_categories_category"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    budget_id: Mapped[UUIDType] = mapped_column(
        UUID(as_uuid=True), ForeignKey("budgets.id", ondelete="CASCADE"), nullable=False
    )
    category_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("transaction_categories.id", ondelete="RESTRICT"), nullable=False
    )
    limit_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    warn_percent: Mapped[int] = mapped_column(Integer, nullable=False, server_default="80")


class BudgetAlertEvent(Base):
    __tablename__ = "budget_alert_events"
    __table_args__ = (
        CheckConstraint("level IN ('warning', 'exceeded')", name="ck_budget_alert_events_level"),
        CheckConstraint("percent_used >= 0", name="ck_budget_alert_events_percent_used"),
        UniqueConstraint("budget_category_id", "level", name="uq_budget_alert_events_category_level"),
    )

    id: Mapped[UUIDType] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    budget_category_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("budget_categories.id", ondelete="CASCADE"), nullable=False
    )
    level: Mapped[str] = mapped_column(String(10), nullable=False)
    percent_used: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)