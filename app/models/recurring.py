import uuid
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID as UUIDType

from sqlalchemy import (
    CheckConstraint, Date, DateTime, ForeignKey, ForeignKeyConstraint, Integer,
    Numeric, String, Text, UniqueConstraint, func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class RecurringTransaction(Base):
    __tablename__ = "recurring_transactions"
    __table_args__ = (
        ForeignKeyConstraint(
            ["account_id", "user_id"], ["accounts.id", "accounts.user_id"],
            ondelete="CASCADE", name="fk_recurring_transactions_account_owner",
        ),
        ForeignKeyConstraint(
            ["category_id", "kind"], ["transaction_categories.id", "transaction_categories.kind"],
            ondelete="RESTRICT", name="fk_recurring_transactions_category_kind",
        ),
        ForeignKeyConstraint(
            ["category_id", "subcategory_id"],
            ["transaction_subcategories.category_id", "transaction_subcategories.id"],
            ondelete="RESTRICT", name="fk_recurring_transactions_subcategory",
        ),
        CheckConstraint("kind IN ('income', 'expense')", name="ck_recurring_transactions_kind"),
        CheckConstraint("amount > 0", name="ck_recurring_transactions_positive_amount"),
        CheckConstraint("interval > 0", name="ck_recurring_transactions_positive_interval"),
        CheckConstraint(
            "(category_id IS NULL AND subcategory_id IS NULL) OR "
            "(category_id IS NOT NULL AND subcategory_id IS NOT NULL)",
            name="ck_recurring_transactions_category_pair",
        ),
        CheckConstraint(
            "frequency IN ('daily', 'weekly', 'monthly', 'yearly')",
            name="ck_recurring_transactions_frequency",
        ),
        CheckConstraint("status IN ('active', 'paused', 'completed')", name="ck_recurring_transactions_status"),
        UniqueConstraint("user_id", "idempotency_key", name="uq_recurring_transactions_idempotency"),
    )

    id: Mapped[UUIDType] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[UUIDType] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    account_id: Mapped[UUIDType] = mapped_column(UUID(as_uuid=True), nullable=False)
    kind: Mapped[str] = mapped_column(String(10), nullable=False)
    category_id: Mapped[int | None] = mapped_column(Integer)
    subcategory_id: Mapped[int | None] = mapped_column(Integer)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    frequency: Mapped[str] = mapped_column(String(10), nullable=False)
    interval: Mapped[int] = mapped_column(nullable=False, server_default="1")
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    next_run_at: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    end_date: Mapped[date | None] = mapped_column(Date)
    last_generated_date: Mapped[date | None] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(10), nullable=False, server_default="active")
    idempotency_key: Mapped[str] = mapped_column(String(64), nullable=False)
    request_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)