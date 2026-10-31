import unittest
from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import uuid4

from app.schemas.goal import (
    GoalContributeAccountSummary,
    GoalContributeResponse,
    GoalContributionCreate,
    GoalContributionRead,
    GoalCreate,
    GoalDetailRead,
    GoalRead,
    GoalUpdate,
    calculate_goal_progress,
)


class GoalSchemaTests(unittest.TestCase):
    def test_calculate_goal_progress_standard(self) -> None:
        # 12M of 30M, deadline 6 months ahead
        rem, pct, needed = calculate_goal_progress(
            target_amount=Decimal("30000000.00"),
            current_amount=Decimal("12000000.00"),
            deadline=date(2027, 4, 30),
            status="active",
            as_of=date(2026, 10, 31),
        )
        self.assertEqual(rem, Decimal("18000000.00"))
        self.assertEqual(pct, Decimal("40.0"))
        self.assertEqual(needed, Decimal("3000000.00"))

    def test_calculate_goal_progress_edge_cases(self) -> None:
        # 1. No deadline
        rem, pct, needed = calculate_goal_progress(
            target_amount=Decimal("10000000.00"),
            current_amount=Decimal("2000000.00"),
            deadline=None,
            status="active",
        )
        self.assertEqual(rem, Decimal("8000000.00"))
        self.assertEqual(pct, Decimal("20.0"))
        self.assertIsNone(needed)

        # 2. Status not active (e.g. achieved or cancelled)
        _, _, needed_achieved = calculate_goal_progress(
            target_amount=Decimal("10000000.00"),
            current_amount=Decimal("10000000.00"),
            deadline=date(2027, 1, 1),
            status="achieved",
        )
        self.assertIsNone(needed_achieved)

        # 3. Remaining <= 0 when active
        rem, pct, needed_zero = calculate_goal_progress(
            target_amount=Decimal("10000000.00"),
            current_amount=Decimal("10000000.00"),
            deadline=date(2027, 1, 1),
            status="active",
        )
        self.assertEqual(rem, Decimal("0.00"))
        self.assertEqual(needed_zero, Decimal("0.00"))

        # 4. Past deadline (overdue)
        rem, pct, needed_overdue = calculate_goal_progress(
            target_amount=Decimal("10000000.00"),
            current_amount=Decimal("4000000.00"),
            deadline=date(2026, 1, 1),
            status="active",
            as_of=date(2026, 10, 31),
        )
        self.assertEqual(rem, Decimal("6000000.00"))
        # months_left <= 0 clamped to 1
        self.assertEqual(needed_overdue, Decimal("6000000.00"))

    def test_goal_read_computed_fields(self) -> None:
        uid = uuid4()
        gid = uuid4()
        now = datetime.now(timezone.utc)
        goal = GoalRead(
            id=gid,
            user_id=uid,
            name="Mua laptop",
            description="Macbook Pro",
            target_amount=Decimal("30000000.00"),
            current_amount=Decimal("12000000.00"),
            deadline=date(2027, 4, 30),
            status="active",
            created_at=now,
            updated_at=now,
        )
        dump = goal.model_dump()
        self.assertEqual(dump["remaining"], Decimal("18000000.00"))
        self.assertEqual(dump["progress_percent"], Decimal("40.0"))
        self.assertIsNotNone(dump["monthly_needed"])

    def test_goal_contribute_response(self) -> None:
        uid = uuid4()
        gid = uuid4()
        tid = uuid4()
        cid = uuid4()
        aid = uuid4()
        now = datetime.now(timezone.utc)
        resp = GoalContributeResponse(
            contribution=GoalContributionRead(
                id=cid,
                goal_id=gid,
                transaction_id=tid,
                amount=Decimal("2000000.00"),
                contributed_at=now,
            ),
            goal=GoalRead(
                id=gid,
                user_id=uid,
                name="Mua laptop",
                target_amount=Decimal("30000000.00"),
                current_amount=Decimal("14000000.00"),
                deadline=date(2027, 4, 30),
                status="active",
                created_at=now,
                updated_at=now,
            ),
            account=GoalContributeAccountSummary(
                id=aid,
                new_balance=Decimal("8000000.00"),
            ),
        )
        dump = resp.model_dump()
        self.assertEqual(dump["contribution"]["amount"], Decimal("2000000.00"))
        self.assertEqual(dump["goal"]["current_amount"], Decimal("14000000.00"))
        self.assertEqual(dump["account"]["new_balance"], Decimal("8000000.00"))


if __name__ == "__main__":
    unittest.main()
