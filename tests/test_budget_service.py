from datetime import date, datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, call
from uuid import uuid4

from fastapi import HTTPException

from app.models.budget import Budget, BudgetAlertEvent, BudgetCategory
from app.schemas.budget import (
    BudgetCategoryCreate,
    BudgetCategoryUpdate,
    BudgetCreate,
    BudgetUpdate,
)
from app.services.budget_service import BudgetService


class BudgetServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.user_id = uuid4()
        self.db = Mock()
        self.budget_repo = Mock()
        self.category_repo = Mock()
        self.service = BudgetService(
            db=self.db,
            budget_repo=self.budget_repo,
            category_repo=self.category_repo,
        )

    def test_create_budget_success(self) -> None:
        cat_id = 1
        self.category_repo.get_visible.return_value = SimpleNamespace(
            id=cat_id,
            name="Ăn uống",
            kind="expense",
        )
        self.budget_repo.get_budget.side_effect = lambda b_id, u_id: SimpleNamespace(
            id=b_id,
            user_id=u_id,
            name="Ngân sách T11",
            period_type="monthly",
            start_date=date(2026, 11, 1),
            end_date=date(2026, 11, 30),
            total_limit=Decimal("5000000.00"),
            status="active",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            categories=[],
        )

        payload = BudgetCreate(
            name="Ngân sách T11",
            period_type="monthly",
            start_date=date(2026, 11, 1),
            end_date=date(2026, 11, 30),
            total_limit=Decimal("5000000.00"),
            categories=[
                BudgetCategoryCreate(
                    category_id=cat_id,
                    limit_amount=Decimal("3000000.00"),
                    warn_percent=80,
                )
            ],
        )

        result = self.service.create_budget(self.user_id, payload)
        self.assertEqual(result.name, "Ngân sách T11")
        self.budget_repo.create_budget.assert_called_once()
        self.budget_repo.add_budget_category.assert_called_once()
        self.db.commit.assert_called_once()

    def test_create_budget_rejects_category_limits_exceeding_total(self) -> None:
        self.category_repo.get_visible.return_value = SimpleNamespace(id=1, kind="expense")

        payload = BudgetCreate(
            name="Ngân sách",
            period_type="monthly",
            start_date=date(2026, 11, 1),
            end_date=date(2026, 11, 30),
            total_limit=Decimal("5000000.00"),
            categories=[
                BudgetCategoryCreate(
                    category_id=1,
                    limit_amount=Decimal("6000000.00"),
                    warn_percent=80,
                )
            ],
        )

        with self.assertRaises(HTTPException) as ctx:
            self.service.create_budget(self.user_id, payload)
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("cannot exceed budget total_limit", ctx.exception.detail)

    def test_create_budget_rejects_non_expense_category(self) -> None:
        self.category_repo.get_visible.return_value = SimpleNamespace(id=2, kind="income")

        payload = BudgetCreate(
            name="Ngân sách",
            period_type="monthly",
            start_date=date(2026, 11, 1),
            end_date=date(2026, 11, 30),
            total_limit=Decimal("5000000.00"),
            categories=[
                BudgetCategoryCreate(
                    category_id=2,
                    limit_amount=Decimal("1000000.00"),
                    warn_percent=80,
                )
            ],
        )

        with self.assertRaises(HTTPException) as ctx:
            self.service.create_budget(self.user_id, payload)
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("not an expense category", ctx.exception.detail)

    def test_create_budget_rejects_duplicate_category(self) -> None:
        self.category_repo.get_visible.return_value = SimpleNamespace(id=1, kind="expense")

        payload = BudgetCreate(
            name="Ngân sách",
            period_type="monthly",
            start_date=date(2026, 11, 1),
            end_date=date(2026, 11, 30),
            total_limit=Decimal("5000000.00"),
            categories=[
                BudgetCategoryCreate(category_id=1, limit_amount=Decimal("1000000.00")),
                BudgetCategoryCreate(category_id=1, limit_amount=Decimal("2000000.00")),
            ],
        )

        with self.assertRaises(HTTPException) as ctx:
            self.service.create_budget(self.user_id, payload)
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("Duplicate category_id", ctx.exception.detail)

    def test_get_budget_not_found(self) -> None:
        self.budget_repo.get_budget.return_value = None
        with self.assertRaises(HTTPException) as ctx:
            self.service.get_budget(self.user_id, uuid4())
        self.assertEqual(ctx.exception.status_code, 404)

    def test_update_budget_rejects_lower_total_than_allocated(self) -> None:
        budget_id = uuid4()
        existing_cat = SimpleNamespace(limit_amount=Decimal("3000000.00"))
        budget = SimpleNamespace(
            id=budget_id,
            user_id=self.user_id,
            start_date=date(2026, 11, 1),
            end_date=date(2026, 11, 30),
            total_limit=Decimal("5000000.00"),
            categories=[existing_cat],
        )
        self.budget_repo.get_budget.return_value = budget

        payload = BudgetUpdate(total_limit=Decimal("2000000.00"))
        with self.assertRaises(HTTPException) as ctx:
            self.service.update_budget(self.user_id, budget_id, payload)
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("less than current category allocations", ctx.exception.detail)

    def test_add_category_limit_exceeding_budget_total(self) -> None:
        budget_id = uuid4()
        existing_cat = SimpleNamespace(category_id=1, limit_amount=Decimal("4000000.00"))
        budget = SimpleNamespace(
            id=budget_id,
            user_id=self.user_id,
            total_limit=Decimal("5000000.00"),
            categories=[existing_cat],
        )
        self.budget_repo.get_budget.return_value = budget
        self.category_repo.get_visible.return_value = SimpleNamespace(id=2, kind="expense")
        self.budget_repo.get_budget_category_by_category_id.return_value = None

        payload = BudgetCategoryCreate(category_id=2, limit_amount=Decimal("2000000.00"))
        with self.assertRaises(HTTPException) as ctx:
            self.service.add_category_limit(self.user_id, budget_id, payload)
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("exceeds budget total_limit", ctx.exception.detail)

    def test_calculate_progress_and_triggers_warning_and_exceeded(self) -> None:
        budget_id = uuid4()
        cat1_id = uuid4()
        cat2_id = uuid4()

        bc1 = SimpleNamespace(
            id=cat1_id,
            category_id=1,
            limit_amount=Decimal("1000000.00"),
            warn_percent=80,
            category=SimpleNamespace(name="Ăn uống"),
        )
        bc2 = SimpleNamespace(
            id=cat2_id,
            category_id=2,
            limit_amount=Decimal("2000000.00"),
            warn_percent=80,
            category=SimpleNamespace(name="Di chuyển"),
        )

        budget = SimpleNamespace(
            id=budget_id,
            user_id=self.user_id,
            name="Ngân sách T11",
            period_type="monthly",
            start_date=date(2026, 11, 1),
            end_date=date(2026, 11, 30),
            total_limit=Decimal("5000000.00"),
            categories=[bc1, bc2],
        )
        self.budget_repo.get_budget.return_value = budget

        # Cat 1 spent 850,000 (85%) -> warning triggered
        # Cat 2 spent 2,100,000 (105%) -> warning & exceeded triggered
        def mock_spent(user_id, category_id, start_date, end_date):
            if category_id == 1:
                return Decimal("850000.00")
            return Decimal("2100000.00")

        self.budget_repo.get_spent_amount_by_category.side_effect = mock_spent
        self.budget_repo.get_total_spent_for_budget.return_value = Decimal("2950000.00")
        self.budget_repo.get_alert_event.return_value = None  # No prior alerts

        progress = self.service.calculate_progress(self.user_id, budget_id)

        self.assertEqual(progress.total_spent, Decimal("2950000.00"))
        self.assertEqual(progress.total_remaining, Decimal("2050000.00"))
        self.assertEqual(progress.overall_percent_used, Decimal("59.00"))

        self.assertEqual(len(progress.categories), 2)
        # Cat 1: 85% is warning, not exceeded
        self.assertTrue(progress.categories[0].is_warning)
        self.assertFalse(progress.categories[0].is_exceeded)

        # Cat 2: 105% is exceeded
        self.assertTrue(progress.categories[1].is_exceeded)

        # Verify alert events were created: Cat 1 (warning), Cat 2 (warning & exceeded) = 3 alerts
        self.assertEqual(self.budget_repo.create_alert_event.call_count, 3)
        self.db.commit.assert_called()
