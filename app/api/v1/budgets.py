from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.api.deps import CurrentUser, DbSession
from app.models.budget import Budget
from app.schemas.budget import BudgetCreate, BudgetRead


router = APIRouter(prefix="/budgets", tags=["budgets"])


@router.post("", response_model=BudgetRead, status_code=status.HTTP_201_CREATED)
def create_budget(data: BudgetCreate, user: CurrentUser, db: DbSession) -> Budget:
    budget = Budget(
        user_id=user.id,
        name=data.name,
        period_type=data.period_type,
        start_date=data.start_date,
        end_date=data.end_date,
        total_limit=data.total_limit,
    )
    db.add(budget)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Budget period overlaps an existing active budget or violates a constraint",
        ) from exc
    db.refresh(budget)
    return budget


@router.get("", response_model=list[BudgetRead])
def list_budgets(
    user: CurrentUser,
    db: DbSession,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
) -> list[Budget]:
    return list(
        db.scalars(
            select(Budget)
            .where(Budget.user_id == user.id)
            .order_by(Budget.start_date.desc())
            .offset(offset)
            .limit(limit)
        ).all()
    )


@router.get("/{budget_id}", response_model=BudgetRead)
def get_budget(budget_id: UUID, user: CurrentUser, db: DbSession) -> Budget:
    budget = db.scalar(
        select(Budget).where(Budget.id == budget_id, Budget.user_id == user.id)
    )
    if budget is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Budget not found")
    return budget
