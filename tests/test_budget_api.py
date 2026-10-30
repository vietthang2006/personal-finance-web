from datetime import date, datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
import unittest
from unittest.mock import Mock
from uuid import uuid4

from fastapi.testclient import TestClient

from app.api.deps import get_budget_service, get_current_user, get_db
from app.main import app
from app.schemas.budget import (
    BudgetCategoryProgressRead,
    BudgetProgressRead,
)


class BudgetApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.user_id = uuid4()
        self.budget_service = Mock()
        self.db = Mock()
        self.previous_overrides = dict(app.dependency_overrides)
        app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=self.user_id)
        app.dependency_overrides[get_budget_service] = lambda: self.budget_service
        app.dependency_overrides[get_db] = lambda: self.db
        self.client = TestClient(app)

    def tearDown(self) -> None:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(self.previous_overrides)

    def _sample_budget(self, budget_id=None):
        now = datetime.now(timezone.utc)
        return SimpleNamespace(
            id=budget_id or uuid4(),
            user_id=self.user_id,
            name="Ngân sách T11",
            period_type="monthly",
            start_date=date(2026, 11, 1),
            end_date=date(2026, 11, 30),
            total_limit=Decimal("5000000.00"),
            status="active",
            created_at=now,
            updated_at=now,
            categories=[],
        )

    def test_create_budget_api(self) -> None:
        b = self._sample_budget()
        self.budget_service.create_budget.return_value = b

        payload = {
            "name": "Ngân sách T11",
            "period_type": "monthly",
            "start_date": "2026-11-01",
            "end_date": "2026-11-30",
            "total_limit": "5000000.00",
            "categories": [],
        }

        response = self.client.post("/api/v1/budgets", json=payload)
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(data["name"], "Ngân sách T11")
        self.budget_service.create_budget.assert_called_once()

    def test_list_budgets_api(self) -> None:
        b = self._sample_budget()
        self.budget_service.list_budgets.return_value = [b]

        response = self.client.get("/api/v1/budgets")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["id"], str(b.id))

    def test_get_budget_api(self) -> None:
        budget_id = uuid4()
        b = self._sample_budget(budget_id)
        self.budget_service.get_budget.return_value = b

        response = self.client.get(f"/api/v1/budgets/{budget_id}")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["id"], str(budget_id))

    def test_update_budget_api(self) -> None:
        budget_id = uuid4()
        b = self._sample_budget(budget_id)
        b.name = "Ngân sách T11 - Sửa"
        self.budget_service.update_budget.return_value = b

        response = self.client.put(
            f"/api/v1/budgets/{budget_id}",
            json={"name": "Ngân sách T11 - Sửa"},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["name"], "Ngân sách T11 - Sửa")

    def test_delete_budget_api(self) -> None:
        budget_id = uuid4()
        response = self.client.delete(f"/api/v1/budgets/{budget_id}")
        self.assertEqual(response.status_code, 204)
        self.budget_service.delete_budget.assert_called_once_with(self.user_id, budget_id)

    def test_add_category_limit_api(self) -> None:
        budget_id = uuid4()
        bc_id = uuid4()
        self.budget_service.add_category_limit.return_value = SimpleNamespace(
            id=bc_id,
            budget_id=budget_id,
            category_id=1,
            category_kind="expense",
            limit_amount=Decimal("2000000.00"),
            warn_percent=80,
        )

        response = self.client.post(
            f"/api/v1/budgets/{budget_id}/categories",
            json={"category_id": 1, "limit_amount": "2000000.00", "warn_percent": 80},
        )
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(data["category_id"], 1)

    def test_update_category_limit_api(self) -> None:
        budget_id = uuid4()
        bc_id = uuid4()
        self.budget_service.update_category_limit.return_value = SimpleNamespace(
            id=bc_id,
            budget_id=budget_id,
            category_id=1,
            category_kind="expense",
            limit_amount=Decimal("2500000.00"),
            warn_percent=85,
        )

        response = self.client.put(
            f"/api/v1/budgets/{budget_id}/categories/1",
            json={"limit_amount": "2500000.00", "warn_percent": 85},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["limit_amount"], "2500000.00")
        self.assertEqual(data["warn_percent"], 85)

    def test_delete_category_limit_api(self) -> None:
        budget_id = uuid4()
        response = self.client.delete(f"/api/v1/budgets/{budget_id}/categories/1")
        self.assertEqual(response.status_code, 204)
        self.budget_service.delete_category_limit.assert_called_once_with(self.user_id, budget_id, 1)

    def test_get_budget_progress_api(self) -> None:
        budget_id = uuid4()
        self.budget_service.calculate_progress.return_value = BudgetProgressRead(
            budget_id=budget_id,
            name="Ngân sách T11",
            period_type="monthly",
            start_date=date(2026, 11, 1),
            end_date=date(2026, 11, 30),
            total_limit=Decimal("5000000.00"),
            total_spent=Decimal("2500000.00"),
            total_remaining=Decimal("2500000.00"),
            overall_percent_used=Decimal("50.00"),
            categories=[
                BudgetCategoryProgressRead(
                    category_id=1,
                    category_name="Ăn uống",
                    limit_amount=Decimal("2000000.00"),
                    spent_amount=Decimal("1500000.00"),
                    remaining_amount=Decimal("500000.00"),
                    percent_used=Decimal("75.00"),
                    warn_percent=80,
                    is_warning=False,
                    is_exceeded=False,
                )
            ],
        )

        response = self.client.get(f"/api/v1/budgets/{budget_id}/progress")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["total_spent"], "2500000.00")
        self.assertEqual(data["overall_percent_used"], "50.00")

    def test_list_budget_alerts_api(self) -> None:
        budget_id = uuid4()
        alert_id = 1
        now = datetime.now(timezone.utc)
        self.budget_service.list_alerts.return_value = [
            SimpleNamespace(
                id=alert_id,
                budget_category_id=uuid4(),
                level="warning",
                spent_amount=Decimal("1700000.00"),
                percent_used=Decimal("85.00"),
                triggered_at=now,
                notification_id=None,
            )
        ]

        response = self.client.get(f"/api/v1/budgets/{budget_id}/alerts")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["level"], "warning")

