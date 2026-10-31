import unittest
from datetime import date, datetime, timezone
from decimal import Decimal
from unittest.mock import MagicMock, Mock, patch
from uuid import uuid4

from sqlalchemy.sql.elements import BinaryExpression, Case

from app.models.goal import GoalContribution, SavingsGoal
from app.models.transaction import TransactionCategory
from app.repositories.category_repository import CategoryRepository
from app.repositories.goal_repository import GoalRepository


class TestGoalAndCategoryRepositories(unittest.TestCase):
    def setUp(self) -> None:
        self.db = Mock()
        self.user_id = uuid4()
        self.goal_id = uuid4()
        self.category_repo = CategoryRepository(self.db)
        self.goal_repo = GoalRepository(self.db)

    # -------------------------------------------------------------------------
    # 1. CategoryRepository.get_system_by_code
    # -------------------------------------------------------------------------
    def test_category_repo_get_system_by_code_success(self) -> None:
        expected_cat = TransactionCategory(
            id=10,
            user_id=None,
            code="SAVING",
            name="Tiết kiệm",
            kind="expense",
            is_active=True,
        )
        self.db.scalar.return_value = expected_cat

        cat = self.category_repo.get_system_by_code("saving", kind="expense")

        self.assertIsNotNone(cat)
        self.assertEqual(cat.code, "SAVING")
        self.assertEqual(cat.kind, "expense")
        self.db.scalar.assert_called_once()

    def test_category_repo_get_system_by_code_not_found(self) -> None:
        self.db.scalar.return_value = None

        cat = self.category_repo.get_system_by_code("NON_EXISTENT")
        self.assertIsNone(cat)

    # -------------------------------------------------------------------------
    # 2. GoalRepository.create
    # -------------------------------------------------------------------------
    def test_goal_repo_create_goal_flushes_without_commit(self) -> None:
        goal = SavingsGoal(
            id=self.goal_id,
            user_id=self.user_id,
            name="Mua xe máy",
            target_amount=Decimal("40000000.00"),
            current_amount=Decimal("0.00"),
            deadline=date(2027, 12, 31),
            status="active",
        )

        created = self.goal_repo.create(goal)

        self.assertEqual(created.id, self.goal_id)
        self.db.add.assert_called_once_with(goal)
        self.db.flush.assert_called_once()
        self.db.commit.assert_not_called()

    # -------------------------------------------------------------------------
    # 3. GoalRepository.get_by_id and get_for_update
    # -------------------------------------------------------------------------
    def test_goal_repo_get_by_id_calls_scalar(self) -> None:
        fake_goal = SavingsGoal(id=self.goal_id, user_id=self.user_id, name="Test Goal")
        self.db.scalar.return_value = fake_goal

        goal = self.goal_repo.get_by_id(self.goal_id, self.user_id)
        self.assertEqual(goal, fake_goal)
        self.db.scalar.assert_called_once()

    def test_goal_repo_get_for_update_calls_get_by_id_with_for_update(self) -> None:
        with patch.object(self.goal_repo, "get_by_id") as mock_get:
            mock_get.return_value = SavingsGoal(id=self.goal_id, user_id=self.user_id)
            res = self.goal_repo.get_for_update(self.goal_id, self.user_id)
            mock_get.assert_called_once_with(self.goal_id, self.user_id, for_update=True)
            self.assertEqual(res, mock_get.return_value)

    # -------------------------------------------------------------------------
    # 4. GoalRepository.exists_by_name
    # -------------------------------------------------------------------------
    def test_goal_repo_exists_by_name(self) -> None:
        self.db.scalar.return_value = True
        exists = self.goal_repo.exists_by_name(self.user_id, "  Quỹ khẩn cấp  ")
        self.assertTrue(exists)
        self.db.scalar.assert_called_once()

    def test_goal_repo_exists_by_name_with_exclude_id(self) -> None:
        self.db.scalar.return_value = False
        other_id = uuid4()
        exists = self.goal_repo.exists_by_name(self.user_id, "Quỹ khẩn cấp", exclude_id=other_id)
        self.assertFalse(exists)
        self.db.scalar.assert_called_once()

    # -------------------------------------------------------------------------
    # 5. GoalRepository.list_by_user
    # -------------------------------------------------------------------------
    def test_goal_repo_list_by_user(self) -> None:
        goals = [
            SavingsGoal(id=uuid4(), user_id=self.user_id, name="Goal 1", status="active"),
            SavingsGoal(id=uuid4(), user_id=self.user_id, name="Goal 2", status="achieved"),
        ]
        scalars_mock = Mock()
        scalars_mock.all.return_value = goals
        self.db.scalars.return_value = scalars_mock

        result = self.goal_repo.list_by_user(self.user_id, status="active", offset=0, limit=10)

        self.assertEqual(len(result), 2)
        self.db.scalars.assert_called_once()

    # -------------------------------------------------------------------------
    # 6. GoalRepository.add_contribution and list_contributions
    # -------------------------------------------------------------------------
    def test_goal_repo_add_contribution_flushes_without_commit(self) -> None:
        contrib = GoalContribution(
            id=uuid4(),
            goal_id=self.goal_id,
            transaction_id=uuid4(),
            amount=Decimal("1000000.00"),
        )

        res = self.goal_repo.add_contribution(contrib)

        self.assertEqual(res, contrib)
        self.db.add.assert_called_once_with(contrib)
        self.db.flush.assert_called_once()
        self.db.commit.assert_not_called()

    def test_goal_repo_list_contributions(self) -> None:
        contribs = [
            GoalContribution(id=uuid4(), goal_id=self.goal_id, amount=Decimal("500000.00")),
            GoalContribution(id=uuid4(), goal_id=self.goal_id, amount=Decimal("1500000.00")),
        ]
        scalars_mock = Mock()
        scalars_mock.all.return_value = contribs
        self.db.scalars.return_value = scalars_mock

        res = self.goal_repo.list_contributions(self.goal_id)

        self.assertEqual(len(res), 2)
        self.db.scalars.assert_called_once()

    # -------------------------------------------------------------------------
    # 7. GoalRepository.increment_current_atomic
    # -------------------------------------------------------------------------
    def test_goal_repo_increment_current_atomic(self) -> None:
        updated_goal = SavingsGoal(
            id=self.goal_id,
            user_id=self.user_id,
            current_amount=Decimal("10000000.00"),
            target_amount=Decimal("10000000.00"),
            status="achieved",
            achieved_at=datetime.now(timezone.utc),
        )
        self.db.scalar.return_value = updated_goal

        res = self.goal_repo.increment_current_atomic(self.goal_id, Decimal("2000000.00"))

        self.assertIsNotNone(res)
        self.assertEqual(res.status, "achieved")
        self.db.scalar.assert_called_once()
        self.db.flush.assert_called_once()
        self.db.commit.assert_not_called()


if __name__ == "__main__":
    unittest.main()
