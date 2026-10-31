from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models.budget import Budget, BudgetAlertEvent, BudgetCategory
from app.models.system import Notification
from app.repositories.audit_log_repository import AuditLogRepository
from app.repositories.budget_repository import BudgetRepository
from app.repositories.category_repository import CategoryRepository
from app.repositories.notification_repository import NotificationRepository
from app.schemas.budget import (
    BudgetCategoryCreate,
    BudgetCategoryProgressRead,
    BudgetCategoryUpdate,
    BudgetCreate,
    BudgetProgressRead,
    BudgetUpdate,
)


class BudgetServiceError(AppError):
    def __init__(self, message: str, status_code: int = 400, code: str = "BUDGET_ERROR"):
        super().__init__(code=code, status_code=status_code, message=message)


class BudgetNotFoundError(BudgetServiceError):
    def __init__(self, message: str = "Budget not found"):
        super().__init__(message=message, status_code=404, code="BUDGET_NOT_FOUND")


class BudgetValidationError(BudgetServiceError):
    def __init__(self, message: str = "Budget validation failed", status_code: int = 400):
        super().__init__(message=message, status_code=status_code, code="BUDGET_VALIDATION_ERROR")


class BudgetConflictError(BudgetServiceError):
    def __init__(self, message: str = "Budget conflict", status_code: int = 400):
        super().__init__(message=message, status_code=status_code, code="BUDGET_CONFLICT")


class BudgetService:
    def __init__(
        self,
        db: Session,
        budget_repo: BudgetRepository | None = None,
        category_repo: CategoryRepository | None = None,
        notification_repo: NotificationRepository | None = None,
        audit_repo: AuditLogRepository | None = None,
    ) -> None:
        self.db = db
        self.budget_repo = budget_repo or BudgetRepository(db)
        self.category_repo = category_repo or CategoryRepository(db)
        self.notification_repo = notification_repo or NotificationRepository(db)
        self.audit_repo = audit_repo or AuditLogRepository(db)

    def create_budget(self, user_id: UUID, payload: BudgetCreate) -> Budget:
        if payload.end_date < payload.start_date:
            raise BudgetValidationError("end_date must not be before start_date")

        if payload.total_limit <= Decimal("0"):
            raise BudgetValidationError("total_limit must be strictly positive")

        total_cat_limit = Decimal("0.00")
        seen_categories: set[int] = set()

        for cat_item in payload.categories:
            if cat_item.category_id in seen_categories:
                raise BudgetConflictError(
                    f"Duplicate category_id {cat_item.category_id} in budget allocation"
                )
            seen_categories.add(cat_item.category_id)

            category = self.category_repo.get_visible(cat_item.category_id, user_id)
            if not category or category.kind != "expense":
                raise BudgetValidationError(
                    f"Category {cat_item.category_id} is not an expense category or not found"
                )
            total_cat_limit += cat_item.limit_amount

        if total_cat_limit > payload.total_limit:
            raise BudgetValidationError(
                f"Sum of category limits ({total_cat_limit}) cannot exceed budget total_limit ({payload.total_limit})"
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

        if getattr(self, "audit_repo", None) is not None:
            self.audit_repo.log(
                action="CREATE",
                entity_type="budget",
                actor_id=user_id,
                entity_id=str(budget.id),
                changes={
                    "name": payload.name,
                    "total_limit": str(payload.total_limit),
                    "period_type": payload.period_type,
                },
            )

        self.db.commit()
        return self.budget_repo.get_budget(budget.id, user_id) or budget

    def get_budget(self, user_id: UUID, budget_id: UUID) -> Budget:
        budget = self.budget_repo.get_budget(budget_id, user_id)
        if not budget:
            raise BudgetNotFoundError("Budget not found")
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

        new_start = payload.start_date if payload.start_date is not None else budget.start_date
        new_end = payload.end_date if payload.end_date is not None else budget.end_date
        if new_end < new_start:
            raise BudgetValidationError("end_date must not be before start_date")

        if payload.total_limit is not None:
            if payload.total_limit <= Decimal("0"):
                raise BudgetValidationError("total_limit must be strictly positive")
            existing_total = sum(c.limit_amount for c in budget.categories)
            if existing_total > payload.total_limit:
                raise BudgetValidationError(
                    f"New total_limit ({payload.total_limit}) is less than current category allocations sum ({existing_total})"
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

        if getattr(self, "audit_repo", None) is not None:
            self.audit_repo.log(
                action="UPDATE",
                entity_type="budget",
                actor_id=user_id,
                entity_id=str(budget.id),
                changes=payload.model_dump(exclude_unset=True),
            )

        self.db.commit()
        return budget

    def delete_budget(self, user_id: UUID, budget_id: UUID) -> None:
        budget = self.get_budget(user_id, budget_id)
        self.budget_repo.delete_budget(budget)

        if getattr(self, "audit_repo", None) is not None:
            self.audit_repo.log(
                action="DELETE",
                entity_type="budget",
                actor_id=user_id,
                entity_id=str(budget_id),
            )

        self.db.commit()

    def add_category_limit(
        self, user_id: UUID, budget_id: UUID, payload: BudgetCategoryCreate
    ) -> BudgetCategory:
        budget = self.get_budget(user_id, budget_id)

        category = self.category_repo.get_visible(payload.category_id, user_id)
        if not category or category.kind != "expense":
            raise BudgetValidationError(
                f"Category {payload.category_id} is not an expense category or not found"
            )

        existing = self.budget_repo.get_budget_category_by_category_id(budget_id, payload.category_id)
        if existing:
            raise BudgetConflictError(
                f"Category {payload.category_id} is already allocated in this budget"
            )

        current_sum = sum(c.limit_amount for c in budget.categories)
        if current_sum + payload.limit_amount > budget.total_limit:
            raise BudgetValidationError(
                f"Adding limit {payload.limit_amount} exceeds budget total_limit (remaining capacity: {budget.total_limit - current_sum})"
            )

        bc = BudgetCategory(
            budget_id=budget_id,
            category_id=payload.category_id,
            category_kind="expense",
            limit_amount=payload.limit_amount,
            warn_percent=payload.warn_percent,
        )
        self.budget_repo.add_budget_category(bc)

        if getattr(self, "audit_repo", None) is not None:
            self.audit_repo.log(
                action="CREATE",
                entity_type="budget_category",
                actor_id=user_id,
                entity_id=str(bc.id),
                changes=payload.model_dump(),
            )

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
            raise BudgetNotFoundError(f"Category {category_id} is not allocated in this budget")

        if payload.limit_amount is not None:
            if payload.limit_amount <= Decimal("0"):
                raise BudgetValidationError("limit_amount must be strictly positive")
            other_sum = sum(c.limit_amount for c in budget.categories if c.category_id != category_id)
            if other_sum + payload.limit_amount > budget.total_limit:
                raise BudgetValidationError(
                    f"New limit {payload.limit_amount} exceeds budget total_limit (remaining capacity: {budget.total_limit - other_sum})"
                )
            bc.limit_amount = payload.limit_amount

        if payload.warn_percent is not None:
            bc.warn_percent = payload.warn_percent

        if getattr(self, "audit_repo", None) is not None:
            self.audit_repo.log(
                action="UPDATE",
                entity_type="budget_category",
                actor_id=user_id,
                entity_id=str(bc.id),
                changes=payload.model_dump(exclude_unset=True),
            )

        self.db.commit()
        return bc

    def delete_category_limit(self, user_id: UUID, budget_id: UUID, category_id: int) -> None:
        self.get_budget(user_id, budget_id)
        bc = self.budget_repo.get_budget_category_by_category_id(budget_id, category_id)
        if not bc:
            raise BudgetNotFoundError(f"Category {category_id} is not allocated in this budget")

        self.budget_repo.delete_budget_category(bc)

        if getattr(self, "audit_repo", None) is not None:
            self.audit_repo.log(
                action="DELETE",
                entity_type="budget_category",
                actor_id=user_id,
                entity_id=str(bc.id),
            )

        self.db.commit()

    def _trigger_alert(
        self,
        user_id: UUID,
        bc: BudgetCategory,
        level: str,
        spent: Decimal,
        percent: Decimal,
        budget_name: str,
    ) -> BudgetAlertEvent | None:
        existing = self.budget_repo.get_alert_event(bc.id, level)
        if existing:
            return existing

        notif_id = None
        if getattr(self, "notification_repo", None) is not None:
            idempotency_key = f"budget_{bc.id}_{level}"
            notif = self.notification_repo.get_by_idempotency_key(user_id, idempotency_key)
            if not notif:
                title = (
                    f"Cảnh báo ngân sách: {budget_name}"
                    if level == "warning"
                    else f"Vượt ngân sách: {budget_name}"
                )
                cat_name = bc.category.name if getattr(bc, "category", None) and hasattr(bc.category, "name") else f"danh mục {bc.category_id}"
                body = (
                    f"Chi tiêu danh mục {cat_name} đã đạt {percent}% ({spent}đ) so với hạn mức {bc.limit_amount}đ."
                )
                notif = Notification(
                    user_id=user_id,
                    kind=f"budget_{level}",
                    title=title,
                    body=body,
                    status="unread",
                    idempotency_key=idempotency_key,
                )
                self.notification_repo.create(notif)
            notif_id = notif.id

        alert = BudgetAlertEvent(
            budget_category_id=bc.id,
            level=level,
            spent_amount=spent,
            percent_used=percent,
            notification_id=notif_id,
        )
        try:
            self.budget_repo.create_alert_event(alert)
            return alert
        except IntegrityError:
            self.db.rollback()
            return None

    def calculate_progress(
        self, user_id: UUID, budget_id: UUID, auto_trigger_alerts: bool = True
    ) -> BudgetProgressRead:
        budget = self.get_budget(user_id, budget_id)

        categories_progress: list[BudgetCategoryProgressRead] = []
        alerts_changed = False

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
                if percent >= Decimal(str(bc.warn_percent)):
                    res = self._trigger_alert(user_id, bc, "warning", spent, percent, budget.name)
                    if res:
                        alerts_changed = True
                if percent >= Decimal("100.00"):
                    res = self._trigger_alert(user_id, bc, "exceeded", spent, percent, budget.name)
                    if res:
                        alerts_changed = True

        if alerts_changed:
            try:
                self.db.commit()
            except IntegrityError:
                self.db.rollback()

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

    def rearm_and_evaluate(
        self, user_id: UUID, target_date: date | None = None
    ) -> list[BudgetProgressRead]:
        """Rearms (resets) alerts if spending has dropped below thresholds, and evaluates current status."""
        check_date = target_date or datetime.now(timezone.utc).date()
        active_budgets = self.budget_repo.list_active_budgets_for_date(user_id, check_date)
        results: list[BudgetProgressRead] = []

        for budget in active_budgets:
            for bc in budget.categories:
                spent = self.budget_repo.get_spent_amount_by_category(
                    user_id=user_id,
                    category_id=bc.category_id,
                    start_date=budget.start_date,
                    end_date=budget.end_date,
                )
                percent = (
                    (spent / bc.limit_amount * Decimal("100")).quantize(Decimal("0.01"))
                    if bc.limit_amount > 0
                    else Decimal("0.00")
                )

                # Rearm warning if spent dropped below warn_percent
                if percent < Decimal(str(bc.warn_percent)):
                    warn_alert = self.budget_repo.get_alert_event(bc.id, "warning")
                    if warn_alert:
                        self.budget_repo.delete_alert_event(warn_alert)

                # Rearm exceeded if spent dropped below 100%
                if percent < Decimal("100.00"):
                    exc_alert = self.budget_repo.get_alert_event(bc.id, "exceeded")
                    if exc_alert:
                        self.budget_repo.delete_alert_event(exc_alert)

            progress = self.calculate_progress(user_id, budget.id, auto_trigger_alerts=True)
            results.append(progress)

        try:
            self.db.commit()
        except Exception:
            self.db.rollback()

        return results

    def list_alerts(self, user_id: UUID, budget_id: UUID) -> list[BudgetAlertEvent]:
        self.get_budget(user_id, budget_id)
        return self.budget_repo.list_alert_events_by_budget(budget_id)
