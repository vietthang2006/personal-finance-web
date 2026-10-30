"""Align schema for Group C and D.

Revision ID: 0010_align_group_c_and_d
Revises: 0009_budgets_schema_update
Create Date: 2026-10-31
"""

import sqlalchemy as sa
from alembic import op


revision = "0010_align_group_c_and_d"
down_revision = "0009_budgets_schema_update"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Allow transaction_categories.code to be NULL
    op.alter_column(
        "transaction_categories",
        "code",
        existing_type=sa.String(length=50),
        nullable=True,
    )

    # 2. Make tags.user_id NOT NULL
    op.alter_column(
        "tags",
        "user_id",
        existing_type=sa.dialects.postgresql.UUID(as_uuid=True),
        nullable=False,
    )

    # 3. Update transactions.ck_transactions_category_pair constraint
    op.drop_constraint("ck_transactions_category_pair", "transactions", type_="check")
    op.create_check_constraint(
        "ck_transactions_category_pair",
        "transactions",
        "subcategory_id IS NULL OR category_id IS NOT NULL",
    )

    # 4. Add uq_tx_account_dedup
    op.create_unique_constraint(
        "uq_tx_account_dedup",
        "transactions",
        ["account_id", "dedup_hash"],
    )

    # 5. Update transfers.purpose constraint
    op.drop_constraint("ck_transfers_purpose", "transfers", type_="check")
    op.create_check_constraint(
        "ck_transfers_purpose",
        "transfers",
        "purpose IN ('normal', 'card_payment', 'internal', 'credit_card_payment')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_transfers_purpose", "transfers", type_="check")
    op.create_check_constraint(
        "ck_transfers_purpose",
        "transfers",
        "purpose IN ('internal', 'credit_card_payment')",
    )

    op.drop_constraint("uq_tx_account_dedup", "transactions", type_="unique")

    op.drop_constraint("ck_transactions_category_pair", "transactions", type_="check")
    op.create_check_constraint(
        "ck_transactions_category_pair",
        "transactions",
        "(category_id IS NULL AND subcategory_id IS NULL) OR (category_id IS NOT NULL AND subcategory_id IS NOT NULL)",
    )

    op.alter_column(
        "tags",
        "user_id",
        existing_type=sa.dialects.postgresql.UUID(as_uuid=True),
        nullable=True,
    )

    op.alter_column(
        "transaction_categories",
        "code",
        existing_type=sa.String(length=50),
        nullable=False,
    )
