"""Create the initial personal finance schema.

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-10-15
"""

from alembic import op

from app.core.database import Base
import app.models


revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS btree_gist")
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)
    op.bulk_insert(
        Base.metadata.tables["currencies"],
        [
            {"code": "VND", "name": "Vietnamese Dong", "symbol": "₫", "decimal_places": 0},
            {"code": "USD", "name": "US Dollar", "symbol": "$", "decimal_places": 2},
            {"code": "EUR", "name": "Euro", "symbol": "€", "decimal_places": 2},
            {"code": "GBP", "name": "British Pound", "symbol": "£", "decimal_places": 2},
        ],
    )
    op.bulk_insert(
        Base.metadata.tables["roles"],
        [
            {"id": 1, "code": "user", "name": "User"},
            {"id": 2, "code": "admin", "name": "Administrator"},
        ],
    )


def downgrade() -> None:
    Base.metadata.drop_all(bind=op.get_bind(), checkfirst=False)
