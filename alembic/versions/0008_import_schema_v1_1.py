"""Sync Module E import schema to v1.1.

Revision ID: 0008_import_schema_v1_1
Revises: 0007_sync_module_d_v1_1
Create Date: 2026-10-31
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision = "0008_import_schema_v1_1"
down_revision = "0007_sync_module_d_v1_1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Update import_batches table
    op.add_column(
        "import_batches",
        sa.Column("file_name", sa.String(length=255), nullable=False, server_default="statement.csv"),
    )
    op.add_column(
        "import_batches",
        sa.Column("total_rows", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "import_batches",
        sa.Column("imported_rows", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "import_batches",
        sa.Column("error_message", sa.Text(), nullable=True),
    )

    op.drop_constraint("ck_import_batches_status", "import_batches", type_="check")
    op.create_check_constraint(
        "ck_import_batches_status",
        "import_batches",
        "status IN ('staged', 'previewed', 'confirmed', 'failed', 'expired')",
    )

    # 2. Update import_rows table
    op.add_column(
        "import_rows",
        sa.Column("tx_date", sa.Date(), nullable=True),
    )
    op.add_column(
        "import_rows",
        sa.Column("description", sa.String(length=500), nullable=True),
    )
    op.add_column(
        "import_rows",
        sa.Column("merchant", sa.String(length=150), nullable=True),
    )
    op.add_column(
        "import_rows",
        sa.Column("amount", sa.Numeric(precision=18, scale=2), nullable=True),
    )
    op.add_column(
        "import_rows",
        sa.Column("kind", sa.String(length=10), nullable=True),
    )
    op.create_check_constraint(
        "ck_import_rows_kind",
        "import_rows",
        "kind IS NULL OR kind IN ('income', 'expense')",
    )
    op.add_column(
        "import_rows",
        sa.Column("transaction_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_import_rows_transaction",
        "import_rows",
        "transactions",
        ["transaction_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.drop_constraint("ck_import_rows_status", "import_rows", type_="check")
    op.create_check_constraint(
        "ck_import_rows_status",
        "import_rows",
        "status IN ('valid', 'duplicate', 'invalid', 'imported', 'skipped')",
    )


def downgrade() -> None:
    # 2. Revert import_rows table
    op.drop_constraint("ck_import_rows_status", "import_rows", type_="check")
    op.create_check_constraint(
        "ck_import_rows_status",
        "import_rows",
        "status IN ('valid', 'duplicate', 'invalid')",
    )
    op.drop_constraint("fk_import_rows_transaction", "import_rows", type_="foreignkey")
    op.drop_column("import_rows", "transaction_id")
    op.drop_constraint("ck_import_rows_kind", "import_rows", type_="check")
    op.drop_column("import_rows", "kind")
    op.drop_column("import_rows", "amount")
    op.drop_column("import_rows", "merchant")
    op.drop_column("import_rows", "description")
    op.drop_column("import_rows", "tx_date")

    # 1. Revert import_batches table
    op.drop_constraint("ck_import_batches_status", "import_batches", type_="check")
    op.create_check_constraint(
        "ck_import_batches_status",
        "import_batches",
        "status IN ('previewed', 'confirmed', 'failed', 'expired')",
    )
    op.drop_column("import_batches", "error_message")
    op.drop_column("import_batches", "imported_rows")
    op.drop_column("import_batches", "total_rows")
    op.drop_column("import_batches", "file_name")
