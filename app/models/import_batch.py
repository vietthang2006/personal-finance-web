import uuid
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID as UUIDType

from sqlalchemy import (
    CheckConstraint, Date, DateTime, ForeignKey, ForeignKeyConstraint, Index, Integer,
    Numeric, String, Text, UniqueConstraint, func, text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ImportBatch(Base):
    __tablename__ = "import_batches"
    __table_args__ = (
        ForeignKeyConstraint(
            ["account_id", "user_id"], ["accounts.id", "accounts.user_id"],
            ondelete="CASCADE", name="fk_import_batches_account_owner",
        ),
        CheckConstraint(
            "status IN ('staged', 'previewed', 'confirmed', 'failed', 'expired')",
            name="ck_import_batches_status",
        ),
        CheckConstraint(
            "valid_rows >= 0 AND duplicate_rows >= 0 AND invalid_rows >= 0",
            name="ck_import_batches_row_counts",
        ),
        Index(
            "uq_import_batches_confirmed_file",
            "account_id",
            "file_hash",
            unique=True,
            postgresql_where=text("status = 'confirmed'"),
        ),
    )

    id: Mapped[UUIDType] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[UUIDType] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    account_id: Mapped[UUIDType] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False, server_default="statement.csv")
    file_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="staged")
    total_rows: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    valid_rows: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    duplicate_rows: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    invalid_rows: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    imported_rows: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ImportRow(Base):
    __tablename__ = "import_rows"
    __table_args__ = (
        CheckConstraint(
            "status IN ('valid', 'duplicate', 'invalid', 'imported', 'skipped')",
            name="ck_import_rows_status",
        ),
        CheckConstraint(
            "kind IS NULL OR kind IN ('income', 'expense')",
            name="ck_import_rows_kind",
        ),
        UniqueConstraint("batch_id", "row_number", name="uq_import_rows_batch_row_number"),
    )

    id: Mapped[UUIDType] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    batch_id: Mapped[UUIDType] = mapped_column(
        UUID(as_uuid=True), ForeignKey("import_batches.id", ondelete="CASCADE"), nullable=False, index=True
    )
    row_number: Mapped[int] = mapped_column(Integer, nullable=False)
    raw_data: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    parsed_data: Mapped[dict[str, object] | None] = mapped_column(JSONB)
    tx_date: Mapped[date | None] = mapped_column(Date)
    description: Mapped[str | None] = mapped_column(String(500))
    merchant: Mapped[str | None] = mapped_column(String(150))
    amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))
    kind: Mapped[str | None] = mapped_column(String(10))
    suggested_category_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("transaction_categories.id", ondelete="SET NULL")
    )
    chosen_category_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("transaction_categories.id", ondelete="SET NULL")
    )
    dedup_hash: Mapped[str | None] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    error_message: Mapped[str | None] = mapped_column(String(500))
    transaction_id: Mapped[UUIDType | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("transactions.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)
