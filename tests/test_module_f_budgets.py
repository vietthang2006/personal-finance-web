from datetime import date, datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, call
from uuid import UUID, uuid4

from app.core.errors import AppError
from app.models.budget import Budget, BudgetAlertEvent, BudgetCategory
from app.schemas.budget import (
    BudgetCategoryCreate,
    BudgetCategoryUpdate,
    BudgetCreate,
    BudgetUpdate,
)
from app.services.budget_service import (
    BudgetConflictError,
    BudgetNotFoundError,
    BudgetService,
    BudgetValidationError,
)
from app.services.transaction_service import TransactionService
from app.schemas.transaction import TransactionCreate, TransactionUpdate


class ModuleFBudgetsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.user_id = uuid4()
        self.db = Mock()

    # --- [ISSUE-F01] Budget Creation and Limits Validation ---
    def test_issue_f01_budget_creation_and_limit_validation(self) -> None:
        """[ISSUE-F01] Create budget with period_type, date range, total_limit, and validate category limit sum <= total_limit."""
        budget_repo = Mock()
        category_repo = Mock()

        # Category 1 & 2 are visible expense categories
        category_repo.get_visible.side_effect = lambda cid, uid: SimpleNamespace(
            id=cid, kind="expense", is_active=True
        )

        service = BudgetService(db=self.db, budget_repo=budget_repo, category_repo=category_repo)

        # 1.1 Invalid date range (end_date < start_date)
        with self.assertRaises(ValueError) as ctx:
            BudgetCreate(
                name="Ngân sách tháng 10",
                period_type="monthly",
                start_date=date(2026, 10, 31),
                end_date=date(2026, 10, 1),  # earlier than start
                total_limit=Decimal("5000000.00"),
            )
        self.assertIn("end_date must not be before start_date", str(ctx.exception))

        # 1.2 Category limits sum exceeds total_limit
        with self.assertRaises(BudgetValidationError) as ctx:
            service.create_budget(
                self.user_id,
                BudgetCreate(
                    name="Ngân sách tháng 10",
                    period_type="monthly",
                    start_date=date(2026, 10, 1),
                    end_date=date(2026, 10, 31),
                    total_limit=Decimal("5000000.00"),
                    categories=[
                        BudgetCategoryCreate(category_id=1, limit_amount=Decimal("3000000.00")),
                        BudgetCategoryCreate(category_id=2, limit_amount=Decimal("3000000.00")),  # sum = 6m > 5m
                    ],
                ),
            )
        self.assertIn("cannot exceed budget total_limit", str(ctx.exception))

        # 1.3 Duplicate category in budget allocations
        with self.assertRaises(BudgetConflictError) as ctx:
            service.create_budget(
                self.user_id,
                BudgetCreate(
                    name="Ngân sách tháng 10",
                    period_type="monthly",
                    start_date=date(2026, 10, 1),
                    end_date=date(2026, 10, 31),
                    total_limit=Decimal("5000000.00"),
                    categories=[
                        BudgetCategoryCreate(category_id=1, limit_amount=Decimal("2000000.00")),
                        BudgetCategoryCreate(category_id=1, limit_amount=Decimal("1000000.00")),
                    ],
                ),
            )
        self.assertIn("Duplicate category_id 1", str(ctx.exception))

        # 1.4 Valid budget creation
        valid_payload = BudgetCreate(
            name="Ngân sách hợp lệ",
            period_type="monthly",
            start_date=date(2026, 10, 1),
            end_date=date(2026, 10, 31),
            total_limit=Decimal("5000000.00"),
            categories=[
                BudgetCategoryCreate(category_id=1, limit_amount=Decimal("2000000.00")),
                BudgetCategoryCreate(category_id=2, limit_amount=Decimal("2000000.00")),
            ],
        )
        created = service.create_budget(self.user_id, valid_payload)
        self.assertIsNotNone(created)
        budget_repo.create_budget.assert_called_once()
        self.assertEqual(budget_repo.add_budget_category.call_count, 2)
        self.db.commit.assert_called_once()

    # --- [ISSUE-F02] Category Allocation CRUD & Capacity Protection ---
    def test_issue_f02_category_limit_crud_and_overflow_protection(self) -> None:
        """[ISSUE-F02] Category allocation CRUD preventing total limit overflow."""
        budget_id = uuid4()
        existing_cat = SimpleNamespace(category_id=1, limit_amount=Decimal("3000000.00"), warn_percent=80)
        budget = SimpleNamespace(
            id=budget_id,
            user_id=self.user_id,
            total_limit=Decimal("5000000.00"),
            categories=[existing_cat],
        )

        budget_repo = Mock()
        budget_repo.get_budget.return_value = budget
        budget_repo.get_budget_category_by_category_id.return_value = None

        category_repo = Mock()
        category_repo.get_visible.return_value = SimpleNamespace(id=2, kind="expense")

        service = BudgetService(db=self.db, budget_repo=budget_repo, category_repo=category_repo)

        # 2.1 Adding limit exceeding capacity (3m + 3m = 6m > 5m)
        with self.assertRaises(BudgetValidationError) as ctx:
            service.add_category_limit(
                self.user_id,
                budget_id,
                BudgetCategoryCreate(category_id=2, limit_amount=Decimal("3000000.00")),
            )
        self.assertIn("exceeds budget total_limit", str(ctx.exception))

        # 2.2 Adding valid limit (3m + 1.5m = 4.5m <= 5m)
        service.add_category_limit(
            self.user_id,
            budget_id,
            BudgetCategoryCreate(category_id=2, limit_amount=Decimal("1500000.00")),
        )
        budget_repo.add_budget_category.assert_called_once()
        self.db.commit.assert_called_once()

    # --- [ISSUE-F03] Progress Calculation & Auto Alert Triggering ---
    def test_issue_f03_budget_progress_and_threshold_alerts(self) -> None:
        """[ISSUE-F03] Calculate progress and auto-trigger warning and exceeded alerts with notification generation."""
        budget_id = uuid4()
        bc1_id = uuid4()
        bc1 = SimpleNamespace(
            id=bc1_id,
            category_id=1,
            limit_amount=Decimal("1000000.00"),
            warn_percent=80,
            category=SimpleNamespace(name="Ăn uống"),
        )
        budget = SimpleNamespace(
            id=budget_id,
            user_id=self.user_id,
            name="Ngân sách ăn uống",
            period_type="monthly",
            start_date=date(2026, 10, 1),
            end_date=date(2026, 10, 31),
            total_limit=Decimal("1000000.00"),
            categories=[bc1],
        )

        budget_repo = Mock()
        budget_repo.get_budget.return_value = budget
        # Spent 850,000 (85% >= 80% warning threshold)
        budget_repo.get_spent_amount_by_category.return_value = Decimal("850000.00")
        budget_repo.get_total_spent_for_budget.return_value = Decimal("850000.00")
        # No alert exists yet
        budget_repo.get_alert_event.return_value = None

        notification_repo = Mock()
        notification_repo.get_by_idempotency_key.return_value = None

        service = BudgetService(
            db=self.db,
            budget_repo=budget_repo,
            notification_repo=notification_repo,
        )

        progress = service.calculate_progress(self.user_id, budget_id, auto_trigger_alerts=True)

        self.assertEqual(progress.total_spent, Decimal("850000.00"))
        self.assertEqual(progress.overall_percent_used, Decimal("85.00"))
        self.assertTrue(progress.categories[0].is_warning)
        self.assertFalse(progress.categories[0].is_exceeded)

        # Ensure warning alert event was created
        budget_repo.create_alert_event.assert_called_once()
        alert_arg = budget_repo.create_alert_event.call_args[0][0]
        self.assertEqual(alert_arg.level, "warning")
        self.assertEqual(alert_arg.percent_used, Decimal("85.00"))

        # Ensure notification was generated
        notification_repo.create.assert_called_once()
        notif_arg = notification_repo.create.call_args[0][0]
        self.assertEqual(notif_arg.kind, "budget_warning")
        self.assertIn("Ăn uống", notif_arg.body)

    # --- [ISSUE-F04] Budget Rearm and Evaluate on Reduced Spending ---
    def test_issue_f04_budget_rearm_and_evaluate_on_spending_reduction(self) -> None:
        """[ISSUE-F04] Rearm (delete) alerts when spending drops below threshold."""
        budget_id = uuid4()
        bc1_id = uuid4()
        bc1 = SimpleNamespace(
            id=bc1_id,
            category_id=1,
            limit_amount=Decimal("1000000.00"),
            warn_percent=80,
            category=SimpleNamespace(name="Ăn uống"),
        )
        budget = SimpleNamespace(
            id=budget_id,
            user_id=self.user_id,
            name="Ngân sách ăn uống",
            period_type="monthly",
            start_date=date(2026, 10, 1),
            end_date=date(2026, 10, 31),
            total_limit=Decimal("1000000.00"),
            categories=[bc1],
        )

        budget_repo = Mock()
        budget_repo.list_active_budgets_for_date.return_value = [budget]
        budget_repo.get_budget.return_value = budget
        # Spending dropped from 90% down to 50% (500,000 < 800,000)
        budget_repo.get_spent_amount_by_category.return_value = Decimal("500000.00")
        budget_repo.get_total_spent_for_budget.return_value = Decimal("500000.00")

        existing_warn = SimpleNamespace(id=1, budget_category_id=bc1_id, level="warning")
        existing_exc = None
        budget_repo.get_alert_event.side_effect = lambda cid, lvl: existing_warn if lvl == "warning" else existing_exc

        service = BudgetService(db=self.db, budget_repo=budget_repo)

        service.rearm_and_evaluate(self.user_id, date(2026, 10, 15))

        # Warning alert should have been deleted (rearmed) because 50% < 80%
        budget_repo.delete_alert_event.assert_called_once_with(existing_warn)

    # --- [ISSUE-F05] Transaction Hook Triggers Budget Rearm & Evaluate ---
    def test_issue_f05_transaction_hook_triggers_budget_evaluation(self) -> None:
        """[ISSUE-F05] Integration between TransactionService and BudgetService rearm_and_evaluate."""
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
        account_repo.update_balance_atomic.return_value = Decimal("800000.00")

        transaction_repo = Mock()
        category_repo = Mock()
        category_repo.get_visible.return_value = SimpleNamespace(id=1, kind="expense", is_active=True)
        category_repo.get_subcategory.return_value = None

        budget_service = Mock()

        tx_service = TransactionService(
            db=self.db,
            transaction_repo=transaction_repo,
            account_repo=account_repo,
            category_repo=category_repo,
            budget_service=budget_service,
        )

        today = date.today()
        payload = TransactionCreate(
            account_id=account_id,
            kind="expense",
            amount=Decimal("200000.00"),
            transaction_date=today,
            category_id=1,
        )

        tx_service.create_transaction(self.user_id, payload)

        # Verify budget_service.rearm_and_evaluate was invoked with the transaction date
        budget_service.rearm_and_evaluate.assert_called_once_with(self.user_id, today)

    # --- [ISSUE-F06] Audit Logging in Budget Operations ---
    def test_issue_f06_budget_unit_of_work_and_audit_logging(self) -> None:
        """[ISSUE-F06] AuditLogRepository integration for all budget mutation operations."""
        budget_repo = Mock()
        audit_repo = Mock()

        service = BudgetService(db=self.db, budget_repo=budget_repo, audit_repo=audit_repo)

        payload = BudgetCreate(
            name="Ngân sách du lịch",
            period_type="custom",
            start_date=date(2026, 11, 1),
            end_date=date(2026, 11, 15),
            total_limit=Decimal("15000000.00"),
        )

        service.create_budget(self.user_id, payload)

        audit_repo.log.assert_called_once()
        log_kwargs = audit_repo.log.call_args.kwargs
        self.assertEqual(log_kwargs["action"], "CREATE")
        self.assertEqual(log_kwargs["entity_type"], "budget")
        self.assertEqual(log_kwargs["actor_id"], self.user_id)
        self.assertEqual(log_kwargs["changes"]["name"], "Ngân sách du lịch")
