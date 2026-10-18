"""Seed commonly used Asian currencies.

Revision ID: 0004_common_asian_currencies
Revises: 0003_exchange_rate_history
Create Date: 2026-10-18
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import insert


revision = "0004_common_asian_currencies"
down_revision = "0003_exchange_rate_history"
branch_labels = None
depends_on = None


def upgrade() -> None:
    currencies = sa.table(
        "currencies",
        sa.column("code", sa.String(3)),
        sa.column("name", sa.String(80)),
        sa.column("symbol", sa.String(8)),
        sa.column("decimal_places", sa.SmallInteger),
    )
    op.get_bind().execute(
        insert(currencies)
        .values(
            [
                {
                    "code": "CNY",
                    "name": "Chinese Yuan",
                    "symbol": "¥",
                    "decimal_places": 2,
                },
                {
                    "code": "JPY",
                    "name": "Japanese Yen",
                    "symbol": "¥",
                    "decimal_places": 0,
                },
                {
                    "code": "KRW",
                    "name": "South Korean Won",
                    "symbol": "₩",
                    "decimal_places": 0,
                },
            ]
        )
        .on_conflict_do_nothing(index_elements=["code"])
    )


def downgrade() -> None:
    op.execute("DELETE FROM currencies WHERE code IN ('CNY', 'JPY', 'KRW')")