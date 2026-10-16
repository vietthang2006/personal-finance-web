import uuid
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID as UUIDType

from sqlalchemy import (
    Boolean, CheckConstraint, Date, DateTime, ForeignKey, ForeignKeyConstraint,
    Numeric, String, UniqueConstraint, func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Account(Base):
    __tablename__ = "accounts"
    __table_args__ = (
        UniqueConstraint("id", "user_id", name="uq_accounts_id_user"),
        CheckConstraint(
            "kind IN ('cash', 'bank', 'e_wallet', 'savings', 'credit_card')",
            name="ck_accounts_kind",
        ),
        CheckConstraint("opening_balance >= 0", name="ck_accounts_opening_balance"),
        CheckConstraint(
            "allow_negative OR current_balance >= 0",
            name="ck_accounts_nonnegative_balance",
        ),
        CheckConstraint("credit_limit IS NULL OR credit_limit >= 0", name="ck_accounts_credit_limit"),
        CheckConstraint("billing_day IS NULL OR billing_day BETWEEN 1 AND 31", name="ck_accounts_billing_day"),
        CheckConstraint("due_day IS NULL OR due_day BETWEEN 1 AND 31", name="ck_accounts_due_day"),
    )

    id: Mapped[UUIDType] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[UUIDType] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    kind: Mapped[str] = mapped_column(String(20), nullable=False)
    currency_code: Mapped[str] = mapped_column(
        String(3), ForeignKey("currencies.code", ondelete="RESTRICT"), nullable=False
    )
    opening_balance: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, server_default="0")
    current_balance: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, server_default="0")
    allow_negative: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    credit_limit: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))
    billing_day: Mapped[int | None] = mapped_column()
    due_day: Mapped[int | None] = mapped_column()
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now(), nullable=False)


class AccountBalanceHistory(Base):
    __tablename__ = "account_balance_history"
    __table_args__ = (ForeignKeyConstraint(["account_id"], ["accounts.id"], ondelete="CASCADE"),)

    account_id: Mapped[UUIDType] = mapped_column(UUID(as_uuid=True), primary_key=True)
    snapshot_date: Mapped[date] = mapped_column(Date, primary_key=True)
    balance: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)