from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models.budget import Budget, BudgetAlertEvent, BudgetCategory
from app.models.transaction import Transaction
from app.repositories.base import BaseRepository


class BudgetRepository(BaseRepository[Budget]):
    def __init__(self, db: Session) -> None:
        super().__init__(db)

    def get_budget(self, budget_id: UUID, user_id: UUID) -> Budget | None:
        stmt = (
            select(Budget)
            .where(Budget.id == budget_id, Budget.user_id == user_id)
            .options(selectinload(Budget.categories).joinedload(BudgetCategory.category))
        )
        return self.db.scalar(stmt)

    def list_budgets(
        self,
        user_id: UUID,
        status: str | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> list[Budget]:
        stmt = (
            select(Budget)
            .where(Budget.user_id == user_id)
            .options(selectinload(Budget.categories).joinedload(BudgetCategory.category))
        )
        if status is not None:
            stmt = stmt.where(Budget.status == status)
        stmt = stmt.order_by(Budget.start_date.desc(), Budget.created_at.desc()).offset(offset).limit(limit)
        return list(self.db.scalars(stmt).all())

    def create_budget(self, budget: Budget) -> Budget:
        self.db.add(budget)
        self.db.flush()
        return budget

    def update_budget(self, budget: Budget) -> Budget:
        self.db.flush()
        return budget

    def delete_budget(self, budget: Budget) -> None:
        self.db.delete(budget)
        self.db.flush()

    def get_budget_category(self, budget_category_id: UUID, user_id: UUID) -> BudgetCategory | None:
        stmt = (
            select(BudgetCategory)
            .join(Budget, BudgetCategory.budget_id == Budget.id)
            .where(BudgetCategory.id == budget_category_id, Budget.user_id == user_id)
            .options(selectinload(BudgetCategory.alerts))
        )
        return self.db.scalar(stmt)

    def get_budget_category_by_category_id(
        self, budget_id: UUID, category_id: int
    ) -> BudgetCategory | None:
        stmt = select(BudgetCategory).where(
            BudgetCategory.budget_id == budget_id,
            BudgetCategory.category_id == category_id,
        )
        return self.db.scalar(stmt)

    def add_budget_category(self, item: BudgetCategory) -> BudgetCategory:
        self.db.add(item)
        self.db.flush()
        return item

    def delete_budget_category(self, item: BudgetCategory) -> None:
        self.db.delete(item)
        self.db.flush()

    def get_spent_amount_by_category(
        self, user_id: UUID, category_id: int, start_date: date, end_date: date
    ) -> Decimal:
        stmt = select(func.coalesce(func.sum(Transaction.amount), 0)).where(
            Transaction.user_id == user_id,
            Transaction.category_id == category_id,
            Transaction.kind == "expense",
            Transaction.transaction_date >= start_date,
            Transaction.transaction_date <= end_date,
        )
        val = self.db.scalar(stmt)
        return Decimal(str(val)) if val is not None else Decimal("0.00")

    def get_total_spent_for_budget(
        self,
        user_id: UUID,
        start_date: date,
        end_date: date,
        category_ids: list[int] | None = None,
    ) -> Decimal:
        stmt = select(func.coalesce(func.sum(Transaction.amount), 0)).where(
            Transaction.user_id == user_id,
            Transaction.kind == "expense",
            Transaction.transaction_date >= start_date,
            Transaction.transaction_date <= end_date,
        )
        if category_ids:
            stmt = stmt.where(Transaction.category_id.in_(category_ids))
        val = self.db.scalar(stmt)
        return Decimal(str(val)) if val is not None else Decimal("0.00")

    def get_alert_event(self, budget_category_id: UUID, level: str) -> BudgetAlertEvent | None:
        stmt = select(BudgetAlertEvent).where(
            BudgetAlertEvent.budget_category_id == budget_category_id,
            BudgetAlertEvent.level == level,
        )
        return self.db.scalar(stmt)

    def create_alert_event(self, alert: BudgetAlertEvent) -> BudgetAlertEvent:
        self.db.add(alert)
        self.db.flush()
        return alert

    def list_alert_events_by_budget(self, budget_id: UUID) -> list[BudgetAlertEvent]:
        stmt = (
            select(BudgetAlertEvent)
            .join(BudgetCategory, BudgetAlertEvent.budget_category_id == BudgetCategory.id)
            .where(BudgetCategory.budget_id == budget_id)
            .order_by(BudgetAlertEvent.triggered_at.desc())
        )
        return list(self.db.scalars(stmt).all())
