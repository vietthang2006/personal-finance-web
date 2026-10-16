from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.api.deps import CurrentUser, DbSession
from app.models.account import Account
from app.models.currency import Currency
from app.schemas.account import AccountCreate, AccountRead


router = APIRouter(prefix="/accounts", tags=["accounts"])


@router.post("", response_model=AccountRead, status_code=status.HTTP_201_CREATED)
def create_account(data: AccountCreate, user: CurrentUser, db: DbSession) -> Account:
    if db.get(Currency, data.currency_code) is None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Unsupported currency")
    account = Account(
        user_id=user.id,
        name=data.name,
        kind=data.kind,
        currency_code=data.currency_code,
        opening_balance=data.opening_balance,
        current_balance=data.opening_balance,
        allow_negative=data.allow_negative,
        credit_limit=data.credit_limit,
        billing_day=data.billing_day,
        due_day=data.due_day,
    )
    db.add(account)
    db.commit()
    db.refresh(account)
    return account


@router.get("", response_model=list[AccountRead])
def list_accounts(user: CurrentUser, db: DbSession) -> list[Account]:
    return list(
        db.scalars(
            select(Account).where(Account.user_id == user.id).order_by(Account.created_at.desc())
        ).all()
    )


@router.get("/{account_id}", response_model=AccountRead)
def get_account(account_id: UUID, user: CurrentUser, db: DbSession) -> Account:
    account = db.scalar(
        select(Account).where(Account.id == account_id, Account.user_id == user.id)
    )
    if account is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")
    return account