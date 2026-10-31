import unittest
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import MagicMock, Mock, patch
from uuid import uuid4

from app.core.errors import AppError
from app.models.goal import GoalContribution, SavingsGoal
from app.models.system import Notification
from app.models.transaction import Transaction, TransactionCategory
from app.models.user import User
from app.schemas.goal import GoalContributionCreate, GoalCreate, GoalUpdate
from app.services.goal_service import GoalService, get_user_today


class TestGoalService(unittest.TestCase):
    def setUp(self) -> None:
        self.db = Mock()
        self.goal_repo = Mock()
        self.account_repo = Mock()
        self.category_repo = Mock()
        self.transaction_repo = Mock()
        self.notification_repo = Mock()
        self.audit_repo = Mock()
        self.budget_service = Mock()

        self.service = GoalService(
            db=self.db,
            goal_repo=self.goal_repo,
            account_repo=self.account_repo,
            category_repo=self.category_repo,
            transaction_repo=self.transaction_repo,
            notification_repo=self.notification_repo,
            audit_repo=self.audit_repo,
            budget_service=self.budget_service,
        )

        self.user_id = uuid4()
        self.user = User(
            id=self.user_id,
            email="test@example.com",
            username="testuser",
            default_currency="VND",
            timezone="Asia/Ho_Chi_Minh",
        )
        self.goal_id = uuid4()
        self.account_id = uuid4()

    # -------------------------------------------------------------------------
    # 1. create_goal
    # -------------------------------------------------------------------------
    def test_create_goal_success(self) -> None:
        tomorrow = get_user_today(self.user.timezone) + timedelta(days=30)
        payload = GoalCreate(
            name="Quỹ du lịch Nhật Bản",
            target_amount=Decimal("50000000.00"),
            deadline=tomorrow,
            description="Đi ngắm hoa anh đào",
        )
        self.goal_repo.exists_by_name.return_value = False

        goal = self.service.create_goal(self.user, payload)

        self.goal_repo.create.assert_called_once()
        self.db.commit.assert_called_once()
        self.db.refresh.assert_called_once()
        self.audit_repo.log.assert_called_once()
        self.assertEqual(goal.name, payload.name)
        self.assertEqual(goal.status, "active")
        self.assertEqual(goal.current_amount, Decimal("0.00"))

    def test_create_goal_invalid_deadline_past_or_today(self) -> None:
        today = get_user_today(self.user.timezone)
        payload = GoalCreate(
            name="Mục tiêu lỗi",
            target_amount=Decimal("1000000.00"),
            deadline=today,
        )

        with self.assertRaises(AppError) as ctx:
            self.service.create_goal(self.user, payload)
        self.assertEqual(ctx.exception.code, "INVALID_DEADLINE")
        self.assertEqual(ctx.exception.status_code, 422)

    def test_create_goal_name_taken(self) -> None:
        tomorrow = get_user_today(self.user.timezone) + timedelta(days=10)
        payload = GoalCreate(
            name="Quỹ khẩn cấp",
            target_amount=Decimal("20000000.00"),
            deadline=tomorrow,
        )
        self.goal_repo.exists_by_name.return_value = True

        with self.assertRaises(AppError) as ctx:
            self.service.create_goal(self.user, payload)
        self.assertEqual(ctx.exception.code, "GOAL_NAME_TAKEN")
        self.assertEqual(ctx.exception.status_code, 409)

    # -------------------------------------------------------------------------
    # 2. get_goal & list_goals & get_goal_detail
    # -------------------------------------------------------------------------
    def test_get_goal_success(self) -> None:
        mock_goal = SavingsGoal(id=self.goal_id, user_id=self.user.id, name="Goal 1")
        self.goal_repo.get_by_id.return_value = mock_goal

        goal = self.service.get_goal(self.user.id, self.goal_id)
        self.assertEqual(goal, mock_goal)

    def test_get_goal_not_found(self) -> None:
        self.goal_repo.get_by_id.return_value = None

        with self.assertRaises(AppError) as ctx:
            self.service.get_goal(self.user.id, self.goal_id)
        self.assertEqual(ctx.exception.code, "GOAL_NOT_FOUND")
        self.assertEqual(ctx.exception.status_code, 404)

    def test_list_goals(self) -> None:
        self.goal_repo.list_by_user.return_value = [
            SavingsGoal(id=uuid4(), user_id=self.user.id, name="Goal A"),
        ]
        res = self.service.list_goals(self.user.id, status_filter="active", offset=0, limit=10)
        self.assertEqual(len(res), 1)
        self.goal_repo.list_by_user.assert_called_once_with(
            user_id=self.user.id, status="active", offset=0, limit=10
        )

    def test_get_goal_detail(self) -> None:
        mock_goal = SavingsGoal(id=self.goal_id, user_id=self.user.id, name="Goal Detail")
        self.goal_repo.get_by_id.return_value = mock_goal
        mock_contrib = GoalContribution(id=uuid4(), goal_id=self.goal_id, amount=Decimal("1000.00"))
        self.goal_repo.list_contributions.return_value = [mock_contrib]

        goal, contribs = self.service.get_goal_detail(self.user.id, self.goal_id)
        self.assertEqual(goal, mock_goal)
        self.assertEqual(len(contribs), 1)

    # -------------------------------------------------------------------------
    # 3. update_goal
    # -------------------------------------------------------------------------
    def test_update_goal_success(self) -> None:
        tomorrow = get_user_today(self.user.timezone) + timedelta(days=60)
        mock_goal = SavingsGoal(
            id=self.goal_id,
            user_id=self.user.id,
            name="Old Name",
            target_amount=Decimal("10000000.00"),
            current_amount=Decimal("2000000.00"),
            status="active",
        )
        self.goal_repo.get_for_update.return_value = mock_goal
        self.goal_repo.exists_by_name.return_value = False

        update_data = GoalUpdate(
            name="New Name",
            target_amount=Decimal("15000000.00"),
            deadline=tomorrow,
        )

        res = self.service.update_goal(self.user, self.goal_id, update_data)
        self.assertEqual(res.name, "New Name")
        self.assertEqual(res.target_amount, Decimal("15000000.00"))
        self.db.commit.assert_called_once()

    def test_update_goal_target_less_than_current_raises_422(self) -> None:
        mock_goal = SavingsGoal(
            id=self.goal_id,
            user_id=self.user.id,
            name="Goal",
            target_amount=Decimal("10000000.00"),
            current_amount=Decimal("5000000.00"),
            status="active",
        )
        self.goal_repo.get_for_update.return_value = mock_goal

        update_data = GoalUpdate(target_amount=Decimal("4000000.00"))

        with self.assertRaises(AppError) as ctx:
            self.service.update_goal(self.user, self.goal_id, update_data)
        self.assertEqual(ctx.exception.code, "GOAL_OVER_TARGET")
        self.assertEqual(ctx.exception.status_code, 422)

    def test_update_goal_not_active_raises_409(self) -> None:
        mock_goal = SavingsGoal(
            id=self.goal_id,
            user_id=self.user.id,
            name="Goal",
            target_amount=Decimal("10000000.00"),
            current_amount=Decimal("10000000.00"),
            status="achieved",
        )
        self.goal_repo.get_for_update.return_value = mock_goal

        with self.assertRaises(AppError) as ctx:
            self.service.update_goal(self.user, self.goal_id, GoalUpdate(name="Change"))
        self.assertEqual(ctx.exception.code, "GOAL_NOT_ACTIVE")
        self.assertEqual(ctx.exception.status_code, 409)

    # -------------------------------------------------------------------------
    # 4. cancel_goal
    # -------------------------------------------------------------------------
    def test_cancel_goal_success(self) -> None:
        mock_goal = SavingsGoal(
            id=self.goal_id,
            user_id=self.user.id,
            name="Active Goal",
            status="active",
        )
        self.goal_repo.get_for_update.return_value = mock_goal

        res = self.service.cancel_goal(self.user, self.goal_id)
        self.assertEqual(res.status, "cancelled")
        self.db.commit.assert_called_once()

    def test_cancel_goal_already_cancelled_raises_409(self) -> None:
        mock_goal = SavingsGoal(
            id=self.goal_id,
            user_id=self.user.id,
            name="Cancelled Goal",
            status="cancelled",
        )
        self.goal_repo.get_for_update.return_value = mock_goal

        with self.assertRaises(AppError) as ctx:
            self.service.cancel_goal(self.user, self.goal_id)
        self.assertEqual(ctx.exception.code, "GOAL_NOT_ACTIVE")
        self.assertEqual(ctx.exception.status_code, 409)

    # -------------------------------------------------------------------------
    # 5. contribute (Core Workflow W11)
    # -------------------------------------------------------------------------
    def test_contribute_success_partial_progress(self) -> None:
        goal = SavingsGoal(
            id=self.goal_id,
            user_id=self.user.id,
            name="Mua máy tính",
            target_amount=Decimal("30000000.00"),
            current_amount=Decimal("10000000.00"),
            status="active",
            deadline=date(2027, 12, 31),
        )
        self.goal_repo.get_for_update.return_value = goal

        account = Mock(
            id=self.account_id,
            user_id=self.user.id,
            currency_code="VND",
            is_archived=False,
            current_balance=Decimal("25000000.00"),
        )
        self.account_repo.get_for_update.return_value = account
        self.account_repo.update_balance_atomic.return_value = Decimal("23000000.00")

        self.category_repo.get_system_by_code.return_value = TransactionCategory(
            id=1, code="SAVING", kind="expense", name="Tiết kiệm"
        )

        updated_goal = SavingsGoal(
            id=self.goal_id,
            user_id=self.user.id,
            name="Mua máy tính",
            target_amount=Decimal("30000000.00"),
            current_amount=Decimal("12000000.00"),
            status="active",
            deadline=date(2027, 12, 31),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        self.goal_repo.increment_current_atomic.return_value = updated_goal

        payload = GoalContributionCreate(
            account_id=self.account_id,
            amount=Decimal("2000000.00"),
        )

        resp = self.service.contribute(self.user, self.goal_id, payload)

        # 1. Locked goal then account (anti-deadlock)
        self.goal_repo.get_for_update.assert_called_once_with(self.goal_id, self.user.id)
        self.account_repo.get_for_update.assert_called_once_with(self.account_id, self.user.id)

        # 2. Created linked expense transaction
        self.transaction_repo.create_transaction.assert_called_once()
        created_tx = self.transaction_repo.create_transaction.call_args[0][0]
        self.assertEqual(created_tx.kind, "expense")
        self.assertEqual(created_tx.source, "goal")
        self.assertEqual(created_tx.amount, Decimal("2000000.00"))

        # 3. Atomic account deduction
        self.account_repo.update_balance_atomic.assert_called_once_with(
            self.account_id, self.user.id, -Decimal("2000000.00")
        )

        # 4. Added contribution & incremented goal atomically
        self.goal_repo.add_contribution.assert_called_once()
        self.goal_repo.increment_current_atomic.assert_called_once_with(
            self.goal_id, Decimal("2000000.00")
        )

        # 5. Commited transaction & logged audit
        self.db.commit.assert_called_once()
        self.audit_repo.log.assert_called_once()

        # 6. Response assertion
        self.assertEqual(resp.contribution.amount, Decimal("2000000.00"))
        self.assertEqual(resp.account.new_balance, Decimal("23000000.00"))
        self.assertEqual(resp.goal.current_amount, Decimal("12000000.00"))
        self.assertEqual(resp.goal.status, "active")

    def test_contribute_achieves_goal_triggers_notification(self) -> None:
        goal = SavingsGoal(
            id=self.goal_id,
            user_id=self.user.id,
            name="Mua điện thoại",
            target_amount=Decimal("10000000.00"),
            current_amount=Decimal("9000000.00"),
            status="active",
        )
        self.goal_repo.get_for_update.return_value = goal

        account = Mock(
            id=self.account_id,
            user_id=self.user.id,
            currency_code="VND",
            is_archived=False,
        )
        self.account_repo.get_for_update.return_value = account
        self.account_repo.update_balance_atomic.return_value = Decimal("5000000.00")

        achieved_goal = SavingsGoal(
            id=self.goal_id,
            user_id=self.user.id,
            name="Mua điện thoại",
            target_amount=Decimal("10000000.00"),
            current_amount=Decimal("10000000.00"),
            status="achieved",
            achieved_at=datetime.now(timezone.utc),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        self.goal_repo.increment_current_atomic.return_value = achieved_goal
        self.notification_repo.get_by_idempotency_key.return_value = None

        payload = GoalContributionCreate(
            account_id=self.account_id,
            amount=Decimal("1000000.00"),
        )

        resp = self.service.contribute(self.user, self.goal_id, payload)

        self.assertEqual(resp.goal.status, "achieved")
        self.notification_repo.create.assert_called_once()
        notif = self.notification_repo.create.call_args[0][0]
        self.assertEqual(notif.kind, "goal_achieved")
        self.assertEqual(notif.idempotency_key, f"goal_achieved:{self.goal_id}")

    def test_contribute_exceeds_remaining_raises_422(self) -> None:
        goal = SavingsGoal(
            id=self.goal_id,
            user_id=self.user.id,
            name="Goal",
            target_amount=Decimal("10000000.00"),
            current_amount=Decimal("8000000.00"),
            status="active",
        )
        self.goal_repo.get_for_update.return_value = goal

        payload = GoalContributionCreate(
            account_id=self.account_id,
            amount=Decimal("3000000.00"),  # remaining is 2M
        )

        with self.assertRaises(AppError) as ctx:
            self.service.contribute(self.user, self.goal_id, payload)
        self.assertEqual(ctx.exception.code, "GOAL_OVER_TARGET")
        self.assertEqual(ctx.exception.status_code, 422)
        # Account was not even fetched or locked
        self.account_repo.get_for_update.assert_not_called()

    def test_contribute_currency_mismatch_raises_422(self) -> None:
        goal = SavingsGoal(
            id=self.goal_id,
            user_id=self.user.id,
            name="Goal",
            target_amount=Decimal("10000000.00"),
            current_amount=Decimal("0.00"),
            status="active",
        )
        self.goal_repo.get_for_update.return_value = goal

        account = Mock(
            id=self.account_id,
            user_id=self.user.id,
            currency_code="USD",  # mismatch with user.default_currency="VND"
            is_archived=False,
        )
        self.account_repo.get_for_update.return_value = account

        payload = GoalContributionCreate(
            account_id=self.account_id,
            amount=Decimal("500000.00"),
        )

        with self.assertRaises(AppError) as ctx:
            self.service.contribute(self.user, self.goal_id, payload)
        self.assertEqual(ctx.exception.code, "CURRENCY_MISMATCH")
        self.assertEqual(ctx.exception.status_code, 422)

    def test_contribute_insufficient_funds_rolls_back(self) -> None:
        goal = SavingsGoal(
            id=self.goal_id,
            user_id=self.user.id,
            name="Goal",
            target_amount=Decimal("10000000.00"),
            current_amount=Decimal("0.00"),
            status="active",
        )
        self.goal_repo.get_for_update.return_value = goal

        account = Mock(
            id=self.account_id,
            user_id=self.user.id,
            currency_code="VND",
            is_archived=False,
        )
        self.account_repo.get_for_update.return_value = account
        self.account_repo.update_balance_atomic.return_value = None  # Insufficient funds!

        payload = GoalContributionCreate(
            account_id=self.account_id,
            amount=Decimal("500000.00"),
        )

        with self.assertRaises(AppError) as ctx:
            self.service.contribute(self.user, self.goal_id, payload)
        self.assertEqual(ctx.exception.code, "INSUFFICIENT_FUNDS")
        self.assertEqual(ctx.exception.status_code, 422)
        # Verify rollback was triggered
        self.db.rollback.assert_called_once()
        self.db.commit.assert_not_called()

    def test_contribute_goal_not_active_raises_409(self) -> None:
        goal = SavingsGoal(
            id=self.goal_id,
            user_id=self.user.id,
            name="Mục tiêu hoàn thành",
            target_amount=Decimal("10000000.00"),
            current_amount=Decimal("10000000.00"),
            status="achieved",
        )
        self.goal_repo.get_for_update.return_value = goal

        payload = GoalContributionCreate(
            account_id=self.account_id,
            amount=Decimal("500000.00"),
        )
        with self.assertRaises(AppError) as ctx:
            self.service.contribute(self.user, self.goal_id, payload)
        self.assertEqual(ctx.exception.code, "GOAL_NOT_ACTIVE")
        self.assertEqual(ctx.exception.status_code, 409)

    def test_contribute_goal_not_found_raises_404(self) -> None:
        self.goal_repo.get_for_update.return_value = None

        payload = GoalContributionCreate(
            account_id=self.account_id,
            amount=Decimal("500000.00"),
        )
        with self.assertRaises(AppError) as ctx:
            self.service.contribute(self.user, self.goal_id, payload)
        self.assertEqual(ctx.exception.code, "GOAL_NOT_FOUND")
        self.assertEqual(ctx.exception.status_code, 404)

    def test_contribute_account_not_found_raises_404(self) -> None:
        goal = SavingsGoal(
            id=self.goal_id,
            user_id=self.user.id,
            name="Goal",
            target_amount=Decimal("10000000.00"),
            current_amount=Decimal("0.00"),
            status="active",
        )
        self.goal_repo.get_for_update.return_value = goal
        self.account_repo.get_for_update.return_value = None

        payload = GoalContributionCreate(
            account_id=self.account_id,
            amount=Decimal("500000.00"),
        )
        with self.assertRaises(AppError) as ctx:
            self.service.contribute(self.user, self.goal_id, payload)
        self.assertEqual(ctx.exception.code, "ACCOUNT_NOT_FOUND")
        self.assertEqual(ctx.exception.status_code, 404)

    def test_contribute_archived_account_raises_422(self) -> None:
        goal = SavingsGoal(
            id=self.goal_id,
            user_id=self.user.id,
            name="Goal",
            target_amount=Decimal("10000000.00"),
            current_amount=Decimal("0.00"),
            status="active",
        )
        self.goal_repo.get_for_update.return_value = goal
        account = Mock(
            id=self.account_id,
            user_id=self.user.id,
            currency_code="VND",
            is_archived=True,
        )
        self.account_repo.get_for_update.return_value = account

        payload = GoalContributionCreate(
            account_id=self.account_id,
            amount=Decimal("500000.00"),
        )
        with self.assertRaises(AppError) as ctx:
            self.service.contribute(self.user, self.goal_id, payload)
        self.assertEqual(ctx.exception.code, "ACCOUNT_ARCHIVED")
        self.assertEqual(ctx.exception.status_code, 422)

    def test_contribute_category_saving_not_found_raises_500(self) -> None:
        goal = SavingsGoal(
            id=self.goal_id,
            user_id=self.user.id,
            name="Goal",
            target_amount=Decimal("10000000.00"),
            current_amount=Decimal("0.00"),
            status="active",
        )
        self.goal_repo.get_for_update.return_value = goal
        account = Mock(
            id=self.account_id,
            user_id=self.user.id,
            currency_code="VND",
            is_archived=False,
        )
        self.account_repo.get_for_update.return_value = account
        self.category_repo.get_system_by_code.return_value = None

        payload = GoalContributionCreate(
            account_id=self.account_id,
            amount=Decimal("500000.00"),
        )
        with self.assertRaises(AppError) as ctx:
            self.service.contribute(self.user, self.goal_id, payload)
        self.assertEqual(ctx.exception.code, "CATEGORY_NOT_FOUND")
        self.assertEqual(ctx.exception.status_code, 500)

    def test_contribute_atomic_increment_failed_rolls_back(self) -> None:
        goal = SavingsGoal(
            id=self.goal_id,
            user_id=self.user.id,
            name="Goal",
            target_amount=Decimal("10000000.00"),
            current_amount=Decimal("9000000.00"),
            status="active",
        )
        self.goal_repo.get_for_update.return_value = goal
        account = Mock(
            id=self.account_id,
            user_id=self.user.id,
            currency_code="VND",
            is_archived=False,
        )
        self.account_repo.get_for_update.return_value = account
        self.account_repo.update_balance_atomic.return_value = Decimal("1000000.00")
        self.category_repo.get_system_by_code.return_value = TransactionCategory(
            id=1, code="SAVING", kind="expense", name="Tiết kiệm"
        )
        self.goal_repo.increment_current_atomic.return_value = None

        payload = GoalContributionCreate(
            account_id=self.account_id,
            amount=Decimal("1000000.00"),
        )
        with self.assertRaises(AppError) as ctx:
            self.service.contribute(self.user, self.goal_id, payload)
        self.assertEqual(ctx.exception.code, "GOAL_OVER_TARGET")
        self.assertEqual(ctx.exception.status_code, 422)
        self.db.rollback.assert_called_once()

    def test_contribute_notification_idempotency_prevents_duplicate(self) -> None:
        goal = SavingsGoal(
            id=self.goal_id,
            user_id=self.user.id,
            name="Mua điện thoại",
            target_amount=Decimal("10000000.00"),
            current_amount=Decimal("9000000.00"),
            status="active",
        )
        self.goal_repo.get_for_update.return_value = goal

        account = Mock(
            id=self.account_id,
            user_id=self.user.id,
            currency_code="VND",
            is_archived=False,
        )
        self.account_repo.get_for_update.return_value = account
        self.account_repo.update_balance_atomic.return_value = Decimal("5000000.00")

        achieved_goal = SavingsGoal(
            id=self.goal_id,
            user_id=self.user.id,
            name="Mua điện thoại",
            target_amount=Decimal("10000000.00"),
            current_amount=Decimal("10000000.00"),
            status="achieved",
            achieved_at=datetime.now(timezone.utc),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        self.goal_repo.increment_current_atomic.return_value = achieved_goal
        self.notification_repo.get_by_idempotency_key.return_value = Notification(
            id=uuid4(), user_id=self.user.id, title="Đạt mục tiêu"
        )

        payload = GoalContributionCreate(
            account_id=self.account_id,
            amount=Decimal("1000000.00"),
        )

        resp = self.service.contribute(self.user, self.goal_id, payload)
        self.assertEqual(resp.goal.status, "achieved")
        self.notification_repo.create.assert_not_called()



if __name__ == "__main__":
    unittest.main()
