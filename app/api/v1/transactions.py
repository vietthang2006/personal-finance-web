from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import or_, select, update
from sqlalchemy.exc import IntegrityError

from app.api.deps import CurrentUser, DbSession
from app.models.account import Account
from app.models.transaction import Transaction, TransactionCategory, TransactionSubcategory
from app.schemas.transaction import TransactionCreate, TransactionRead


router = APIRouter(prefix="/transactions", tags=["transactions"])


@router.post("", response_model=TransactionRead, status_code=status.HTTP_201_CREATED)
def create_transaction(
    data: TransactionCreate,
    user: CurrentUser,
    db: DbSession,
) -> Transaction:
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

    delta = data.amount if data.kind == "income" else -data.amount
    updated_account_id = db.scalar(
        update(Account)
        .where(
            Account.id == data.account_id,
            Account.user_id == user.id,
            or_(
                (Account.allow_negative.is_(False) & (Account.current_balance + delta >= 0)),
                (
                    Account.allow_negative.is_(True)
                    & (
                        Account.credit_limit.is_(None)
                        | (Account.current_balance + delta >= -Account.credit_limit)
                    )
                ),
            ),
        )
        .values(current_balance=Account.current_balance + delta)
        .returning(Account.id)
    )
    if updated_account_id is None:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Transaction would exceed the account's available balance or credit limit",
        )
    transaction = Transaction(
        user_id=user.id,
        account_id=data.account_id,
        kind=data.kind,
        category_id=data.category_id,
        subcategory_id=data.subcategory_id,
        amount=data.amount,
        transaction_date=data.transaction_date,
        description=data.description,
        merchant=data.merchant,
        dedup_hash=data.dedup_hash,
    )
    db.add(transaction)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Duplicate transaction or invalid transaction reference",
        ) from exc
    db.refresh(transaction)
    return transaction


@router.get("", response_model=list[TransactionRead])
def list_transactions(
    user: CurrentUser,
    db: DbSession,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
) -> list[Transaction]:
    return list(
        db.scalars(
            select(Transaction)
            .where(Transaction.user_id == user.id)
            .order_by(Transaction.transaction_date.desc(), Transaction.created_at.desc())
            .offset(offset)
            .limit(limit)
        ).all()
    )


@router.get("/{transaction_id}", response_model=TransactionRead)
def get_transaction(transaction_id: UUID, user: CurrentUser, db: DbSession) -> Transaction:
    transaction = db.scalar(
        select(Transaction).where(
            Transaction.id == transaction_id, Transaction.user_id == user.id
        )
    )
    if transaction is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found")
    return transaction