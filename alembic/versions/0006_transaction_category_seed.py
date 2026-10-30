"""Seed default transaction categories and subcategories.

Revision ID: 0006_transaction_category_seed
Revises: 0005_accounts_schema_update
Create Date: 2026-10-30
"""

import sqlalchemy as sa
from alembic import op


revision = "0006_transaction_category_seed"
down_revision = "0005_accounts_schema_update"
branch_labels = None
depends_on = None


DEFAULT_CATEGORIES = (
    ("income", "salary", "Lương", ("Lương chính", "Thưởng")),
    ("income", "business", "Kinh doanh", ("Bán hàng", "Dịch vụ")),
    ("income", "investment", "Đầu tư", ("Cổ tức", "Lãi tiết kiệm")),
    ("income", "gift", "Quà tặng", ("Quà tặng", "Trợ cấp")),
    ("income", "other_income", "Thu nhập khác", ("Khác",)),
    ("expense", "food", "Ăn uống", ("Ăn ngoài", "Đi chợ", "Cà phê")),
    ("expense", "transport", "Di chuyển", ("Xăng xe", "Phương tiện công cộng", "Taxi")),
    ("expense", "housing", "Nhà ở", ("Tiền thuê", "Điện nước", "Sửa chữa")),
    ("expense", "shopping", "Mua sắm", ("Quần áo", "Đồ gia dụng")),
    ("expense", "health", "Sức khỏe", ("Khám chữa bệnh", "Thuốc")),
    ("expense", "education", "Giáo dục", ("Học phí", "Sách vở")),
    ("expense", "entertainment", "Giải trí", ("Phim ảnh", "Sở thích")),
    ("expense", "bills", "Hóa đơn", ("Điện", "Nước", "Internet")),
    ("expense", "other_expense", "Chi tiêu khác", ("Khác",)),
)


def upgrade() -> None:
    op.create_index(
        "uq_transaction_categories_system_code_kind",
        "transaction_categories",
        ["code", "kind"],
        unique=True,
        postgresql_where=sa.text("user_id IS NULL"),
    )
    op.create_index(
        "uq_transaction_categories_user_code_kind",
        "transaction_categories",
        ["user_id", "code", "kind"],
        unique=True,
        postgresql_where=sa.text("user_id IS NOT NULL"),
    )
    op.create_unique_constraint(
        "uq_transaction_subcategories_category_name",
        "transaction_subcategories",
        ["category_id", "name"],
    )

    bind = op.get_bind()
    for kind, code, name, subcategory_names in DEFAULT_CATEGORIES:
        category_id = bind.execute(
            sa.text(
                """
                SELECT id FROM transaction_categories
                WHERE user_id IS NULL AND code = :code AND kind = :kind
                """
            ),
            {"code": code, "kind": kind},
        ).scalar_one_or_none()
        if category_id is None:
            category_id = bind.execute(
                sa.text(
                    """
                    INSERT INTO transaction_categories (user_id, code, name, kind, is_active)
                    VALUES (NULL, :code, :name, :kind, TRUE)
                    RETURNING id
                    """
                ),
                {"code": code, "name": name, "kind": kind},
            ).scalar_one()

        for subcategory_name in subcategory_names:
            bind.execute(
                sa.text(
                    """
                    INSERT INTO transaction_subcategories (category_id, name, is_active)
                    SELECT :category_id, CAST(:name AS varchar(80)), TRUE
                    WHERE NOT EXISTS (
                        SELECT 1 FROM transaction_subcategories
                        WHERE category_id = :category_id AND name = :name
                    )
                    """
                ),
                {"category_id": category_id, "name": subcategory_name},
            )


def downgrade() -> None:
    op.drop_constraint(
        "uq_transaction_subcategories_category_name",
        "transaction_subcategories",
        type_="unique",
    )
    op.drop_index(
        "uq_transaction_categories_user_code_kind",
        table_name="transaction_categories",
    )
    op.drop_index(
        "uq_transaction_categories_system_code_kind",
        table_name="transaction_categories",
    )