"""Add source-specific exchange rate history.

Revision ID: 0003_exchange_rate_history
Revises: 0002_password_reset_tokens
Create Date: 2026-10-18
"""

from alembic import op
from sqlalchemy import Column, DateTime, String, text
from sqlalchemy.dialects import postgresql


revision = "0003_exchange_rate_history"
down_revision = "0002_password_reset_tokens"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "exchange_rates",
        Column("id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "exchange_rates",
        Column("source", String(length=30), nullable=True),
    )
    op.add_column(
        "exchange_rates",
        Column("rate_type", String(length=20), nullable=True),
    )
    op.add_column(
        "exchange_rates",
        Column("fetched_at", DateTime(timezone=True), nullable=True),
    )

    # Legacy timestamps had no timezone; interpret them as UTC during backfill.
    op.execute(
        """
        UPDATE exchange_rates
        SET id = gen_random_uuid(),
            source = 'legacy',
            rate_type = 'unknown',
            fetched_at = created_at AT TIME ZONE 'UTC'
        """
    )

    op.alter_column("exchange_rates", "id", nullable=False)
    op.alter_column("exchange_rates", "source", nullable=False)
    op.alter_column("exchange_rates", "rate_type", nullable=False)
    op.alter_column(
        "exchange_rates",
        "fetched_at",
        nullable=False,
        server_default=text("now()"),
    )

    op.drop_constraint("exchange_rates_pkey", "exchange_rates", type_="primary")
    op.create_primary_key("exchange_rates_pkey", "exchange_rates", ["id"])
    op.create_check_constraint(
        "ck_exchange_rates_different_currencies",
        "exchange_rates",
        "base_currency <> target_currency",
    )
    op.create_check_constraint(
        "ck_exchange_rates_rate_type",
        "exchange_rates",
        "rate_type IN ('cash_buy', 'transfer_buy', 'sell', 'unknown')",
    )
    op.create_unique_constraint(
        "uq_exchange_rates_quote_snapshot",
        "exchange_rates",
        [
            "base_currency",
            "target_currency",
            "source",
            "rate_type",
            "rate_date",
            "fetched_at",
        ],
    )


def downgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM exchange_rates
                GROUP BY base_currency, target_currency, rate_date
                HAVING count(*) > 1
            ) THEN
                RAISE EXCEPTION
                    'Cannot downgrade: multiple exchange-rate snapshots exist for a date';
            END IF;
        END $$;
        """
    )
    op.drop_constraint(
        "uq_exchange_rates_quote_snapshot",
        "exchange_rates",
        type_="unique",
    )
    op.drop_constraint(
        "ck_exchange_rates_rate_type",
        "exchange_rates",
        type_="check",
    )
    op.drop_constraint(
        "ck_exchange_rates_different_currencies",
        "exchange_rates",
        type_="check",
    )
    op.drop_constraint("exchange_rates_pkey", "exchange_rates", type_="primary")
    op.drop_column("exchange_rates", "fetched_at")
    op.drop_column("exchange_rates", "rate_type")
    op.drop_column("exchange_rates", "source")
    op.drop_column("exchange_rates", "id")
    op.create_primary_key(
        "exchange_rates_pkey",
        "exchange_rates",
        ["base_currency", "target_currency", "rate_date"],
    )