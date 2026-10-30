from datetime import date
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from app.api.deps import CurrentUser, DbSession, TransferServiceDep
from app.models.transaction import Transfer
from app.schemas.transfer import TransferCreate, TransferRead
from app.services.transfer_service import (
    TransferConflictError,
    TransferNotFoundError,
    TransferValidationError,
)


router = APIRouter(prefix="/transfers", tags=["transfers"])


@router.post("", response_model=TransferRead, status_code=status.HTTP_201_CREATED)
def create_transfer(
    data: TransferCreate,
    user: CurrentUser,
    transfer_service: TransferServiceDep,
    db: DbSession,
) -> Transfer:
    try:
        return transfer_service.create_transfer(user.id, data)
    except TransferValidationError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except TransferConflictError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.get("", response_model=list[TransferRead])
def list_transfers(
    user: CurrentUser,
    transfer_service: TransferServiceDep,
    from_account_id: UUID | None = None,
    to_account_id: UUID | None = None,
    from_date: date | None = None,
    to_date: date | None = None,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
) -> list[Transfer]:
    return transfer_service.list_transfers(
        user_id=user.id,
        from_account_id=from_account_id,
        to_account_id=to_account_id,
        from_date=from_date,
        to_date=to_date,
        offset=offset,
        limit=limit,
    )


@router.get("/{transfer_id}", response_model=TransferRead)
def get_transfer(
    transfer_id: UUID,
    user: CurrentUser,
    transfer_service: TransferServiceDep,
) -> Transfer:
    try:
        return transfer_service.get_transfer(user.id, transfer_id)
    except TransferNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

