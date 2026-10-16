import hashlib
import json
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Header, HTTPException, Query, status
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError

from app.api.deps import CurrentUser, DbSession
from app.models.account import Account
from app.models.recurring import RecurringTransaction
from app.models.transaction import TransactionCategory, TransactionSubcategory
from app.schemas.recurring import RecurringCreate, RecurringRead, RecurringStatusUpdate


router = APIRouter(prefix="/recurring-transactions", tags=["recurring transactions"])


@router.post("", response_model=RecurringRead, status_code=status.HTTP_201_CREATED)
def create_recurring_transaction(
    data: RecurringCreate,
    user: CurrentUser,
    db: DbSession,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=8, max_length=200)],
) -> RecurringTransaction:
    key_hash = hashlib.sha256(idempotency_key.encode("utf-8")).hexdigest()
    request_hash = hashlib.sha256(
        json.dumps(data.model_dump(mode="json"), sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    existing = db.scalar(
        select(RecurringTransaction).where(
            RecurringTransaction.user_id == user.id,
            RecurringTransaction.idempotency_key == key_hash,
        )
    )
    if existing is not None:
        if existing.request_hash != request_hash:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Idempotency key was reused")
        return existing

    account = db.scalar(
        select(Account).where(Account.id == data.account_id, Account.user_id == user.id)
    )
    if account is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")
    if data.category_id is not None:
        category = db.scalar(
            select(TransactionCategory).where(
                TransactionCategory.id == data.category_id,
                TransactionCategory.kind == data.kind,
                or_(TransactionCategory.user_id == user.id, TransactionCategory.user_id.is_(None)),
                TransactionCategory.is_active.is_(True),
            )
        )
        subcategory = db.scalar(
            select(TransactionSubcategory).where(
                TransactionSubcategory.id == data.subcategory_id,
                TransactionSubcategory.category_id == data.category_id,
                TransactionSubcategory.is_active.is_(True),
            )
        )
        if category is None or subcategory is None:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid category")

    recurring = RecurringTransaction(
        user_id=user.id,
        account_id=data.account_id,
        kind=data.kind,
        category_id=data.category_id,
        subcategory_id=data.subcategory_id,
        amount=data.amount,
        description=data.description,
        frequency=data.frequency,
        interval=data.interval,
        start_date=data.start_date,
        next_run_at=data.start_date,
        end_date=data.end_date,
        idempotency_key=key_hash,
        request_hash=request_hash,
    )
    db.add(recurring)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        existing = db.scalar(
            select(RecurringTransaction).where(
                RecurringTransaction.user_id == user.id,
                RecurringTransaction.idempotency_key == key_hash,
            )
        )
        if existing is not None and existing.request_hash == request_hash:
            return existing
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Recurring transaction conflicts with an existing rule",
        ) from exc
    db.refresh(recurring)
    return recurring


@router.get("", response_model=list[RecurringRead])
def list_recurring_transactions(
    user: CurrentUser,
    db: DbSession,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
) -> list[RecurringTransaction]:
    return list(
        db.scalars(
            select(RecurringTransaction)
            .where(RecurringTransaction.user_id == user.id)
            .order_by(RecurringTransaction.next_run_at)
            .offset(offset)
            .limit(limit)
        ).all()
    )


@router.patch("/{recurring_id}", response_model=RecurringRead)
def update_recurring_status(
    recurring_id: UUID,
    data: RecurringStatusUpdate,
    user: CurrentUser,
    db: DbSession,
) -> RecurringTransaction:
    recurring = db.scalar(
        select(RecurringTransaction).where(
            RecurringTransaction.id == recurring_id,
            RecurringTransaction.user_id == user.id,
        )
    )
    if recurring is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recurring rule not found")
    if recurring.status == "completed" and data.status == "active":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Completed rules cannot be resumed")
    recurring.status = data.status
    db.commit()
    db.refresh(recurring)
    return recurring
