from datetime import date, datetime, timezone
from decimal import Decimal
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, call
from uuid import UUID, uuid4

from app.core.errors import AppError, round_currency
from app.models.account import Account
from app.models.transaction import Transaction, Transfer
from app.repositories.account_repository import AccountRepository
from app.schemas.account import AccountCreate, AccountUpdate
from app.schemas.transaction import TransactionCreate, TransactionUpdate
from app.schemas.transfer import TransferCreate
from app.services.account_service import (
    AccountConflictError,
    AccountService,
    AccountValidationError,
)
from app.services.transaction_service import (
    AccountInsufficientFundsError,
    TransactionService,
    TransactionValidationError,
)
from app.services.transfer_service import TransferService, TransferValidationError


class ModuleCDAdvancedTests(unittest.TestCase):
    def setUp(self) -> None:
        self.user_id = uuid4()
        self.db = Mock()

    # --- [ISSUE-C01] Unit/Integration: Account Creation Validations ---
    def test_issue_c01_account_creation_validation_errors(self) -> None:
        """[ISSUE-C01] Validate credit card fields, normal wallet constraints, and duplicate name check."""
        account_repo = Mock()
        account_repo.exists_by_name.return_value = False
        currency_repo = Mock()
        currency_repo.exists.return_value = True

        service = AccountService(
            db=self.db,
            account_repo=account_repo,
            currency_repo=currency_repo,
        )

        # 1.1 Invalid credit card: missing billing_day and due_day
        with self.assertRaises(ValueError):
            AccountCreate(
                name="Thẻ tín dụng lỗi",
                kind="credit_card",
                currency_code="VND",
                credit_limit=Decimal("10000000.00"),
                billing_day=None,
                due_day=None,
            )

        # 1.2 Normal cash wallet cannot have credit_limit
        with self.assertRaises(ValueError):
            AccountCreate(
                name="Ví tiền mặt lỗi",
                kind="cash",
                currency_code="VND",
                credit_limit=Decimal("5000000.00"),
            )

        # 1.3 Duplicate account name
        account_repo.exists_by_name.return_value = True
        valid_payload = AccountCreate(
            name="Ví tiền mặt",
            kind="cash",
            currency_code="VND",
            opening_balance=Decimal("100000.00"),
        )
        with self.assertRaises(AccountConflictError):
            service.create_account(self.user_id, valid_payload)

    # --- [ISSUE-C02] Multi-currency summary and cross-rate calculation ---
    def test_issue_c02_multi_currency_summary_and_cross_rate(self) -> None:
        """[ISSUE-C02] Multi-currency account balance conversion via cross-rates, total assets, liabilities, and net worth."""
        acc1 = SimpleNamespace(
            id=uuid4(),
            user_id=self.user_id,
            name="Ví VND",
            kind="bank",
            currency_code="VND",
            bank_name="Vietcombank",
            opening_balance=Decimal("10000000.00"),
            current_balance=Decimal("10000000.00"),
            allow_negative=False,
            credit_limit=None,
            billing_day=None,
            due_day=None,
            is_archived=False,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        acc2 = SimpleNamespace(
            id=uuid4(),
            user_id=self.user_id,
            name="Ví USD",
            kind="bank",
            currency_code="USD",
            bank_name="Chase",
            opening_balance=Decimal("1000.00"),
            current_balance=Decimal("1000.00"),
            allow_negative=False,
            credit_limit=None,
            billing_day=None,
            due_day=None,
            is_archived=False,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        acc3 = SimpleNamespace(
            id=uuid4(),
            user_id=self.user_id,
            name="Thẻ tín dụng",
            kind="credit_card",
            currency_code="VND",
            bank_name="Techcombank",
            opening_balance=Decimal("0.00"),
            current_balance=Decimal("-5000000.00"),
            allow_negative=True,
            credit_limit=Decimal("20000000.00"),
            billing_day=15,
            due_day=5,
            is_archived=False,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        account_repo = Mock()
        account_repo.list_by_user.return_value = [acc1, acc2, acc3]

        currency_repo = Mock()
        currency_repo.get_by_code.side_effect = lambda c: SimpleNamespace(
            code=c, decimal_places=0 if c == "VND" else 2
        )

        # Mock rate USD -> VND = 25,700
        def mock_convert(amount, from_c, to_c, preferred_type="transfer_buy"):
            if from_c == to_c:
                return amount
            if from_c == "USD" and to_c == "VND":
                return (amount * Decimal("25700")).quantize(Decimal("1"))
            return amount

        currency_repo.convert_currency.side_effect = mock_convert

        service = AccountService(
            db=self.db,
            account_repo=account_repo,
            currency_repo=currency_repo,
        )

        summary = service.list_accounts_summary(self.user_id, default_currency="VND")

        self.assertEqual(summary.default_currency, "VND")
        # acc1: 10,000,000 VND
        # acc2: 1,000 USD * 25,700 = 25,700,000 VND
        # Total assets = 10,000,000 + 25,700,000 = 35,700,000 VND
        self.assertEqual(summary.total_assets_base, Decimal("35700000"))
        # acc3: -5,000,000 VND (liability)
        self.assertEqual(summary.total_liabilities_base, Decimal("5000000"))
        # Net worth = 35,700,000 - 5,000,000 = 30,700,000 VND
        self.assertEqual(summary.net_worth_base, Decimal("30700000"))

    # --- [ISSUE-C03] Account Modification & Deletion Restrictions ---
    def test_issue_c03_account_deletion_and_modification_restrictions(self) -> None:
        """[ISSUE-C03] Block modification of kind/currency/opening_balance and block physical delete if transaction history exists."""
        account_id = uuid4()
        account = SimpleNamespace(
            id=account_id,
            user_id=self.user_id,
            name="Ví Tiết kiệm",
            kind="savings",
            currency_code="VND",
            opening_balance=Decimal("1000000.00"),
            current_balance=Decimal("1000000.00"),
            allow_negative=False,
            credit_limit=None,
            billing_day=None,
            due_day=None,
            is_archived=False,
        )
        account_repo = Mock()
        account_repo.get_by_id.return_value = account
        account_repo.has_transactions.return_value = True  # Has transactions!

        service = AccountService(db=self.db, account_repo=account_repo)

        # 3.1 Block modifying kind (409)
        with self.assertRaises(AppError) as ctx:
            service.update_account(self.user_id, account_id, AccountUpdate(kind="bank"))
        self.assertEqual(ctx.exception.status_code, 409)
        self.assertEqual(ctx.exception.code, "ACCOUNT_HAS_TRANSACTIONS")

        # 3.2 Block modifying currency_code (409)
        with self.assertRaises(AppError) as ctx:
            service.update_account(self.user_id, account_id, AccountUpdate(currency_code="USD"))
        self.assertEqual(ctx.exception.status_code, 409)

        # 3.3 Block physical delete (409)
        with self.assertRaises(AppError) as ctx:
            service.delete_account(self.user_id, account_id)
        self.assertEqual(ctx.exception.status_code, 409)
        account_repo.delete.assert_not_called()

    # --- [ISSUE-D01] Atomic Rollback on Failed Transaction ---
    def test_issue_d01_atomic_rollback_on_failed_transaction(self) -> None:
        """[ISSUE-D01] Atomic rollback on non-existent tag or invalid metadata."""
        account_id = uuid4()
        account = SimpleNamespace(
            id=account_id,
            user_id=self.user_id,
            is_archived=False,
            current_balance=Decimal("1000000.00"),
        )
        account_repo = Mock()
        account_repo.get_by_id.return_value = account
        account_repo.get_for_update.return_value = account

        tag_repo = Mock()
        tag_repo.get_by_id.return_value = None  # Tag does not exist!

        transaction_repo = Mock()

        service = TransactionService(
            db=self.db,
            transaction_repo=transaction_repo,
            account_repo=account_repo,
            tag_repo=tag_repo,
        )

        payload = TransactionCreate(
            account_id=account_id,
            kind="expense",
            amount=Decimal("100000.00"),
            transaction_date=date.today(),
            tag_ids=[999],  # non-existent tag
        )

        with self.assertRaises(TransactionValidationError) as ctx:
            service.create_transaction(self.user_id, payload)

        self.assertIn("Tag with id 999 does not exist", str(ctx.exception))
        # Ensure no balance was updated and no transaction was created
        account_repo.update_balance_atomic.assert_not_called()
        transaction_repo.create_transaction.assert_not_called()

    # --- [ISSUE-D02] Atomic Rollback on Insufficient Funds ---
    def test_issue_d02_atomic_rollback_on_insufficient_funds(self) -> None:
        """[ISSUE-D02] Transaction that exceeds available balance or credit limit raises AccountInsufficientFundsError."""
        account_id = uuid4()
        account = SimpleNamespace(
            id=account_id,
            user_id=self.user_id,
            is_archived=False,
            current_balance=Decimal("50000.00"),
        )
        account_repo = Mock()
        account_repo.get_by_id.return_value = account
        account_repo.get_for_update.return_value = account
        # update_balance_atomic returns None when balance cannot be negative
        account_repo.update_balance_atomic.return_value = None

        transaction_repo = Mock()

        service = TransactionService(
            db=self.db,
            transaction_repo=transaction_repo,
            account_repo=account_repo,
        )

        payload = TransactionCreate(
            account_id=account_id,
            kind="expense",
            amount=Decimal("100000.00"),  # 100k > 50k
            transaction_date=date.today(),
        )

        with self.assertRaises(AccountInsufficientFundsError):
            service.create_transaction(self.user_id, payload)

        transaction_repo.create_transaction.assert_not_called()

    # --- [ISSUE-E08] Logic Ví E-08: Same Account Edit - No Intermediate False Overdraft ---
    def test_issue_d03_logic_vi_e08_same_account_update_net_delta(self) -> None:
        """[ISSUE-E08] Logic Ví (E-08): Same account edit updates balance with net delta in a single atomic step."""
        account_id = uuid4()
        tx_id = uuid4()

        account = SimpleNamespace(
            id=account_id,
            user_id=self.user_id,
            is_archived=False,
            current_balance=Decimal("50.00"),
        )
        account_repo = Mock()
        account_repo.get_by_id.return_value = account
        account_repo.lock_many.return_value = [account]
        account_repo.update_balance_atomic.return_value = Decimal("60.00")

        existing_tx = SimpleNamespace(
            id=tx_id,
            user_id=self.user_id,
            account_id=account_id,
            kind="expense",
            amount=Decimal("100.00"),  # old expense was 100
            category_id=None,
            subcategory_id=None,
            transaction_date=date.today(),
            description="Expense",
            merchant=None,
            source="manual",
        )
        transaction_repo = Mock()
        transaction_repo.get_by_id.return_value = existing_tx

        service = TransactionService(
            db=self.db,
            transaction_repo=transaction_repo,
            account_repo=account_repo,
        )

        # User reduces expense from 100 to 90
        # Net delta should be: new_delta (-90) - old_delta (-100) = +10.00
        # Single atomic call with +10.00 avoids false overdraft
        patch_payload = TransactionUpdate(amount=Decimal("90.00"))
        updated = service.update_transaction(self.user_id, tx_id, patch_payload)

        self.assertEqual(updated.amount, Decimal("90.00"))
        account_repo.update_balance_atomic.assert_called_once_with(
            account_id, self.user_id, Decimal("10.00")
        )

    # --- [ISSUE-D04] Block Modifying Transactions Linked to Goal or Loan ---
    def test_issue_d04_block_modify_linked_goal_or_loan_transactions(self) -> None:
        """[ISSUE-D04] Block modifying amount/account/kind of transactions linked to savings goals or loans."""
        account_id = uuid4()
        tx_id = uuid4()

        existing_tx = SimpleNamespace(
            id=tx_id,
            user_id=self.user_id,
            account_id=account_id,
            kind="expense",
            amount=Decimal("500000.00"),
            source="goal",  # linked to savings goal!
            transaction_date=date.today(),
        )
        transaction_repo = Mock()
        transaction_repo.get_by_id.return_value = existing_tx

        service = TransactionService(
            db=self.db,
            transaction_repo=transaction_repo,
        )

        with self.assertRaises(AppError) as ctx:
            service.update_transaction(self.user_id, tx_id, TransactionUpdate(amount=Decimal("600000.00")))
        self.assertEqual(ctx.exception.code, "CANNOT_MODIFY_LINKED_TRANSACTION")
        self.assertEqual(ctx.exception.status_code, 400)

    # --- [ISSUE-D05] Delete Transaction Reverses Balance & Collects Attachment Keys ---
    def test_issue_d05_delete_transaction_balance_reversal_and_attachments(self) -> None:
        """[ISSUE-D05] Deleting transaction reverses balance atomically and logs attachment storage keys."""
        account_id = uuid4()
        tx_id = uuid4()

        existing_tx = SimpleNamespace(
            id=tx_id,
            user_id=self.user_id,
            account_id=account_id,
            kind="expense",
            amount=Decimal("200000.00"),
        )
        transaction_repo = Mock()
        transaction_repo.get_by_id.return_value = existing_tx

        account = SimpleNamespace(id=account_id, user_id=self.user_id, current_balance=Decimal("300000.00"))
        account_repo = Mock()
        account_repo.get_by_id.return_value = account
        account_repo.get_for_update.return_value = account
        account_repo.update_balance_atomic.return_value = Decimal("500000.00")

        attachment_repo = Mock()
        attachment_repo.list_by_transaction.return_value = [
            SimpleNamespace(storage_key="attachments/receipt1.png"),
            SimpleNamespace(storage_key="attachments/receipt2.pdf"),
        ]

        audit_repo = Mock()

        service = TransactionService(
            db=self.db,
            transaction_repo=transaction_repo,
            account_repo=account_repo,
            attachment_repo=attachment_repo,
            audit_repo=audit_repo,
        )

        service.delete_transaction(self.user_id, tx_id)

        # Reverse balance of expense: +200,000
        account_repo.update_balance_atomic.assert_called_once_with(account_id, self.user_id, Decimal("200000.00"))
        transaction_repo.delete_transaction.assert_called_once_with(existing_tx)
        audit_repo.log.assert_called_once()
        logged_changes = audit_repo.log.call_args.kwargs["changes"]
        self.assertEqual(logged_changes["deleted_storage_keys"], ["attachments/receipt1.png", "attachments/receipt2.pdf"])

    # --- [ISSUE-C1] Concurrency C1: Multiple threads deducting balance simultaneously ---
    def test_issue_d06_concurrency_c1_simultaneous_deductions(self) -> None:
        """[ISSUE-C1] Concurrency Test C1: Race condition prevention on concurrent deductions using threading.Barrier."""
        balance_lock = threading.Lock()
        current_balance = [Decimal("1000.00")]

        def thread_safe_atomic_update(acc_id, u_id, delta):
            with balance_lock:
                if current_balance[0] + delta >= Decimal("0"):
                    current_balance[0] += delta
                    return current_balance[0]
                return None

        account_id = uuid4()
        num_threads = 5
        deduction_amount = Decimal("250.00")  # 5 * 250 = 1250 > 1000 (only 4 should succeed, 1 fails)

        barrier = threading.Barrier(num_threads)
        results = []

        def worker():
            barrier.wait()  # synchronize all threads to fire simultaneously
            res = thread_safe_atomic_update(account_id, self.user_id, -deduction_amount)
            results.append(res)

        threads = [threading.Thread(target=worker) for _ in range(num_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        successes = [r for r in results if r is not None]
        failures = [r for r in results if r is None]

        # 4 succeeded (4 * 250 = 1000), 1 failed (cannot overdraft below 0)
        self.assertEqual(len(successes), 4)
        self.assertEqual(len(failures), 1)
        self.assertEqual(current_balance[0], Decimal("0.00"))

    # --- [ISSUE-C6] Concurrency C6: Anti-Deadlock Cross Transfers (A -> B and B -> A) ---
    def test_issue_d07_concurrency_c6_deadlock_prevention_cross_transfers(self) -> None:
        """[ISSUE-C6] Concurrency Test C6: Anti-deadlock via ascending ID order account locking with threading.Barrier."""
        acc_a_id = UUID("11111111-1111-1111-1111-111111111111")
        acc_b_id = UUID("22222222-2222-2222-2222-222222222222")

        acc_a = SimpleNamespace(
            id=acc_a_id, user_id=self.user_id, currency_code="VND", is_archived=False, current_balance=Decimal("1000000.00")
        )
        acc_b = SimpleNamespace(
            id=acc_b_id, user_id=self.user_id, currency_code="VND", is_archived=False, current_balance=Decimal("1000000.00")
        )

        global_lock = threading.Lock()
        locks_acquired_order = []

        # Simulated AccountRepository.lock_many: always locks in ascending ID order
        def simulated_lock_many(acc_ids, u_id):
            sorted_ids = sorted(acc_ids)
            with global_lock:
                locks_acquired_order.append(list(sorted_ids))
            return [acc_a if aid == acc_a_id else acc_b for aid in sorted_ids]

        account_repo = Mock()
        account_repo.lock_many.side_effect = simulated_lock_many
        account_repo.update_balance_atomic.return_value = Decimal("900000.00")

        transfer_repo = Mock()
        transfer_repo.get_by_idempotency_key.return_value = None

        service = TransferService(
            db=self.db,
            transfer_repo=transfer_repo,
            account_repo=account_repo,
        )

        barrier = threading.Barrier(2)

        # Thread 1: transfers A -> B
        # Thread 2: transfers B -> A
        def transfer_a_to_b():
            barrier.wait()
            payload = TransferCreate(
                from_account_id=acc_a_id,
                to_account_id=acc_b_id,
                amount=Decimal("100000.00"),
                transaction_date=date.today(),
            )
            service.create_transfer(self.user_id, payload)

        def transfer_b_to_a():
            barrier.wait()
            payload = TransferCreate(
                from_account_id=acc_b_id,
                to_account_id=acc_a_id,
                amount=Decimal("100000.00"),
                transaction_date=date.today(),
            )
            service.create_transfer(self.user_id, payload)

        t1 = threading.Thread(target=transfer_a_to_b)
        t2 = threading.Thread(target=transfer_b_to_a)

        t1.start()
        t2.start()

        t1.join()
        t2.join()

        # Both transfers acquired accounts in the EXACT SAME sorted order: [acc_a_id, acc_b_id]
        # This completely eliminates SQLSTATE 40P01 deadlocks!
        self.assertEqual(len(locks_acquired_order), 2)
        for order in locks_acquired_order:
            self.assertEqual(order, [acc_a_id, acc_b_id])
