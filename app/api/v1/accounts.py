from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from app.api.deps import AccountServiceDep, CurrentUser
from app.models.account import Account, AccountBalanceHistory
from app.schemas.account import (
    AccountBalanceHistoryRead,
    AccountCreate,
    AccountRead,
    AccountSummaryResponse,
    AccountUpdate,
)

router = APIRouter(prefix="/accounts", tags=["accounts"])


@router.post("", response_model=AccountRead, status_code=status.HTTP_201_CREATED)
def create_account(
    data: AccountCreate,
    user: CurrentUser,
    account_service: AccountServiceDep,
) -> Account:
    return account_service.create_account(user.id, data)


@router.get("", response_model=AccountSummaryResponse)
def list_accounts(
    user: CurrentUser,
    account_service: AccountServiceDep,
    include_archived: bool = Query(default=False, description="Bao gồm các ví đã lưu trữ"),
) -> AccountSummaryResponse:
    default_curr = getattr(user, "default_currency", "VND")
    return account_service.list_accounts_summary(
        user.id, default_currency=default_curr, include_archived=include_archived
    )


@router.get("/{account_id}", response_model=AccountRead)
def get_account(
    account_id: UUID,
    user: CurrentUser,
    account_service: AccountServiceDep,
) -> Account:
    return account_service.get_account(user.id, account_id)


@router.patch("/{account_id}", response_model=AccountRead)
def update_account(
    account_id: UUID,
    data: AccountUpdate,
    user: CurrentUser,
    account_service: AccountServiceDep,
) -> Account:
    return account_service.update_account(user.id, account_id, data)


@router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_account(
    account_id: UUID,
    user: CurrentUser,
    account_service: AccountServiceDep,
) -> None:
    account_service.delete_account(user.id, account_id)


@router.post("/{account_id}/archive", response_model=AccountRead)
def archive_account(
    account_id: UUID,
    user: CurrentUser,
    account_service: AccountServiceDep,
) -> Account:
    return account_service.archive_account(user.id, account_id)


@router.post("/{account_id}/unarchive", response_model=AccountRead)
def unarchive_account(
    account_id: UUID,
    user: CurrentUser,
    account_service: AccountServiceDep,
) -> Account:
    return account_service.unarchive_account(user.id, account_id)


@router.get("/{account_id}/history", response_model=list[AccountBalanceHistoryRead])
def get_account_history(
    account_id: UUID,
    user: CurrentUser,
    account_service: AccountServiceDep,
    start_date: Annotated[date | None, Query(description="Từ ngày (YYYY-MM-DD)")] = None,
    end_date: Annotated[date | None, Query(description="Đến ngày (YYYY-MM-DD)")] = None,
) -> list[AccountBalanceHistory]:
    return account_service.get_balance_history(
        user.id, account_id, start_date=start_date, end_date=end_date
    )


@router.post("/{account_id}/snapshot", response_model=AccountBalanceHistoryRead)
def snapshot_account_balance(
    account_id: UUID,
    user: CurrentUser,
    account_service: AccountServiceDep,
) -> AccountBalanceHistory:
    return account_service.take_snapshot(user.id, account_id)
