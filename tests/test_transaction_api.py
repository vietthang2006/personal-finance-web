import unittest
from datetime import date, datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

from fastapi.testclient import TestClient

from app.api.deps import get_current_user, get_db, get_transaction_service
from app.main import app
from app.services.transaction_service import (
    AccountInsufficientFundsError,
    TransactionNotFoundError,
    TransactionValidationError,
)


class TransactionApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.user_id = uuid4()
        self.transaction_service = Mock()
        self.db = Mock()
        self.previous_overrides = dict(app.dependency_overrides)
        app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=self.user_id)
        app.dependency_overrides[get_transaction_service] = lambda: self.transaction_service
        app.dependency_overrides[get_db] = lambda: self.db
        self.client = TestClient(app)

    def tearDown(self) -> None:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(self.previous_overrides)

    def test_list_transactions_delegates_to_service(self) -> None:
        tx_id = uuid4()
        acc_id = uuid4()
        self.transaction_service.list_transactions.return_value = [
            SimpleNamespace(
                id=tx_id,
                account_id=acc_id,
                kind="income",
                category_id=None,
                subcategory_id=None,
                amount=Decimal("500.00"),
                transaction_date=date(2026, 10, 30),
                description="Salary bonus",
                merchant=None,
                source="manual",
                created_at=datetime(2026, 10, 30, tzinfo=timezone.utc),
            )
        ]

        response = self.client.get("/api/v1/transactions", params={"kind": "income"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 1)
        self.assertEqual(response.json()[0]["id"], str(tx_id))
        self.transaction_service.list_transactions.assert_called_once()

    def test_create_transaction_returns_created(self) -> None:
        tx_id = uuid4()
        acc_id = uuid4()
        self.transaction_service.create_transaction.return_value = SimpleNamespace(
            id=tx_id,
            account_id=acc_id,
            kind="expense",
            category_id=None,
            subcategory_id=None,
            amount=Decimal("150.00"),
            transaction_date=date(2026, 10, 30),
            description="Dinner",
            merchant="Restaurant",
            source="manual",
            created_at=datetime(2026, 10, 30, tzinfo=timezone.utc),
        )

        payload = {
            "account_id": str(acc_id),
            "kind": "expense",
            "amount": "150.00",
            "transaction_date": "2026-10-30",
            "description": "Dinner",
            "merchant": "Restaurant",
        }
        response = self.client.post("/api/v1/transactions", json=payload)

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["id"], str(tx_id))

    def test_create_transaction_insufficient_funds_returns_409(self) -> None:
        acc_id = uuid4()
        self.transaction_service.create_transaction.side_effect = AccountInsufficientFundsError(
            "Transaction would exceed the account's available balance or credit limit"
        )

        payload = {
            "account_id": str(acc_id),
            "kind": "expense",
            "amount": "99999.00",
            "transaction_date": "2026-10-30",
        }
        response = self.client.post("/api/v1/transactions", json=payload)

        self.assertEqual(response.status_code, 409)

    def test_delete_transaction_returns_204(self) -> None:
        tx_id = uuid4()
        self.transaction_service.delete_transaction.return_value = None

        response = self.client.delete(f"/api/v1/transactions/{tx_id}")

        self.assertEqual(response.status_code, 204)
        self.transaction_service.delete_transaction.assert_called_once_with(self.user_id, tx_id)

