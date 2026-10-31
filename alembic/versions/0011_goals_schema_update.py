"""Goals schema update: standardize columns, add constraints, triggers, and seed SAVING category.

Revision ID: 0011_goals_schema_update
Revises: 0010_align_group_c_and_d
Create Date: 2026-10-31
"""

import sqlalchemy as sa
from alembic import op


revision = "0011_goals_schema_update"
down_revision = "0010_align_group_c_and_d"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # -------------------------------------------------------------------------
    # 1. Standardize savings_goals table columns and constraints
    # -------------------------------------------------------------------------
    # Drop legacy FK and account_id column if present
    op.execute("ALTER TABLE savings_goals DROP CONSTRAINT IF EXISTS fk_savings_goals_account_owner;")
    op.execute("ALTER TABLE savings_goals DROP COLUMN IF EXISTS account_id;")

    # Rename target_date -> deadline if target_date exists
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'savings_goals' AND column_name = 'target_date'
            ) THEN
                ALTER TABLE savings_goals RENAME COLUMN target_date TO deadline;
            END IF;
        END $$;
        """
    )

    # Add achieved_at column if not present
    op.execute("ALTER TABLE savings_goals ADD COLUMN IF NOT EXISTS achieved_at TIMESTAMPTZ;")

    # Migrate any existing legacy status 'completed' -> 'achieved'
    op.execute(
        """
        UPDATE savings_goals
        SET status = 'achieved',
            achieved_at = COALESCE(achieved_at, now())
        WHERE status = 'completed';
        """
    )

    # Expand status column size to VARCHAR(15)
    op.execute("ALTER TABLE savings_goals ALTER COLUMN status TYPE VARCHAR(15);")

    # Update status check constraint
    op.execute("ALTER TABLE savings_goals DROP CONSTRAINT IF EXISTS ck_savings_goals_status;")
    op.execute(
        """
        ALTER TABLE savings_goals
        ADD CONSTRAINT ck_savings_goals_status
        CHECK (status IN ('active', 'achieved', 'cancelled'));
        """
    )

    # Add UNIQUE (user_id, name)
    op.execute("ALTER TABLE savings_goals DROP CONSTRAINT IF EXISTS uq_goals_user_name;")
    op.execute(
        """
        ALTER TABLE savings_goals
        ADD CONSTRAINT uq_goals_user_name
        UNIQUE (user_id, name);
        """
    )

    # Add CHECK ck_goals_not_over (current_amount <= target_amount)
    op.execute("ALTER TABLE savings_goals DROP CONSTRAINT IF EXISTS ck_goals_not_over;")
    op.execute(
        """
        ALTER TABLE savings_goals
        ADD CONSTRAINT ck_goals_not_over
        CHECK (current_amount <= target_amount);
        """
    )

    # Add CHECK ck_goals_achieved
    op.execute("ALTER TABLE savings_goals DROP CONSTRAINT IF EXISTS ck_goals_achieved;")
    op.execute(
        """
        ALTER TABLE savings_goals
        ADD CONSTRAINT ck_goals_achieved
        CHECK (
            (status = 'achieved' AND current_amount = target_amount AND achieved_at IS NOT NULL)
            OR (status <> 'achieved' AND achieved_at IS NULL)
        );
        """
    )

    # -------------------------------------------------------------------------
    # 2. Seed system category SAVING (expense)
    # -------------------------------------------------------------------------
    op.execute(
        """
        INSERT INTO transaction_categories (user_id, code, name, kind, icon, is_active, created_at)
        SELECT NULL, 'SAVING', 'Tiết kiệm', 'expense', 'piggy-bank', TRUE, now()
        WHERE NOT EXISTS (
            SELECT 1 FROM transaction_categories
            WHERE user_id IS NULL AND code = 'SAVING' AND kind = 'expense'
        );
        """
    )

    # -------------------------------------------------------------------------
    # 3. Create Trigger trg_gc_match on goal_contributions (BR-G05)
    # -------------------------------------------------------------------------
    op.execute(
        """
        CREATE OR REPLACE FUNCTION fn_check_goal_contribution_match()
        RETURNS TRIGGER AS $$
        DECLARE
            v_tx RECORD;
            v_goal RECORD;
        BEGIN
            SELECT user_id, kind, source, amount INTO v_tx
            FROM transactions WHERE id = NEW.transaction_id;

            IF NOT FOUND THEN
                RAISE EXCEPTION 'Transaction % not found', NEW.transaction_id
                    USING ERRCODE = '23503';
            END IF;

            SELECT user_id INTO v_goal
            FROM savings_goals WHERE id = NEW.goal_id;

            IF NOT FOUND THEN
                RAISE EXCEPTION 'Savings goal % not found', NEW.goal_id
                    USING ERRCODE = '23503';
            END IF;

            IF v_tx.user_id <> v_goal.user_id THEN
                RAISE EXCEPTION 'Transaction owner does not match goal owner'
                    USING ERRCODE = '23514', CONSTRAINT = 'ck_link_tx_match';
            END IF;

            IF v_tx.kind <> 'expense' OR v_tx.source <> 'goal' THEN
                RAISE EXCEPTION 'Transaction must be expense with source=goal'
                    USING ERRCODE = '23514', CONSTRAINT = 'ck_link_tx_match';
            END IF;

            IF v_tx.amount <> NEW.amount THEN
                RAISE EXCEPTION 'Transaction amount % does not match contribution amount %', v_tx.amount, NEW.amount
                    USING ERRCODE = '23514', CONSTRAINT = 'ck_link_tx_match';
            END IF;

            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )

    op.execute("DROP TRIGGER IF EXISTS trg_gc_match ON goal_contributions;")
    op.execute(
        """
        CREATE TRIGGER trg_gc_match
        BEFORE INSERT OR UPDATE ON goal_contributions
        FOR EACH ROW
        EXECUTE FUNCTION fn_check_goal_contribution_match();
        """
    )

    # -------------------------------------------------------------------------
    # 4. Create Trigger trg_tx_lock_linked on transactions (BR-G07, BR-T10)
    # -------------------------------------------------------------------------
    op.execute(
        """
        CREATE OR REPLACE FUNCTION fn_lock_linked_transactions()
        RETURNS TRIGGER AS $$
        BEGIN
            IF TG_OP = 'DELETE' THEN
                IF OLD.source IN ('goal', 'loan') THEN
                    RAISE EXCEPTION 'Cannot delete transaction linked to goal or loan directly'
                        USING ERRCODE = '23514', CONSTRAINT = 'ck_tx_locked_by_source';
                END IF;
                RETURN OLD;
            ELSIF TG_OP = 'UPDATE' THEN
                IF OLD.source IN ('goal', 'loan') THEN
                    IF (NEW.amount <> OLD.amount OR NEW.account_id <> OLD.account_id OR NEW.kind <> OLD.kind) THEN
                        RAISE EXCEPTION 'Cannot modify financial fields of transaction linked to goal or loan'
                            USING ERRCODE = '23514', CONSTRAINT = 'ck_tx_locked_by_source';
                    END IF;
                END IF;
                RETURN NEW;
            END IF;
            RETURN NULL;
        END;
        $$ LANGUAGE plpgsql;
        """
    )

    op.execute("DROP TRIGGER IF EXISTS trg_tx_lock_linked ON transactions;")
    op.execute(
        """
        CREATE TRIGGER trg_tx_lock_linked
        BEFORE UPDATE OR DELETE ON transactions
        FOR EACH ROW
        EXECUTE FUNCTION fn_lock_linked_transactions();
        """
    )


def downgrade() -> None:
    # -------------------------------------------------------------------------
    # 1. Drop Triggers & Functions
    # -------------------------------------------------------------------------
    op.execute("DROP TRIGGER IF EXISTS trg_tx_lock_linked ON transactions;")
    op.execute("DROP FUNCTION IF EXISTS fn_lock_linked_transactions();")

    op.execute("DROP TRIGGER IF EXISTS trg_gc_match ON goal_contributions;")
    op.execute("DROP FUNCTION IF EXISTS fn_check_goal_contribution_match();")

    # -------------------------------------------------------------------------
    # 2. Remove seeded SAVING category
    # -------------------------------------------------------------------------
    op.execute(
        """
        DELETE FROM transaction_categories
        WHERE user_id IS NULL AND code = 'SAVING' AND kind = 'expense';
        """
    )

    # -------------------------------------------------------------------------
    # 3. Rollback savings_goals constraints & columns
    # -------------------------------------------------------------------------
    op.execute("ALTER TABLE savings_goals DROP CONSTRAINT IF EXISTS ck_goals_achieved;")
    op.execute("ALTER TABLE savings_goals DROP CONSTRAINT IF EXISTS ck_goals_not_over;")
    op.execute("ALTER TABLE savings_goals DROP CONSTRAINT IF EXISTS uq_goals_user_name;")

    op.execute("ALTER TABLE savings_goals DROP CONSTRAINT IF EXISTS ck_savings_goals_status;")
    op.execute(
        """
        ALTER TABLE savings_goals
        ADD CONSTRAINT ck_savings_goals_status
        CHECK (status IN ('active', 'completed', 'cancelled'));
        """
    )

    op.execute("ALTER TABLE savings_goals DROP COLUMN IF EXISTS achieved_at;")

    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'savings_goals' AND column_name = 'deadline'
            ) THEN
                ALTER TABLE savings_goals RENAME COLUMN deadline TO target_date;
            END IF;
        END $$;
        """
    )

    op.execute("ALTER TABLE savings_goals ADD COLUMN IF NOT EXISTS account_id UUID;")
    op.execute(
        """
        ALTER TABLE savings_goals
        ADD CONSTRAINT fk_savings_goals_account_owner
        FOREIGN KEY (account_id, user_id)
        REFERENCES accounts(id, user_id)
        ON DELETE RESTRICT;
        """
    )
