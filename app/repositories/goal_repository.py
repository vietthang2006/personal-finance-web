from decimal import Decimal
from uuid import UUID

from sqlalchemy import case, func, select, update
from sqlalchemy.orm import Session

from app.models.goal import GoalContribution, SavingsGoal
from app.repositories.base import BaseRepository


class GoalRepository(BaseRepository[SavingsGoal]):
    def __init__(self, db: Session) -> None:
        super().__init__(db)

    def create(self, goal: SavingsGoal) -> SavingsGoal:
        """Adds a savings goal to the session and flushes. Does not commit."""
        self.db.add(goal)
        self.db.flush()
        return goal

    def get_by_id(
        self, goal_id: UUID, user_id: UUID, for_update: bool = False
    ) -> SavingsGoal | None:
        """Finds a savings goal by ID and user_id, optionally locking the row FOR UPDATE."""
        stmt = select(SavingsGoal).where(
            SavingsGoal.id == goal_id,
            SavingsGoal.user_id == user_id,
        )
        if for_update:
            stmt = stmt.with_for_update()
        return self.db.scalar(stmt)

    def get_for_update(self, goal_id: UUID, user_id: UUID) -> SavingsGoal | None:
        """Convenience method to retrieve and lock a savings goal FOR UPDATE."""
        return self.get_by_id(goal_id, user_id, for_update=True)

    def exists_by_name(
        self, user_id: UUID, name: str, exclude_id: UUID | None = None
    ) -> bool:
        """Checks if a savings goal with the given name (case-insensitive) already exists for the user."""
        stmt = select(
            select(SavingsGoal.id)
            .where(
                SavingsGoal.user_id == user_id,
                func.lower(SavingsGoal.name) == name.strip().lower(),
            )
            .exists()
        )
        if exclude_id is not None:
            stmt = select(
                select(SavingsGoal.id)
                .where(
                    SavingsGoal.user_id == user_id,
                    func.lower(SavingsGoal.name) == name.strip().lower(),
                    SavingsGoal.id != exclude_id,
                )
                .exists()
            )
        return bool(self.db.scalar(stmt))

    def list_by_user(
        self,
        user_id: UUID,
        status: str | None = None,
        offset: int = 0,
        limit: int | None = None,
    ) -> list[SavingsGoal]:
        """Lists savings goals for a user.
        Sorts active goals first, then by deadline ASC NULLS LAST, and created_at DESC (Query Q10).
        """
        stmt = select(SavingsGoal).where(SavingsGoal.user_id == user_id)
        if status is not None:
            stmt = stmt.where(SavingsGoal.status == status)

        # Q10 ordering: status = 'active' first, then deadline ASC NULLS LAST, created_at DESC
        stmt = stmt.order_by(
            case((SavingsGoal.status == "active", 0), else_=1).asc(),
            SavingsGoal.deadline.asc().nulls_last(),
            SavingsGoal.created_at.desc(),
        )
        if offset > 0:
            stmt = stmt.offset(offset)
        if limit is not None:
            stmt = stmt.limit(limit)

        return list(self.db.scalars(stmt).all())

    def update(self, goal: SavingsGoal) -> SavingsGoal:
        """Flushes session updates to savings goal."""
        self.db.flush()
        return goal

    def delete(self, goal: SavingsGoal) -> None:
        """Deletes a savings goal and flushes."""
        self.db.delete(goal)
        self.db.flush()

    def add_contribution(self, contribution: GoalContribution) -> GoalContribution:
        """Adds a contribution record to the session and flushes."""
        self.db.add(contribution)
        self.db.flush()
        return contribution

    def get_contribution(self, contribution_id: UUID) -> GoalContribution | None:
        """Finds a contribution record by ID."""
        stmt = select(GoalContribution).where(GoalContribution.id == contribution_id)
        return self.db.scalar(stmt)

    def list_contributions(self, goal_id: UUID) -> list[GoalContribution]:
        """Lists contributions for a goal ordered by contributed_at DESC."""
        stmt = (
            select(GoalContribution)
            .where(GoalContribution.goal_id == goal_id)
            .order_by(GoalContribution.contributed_at.desc())
        )
        return list(self.db.scalars(stmt).all())

    def increment_current_atomic(
        self, goal_id: UUID, amount: Decimal
    ) -> SavingsGoal | None:
        """Atomically increments current_amount on savings_goals.
        Transitions status to 'achieved' and sets achieved_at=now() if current_amount + amount >= target_amount.
        Returns the updated SavingsGoal row.
        """
        new_amount = SavingsGoal.current_amount + amount
        is_achieved = new_amount >= SavingsGoal.target_amount
        stmt = (
            update(SavingsGoal)
            .where(SavingsGoal.id == goal_id)
            .values(
                current_amount=new_amount,
                status=case((is_achieved, "achieved"), else_=SavingsGoal.status),
                achieved_at=case((is_achieved, func.now()), else_=SavingsGoal.achieved_at),
            )
            .returning(SavingsGoal)
        )
        updated = self.db.scalar(stmt)
        if updated is not None:
            self.db.flush()
        return updated
