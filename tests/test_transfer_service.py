import unittest
from datetime import date, datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

from app.schemas.transfer import TransferCreate
from app.services.transfer_service import (
    TransferService,
    TransferValidationError,
)


class TransferServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.user_id = uuid4()
        self.from_account_id = uuid4()
        self.to_account_id = uuid4()

        self.service = TransferService.__new__(TransferService)
        self.service.db = Mock()
        self.service.transfer_repo = Mock()
        self.service.account_repo = Mock()

        self.from_account = SimpleNamespace(
            id=self.from_account_id,
            user_id=self.user_id,
            currency_code="VND",
            is_archived=False,
            current_balance=Decimal("1000000.00"),
        )
        self.to_account = SimpleNamespace(
            id=self.to_account_id,
            user_id=self.user_id,
            currency_code="VND",
            is_archived=False,
            current_balance=Decimal("500000.00"),
        )

        def mock_get_account(acc_id: object, uid: object) -> object:
            if acc_id == self.from_account_id:
                return self.from_account
            if acc_id == self.to_account_id:
                return self.to_account
            return None

        self.service.account_repo.get_by_id.side_effect = mock_get_account
        self.service.account_repo.update_balance_atomic.return_value = Decimal("900000.00")
        self.service.transfer_repo.get_by_idempotency_key.return_value = None

    def test_create_transfer_same_currency(self) -> None:
        data = TransferCreate(
            from_account_id=self.from_account_id,
            to_account_id=self.to_account_id,
            amount=Decimal("100000.00"),
            transaction_date=date(2026, 10, 30),
            description="Transfer to savings",
        )

        transfer = self.service.create_transfer(self.user_id, data)

        # Debited source, credited target
        self.service.account_repo.update_balance_atomic.assert_any_call(
            self.from_account_id, self.user_id, Decimal("-100000.00")
        )
        self.service.account_repo.update_balance_atomic.assert_any_call(
            self.to_account_id, self.user_id, Decimal("100000.00")
        )
        created = self.service.transfer_repo.create_transfer.call_args.args[0]
        self.assertEqual(created.user_id, self.user_id)
        self.assertEqual(created.amount, Decimal("100000.00"))
        self.assertEqual(created.to_amount, Decimal("100000.00"))
        self.assertEqual(created.exchange_rate, Decimal("1.00000000"))
        self.service.transfer_repo.commit.assert_called_once()
        self.assertIs(transfer, created)

    def test_create_transfer_cross_currency_with_rate(self) -> None:
        self.from_account.currency_code = "USD"
        self.to_account.currency_code = "VND"

        data = TransferCreate(
            from_account_id=self.from_account_id,
            to_account_id=self.to_account_id,
            amount=Decimal("100.00"),
            exchange_rate=Decimal("25400.00000000"),
            transaction_date=date(2026, 10, 30),
        )

        transfer = self.service.create_transfer(self.user_id, data)

        self.service.account_repo.update_balance_atomic.assert_any_call(
            self.from_account_id, self.user_id, Decimal("-100.00")
        )
        self.service.account_repo.update_balance_atomic.assert_any_call(
            self.to_account_id, self.user_id, Decimal("2540000.00")
        )
        created = self.service.transfer_repo.create_transfer.call_args.args[0]
        self.assertEqual(created.to_amount, Decimal("2540000.00"))
        self.assertIs(transfer, created)

    def test_create_transfer_fails_when_source_insufficient(self) -> None:
        self.service.account_repo.update_balance_atomic.return_value = None
        data = TransferCreate(
            from_account_id=self.from_account_id,
            to_account_id=self.to_account_id,
            amount=Decimal("99999999.00"),
            transaction_date=date(2026, 10, 30),
        )

        with self.assertRaises(TransferValidationError) as ctx:
            self.service.create_transfer(self.user_id, data)
        self.assertIn("insufficient funds", str(ctx.exception))
        self.service.transfer_repo.create_transfer.assert_not_called()

    def test_create_transfer_idempotency_returns_cached(self) -> None:
        cached_transfer = SimpleNamespace(
            id=uuid4(),
            user_id=self.user_id,
            idempotency_key="unique_key_123",
        )
        self.service.transfer_repo.get_by_idempotency_key.return_value = cached_transfer

        data = TransferCreate(
            from_account_id=self.from_account_id,
            to_account_id=self.to_account_id,
            amount=Decimal("100000.00"),
            transaction_date=date(2026, 10, 30),
            idempotency_key="unique_key_123",
        )

        result = self.service.create_transfer(self.user_id, data)

        self.assertIs(result, cached_transfer)
        self.service.account_repo.update_balance_atomic.assert_not_called()
        self.service.transfer_repo.create_transfer.assert_not_called()

