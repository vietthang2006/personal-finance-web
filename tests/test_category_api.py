import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

from fastapi.testclient import TestClient

from app.api.deps import get_category_service, get_current_user, get_db
from app.main import app
from app.services.category_service import CategoryValidationError


class CategoryApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.user_id = uuid4()
        self.category_service = Mock()
        self.db = Mock()
        self.previous_overrides = dict(app.dependency_overrides)
        app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=self.user_id)
        app.dependency_overrides[get_category_service] = lambda: self.category_service
        app.dependency_overrides[get_db] = lambda: self.db
        self.client = TestClient(app)

    def tearDown(self) -> None:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(self.previous_overrides)

    def test_list_categories_returns_system_and_user_categories(self) -> None:
        self.category_service.list_categories.return_value = [
            SimpleNamespace(
                id=1,
                user_id=None,
                code="food",
                name="Ăn uống",
                kind="expense",
                is_active=True,
                created_at=datetime(2026, 10, 30, tzinfo=timezone.utc),
            )
        ]

        response = self.client.get("/api/v1/categories", params={"kind": "expense"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()[0]["code"], "food")
        self.category_service.list_categories.assert_called_once_with(
            self.user_id,
            kind="expense",
            include_inactive=False,
        )

    def test_create_category_returns_created_resource(self) -> None:
        self.category_service.create_category.return_value = SimpleNamespace(
            id=55,
            user_id=self.user_id,
            code="my_food",
            name="Ăn uống",
            kind="expense",
            is_active=True,
            created_at=datetime(2026, 10, 30, tzinfo=timezone.utc),
        )

        response = self.client.post(
            "/api/v1/categories",
            json={"code": "MY_FOOD", "name": "Ăn uống", "kind": "expense"},
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["code"], "my_food")

    def test_system_category_mutation_returns_forbidden(self) -> None:
        self.category_service.update_category.side_effect = CategoryValidationError(
            "System categories cannot be modified"
        )

        response = self.client.patch(
            "/api/v1/categories/1",
            json={"name": "Tên mới"},
        )

        self.assertEqual(response.status_code, 403)
        self.db.rollback.assert_called_once()


if __name__ == "__main__":
    unittest.main()