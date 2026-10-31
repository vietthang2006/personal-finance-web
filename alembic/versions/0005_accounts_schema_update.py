"""Update accounts schema with missing columns and constraints.

Revision ID: 0005_accounts_schema_update
Revises: 0004_common_asian_currencies
Create Date: 2026-10-30
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "0005_accounts_schema_update"
down_revision = "0004_common_asian_currencies"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)
    existing_cols = [c["name"] for c in insp.get_columns("accounts")]

    if "bank_name" not in existing_cols:
        op.add_column("accounts", sa.Column("bank_name", sa.String(length=100), nullable=True))

    if "is_archived" not in existing_cols:
        op.add_column(
            "accounts",
            sa.Column("is_archived", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        )

    op.execute("""
        DO $$
        BEGIN
            -- Drop old constraints if they exist
            IF EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_accounts_billing_day') THEN
                ALTER TABLE accounts DROP CONSTRAINT ck_accounts_billing_day;
            END IF;
            IF EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_accounts_due_day') THEN
                ALTER TABLE accounts DROP CONSTRAINT ck_accounts_due_day;
            END IF;
            IF EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_accounts_nonnegative_balance') THEN
                ALTER TABLE accounts DROP CONSTRAINT ck_accounts_nonnegative_balance;
            END IF;

            -- Add updated / new constraints
            IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_accounts_non_negative') THEN
                ALTER TABLE accounts ADD CONSTRAINT ck_accounts_non_negative CHECK (allow_negative OR current_balance >= 0);
            END IF;
            IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_accounts_billing_day') THEN
                ALTER TABLE accounts ADD CONSTRAINT ck_accounts_billing_day CHECK (billing_day IS NULL OR billing_day BETWEEN 1 AND 28);
            END IF;
            IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_accounts_due_day') THEN
                ALTER TABLE accounts ADD CONSTRAINT ck_accounts_due_day CHECK (due_day IS NULL OR due_day BETWEEN 1 AND 28);
            END IF;
            IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_accounts_card_flag') THEN
                ALTER TABLE accounts ADD CONSTRAINT ck_accounts_card_flag CHECK (kind <> 'credit_card' OR allow_negative);
            END IF;
            IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_accounts_card_fields') THEN
                ALTER TABLE accounts ADD CONSTRAINT ck_accounts_card_fields CHECK (
                    (kind = 'credit_card' AND credit_limit IS NOT NULL AND billing_day IS NOT NULL AND due_day IS NOT NULL) OR
                    (kind <> 'credit_card' AND credit_limit IS NULL AND billing_day IS NULL AND due_day IS NULL)
                );
            END IF;
            IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_accounts_card_debt_limit') THEN
                ALTER TABLE accounts ADD CONSTRAINT ck_accounts_card_debt_limit CHECK (kind <> 'credit_card' OR current_balance >= -credit_limit);
            END IF;
            IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'uq_accounts_user_name') THEN
                ALTER TABLE accounts ADD CONSTRAINT uq_accounts_user_name UNIQUE (user_id, name);
            END IF;
            IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'uq_accounts_id_kind') THEN
                ALTER TABLE accounts ADD CONSTRAINT uq_accounts_id_kind UNIQUE (id, kind);
            END IF;
        END $$;
    """)


def downgrade() -> None:
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'uq_accounts_id_kind') THEN
                ALTER TABLE accounts DROP CONSTRAINT uq_accounts_id_kind;
            END IF;
            IF EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'uq_accounts_user_name') THEN
                ALTER TABLE accounts DROP CONSTRAINT uq_accounts_user_name;
            END IF;
            IF EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_accounts_card_debt_limit') THEN
                ALTER TABLE accounts DROP CONSTRAINT ck_accounts_card_debt_limit;
            END IF;
            IF EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_accounts_card_fields') THEN
                ALTER TABLE accounts DROP CONSTRAINT ck_accounts_card_fields;
            END IF;
            IF EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_accounts_card_flag') THEN
                ALTER TABLE accounts DROP CONSTRAINT ck_accounts_card_flag;
            END IF;
            IF EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_accounts_non_negative') THEN
                ALTER TABLE accounts DROP CONSTRAINT ck_accounts_non_negative;
            END IF;
            IF EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_accounts_billing_day') THEN
                ALTER TABLE accounts DROP CONSTRAINT ck_accounts_billing_day;
            END IF;
            IF EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_accounts_due_day') THEN
                ALTER TABLE accounts DROP CONSTRAINT ck_accounts_due_day;
            END IF;
        END $$;
    """)
    op.create_check_constraint(
        "ck_accounts_nonnegative_balance",
        "accounts",
        "allow_negative OR current_balance >= 0",
    )
    op.create_check_constraint(
        "ck_accounts_billing_day",
        "accounts",
        "billing_day IS NULL OR billing_day BETWEEN 1 AND 31",
    )
    op.create_check_constraint(
        "ck_accounts_due_day",
        "accounts",
        "due_day IS NULL OR due_day BETWEEN 1 AND 31",
    )
    bind = op.get_bind()
    insp = inspect(bind)
    existing_cols = [c["name"] for c in insp.get_columns("accounts")]
    if "is_archived" in existing_cols:
        op.drop_column("accounts", "is_archived")
    if "bank_name" in existing_cols:
        op.drop_column("accounts", "bank_name")
