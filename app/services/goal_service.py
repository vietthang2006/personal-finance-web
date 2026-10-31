from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models.goal import GoalContribution, SavingsGoal
from app.models.system import Notification
from app.models.transaction import Transaction
from app.models.user import User
from app.repositories.account_repository import AccountRepository
from app.repositories.audit_log_repository import AuditLogRepository
from app.repositories.category_repository import CategoryRepository
from app.repositories.goal_repository import GoalRepository
from app.repositories.notification_repository import NotificationRepository
from app.repositories.transaction_repository import TransactionRepository
from app.schemas.goal import (
    GoalContributeAccountSummary,
    GoalContributeResponse,
    GoalContributionCreate,
    GoalContributionRead,
    GoalCreate,
    GoalRead,
    GoalUpdate,
)


def get_user_today(user_timezone: str | None = None) -> date:
    """Returns the current date in the user's configured timezone, or UTC as fallback."""
    if user_timezone:
        try:
            from zoneinfo import ZoneInfo
            return datetime.now(ZoneInfo(user_timezone)).date()
        except Exception:
            pass
    return datetime.now(timezone.utc).date()


class GoalService:
    def __init__(
        self,
        db: Session,
        goal_repo: GoalRepository,
        account_repo: AccountRepository,
        category_repo: CategoryRepository,
        transaction_repo: TransactionRepository,
        notification_repo: NotificationRepository,
        audit_repo: AuditLogRepository,
        budget_service: Any = None,
    ) -> None:
        self.db = db
        self.goal_repo = goal_repo
        self.account_repo = account_repo
        self.category_repo = category_repo
        self.transaction_repo = transaction_repo
        self.notification_repo = notification_repo
        self.audit_repo = audit_repo
        self.budget_service = budget_service

    def create_goal(self, user: User, data: GoalCreate) -> SavingsGoal:
        """Creates a new active savings goal for the user (BR-G01)."""
        today = get_user_today(getattr(user, "timezone", None))
        if data.deadline is not None and data.deadline <= today:
            raise AppError(
                code="INVALID_DEADLINE",
                status_code=422,
                message="Deadline must be in the future",
            )

        if self.goal_repo.exists_by_name(user.id, data.name):
            raise AppError(
                code="GOAL_NAME_TAKEN",
                status_code=409,
                message="A savings goal with this name already exists",
            )

        now = datetime.now(timezone.utc)
        goal = SavingsGoal(
            id=uuid4(),
            user_id=user.id,
            name=data.name,
            description=data.description,
            target_amount=data.target_amount,
            current_amount=Decimal("0.00"),
            deadline=data.deadline,
            status="active",
            created_at=now,
            updated_at=now,
        )

        try:
            self.goal_repo.create(goal)
            if getattr(self, "audit_repo", None) is not None:
                self.audit_repo.log(
                    action="CREATE_GOAL",
                    entity_type="savings_goal",
                    actor_id=user.id,
                    entity_id=str(goal.id),
                    changes=data.model_dump(mode="json"),
                )
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            raise AppError(
                code="GOAL_NAME_TAKEN",
                status_code=409,
                message="A savings goal with this name already exists",
            ) from exc

        self.db.refresh(goal)
        return goal

    def get_goal(self, user_id: UUID, goal_id: UUID) -> SavingsGoal:
        """Retrieves a savings goal by id for the given user."""
        goal = self.goal_repo.get_by_id(goal_id, user_id)
        if goal is None:
            raise AppError(
                code="GOAL_NOT_FOUND",
                status_code=404,
                message="Savings goal not found",
            )
        return goal

    def list_goals(
        self,
        user_id: UUID,
        status_filter: str | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> list[SavingsGoal]:
        """Lists savings goals for a user using Q10 ordering."""
        return self.goal_repo.list_by_user(
            user_id=user_id,
            status=status_filter,
            offset=offset,
            limit=limit,
        )

    def get_goal_detail(
        self, user_id: UUID, goal_id: UUID
    ) -> tuple[SavingsGoal, list[GoalContribution]]:
        """Retrieves a savings goal and its full contribution history."""
        goal = self.get_goal(user_id, goal_id)
        contributions = self.goal_repo.list_contributions(goal_id)
        return goal, contributions

    def update_goal(self, user: User, goal_id: UUID, data: GoalUpdate) -> SavingsGoal:
        """Updates goal details (name, description, target_amount, deadline) (BR-G09)."""
        goal = self.goal_repo.get_for_update(goal_id, user.id)
        if goal is None:
            raise AppError(
                code="GOAL_NOT_FOUND",
                status_code=404,
                message="Savings goal not found",
            )

        if goal.status != "active":
            raise AppError(
                code="GOAL_NOT_ACTIVE",
                status_code=409,
                message="Cannot update an achieved or cancelled goal",
            )

        if data.name is not None and data.name.strip().lower() != goal.name.lower():
            if self.goal_repo.exists_by_name(user.id, data.name, exclude_id=goal.id):
                raise AppError(
                    code="GOAL_NAME_TAKEN",
                    status_code=409,
                    message="A savings goal with this name already exists",
                )
            goal.name = data.name

        if data.description is not None:
            goal.description = data.description

        if data.target_amount is not None:
            if data.target_amount < goal.current_amount:
                raise AppError(
                    code="GOAL_OVER_TARGET",
                    status_code=422,
                    message="Target amount cannot be less than current amount already saved",
                )
            goal.target_amount = data.target_amount

        if data.deadline is not None:
            today = get_user_today(getattr(user, "timezone", None))
            if data.deadline <= today:
                raise AppError(
                    code="INVALID_DEADLINE",
                    status_code=422,
                    message="Deadline must be in the future",
                )
            goal.deadline = data.deadline

        try:
            self.goal_repo.update(goal)
            if getattr(self, "audit_repo", None) is not None:
                self.audit_repo.log(
                    action="UPDATE_GOAL",
                    entity_type="savings_goal",
                    actor_id=user.id,
                    entity_id=str(goal.id),
                    changes=data.model_dump(exclude_unset=True, mode="json"),
                )
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            raise AppError(
                code="GOAL_NAME_TAKEN",
                status_code=409,
                message="A savings goal with this name already exists",
            ) from exc

        self.db.refresh(goal)
        return goal

    def cancel_goal(self, user: User, goal_id: UUID) -> SavingsGoal:
        """Cancels an active savings goal without reverting past transactions (BR-G08)."""
        goal = self.goal_repo.get_for_update(goal_id, user.id)
        if goal is None:
            raise AppError(
                code="GOAL_NOT_FOUND",
                status_code=404,
                message="Savings goal not found",
            )

        if goal.status != "active":
            raise AppError(
                code="GOAL_NOT_ACTIVE",
                status_code=409,
                message="Only active goals can be cancelled",
            )

        goal.status = "cancelled"
        self.goal_repo.update(goal)

        if getattr(self, "audit_repo", None) is not None:
            self.audit_repo.log(
                action="CANCEL_GOAL",
                entity_type="savings_goal",
                actor_id=user.id,
                entity_id=str(goal.id),
            )

        self.db.commit()
        self.db.refresh(goal)
        return goal

    def contribute(
        self, user: User, goal_id: UUID, data: GoalContributionCreate
    ) -> GoalContributeResponse:
        """Executes the 11-step Core Workflow W11: contributes funds from an account to a savings goal."""
        today = get_user_today(getattr(user, "timezone", None))

        try:
            # Step 1: Lock goal FOR UPDATE (anti-deadlock: goal before account)
            goal = self.goal_repo.get_for_update(goal_id, user.id)
            if goal is None:
                raise AppError(
                    code="GOAL_NOT_FOUND",
                    status_code=404,
                    message="Savings goal not found",
                )

            # Step 2: Validate goal is active (BR-G02)
            if goal.status != "active":
                raise AppError(
                    code="GOAL_NOT_ACTIVE",
                    status_code=409,
                    message="Goal is not active",
                )

            # Step 3: Validate contribution does not exceed remaining target (BR-G04)
            remaining = goal.target_amount - goal.current_amount
            if data.amount > remaining:
                raise AppError(
                    code="GOAL_OVER_TARGET",
                    status_code=422,
                    message="Contribution amount exceeds remaining goal target",
                )

            # Step 4: Lock account FOR UPDATE
            account = self.account_repo.get_for_update(data.account_id, user.id)
            if account is None:
                raise AppError(
                    code="ACCOUNT_NOT_FOUND",
                    status_code=404,
                    message="Account not found",
                )

            # Step 5: Check account validity & default currency (BR-G03)
            if getattr(account, "is_archived", False):
                raise AppError(
                    code="ACCOUNT_ARCHIVED",
                    status_code=422,
                    message="Cannot contribute from an archived account",
                )

            user_currency = getattr(user, "default_currency", "VND")
            if account.currency_code != user_currency:
                raise AppError(
                    code="CURRENCY_MISMATCH",
                    status_code=422,
                    message=f"Account currency {account.currency_code} does not match user default currency {user_currency}",
                )

            # Step 6: Find seeded SAVING system category
            category = self.category_repo.get_system_by_code("SAVING", kind="expense")
            if not category:
                raise AppError(
                    code="CATEGORY_NOT_FOUND",
                    status_code=500,
                    message="System category 'SAVING' is missing. Please ensure migrations have been applied.",
                )
            category_id = category.id

            # Step 7: Record expense transaction linked to goal (source='goal')
            now = datetime.now(timezone.utc)
            tx = Transaction(
                id=uuid4(),
                user_id=user.id,
                account_id=account.id,
                kind="expense",
                category_id=category_id,
                amount=data.amount,
                transaction_date=today,
                description=f"Góp tiền tiết kiệm: {goal.name}",
                source="goal",
                created_at=now,
                updated_at=now,
            )
            self.transaction_repo.create_transaction(tx)

            # Step 8: Deduct account balance atomically
            new_balance = self.account_repo.update_balance_atomic(
                account.id, user.id, -data.amount
            )
            if new_balance is None:
                raise AppError(
                    code="INSUFFICIENT_FUNDS",
                    status_code=422,
                    message="Account has insufficient funds to make this contribution",
                )

            # Step 9: Record goal contribution
            contribution = GoalContribution(
                id=uuid4(),
                goal_id=goal.id,
                transaction_id=tx.id,
                amount=data.amount,
                contributed_at=now,
            )
            self.goal_repo.add_contribution(contribution)

            # Step 10: Increment current_amount and transition status if achieved (BR-G06)
            updated_goal = self.goal_repo.increment_current_atomic(goal.id, data.amount)
            if updated_goal is None:
                raise AppError(
                    code="GOAL_OVER_TARGET",
                    status_code=422,
                    message="Contribution exceeds goal target or goal is no longer active",
                )

            if updated_goal.status == "achieved":
                idempotency_key = f"goal_achieved:{goal.id}"
                existing_notif = None
                if getattr(self, "notification_repo", None) is not None:
                    if hasattr(self.notification_repo, "get_by_idempotency_key"):
                        existing_notif = self.notification_repo.get_by_idempotency_key(
                            user.id, idempotency_key
                        )
                    if not existing_notif:
                        notif = Notification(
                            user_id=user.id,
                            kind="goal_achieved",
                            title="Mục tiêu tiết kiệm hoàn thành",
                            body=f"Chúc mừng bạn! Mục tiêu '{updated_goal.name}' đã hoàn thành 100%.",
                            idempotency_key=idempotency_key,
                            status="unread",
                        )
                        self.notification_repo.create(notif)

            # Step 11: Audit log and single commit
            if getattr(self, "audit_repo", None) is not None:
                self.audit_repo.log(
                    action="CONTRIBUTE_GOAL",
                    entity_type="savings_goal",
                    actor_id=user.id,
                    entity_id=str(goal.id),
                    changes={
                        "amount": str(data.amount),
                        "account_id": str(account.id),
                        "transaction_id": str(tx.id),
                        "new_balance": str(new_balance),
                    },
                )

            self.db.commit()
        except Exception:
            self.db.rollback()
            raise

        # Post-commit budget rearm and evaluate
        if getattr(self, "budget_service", None) is not None:
            try:
                if hasattr(self.budget_service, "rearm_and_evaluate"):
                    self.budget_service.rearm_and_evaluate(user.id, today)
            except Exception:
                pass

        try:
            self.db.refresh(updated_goal)
        except Exception:
            pass

        return GoalContributeResponse(
            contribution=GoalContributionRead.model_validate(contribution),
            goal=GoalRead.model_validate(updated_goal),
            account=GoalContributeAccountSummary(id=account.id, new_balance=new_balance),
        )
