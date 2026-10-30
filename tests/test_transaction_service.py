import unittest
from datetime import date, datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

from app.schemas.transaction import TransactionCreate, TransactionUpdate
from app.services.transaction_service import (
    AccountInsufficientFundsError,
    TransactionNotFoundError,
    TransactionService,
    TransactionValidationError,
)


class TransactionServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.user_id = uuid4()
        self.account_id = uuid4()
        self.service = TransactionService.__new__(TransactionService)
        self.service.db = Mock()
        self.service.transaction_repo = Mock()
        self.service.account_repo = Mock()
        self.service.category_repo = Mock()

        # default mock account
        self.account = SimpleNamespace(
            id=self.account_id,
            user_id=self.user_id,
            is_archived=False,
            current_balance=Decimal("1000.00"),
        )
        self.service.account_repo.get_by_id.return_value = self.account
        self.service.account_repo.update_balance_atomic.return_value = Decimal("900.00")

    def test_create_expense_transaction_updates_balance_negatively(self) -> None:
        data = TransactionCreate(
            account_id=self.account_id,
            kind="expense",
            amount=Decimal("100.00"),
            transaction_date=date(2026, 10, 30),
            description="Lunch",
        )

        tx = self.service.create_transaction(self.user_id, data)

        self.service.account_repo.update_balance_atomic.assert_called_once_with(
            self.account_id, self.user_id, Decimal("-100.00")
        )
        created = self.service.transaction_repo.create_transaction.call_args.args[0]
        self.assertEqual(created.user_id, self.user_id)
        self.assertEqual(created.account_id, self.account_id)
        self.assertEqual(created.kind, "expense")
        self.assertEqual(created.amount, Decimal("100.00"))
        self.service.transaction_repo.commit.assert_called_once()
        self.assertIs(tx, created)

    def test_create_transaction_rejects_archived_account(self) -> None:
        self.account.is_archived = True
        data = TransactionCreate(
            account_id=self.account_id,
            kind="expense",
            amount=Decimal("100.00"),
            transaction_date=date(2026, 10, 30),
        )

        with self.assertRaises(TransactionValidationError) as ctx:
            self.service.create_transaction(self.user_id, data)
        self.assertIn("archived", str(ctx.exception))
        self.service.account_repo.update_balance_atomic.assert_not_called()

    def test_create_transaction_raises_when_insufficient_funds(self) -> None:
        self.service.account_repo.update_balance_atomic.return_value = None
        data = TransactionCreate(
            account_id=self.account_id,
            kind="expense",
            amount=Decimal("2000.00"),
            transaction_date=date(2026, 10, 30),
        )

        with self.assertRaises(AccountInsufficientFundsError):
            self.service.create_transaction(self.user_id, data)
        self.service.transaction_repo.create_transaction.assert_not_called()

    def test_create_transaction_validates_category_kind_mismatch(self) -> None:
        self.service.category_repo.get_visible.return_value = SimpleNamespace(
            id=1, kind="income", is_active=True
        )
        data = TransactionCreate(
            account_id=self.account_id,
            kind="expense",
            category_id=1,
            subcategory_id=2,
            amount=Decimal("50.00"),
            transaction_date=date(2026, 10, 30),
        )

        with self.assertRaises(TransactionValidationError):
            self.service.create_transaction(self.user_id, data)
        self.service.account_repo.update_balance_atomic.assert_not_called()

    def test_update_transaction_adjusts_net_balance_delta(self) -> None:
        tx_id = uuid4()
        existing_tx = SimpleNamespace(
            id=tx_id,
            user_id=self.user_id,
            account_id=self.account_id,
            kind="expense",
            amount=Decimal("100.00"),
            category_id=None,
            subcategory_id=None,
            transaction_date=date(2026, 10, 30),
            description="Old",
            merchant=None,
        )
        self.service.transaction_repo.get_by_id.return_value = existing_tx
        self.service.account_repo.update_balance_atomic.return_value = Decimal("850.00")

        # Expense changed from 100 to 150 -> old delta = -100, new delta = -150 -> net delta = -50
        data = TransactionUpdate(amount=Decimal("150.00"))
        updated_tx = self.service.update_transaction(self.user_id, tx_id, data)

        self.service.account_repo.update_balance_atomic.assert_called_once_with(
            self.account_id, self.user_id, Decimal("-50.00")
        )
        self.assertEqual(existing_tx.amount, Decimal("150.00"))
        self.service.transaction_repo.commit.assert_called_once()
        self.assertIs(updated_tx, existing_tx)

    def test_delete_transaction_reverses_balance(self) -> None:
        tx_id = uuid4()
        existing_tx = SimpleNamespace(
            id=tx_id,
            user_id=self.user_id,
            account_id=self.account_id,
            kind="expense",
            amount=Decimal("100.00"),
        )
        self.service.transaction_repo.get_by_id.return_value = existing_tx
        self.service.account_repo.update_balance_atomic.return_value = Decimal("1100.00")

        self.service.delete_transaction(self.user_id, tx_id)

        # Deleting expense reverses by +100.00
        self.service.account_repo.update_balance_atomic.assert_called_once_with(
            self.account_id, self.user_id, Decimal("100.00")
        )
        self.service.transaction_repo.delete_transaction.assert_called_once_with(existing_tx)
        self.service.transaction_repo.commit.assert_called_once()

