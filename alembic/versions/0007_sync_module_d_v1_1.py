"""Sync Module D schema to v1.1.

Revision ID: 0007_sync_module_d_v1_1
Revises: 0006_transaction_category_seed
Create Date: 2026-10-31
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision = "0007_sync_module_d_v1_1"
down_revision = "0006_transaction_category_seed"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Add icon to transaction_categories
    op.add_column(
        "transaction_categories",
        sa.Column("icon", sa.String(length=50), nullable=True),
    )

    # 2. Add UNIQUE (user_id, name) to tags
    op.create_unique_constraint(
        "uq_tags_user_name",
        "tags",
        ["user_id", "name"],
    )

    # 3. Add import_batch_id and recurring_id to transactions
    op.add_column(
        "transactions",
        sa.Column("import_batch_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_transactions_import_batch",
        "transactions",
        "import_batches",
        ["import_batch_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.add_column(
        "transactions",
        sa.Column("recurring_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_transactions_recurring",
        "transactions",
        "recurring_transactions",
        ["recurring_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_unique_constraint(
        "uq_tx_recurring_day",
        "transactions",
        ["recurring_id", "transaction_date"],
    )

    # 4. Add purpose to transfers with default and check constraint
    op.add_column(
        "transfers",
        sa.Column("purpose", sa.String(length=30), nullable=False, server_default="internal"),
    )
    op.create_check_constraint(
        "ck_transfers_purpose",
        "transfers",
        "purpose IN ('internal', 'credit_card_payment')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_transfers_purpose", "transfers", type_="check")
    op.drop_column("transfers", "purpose")

    op.drop_constraint("uq_tx_recurring_day", "transactions", type_="unique")
    op.drop_constraint("fk_transactions_recurring", "transactions", type_="foreignkey")
    op.drop_column("transactions", "recurring_id")
    op.drop_constraint("fk_transactions_import_batch", "transactions", type_="foreignkey")
    op.drop_column("transactions", "import_batch_id")

    op.drop_constraint("uq_tags_user_name", "tags", type_="unique")

    op.drop_column("transaction_categories", "icon")
