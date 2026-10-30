from datetime import datetime, timezone
from types import SimpleNamespace
import unittest
from unittest.mock import Mock
from uuid import uuid4

from fastapi.testclient import TestClient

from app.api.deps import get_current_user, get_db, get_import_service
from app.main import app
from app.services.import_service import ImportConflictError, ImportValidationError


class ImportApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.user_id = uuid4()
        self.import_service = Mock()
        self.db = Mock()
        self.previous_overrides = dict(app.dependency_overrides)
        app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=self.user_id)
        app.dependency_overrides[get_import_service] = lambda: self.import_service
        app.dependency_overrides[get_db] = lambda: self.db
        self.client = TestClient(app)

    def tearDown(self) -> None:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(self.previous_overrides)

    def test_list_batches_api(self) -> None:
        batch_id = uuid4()
        acc_id = uuid4()
        now = datetime.now(timezone.utc)
        self.import_service.list_batches.return_value = [
            SimpleNamespace(
                id=batch_id,
                user_id=self.user_id,
                account_id=acc_id,
                file_name="statement.csv",
                file_hash="abc123hash",
                status="staged",
                total_rows=10,
                valid_rows=8,
                duplicate_rows=2,
                invalid_rows=0,
                imported_rows=0,
                error_message=None,
                created_at=now,
                expires_at=now,
                confirmed_at=None,
            )
        ]

        response = self.client.get("/api/v1/imports/batches")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 1)
        self.assertEqual(response.json()[0]["id"], str(batch_id))
        self.assertEqual(response.json()[0]["file_name"], "statement.csv")

    def test_confirm_batch_api_success(self) -> None:
        batch_id = uuid4()
        self.import_service.confirm_import.return_value = SimpleNamespace(
            id=batch_id,
            status="confirmed",
            imported_rows=5,
        )

        response = self.client.post(
            f"/api/v1/imports/batches/{batch_id}/confirm",
            json={"category_choices": []},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["id"], str(batch_id))
        self.assertEqual(response.json()["status"], "confirmed")
        self.assertEqual(response.json()["imported_rows"], 5)

    def test_confirm_batch_api_conflict(self) -> None:
        batch_id = uuid4()
        self.import_service.confirm_import.side_effect = ImportConflictError(
            "Import batch has already been confirmed"
        )

        response = self.client.post(
            f"/api/v1/imports/batches/{batch_id}/confirm",
            json={"category_choices": []},
        )

        self.assertEqual(response.status_code, 409)

    def test_cancel_batch_api_success(self) -> None:
        batch_id = uuid4()
        self.import_service.cancel_batch.return_value = None

        response = self.client.delete(f"/api/v1/imports/batches/{batch_id}")

        self.assertEqual(response.status_code, 204)
        self.import_service.cancel_batch.assert_called_once_with(self.user_id, batch_id)

