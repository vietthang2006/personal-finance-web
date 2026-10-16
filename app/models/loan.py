import uuid
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID as UUIDType

from sqlalchemy import (
    CheckConstraint, Date, DateTime, ForeignKey, ForeignKeyConstraint, Numeric,
    String, UniqueConstraint, func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Loan(Base):
    __tablename__ = "loans"
    __table_args__ = (
        ForeignKeyConstraint(
            ["account_id", "user_id"], ["accounts.id", "accounts.user_id"],
            ondelete="RESTRICT", name="fk_loans_account_owner",
        ),
        CheckConstraint("principal > 0", name="ck_loans_positive_principal"),
        CheckConstraint("outstanding_balance >= 0", name="ck_loans_nonnegative_outstanding"),
        CheckConstraint("interest_rate >= 0", name="ck_loans_nonnegative_interest"),
        CheckConstraint("status IN ('active', 'paid', 'defaulted')", name="ck_loans_status"),
    )

    id: Mapped[UUIDType] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[UUIDType] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    account_id: Mapped[UUIDType] = mapped_column(UUID(as_uuid=True), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    lender: Mapped[str | None] = mapped_column(String(120))
    principal: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    outstanding_balance: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    interest_rate: Mapped[Decimal] = mapped_column(Numeric(8, 4), nullable=False, server_default="0")
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    due_date: Mapped[date | None] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(10), nullable=False, server_default="active")
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)


class LoanPayment(Base):
    __tablename__ = "loan_payments"
    __table_args__ = (CheckConstraint("amount > 0", name="ck_loan_payments_positive_amount"),)

    id: Mapped[UUIDType] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    loan_id: Mapped[UUIDType] = mapped_column(
        UUID(as_uuid=True), ForeignKey("loans.id", ondelete="CASCADE"), nullable=False, index=True
    )
    transaction_id: Mapped[UUIDType] = mapped_column(
        UUID(as_uuid=True), ForeignKey("transactions.id", ondelete="RESTRICT"), unique=True, nullable=False
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    paid_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)


class CreditCardStatement(Base):
    __tablename__ = "credit_card_statements"
    __table_args__ = (
        ForeignKeyConstraint(
            ["account_id", "user_id"], ["accounts.id", "accounts.user_id"],
            ondelete="CASCADE", name="fk_credit_card_statements_account_owner",
        ),
        CheckConstraint("total_due >= 0 AND minimum_due >= 0", name="ck_credit_card_statements_amounts"),
        CheckConstraint("minimum_due <= total_due", name="ck_credit_card_statements_minimum"),
        CheckConstraint("period_start <= period_end", name="ck_credit_card_statements_period"),
        UniqueConstraint("account_id", "period_start", "period_end", name="uq_credit_card_statements_period"),
    )

    id: Mapped[UUIDType] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[UUIDType] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    account_id: Mapped[UUIDType] = mapped_column(UUID(as_uuid=True), nullable=False)
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    total_due: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    minimum_due: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)