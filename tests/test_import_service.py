from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
from uuid import uuid4

from app.schemas.import_batch import ImportCategoryChoice
from app.services.import_service import (
    ImportConflictError,
    ImportNotFoundError,
    ImportService,
    ImportValidationError,
)


class ImportServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.user_id = uuid4()
        self.account_id = uuid4()
        self.service = ImportService.__new__(ImportService)
        self.service.db = Mock()
        self.service.import_repo = Mock()
        self.service.account_repo = Mock()
        self.service.transaction_repo = Mock()
        self.service.category_repo = Mock()

        self.account = SimpleNamespace(
            id=self.account_id,
            user_id=self.user_id,
            is_archived=False,
            current_balance=Decimal("1000000.00"),
        )
        self.service.account_repo.get_by_id.return_value = self.account
        self.service.import_repo.get_confirmed_by_hash.return_value = None
        self.service.db.scalars.return_value.all.return_value = []

    def test_preview_import_csv_success(self) -> None:
        csv_data = (
            "transaction_date,kind,amount,description,merchant\n"
            "2026-10-30,expense,50000.00,Lunch,Pho 24\n"
            "2026-10-31,income,200000.00,Freelance,Client A\n"
        ).encode("utf-8")

        batch, rows = self.service.preview_import(
            user_id=self.user_id,
            account_id=self.account_id,
            filename="statement.csv",
            content=csv_data,
        )

        self.assertEqual(batch.total_rows, 2)
        self.assertEqual(batch.valid_rows, 2)
        self.assertEqual(batch.duplicate_rows, 0)
        self.assertEqual(batch.invalid_rows, 0)
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0].status, "valid")
        self.assertEqual(rows[0].amount, Decimal("50000.00"))
        self.assertEqual(rows[1].kind, "income")
        self.service.import_repo.commit.assert_called_once()

    def test_preview_import_rejects_empty_file(self) -> None:
        with self.assertRaises(ImportValidationError):
            self.service.preview_import(
                user_id=self.user_id,
                account_id=self.account_id,
                filename="empty.csv",
                content=b"",
            )

    def test_preview_import_rejects_duplicate_confirmed_file(self) -> None:
        self.service.import_repo.get_confirmed_by_hash.return_value = SimpleNamespace(id=uuid4())

        csv_data = "transaction_date,kind,amount\n2026-10-30,expense,100.00\n".encode("utf-8")
        with self.assertRaises(ImportConflictError):
            self.service.preview_import(
                user_id=self.user_id,
                account_id=self.account_id,
                filename="duplicate.csv",
                content=csv_data,
            )

    def test_confirm_import_updates_balance_and_creates_transactions(self) -> None:
        batch_id = uuid4()
        now = datetime.now(timezone.utc)
        batch = SimpleNamespace(
            id=batch_id,
            user_id=self.user_id,
            account_id=self.account_id,
            file_hash="dummy_hash",
            status="staged",
            expires_at=now + timedelta(hours=10),
            imported_rows=0,
            confirmed_at=None,
        )
        self.service.import_repo.get_batch.return_value = batch

        row_1 = SimpleNamespace(
            id=uuid4(),
            batch_id=batch_id,
            row_number=1,
            status="valid",
            kind="expense",
            amount=Decimal("50000.00"),
            tx_date=date(2026, 10, 30),
            description="Lunch",
            merchant="Restaurant",
            dedup_hash="hash1",
            chosen_category_id=None,
            transaction_id=None,
        )
        row_2 = SimpleNamespace(
            id=uuid4(),
            batch_id=batch_id,
            row_number=2,
            status="duplicate",
            kind="expense",
            amount=Decimal("10000.00"),
            tx_date=date(2026, 10, 30),
            description="Coffee",
            merchant=None,
            dedup_hash="hash2",
            chosen_category_id=None,
            transaction_id=None,
        )
        self.service.import_repo.list_rows.return_value = [row_1, row_2]
        self.service.account_repo.update_balance_atomic.return_value = Decimal("950000.00")

        confirmed_batch = self.service.confirm_import(
            user_id=self.user_id,
            batch_id=batch_id,
            category_choices=[],
        )

        self.assertEqual(confirmed_batch.status, "confirmed")
        self.assertEqual(confirmed_batch.imported_rows, 1)
        # Atomically debited 50000.00
        self.service.account_repo.update_balance_atomic.assert_called_once_with(
            self.account_id, self.user_id, Decimal("-50000.00")
        )
        self.assertEqual(row_1.status, "imported")
        self.service.import_repo.commit.assert_called_once()

    def test_confirm_import_rejects_expired_batch(self) -> None:
        batch_id = uuid4()
        now = datetime.now(timezone.utc)
        batch = SimpleNamespace(
            id=batch_id,
            user_id=self.user_id,
            account_id=self.account_id,
            file_hash="dummy_hash",
            status="staged",
            expires_at=now - timedelta(minutes=5),  # expired
        )
        self.service.import_repo.get_batch.return_value = batch

        with self.assertRaises(ImportValidationError) as ctx:
            self.service.confirm_import(
                user_id=self.user_id,
                batch_id=batch_id,
                category_choices=[],
            )
        self.assertIn("expired", str(ctx.exception))
        self.assertEqual(batch.status, "expired")
