import unittest
from datetime import date, datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

from app.api.v1.goals import (
    cancel_goal,
    contribute,
    create_goal,
    get_goal,
    list_goals,
    update_goal,
)
from app.models.goal import GoalContribution, SavingsGoal
from app.schemas.goal import (
    GoalContributeAccountSummary,
    GoalContributeResponse,
    GoalContributionCreate,
    GoalContributionRead,
    GoalCreate,
    GoalDetailRead,
    GoalRead,
    GoalUpdate,
)


class TestGoalApiHandlers(unittest.TestCase):
    def setUp(self) -> None:
        self.user_id = uuid4()
        self.goal_id = uuid4()
        self.account_id = uuid4()
        self.now = datetime.now(timezone.utc)

        self.user = SimpleNamespace(
            id=self.user_id,
            email="test@example.com",
            username="testuser",
            default_currency="VND",
            timezone="Asia/Ho_Chi_Minh",
            roles=[],
        )
        self.goal_service = Mock()

    def test_create_goal_handler(self) -> None:
        mock_goal = SavingsGoal(
            id=self.goal_id,
            user_id=self.user_id,
            name="Mua xe hơi",
            target_amount=Decimal("500000000.00"),
            current_amount=Decimal("0.00"),
            status="active",
            created_at=self.now,
            updated_at=self.now,
        )
        self.goal_service.create_goal.return_value = mock_goal

        payload = GoalCreate(
            name="Mua xe hơi",
            target_amount=Decimal("500000000.00"),
            deadline=date(2027, 12, 31),
        )
        result = create_goal(payload=payload, user=self.user, service=self.goal_service)

        self.assertIsInstance(result, GoalRead)
        self.assertEqual(result.id, self.goal_id)
        self.assertEqual(result.name, "Mua xe hơi")
        self.assertEqual(result.remaining, Decimal("500000000.00"))
        self.assertEqual(result.progress_percent, Decimal("0.0"))
        self.goal_service.create_goal.assert_called_once_with(self.user, payload)

    def test_list_goals_handler(self) -> None:
        mock_goal = SavingsGoal(
            id=self.goal_id,
            user_id=self.user_id,
            name="Quỹ du lịch",
            target_amount=Decimal("20000000.00"),
            current_amount=Decimal("5000000.00"),
            status="active",
            created_at=self.now,
            updated_at=self.now,
        )
        self.goal_service.list_goals.return_value = [mock_goal]

        results = list_goals(
            user=self.user,
            service=self.goal_service,
            status_filter="active",
            offset=0,
            limit=50,
        )

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].name, "Quỹ du lịch")
        self.assertEqual(results[0].progress_percent, Decimal("25.0"))
        self.goal_service.list_goals.assert_called_once_with(
            user_id=self.user.id,
            status_filter="active",
            offset=0,
            limit=50,
        )

    def test_get_goal_detail_handler(self) -> None:
        mock_goal = SavingsGoal(
            id=self.goal_id,
            user_id=self.user_id,
            name="Quỹ học tập",
            target_amount=Decimal("10000000.00"),
            current_amount=Decimal("3000000.00"),
            status="active",
            created_at=self.now,
            updated_at=self.now,
        )
        contrib_id = uuid4()
        tx_id = uuid4()
        mock_contrib = GoalContribution(
            id=contrib_id,
            goal_id=self.goal_id,
            transaction_id=tx_id,
            amount=Decimal("3000000.00"),
            contributed_at=self.now,
        )
        self.goal_service.get_goal_detail.return_value = (mock_goal, [mock_contrib])

        detail = get_goal(goal_id=self.goal_id, user=self.user, service=self.goal_service)

        self.assertIsInstance(detail, GoalDetailRead)
        self.assertEqual(detail.id, self.goal_id)
        self.assertEqual(len(detail.contributions), 1)
        self.assertEqual(detail.contributions[0].id, contrib_id)
        self.assertEqual(detail.contributions[0].amount, Decimal("3000000.00"))
        self.goal_service.get_goal_detail.assert_called_once_with(self.user.id, self.goal_id)

    def test_update_goal_handler(self) -> None:
        mock_goal = SavingsGoal(
            id=self.goal_id,
            user_id=self.user_id,
            name="Quỹ mới",
            target_amount=Decimal("15000000.00"),
            current_amount=Decimal("3000000.00"),
            status="active",
            created_at=self.now,
            updated_at=self.now,
        )
        self.goal_service.update_goal.return_value = mock_goal

        payload = GoalUpdate(name="Quỹ mới", target_amount=Decimal("15000000.00"))
        result = update_goal(
            goal_id=self.goal_id,
            payload=payload,
            user=self.user,
            service=self.goal_service,
        )

        self.assertEqual(result.name, "Quỹ mới")
        self.assertEqual(result.target_amount, Decimal("15000000.00"))
        self.goal_service.update_goal.assert_called_once_with(self.user, self.goal_id, payload)

    def test_cancel_goal_handler(self) -> None:
        mock_goal = SavingsGoal(
            id=self.goal_id,
            user_id=self.user_id,
            name="Mục tiêu hủy",
            target_amount=Decimal("10000000.00"),
            current_amount=Decimal("2000000.00"),
            status="cancelled",
            created_at=self.now,
            updated_at=self.now,
        )
        self.goal_service.cancel_goal.return_value = mock_goal

        result = cancel_goal(
            goal_id=self.goal_id,
            user=self.user,
            service=self.goal_service,
        )

        self.assertEqual(result.status, "cancelled")
        self.goal_service.cancel_goal.assert_called_once_with(self.user, self.goal_id)

    def test_contribute_handler(self) -> None:
        contrib_id = uuid4()
        tx_id = uuid4()

        updated_goal = SavingsGoal(
            id=self.goal_id,
            user_id=self.user_id,
            name="Laptop xịn",
            target_amount=Decimal("30000000.00"),
            current_amount=Decimal("10000000.00"),
            status="active",
            created_at=self.now,
            updated_at=self.now,
        )

        mock_resp = GoalContributeResponse(
            contribution=GoalContributionRead(
                id=contrib_id,
                goal_id=self.goal_id,
                transaction_id=tx_id,
                amount=Decimal("2000000.00"),
                contributed_at=self.now,
            ),
            goal=GoalRead.model_validate(updated_goal),
            account=GoalContributeAccountSummary(
                id=self.account_id,
                new_balance=Decimal("18000000.00"),
            ),
        )
        self.goal_service.contribute.return_value = mock_resp

        payload = GoalContributionCreate(
            account_id=self.account_id,
            amount=Decimal("2000000.00"),
        )
        result = contribute(
            goal_id=self.goal_id,
            payload=payload,
            user=self.user,
            service=self.goal_service,
        )

        self.assertEqual(result.contribution.id, contrib_id)
        self.assertEqual(result.contribution.amount, Decimal("2000000.00"))
        self.assertEqual(result.goal.current_amount, Decimal("10000000.00"))
        self.assertEqual(result.account.new_balance, Decimal("18000000.00"))
        self.goal_service.contribute.assert_called_once_with(self.user, self.goal_id, payload)


if __name__ == "__main__":
    unittest.main()
