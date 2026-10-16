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


class TransactionCategory(Base):
    __tablename__ = "transaction_categories"
    __table_args__ = (
        UniqueConstraint("id", "kind", name="uq_transaction_categories_id_kind"),
        CheckConstraint("kind IN ('income', 'expense')", name="ck_transaction_categories_kind"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[UUIDType | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    code: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    kind: Mapped[str] = mapped_column(String(10), nullable=False)
    is_active: Mapped[bool] = mapped_column(nullable=False, server_default="true")
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)


class TransactionSubcategory(Base):
    __tablename__ = "transaction_subcategories"
    __table_args__ = (
        UniqueConstraint("category_id", "id", name="uq_transaction_subcategories_category_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    category_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("transaction_categories.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    is_active: Mapped[bool] = mapped_column(nullable=False, server_default="true")


class Tag(Base):
    __tablename__ = "tags"
    __table_args__ = (CheckConstraint("color ~ '^#[0-9A-Fa-f]{6}$'", name="ck_tags_color_hex"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[UUIDType | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    color: Mapped[str] = mapped_column(String(7), nullable=False, server_default="#808080")
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)


class Transaction(Base):
    __tablename__ = "transactions"
    __table_args__ = (
        ForeignKeyConstraint(
            ["account_id", "user_id"], ["accounts.id", "accounts.user_id"],
            ondelete="RESTRICT", name="fk_transactions_account_owner",
        ),
        ForeignKeyConstraint(
            ["category_id", "kind"], ["transaction_categories.id", "transaction_categories.kind"],
            ondelete="RESTRICT", name="fk_transactions_category_kind",
        ),
        ForeignKeyConstraint(
            ["category_id", "subcategory_id"],
            ["transaction_subcategories.category_id", "transaction_subcategories.id"],
            ondelete="RESTRICT", name="fk_transactions_category_subcategory",
        ),
        CheckConstraint("kind IN ('income', 'expense')", name="ck_transactions_kind"),
        CheckConstraint("amount > 0", name="ck_transactions_positive_amount"),
        CheckConstraint(
            "(category_id IS NULL AND subcategory_id IS NULL) OR "
            "(category_id IS NOT NULL AND subcategory_id IS NOT NULL)",
            name="ck_transactions_category_pair",
        ),
        UniqueConstraint("user_id", "dedup_hash", name="uq_transactions_user_dedup_hash"),
    )

    id: Mapped[UUIDType] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[UUIDType] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    account_id: Mapped[UUIDType] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    kind: Mapped[str] = mapped_column(String(10), nullable=False)
    category_id: Mapped[int | None] = mapped_column(Integer)
    subcategory_id: Mapped[int | None] = mapped_column(Integer)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    transaction_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text)
    merchant: Mapped[str | None] = mapped_column(String(150))
    source: Mapped[str] = mapped_column(String(30), nullable=False, server_default="manual")
    dedup_hash: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now(), nullable=False)


class TransactionTag(Base):
    __tablename__ = "transaction_tags"

    transaction_id: Mapped[UUIDType] = mapped_column(
        UUID(as_uuid=True), ForeignKey("transactions.id", ondelete="CASCADE"), primary_key=True
    )
    tag_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True
    )
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)


class TransactionAttachment(Base):
    __tablename__ = "transaction_attachments"
    __table_args__ = (
        CheckConstraint("size_bytes BETWEEN 0 AND 10485760", name="ck_attachments_max_size"),
    )

    id: Mapped[UUIDType] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    transaction_id: Mapped[UUIDType] = mapped_column(
        UUID(as_uuid=True), ForeignKey("transactions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    storage_key: Mapped[str] = mapped_column(String(512), unique=True, nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)


class Transfer(Base):
    __tablename__ = "transfers"
    __table_args__ = (
        ForeignKeyConstraint(
            ["from_account_id", "user_id"], ["accounts.id", "accounts.user_id"],
            ondelete="RESTRICT", name="fk_transfers_from_owner",
        ),
        ForeignKeyConstraint(
            ["to_account_id", "user_id"], ["accounts.id", "accounts.user_id"],
            ondelete="RESTRICT", name="fk_transfers_to_owner",
        ),
        CheckConstraint("from_account_id <> to_account_id", name="ck_transfers_distinct_accounts"),
        CheckConstraint("amount > 0 AND to_amount > 0", name="ck_transfers_positive_amounts"),
        CheckConstraint("exchange_rate > 0", name="ck_transfers_positive_rate"),
    )

    id: Mapped[UUIDType] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[UUIDType] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    from_account_id: Mapped[UUIDType] = mapped_column(UUID(as_uuid=True), nullable=False)
    to_account_id: Mapped[UUIDType] = mapped_column(UUID(as_uuid=True), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    to_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    exchange_rate: Mapped[Decimal] = mapped_column(Numeric(18, 8), nullable=False, server_default="1")
    transaction_date: Mapped[date] = mapped_column(Date, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    idempotency_key: Mapped[str | None] = mapped_column(String(100), unique=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)