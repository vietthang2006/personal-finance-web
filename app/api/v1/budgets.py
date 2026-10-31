from uuid import UUID

from fastapi import APIRouter, Query, status

from app.api.deps import BudgetServiceDep, CurrentUser
from app.schemas.budget import (
    BudgetAlertEventRead,
    BudgetCategoryCreate,
    BudgetCategoryRead,
    BudgetCategoryUpdate,
    BudgetCreate,
    BudgetDetailRead,
    BudgetProgressRead,
    BudgetUpdate,
)

router = APIRouter(prefix="/budgets", tags=["budgets"])


@router.post("", response_model=BudgetDetailRead, status_code=status.HTTP_201_CREATED)
def create_budget(
    payload: BudgetCreate,
    user: CurrentUser,
    service: BudgetServiceDep,
) -> BudgetDetailRead:
    budget = service.create_budget(user.id, payload)
    return BudgetDetailRead.model_validate(budget)


@router.get("", response_model=list[BudgetDetailRead])
def list_budgets(
    user: CurrentUser,
    service: BudgetServiceDep,
    status_filter: str | None = Query(default=None, alias="status"),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
) -> list[BudgetDetailRead]:
    budgets = service.list_budgets(
        user_id=user.id,
        status_filter=status_filter,
        offset=offset,
        limit=limit,
    )
    return [BudgetDetailRead.model_validate(b) for b in budgets]


@router.get("/{budget_id}", response_model=BudgetDetailRead)
def get_budget(
    budget_id: UUID,
    user: CurrentUser,
    service: BudgetServiceDep,
) -> BudgetDetailRead:
    budget = service.get_budget(user.id, budget_id)
    return BudgetDetailRead.model_validate(budget)


@router.put("/{budget_id}", response_model=BudgetDetailRead)
def update_budget(
    budget_id: UUID,
    payload: BudgetUpdate,
    user: CurrentUser,
    service: BudgetServiceDep,
) -> BudgetDetailRead:
    budget = service.update_budget(user.id, budget_id, payload)
    return BudgetDetailRead.model_validate(budget)


@router.delete("/{budget_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_budget(
    budget_id: UUID,
    user: CurrentUser,
    service: BudgetServiceDep,
) -> None:
    service.delete_budget(user.id, budget_id)


@router.post("/{budget_id}/categories", response_model=BudgetCategoryRead, status_code=status.HTTP_201_CREATED)
def add_category_limit(
    budget_id: UUID,
    payload: BudgetCategoryCreate,
    user: CurrentUser,
    service: BudgetServiceDep,
) -> BudgetCategoryRead:
    bc = service.add_category_limit(user.id, budget_id, payload)
    return BudgetCategoryRead.model_validate(bc)


@router.put("/{budget_id}/categories/{category_id}", response_model=BudgetCategoryRead)
def update_category_limit(
    budget_id: UUID,
    category_id: int,
    payload: BudgetCategoryUpdate,
    user: CurrentUser,
    service: BudgetServiceDep,
) -> BudgetCategoryRead:
    bc = service.update_category_limit(user.id, budget_id, category_id, payload)
    return BudgetCategoryRead.model_validate(bc)


@router.delete("/{budget_id}/categories/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_category_limit(
    budget_id: UUID,
    category_id: int,
    user: CurrentUser,
    service: BudgetServiceDep,
) -> None:
    service.delete_category_limit(user.id, budget_id, category_id)


@router.get("/{budget_id}/progress", response_model=BudgetProgressRead)
def get_budget_progress(
    budget_id: UUID,
    user: CurrentUser,
    service: BudgetServiceDep,
) -> BudgetProgressRead:
    return service.calculate_progress(user.id, budget_id)


@router.get("/{budget_id}/alerts", response_model=list[BudgetAlertEventRead])
def list_budget_alerts(
    budget_id: UUID,
    user: CurrentUser,
    service: BudgetServiceDep,
) -> list[BudgetAlertEventRead]:
    alerts = service.list_alerts(user.id, budget_id)
    return [BudgetAlertEventRead.model_validate(a) for a in alerts]
