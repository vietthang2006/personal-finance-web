import unittest
from datetime import date, datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

from fastapi.testclient import TestClient

from app.api.deps import get_current_user, get_db, get_transfer_service
from app.main import app
from app.services.transfer_service import TransferValidationError


class TransferApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.user_id = uuid4()
        self.transfer_service = Mock()
        self.db = Mock()
        self.previous_overrides = dict(app.dependency_overrides)
        app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=self.user_id)
        app.dependency_overrides[get_transfer_service] = lambda: self.transfer_service
        app.dependency_overrides[get_db] = lambda: self.db
        self.client = TestClient(app)

    def tearDown(self) -> None:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(self.previous_overrides)

    def test_create_transfer_api_success(self) -> None:
        from_id = uuid4()
        to_id = uuid4()
        tf_id = uuid4()

        self.transfer_service.create_transfer.return_value = SimpleNamespace(
            id=tf_id,
            user_id=self.user_id,
            from_account_id=from_id,
            to_account_id=to_id,
            amount=Decimal("50000.00"),
            to_amount=Decimal("50000.00"),
            exchange_rate=Decimal("1.00000000"),
            transaction_date=date(2026, 10, 30),
            purpose="internal",
            description="Test transfer",
            idempotency_key=None,
            created_at=datetime(2026, 10, 30, tzinfo=timezone.utc),
        )

        payload = {
            "from_account_id": str(from_id),
            "to_account_id": str(to_id),
            "amount": "50000.00",
            "transaction_date": "2026-10-30",
            "purpose": "internal",
            "description": "Test transfer",
        }
        response = self.client.post("/api/v1/transfers", json=payload)

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["id"], str(tf_id))
        self.assertEqual(response.json()["amount"], "50000.00")
        self.assertEqual(response.json()["purpose"], "internal")

    def test_create_transfer_api_validation_error(self) -> None:
        from_id = uuid4()
        to_id = uuid4()
        self.transfer_service.create_transfer.side_effect = TransferValidationError(
            "Source account has insufficient funds or exceeds credit limit"
        )

        payload = {
            "from_account_id": str(from_id),
            "to_account_id": str(to_id),
            "amount": "99999999.00",
            "transaction_date": "2026-10-30",
        }
        response = self.client.post("/api/v1/transfers", json=payload)

        self.assertEqual(response.status_code, 422)
