from datetime import date, datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
import unittest
from unittest.mock import Mock
from uuid import uuid4

from app.schemas.account import AccountCreate, AccountUpdate
from app.services.account_service import (
    AccountConflictError,
    AccountNotFoundError,
    AccountService,
    AccountValidationError,
)


class AccountServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.user_id = uuid4()
        self.account_id = uuid4()
        self.account = SimpleNamespace(
            id=self.account_id,
            user_id=self.user_id,
            name="Ví Tiền Mặt",
            kind="cash",
            currency_code="VND",
            bank_name=None,
            opening_balance=Decimal("500000.00"),
            current_balance=Decimal("500000.00"),
            allow_negative=False,
            credit_limit=None,
            billing_day=None,
            due_day=None,
            is_archived=False,
        )

        self.service = AccountService.__new__(AccountService)
        self.service.db = Mock()
        self.service.account_repo = Mock()
        self.service.history_repo = Mock()
        self.service.currency_repo = Mock()

        self.service.currency_repo.exists.return_value = True
        self.service.account_repo.exists_by_name.return_value = False
        self.service.account_repo.get_by_id.return_value = self.account

    def test_create_account_success(self) -> None:
        payload = AccountCreate(
            name="Ví Mới",
            kind="cash",
            currency_code="VND",
            opening_balance=Decimal("100000"),
        )
        created = self.service.create_account(self.user_id, payload)
        self.service.account_repo.create.assert_called_once()
        self.service.account_repo.commit.assert_called_once()
        self.assertEqual(created.name, "Ví Mới")
        self.assertEqual(created.kind, "cash")
        self.assertEqual(created.currency_code, "VND")

    def test_create_account_unsupported_currency(self) -> None:
        self.service.currency_repo.exists.return_value = False
        payload = AccountCreate(
            name="Ví Ngoại Tệ",
            kind="cash",
            currency_code="XYZ",
        )
        with self.assertRaises(AccountValidationError):
            self.service.create_account(self.user_id, payload)
        self.service.account_repo.create.assert_not_called()

    def test_create_account_duplicate_name(self) -> None:
        self.service.account_repo.exists_by_name.return_value = True
        payload = AccountCreate(
            name="Ví Tiền Mặt",
            kind="cash",
            currency_code="VND",
        )
        with self.assertRaises(AccountConflictError):
            self.service.create_account(self.user_id, payload)
        self.service.account_repo.create.assert_not_called()

    def test_get_account_not_found(self) -> None:
        self.service.account_repo.get_by_id.return_value = None
        with self.assertRaises(AccountNotFoundError):
            self.service.get_account(self.user_id, uuid4())

    def test_update_account_name_conflict(self) -> None:
        self.service.account_repo.exists_by_name.return_value = True
        update_data = AccountUpdate(name="Tên Đã Có")
        with self.assertRaises(AccountConflictError):
            self.service.update_account(self.user_id, self.account_id, update_data)

    def test_credit_limit_cannot_be_lower_than_current_card_debt(self) -> None:
        self.account.kind = "credit_card"
        self.account.current_balance = Decimal("-50000.00")
        self.account.credit_limit = Decimal("100000.00")

        with self.assertRaises(AccountValidationError):
            self.service.update_account(
                self.user_id,
                self.account_id,
                AccountUpdate(credit_limit=Decimal("40000.00")),
            )

        self.service.account_repo.update.assert_not_called()
        self.service.account_repo.commit.assert_not_called()

    def test_archive_and_unarchive_account(self) -> None:
        self.service.archive_account(self.user_id, self.account_id)
        self.service.account_repo.archive.assert_called_once_with(self.account)

        self.service.unarchive_account(self.user_id, self.account_id)
        self.service.account_repo.unarchive.assert_called_once_with(self.account)

    def test_take_snapshot(self) -> None:
        test_date = date(2026, 10, 30)
        self.service.take_snapshot(self.user_id, self.account_id, snapshot_date=test_date)
        self.service.history_repo.upsert_snapshot.assert_called_once_with(
            self.account_id, test_date, Decimal("500000.00")
        )
        self.service.account_repo.commit.assert_called_once()


if __name__ == "__main__":
    unittest.main()
