"""Update budgets and alert events schema.

Revision ID: 0009_budgets_schema_update
Revises: 0008_imports_schema_update
Create Date: 2026-10-31
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision = "0009_budgets_schema_update"
down_revision = "0008_imports_schema_update"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Drop existing empty child tables to re-align types and constraints cleanly
    op.execute("DROP TABLE IF EXISTS budget_alert_events CASCADE;")
    op.execute("DROP TABLE IF EXISTS budget_categories CASCADE;")

    # 2. Update budgets constraints and columns
    op.execute("ALTER TABLE budgets DROP CONSTRAINT IF EXISTS ck_budgets_period_type;")
    op.execute("ALTER TABLE budgets DROP CONSTRAINT IF EXISTS ck_budgets_status;")
    op.execute("ALTER TABLE budgets DROP CONSTRAINT IF EXISTS ex_budgets_active_period_per_user;")

    op.alter_column(
        "budgets",
        "period_type",
        existing_type=sa.String(length=10),
        type_=sa.String(length=15),
        existing_nullable=False,
    )
    op.alter_column(
        "budgets",
        "status",
        existing_type=sa.String(length=10),
        type_=sa.String(length=15),
        existing_nullable=False,
    )

    op.create_check_constraint(
        "ck_budgets_period_type",
        "budgets",
        "period_type IN ('monthly', 'quarterly', 'yearly', 'custom')",
    )
    op.create_check_constraint(
        "ck_budgets_status",
        "budgets",
        "status IN ('active', 'archived')",
    )

    # 3. Create budget_categories with UUID PK, category_kind, and composite FK
    op.create_table(
        "budget_categories",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "budget_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("budgets.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("category_id", sa.Integer(), nullable=False),
        sa.Column("category_kind", sa.String(length=10), nullable=False, server_default="expense"),
        sa.Column("limit_amount", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("warn_percent", sa.SmallInteger(), nullable=False, server_default="80"),
        sa.CheckConstraint("category_kind = 'expense'", name="ck_budget_categories_kind"),
        sa.CheckConstraint("limit_amount > 0", name="ck_budget_categories_positive_limit"),
        sa.CheckConstraint("warn_percent BETWEEN 1 AND 100", name="ck_budget_categories_warn_percent"),
        sa.UniqueConstraint("budget_id", "category_id", name="uq_budget_categories_category"),
        sa.ForeignKeyConstraint(
            ["category_id", "category_kind"],
            ["transaction_categories.id", "transaction_categories.kind"],
            name="fk_budget_categories_category",
            ondelete="RESTRICT",
        ),
    )

    # 4. Create budget_alert_events with BIGINT identity PK and uq_alert_once
    op.create_table(
        "budget_alert_events",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column(
            "budget_category_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("budget_categories.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("level", sa.String(length=15), nullable=False),
        sa.Column("spent_amount", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("percent_used", sa.Numeric(precision=6, scale=2), nullable=False),
        sa.Column(
            "triggered_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "notification_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("notifications.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.CheckConstraint("level IN ('warning', 'exceeded')", name="ck_budget_alert_events_level"),
        sa.CheckConstraint("percent_used >= 0", name="ck_budget_alert_events_percent_used"),
        sa.UniqueConstraint("budget_category_id", "level", name="uq_alert_once"),
    )


def downgrade() -> None:
    op.drop_table("budget_alert_events")
    op.drop_table("budget_categories")

    op.drop_constraint("ck_budgets_status", "budgets", type_="check")
    op.drop_constraint("ck_budgets_period_type", "budgets", type_="check")

    op.alter_column(
        "budgets",
        "status",
        existing_type=sa.String(length=15),
        type_=sa.String(length=10),
        existing_nullable=False,
    )
    op.alter_column(
        "budgets",
        "period_type",
        existing_type=sa.String(length=15),
        type_=sa.String(length=10),
        existing_nullable=False,
    )

    op.create_check_constraint(
        "ck_budgets_status",
        "budgets",
        "status IN ('active', 'paused', 'completed')",
    )
    op.create_check_constraint(
        "ck_budgets_period_type",
        "budgets",
        "period_type IN ('monthly', 'weekly', 'custom')",
    )

