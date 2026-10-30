from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from app.api.deps import AccountServiceDep, CurrentUser, DbSession
from app.models.account import Account, AccountBalanceHistory
from app.schemas.account import (
    AccountBalanceHistoryRead,
    AccountCreate,
    AccountRead,
    AccountUpdate,
)
from app.services.account_service import (
    AccountConflictError,
    AccountNotFoundError,
    AccountValidationError,
)

router = APIRouter(prefix="/accounts", tags=["accounts"])


@router.post("", response_model=AccountRead, status_code=status.HTTP_201_CREATED)
def create_account(
    data: AccountCreate,
    user: CurrentUser,
    account_service: AccountServiceDep,
    db: DbSession,
) -> Account:
    try:
        return account_service.create_account(user.id, data)
    except AccountValidationError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except AccountConflictError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.get("", response_model=list[AccountRead])
def list_accounts(
    user: CurrentUser,
    account_service: AccountServiceDep,
    include_archived: bool = Query(default=False, description="Bao gồm các ví đã lưu trữ"),
) -> list[Account]:
    return account_service.list_accounts(user.id, include_archived=include_archived)


@router.get("/{account_id}", response_model=AccountRead)
def get_account(
    account_id: UUID,
    user: CurrentUser,
    account_service: AccountServiceDep,
) -> Account:
    try:
        return account_service.get_account(user.id, account_id)
    except AccountNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.patch("/{account_id}", response_model=AccountRead)
def update_account(
    account_id: UUID,
    data: AccountUpdate,
    user: CurrentUser,
    account_service: AccountServiceDep,
    db: DbSession,
) -> Account:
    try:
        return account_service.update_account(user.id, account_id, data)
    except AccountNotFoundError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except AccountConflictError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except AccountValidationError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc


@router.post("/{account_id}/archive", response_model=AccountRead)
def archive_account(
    account_id: UUID,
    user: CurrentUser,
    account_service: AccountServiceDep,
) -> Account:
    try:
        return account_service.archive_account(user.id, account_id)
    except AccountNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post("/{account_id}/unarchive", response_model=AccountRead)
def unarchive_account(
    account_id: UUID,
    user: CurrentUser,
    account_service: AccountServiceDep,
) -> Account:
    try:
        return account_service.unarchive_account(user.id, account_id)
    except AccountNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get("/{account_id}/history", response_model=list[AccountBalanceHistoryRead])
def get_account_history(
    account_id: UUID,
    user: CurrentUser,
    account_service: AccountServiceDep,
    start_date: Annotated[date | None, Query(description="Từ ngày (YYYY-MM-DD)")] = None,
    end_date: Annotated[date | None, Query(description="Đến ngày (YYYY-MM-DD)")] = None,
) -> list[AccountBalanceHistory]:
    try:
        return account_service.get_balance_history(
            user.id, account_id, start_date=start_date, end_date=end_date
        )
    except AccountNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post("/{account_id}/snapshot", response_model=AccountBalanceHistoryRead)
def snapshot_account_balance(
    account_id: UUID,
    user: CurrentUser,
    account_service: AccountServiceDep,
) -> AccountBalanceHistory:
    try:
        return account_service.take_snapshot(user.id, account_id)
    except AccountNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
