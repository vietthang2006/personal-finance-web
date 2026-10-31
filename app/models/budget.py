import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID as UUIDType

from sqlalchemy import (
    BigInteger, CheckConstraint, Date, ForeignKey, ForeignKeyConstraint,
    Integer, Numeric, SmallInteger, String, UniqueConstraint, func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.transaction import TransactionCategory


class Budget(Base):
    __tablename__ = "budgets"
    __table_args__ = (
        CheckConstraint(
            "period_type IN ('monthly', 'quarterly', 'yearly', 'custom')",
            name="ck_budgets_period_type",
        ),
        CheckConstraint("end_date >= start_date", name="ck_budgets_date_range"),
        CheckConstraint("total_limit > 0", name="ck_budgets_positive_limit"),
        CheckConstraint("status IN ('active', 'archived')", name="ck_budgets_status"),
    )

    id: Mapped[UUIDType] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[UUIDType] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    period_type: Mapped[str] = mapped_column(String(15), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    total_limit: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    status: Mapped[str] = mapped_column(String(15), nullable=False, server_default="active")
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now(), nullable=False
    )

    categories: Mapped[list["BudgetCategory"]] = relationship(
        back_populates="budget", cascade="all, delete-orphan", lazy="selectin"
    )


class BudgetCategory(Base):
    __tablename__ = "budget_categories"
    __table_args__ = (
        CheckConstraint("category_kind = 'expense'", name="ck_budget_categories_kind"),
        CheckConstraint("limit_amount > 0", name="ck_budget_categories_positive_limit"),
        CheckConstraint("warn_percent BETWEEN 1 AND 100", name="ck_budget_categories_warn_percent"),
        UniqueConstraint("budget_id", "category_id", name="uq_budget_categories_category"),
        ForeignKeyConstraint(
            ["category_id", "category_kind"],
            ["transaction_categories.id", "transaction_categories.kind"],
            name="fk_budget_categories_category",
            ondelete="RESTRICT",
        ),
    )

    id: Mapped[UUIDType] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    budget_id: Mapped[UUIDType] = mapped_column(
        UUID(as_uuid=True), ForeignKey("budgets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    category_id: Mapped[int] = mapped_column(Integer, nullable=False)
    category_kind: Mapped[str] = mapped_column(String(10), nullable=False, server_default="expense")
    limit_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    warn_percent: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default="80")

    budget: Mapped["Budget"] = relationship(back_populates="categories")
    category: Mapped["TransactionCategory"] = relationship(foreign_keys=[category_id], lazy="joined")
    alerts: Mapped[list["BudgetAlertEvent"]] = relationship(
        back_populates="budget_category", cascade="all, delete-orphan", lazy="selectin"
    )


class BudgetAlertEvent(Base):
    __tablename__ = "budget_alert_events"
    __table_args__ = (
        CheckConstraint("level IN ('warning', 'exceeded')", name="ck_budget_alert_events_level"),
        CheckConstraint("percent_used >= 0", name="ck_budget_alert_events_percent_used"),
        UniqueConstraint("budget_category_id", "level", name="uq_alert_once"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    budget_category_id: Mapped[UUIDType] = mapped_column(
        UUID(as_uuid=True), ForeignKey("budget_categories.id", ondelete="CASCADE"), nullable=False, index=True
    )
    level: Mapped[str] = mapped_column(String(15), nullable=False)
    spent_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    percent_used: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False)
    triggered_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)
    notification_id: Mapped[UUIDType | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("notifications.id", ondelete="SET NULL"), nullable=True
    )

    budget_category: Mapped["BudgetCategory"] = relationship(back_populates="alerts")
