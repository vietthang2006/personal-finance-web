from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.budget import Budget, BudgetAlertEvent, BudgetCategory
from app.repositories.budget_repository import BudgetRepository
from app.repositories.category_repository import CategoryRepository
from app.schemas.budget import (
    BudgetCategoryCreate,
    BudgetCategoryProgressRead,
    BudgetCategoryUpdate,
    BudgetCreate,
    BudgetProgressRead,
    BudgetUpdate,
)


class BudgetService:
    def __init__(
        self,
        db: Session,
        budget_repo: BudgetRepository | None = None,
        category_repo: CategoryRepository | None = None,
    ) -> None:
        self.db = db
        self.budget_repo = budget_repo or BudgetRepository(db)
        self.category_repo = category_repo or CategoryRepository(db)

    def create_budget(self, user_id: UUID, payload: BudgetCreate) -> Budget:
        # Validate categories if provided
        total_cat_limit = Decimal("0.00")
        seen_categories: set[int] = set()

        for cat_item in payload.categories:
            if cat_item.category_id in seen_categories:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Duplicate category_id {cat_item.category_id} in budget allocation",
                )
            seen_categories.add(cat_item.category_id)

            category = self.category_repo.get_visible(cat_item.category_id, user_id)
            if not category or category.kind != "expense":
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Category {cat_item.category_id} is not an expense category or not found",
                )
            total_cat_limit += cat_item.limit_amount

        if total_cat_limit > payload.total_limit:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Sum of category limits cannot exceed budget total_limit",
            )

        budget = Budget(
            user_id=user_id,
            name=payload.name,
            period_type=payload.period_type,
            start_date=payload.start_date,
            end_date=payload.end_date,
            total_limit=payload.total_limit,
            status="active",
        )
        self.budget_repo.create_budget(budget)

        for cat_item in payload.categories:
            bc = BudgetCategory(
                budget_id=budget.id,
                category_id=cat_item.category_id,
                category_kind="expense",
                limit_amount=cat_item.limit_amount,
                warn_percent=cat_item.warn_percent,
            )
            self.budget_repo.add_budget_category(bc)

        self.db.commit()
        return self.budget_repo.get_budget(budget.id, user_id) or budget

    def get_budget(self, user_id: UUID, budget_id: UUID) -> Budget:
        budget = self.budget_repo.get_budget(budget_id, user_id)
        if not budget:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Budget not found",
            )
        return budget

    def list_budgets(
        self,
        user_id: UUID,
        status_filter: str | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> list[Budget]:
        return self.budget_repo.list_budgets(
            user_id=user_id,
            status=status_filter,
            offset=offset,
            limit=limit,
        )

    def update_budget(self, user_id: UUID, budget_id: UUID, payload: BudgetUpdate) -> Budget:
        budget = self.get_budget(user_id, budget_id)

        # Validate date range
        new_start = payload.start_date if payload.start_date is not None else budget.start_date
        new_end = payload.end_date if payload.end_date is not None else budget.end_date
        if new_end < new_start:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="end_date must not be before start_date",
            )

        # Validate total_limit against existing categories
        if payload.total_limit is not None:
            existing_total = sum(c.limit_amount for c in budget.categories)
            if existing_total > payload.total_limit:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"New total_limit ({payload.total_limit}) is less than current category allocations sum ({existing_total})",
                )
            budget.total_limit = payload.total_limit

        if payload.name is not None:
            budget.name = payload.name
        if payload.period_type is not None:
            budget.period_type = payload.period_type
        if payload.start_date is not None:
            budget.start_date = payload.start_date
        if payload.end_date is not None:
            budget.end_date = payload.end_date
        if payload.status is not None:
            budget.status = payload.status

        self.budget_repo.update_budget(budget)
        self.db.commit()
        return budget

    def delete_budget(self, user_id: UUID, budget_id: UUID) -> None:
        budget = self.get_budget(user_id, budget_id)
        self.budget_repo.delete_budget(budget)
        self.db.commit()

    def add_category_limit(
        self, user_id: UUID, budget_id: UUID, payload: BudgetCategoryCreate
    ) -> BudgetCategory:
        budget = self.get_budget(user_id, budget_id)

        # Validate category
        category = self.category_repo.get_visible(payload.category_id, user_id)
        if not category or category.kind != "expense":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Category {payload.category_id} is not an expense category or not found",
            )

        # Check duplicate
        existing = self.budget_repo.get_budget_category_by_category_id(budget_id, payload.category_id)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Category {payload.category_id} is already allocated in this budget",
            )

        # Check total limits
        current_sum = sum(c.limit_amount for c in budget.categories)
        if current_sum + payload.limit_amount > budget.total_limit:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Adding limit {payload.limit_amount} exceeds budget total_limit (remaining capacity: {budget.total_limit - current_sum})",
            )

        bc = BudgetCategory(
            budget_id=budget_id,
            category_id=payload.category_id,
            category_kind="expense",
            limit_amount=payload.limit_amount,
            warn_percent=payload.warn_percent,
        )
        self.budget_repo.add_budget_category(bc)
        self.db.commit()
        return bc

    def update_category_limit(
        self,
        user_id: UUID,
        budget_id: UUID,
        category_id: int,
        payload: BudgetCategoryUpdate,
    ) -> BudgetCategory:
        budget = self.get_budget(user_id, budget_id)
        bc = self.budget_repo.get_budget_category_by_category_id(budget_id, category_id)
        if not bc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Category {category_id} is not allocated in this budget",
            )

        if payload.limit_amount is not None:
            other_sum = sum(c.limit_amount for c in budget.categories if c.category_id != category_id)
            if other_sum + payload.limit_amount > budget.total_limit:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"New limit {payload.limit_amount} exceeds budget total_limit (remaining capacity: {budget.total_limit - other_sum})",
                )
            bc.limit_amount = payload.limit_amount

        if payload.warn_percent is not None:
            bc.warn_percent = payload.warn_percent

        self.db.commit()
        return bc

    def delete_category_limit(self, user_id: UUID, budget_id: UUID, category_id: int) -> None:
        self.get_budget(user_id, budget_id)
        bc = self.budget_repo.get_budget_category_by_category_id(budget_id, category_id)
        if not bc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Category {category_id} is not allocated in this budget",
            )

        self.budget_repo.delete_budget_category(bc)
        self.db.commit()

    def calculate_progress(
        self, user_id: UUID, budget_id: UUID, auto_trigger_alerts: bool = True
    ) -> BudgetProgressRead:
        budget = self.get_budget(user_id, budget_id)

        categories_progress: list[BudgetCategoryProgressRead] = []
        alerts_to_commit = False

        for bc in budget.categories:
            spent = self.budget_repo.get_spent_amount_by_category(
                user_id=user_id,
                category_id=bc.category_id,
                start_date=budget.start_date,
                end_date=budget.end_date,
            )
            rem = max(Decimal("0.00"), bc.limit_amount - spent)
            percent = (
                (spent / bc.limit_amount * Decimal("100")).quantize(Decimal("0.01"))
                if bc.limit_amount > 0
                else Decimal("0.00")
            )
            is_warning = percent >= Decimal(str(bc.warn_percent)) and percent < Decimal("100.00")
            is_exceeded = percent >= Decimal("100.00")

            cat_name = bc.category.name if bc.category else f"Category {bc.category_id}"

            categories_progress.append(
                BudgetCategoryProgressRead(
                    category_id=bc.category_id,
                    category_name=cat_name,
                    limit_amount=bc.limit_amount,
                    spent_amount=spent,
                    remaining_amount=rem,
                    percent_used=percent,
                    warn_percent=bc.warn_percent,
                    is_warning=is_warning,
                    is_exceeded=is_exceeded,
                )
            )

            if auto_trigger_alerts:
                # 1. Warning level
                if percent >= Decimal(str(bc.warn_percent)):
                    existing_warn = self.budget_repo.get_alert_event(bc.id, "warning")
                    if not existing_warn:
                        alert = BudgetAlertEvent(
                            budget_category_id=bc.id,
                            level="warning",
                            spent_amount=spent,
                            percent_used=percent,
                        )
                        try:
                            self.budget_repo.create_alert_event(alert)
                            alerts_to_commit = True
                        except IntegrityError:
                            self.db.rollback()

                # 2. Exceeded level
                if percent >= Decimal("100.00"):
                    existing_exc = self.budget_repo.get_alert_event(bc.id, "exceeded")
                    if not existing_exc:
                        alert = BudgetAlertEvent(
                            budget_category_id=bc.id,
                            level="exceeded",
                            spent_amount=spent,
                            percent_used=percent,
                        )
                        try:
                            self.budget_repo.create_alert_event(alert)
                            alerts_to_commit = True
                        except IntegrityError:
                            self.db.rollback()

        if alerts_to_commit:
            try:
                self.db.commit()
            except IntegrityError:
                self.db.rollback()

        # Overall budget spending across all categories in the budget
        cat_ids = [bc.category_id for bc in budget.categories] if budget.categories else None
        total_spent = self.budget_repo.get_total_spent_for_budget(
            user_id=user_id,
            start_date=budget.start_date,
            end_date=budget.end_date,
            category_ids=cat_ids,
        )
        total_rem = max(Decimal("0.00"), budget.total_limit - total_spent)
        overall_percent = (
            (total_spent / budget.total_limit * Decimal("100")).quantize(Decimal("0.01"))
            if budget.total_limit > 0
            else Decimal("0.00")
        )

        return BudgetProgressRead(
            budget_id=budget.id,
            name=budget.name,
            period_type=budget.period_type,
            start_date=budget.start_date,
            end_date=budget.end_date,
            total_limit=budget.total_limit,
            total_spent=total_spent,
            total_remaining=total_rem,
            overall_percent_used=overall_percent,
            categories=categories_progress,
        )

    def list_alerts(self, user_id: UUID, budget_id: UUID) -> list[BudgetAlertEvent]:
        self.get_budget(user_id, budget_id)
        return self.budget_repo.list_alert_events_by_budget(budget_id)
