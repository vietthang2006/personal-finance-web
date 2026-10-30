import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

from fastapi.testclient import TestClient

from app.api.deps import get_current_user, get_db, get_tag_service
from app.main import app
from app.services.tag_service import TagConflictError


class TagApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.user_id = uuid4()
        self.tag_service = Mock()
        self.db = Mock()
        self.previous_overrides = dict(app.dependency_overrides)
        app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=self.user_id)
        app.dependency_overrides[get_tag_service] = lambda: self.tag_service
        app.dependency_overrides[get_db] = lambda: self.db
        self.client = TestClient(app)

    def tearDown(self) -> None:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(self.previous_overrides)

    def test_list_tags(self) -> None:
        self.tag_service.list_tags.return_value = [
            SimpleNamespace(
                id=1,
                user_id=self.user_id,
                name="Coffee",
                color="#A52A2A",
                created_at=datetime(2026, 10, 30, tzinfo=timezone.utc),
            )
        ]

        response = self.client.get("/api/v1/tags")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 1)
        self.assertEqual(response.json()[0]["name"], "Coffee")

    def test_create_tag_conflict(self) -> None:
        self.tag_service.create_tag.side_effect = TagConflictError("Tag already exists")

        response = self.client.post("/api/v1/tags", json={"name": "Coffee", "color": "#A52A2A"})

        self.assertEqual(response.status_code, 409)

    def test_assign_tags_to_transaction(self) -> None:
        tx_id = uuid4()
        self.tag_service.assign_tags.return_value = [
            SimpleNamespace(
                id=1,
                user_id=self.user_id,
                name="Coffee",
                color="#A52A2A",
                created_at=datetime(2026, 10, 30, tzinfo=timezone.utc),
            )
        ]

        response = self.client.post(f"/api/v1/transactions/{tx_id}/tags", json={"tag_ids": [1]})

        self.assertEqual(response.status_code, 200)
        self.tag_service.assign_tags.assert_called_once_with(self.user_id, tx_id, [1])

