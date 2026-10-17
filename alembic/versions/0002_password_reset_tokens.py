"""Create password reset tokens.

Revision ID: 0002_password_reset_tokens
Revises: 0001_initial_schema
Create Date: 2026-10-17
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql


revision = "0002_password_reset_tokens"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if not inspect(bind).has_table("password_reset_tokens"):
        op.create_table(
            "password_reset_tokens",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("token_hash", sa.String(length=64), nullable=False),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("ip_address", postgresql.INET(), nullable=True),
            sa.Column("user_agent", sa.String(length=255), nullable=True),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("token_hash"),
            sa.CheckConstraint("expires_at > created_at", name="ck_pwd_reset_expiry"),
            sa.CheckConstraint("used_at IS NULL OR used_at >= created_at", name="ck_pwd_reset_used_order"),
        )
        op.create_index("ix_password_reset_tokens_user_id", "password_reset_tokens", ["user_id"])
        op.create_index("ix_password_reset_tokens_expires_at", "password_reset_tokens", ["expires_at"])
        op.create_index("ix_password_reset_tokens_used_at", "password_reset_tokens", ["used_at"])
        op.create_index(
            "ix_pwd_reset_active",
            "password_reset_tokens",
            ["user_id"],
            postgresql_where=sa.text("used_at IS NULL AND revoked_at IS NULL"),
        )

    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint WHERE conname = 'ck_sessions_expiry'
            ) THEN
                ALTER TABLE user_sessions ADD CONSTRAINT ck_sessions_expiry CHECK (expires_at > created_at);
            END IF;
            IF NOT EXISTS (
                SELECT 1 FROM pg_indexes WHERE indexname = 'ix_sessions_user'
            ) THEN
                CREATE INDEX ix_sessions_user ON user_sessions(user_id) WHERE revoked_at IS NULL;
            END IF;
        END $$;
    """)


def downgrade() -> None:
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_sessions_expiry') THEN
                ALTER TABLE user_sessions DROP CONSTRAINT ck_sessions_expiry;
            END IF;
            IF EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'ix_sessions_user') THEN
                DROP INDEX ix_sessions_user;
            END IF;
        END $$;
    """)
    if inspect(op.get_bind()).has_table("password_reset_tokens"):
        op.drop_table("password_reset_tokens")