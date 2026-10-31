from datetime import date
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, File, HTTPException, Query, Response, UploadFile, status
from fastapi.responses import FileResponse

from app.api.deps import (
    AttachmentServiceDep,
    CurrentUser,
    DbSession,
    TagServiceDep,
    TransactionServiceDep,
)
from app.models.transaction import Tag, Transaction, TransactionAttachment
from app.schemas.attachment import AttachmentRead
from app.schemas.tag import TagRead, TransactionTagAssign
from app.schemas.transaction import TransactionCreate, TransactionRead, TransactionUpdate
from app.services.attachment_service import (
    AttachmentNotFoundError,
    AttachmentPayloadTooLargeError,
    AttachmentValidationError,
)
from app.services.tag_service import (
    TagNotFoundError,
    TagValidationError,
)
from app.services.transaction_service import (
    AccountInsufficientFundsError,
    TransactionConflictError,
    TransactionNotFoundError,
    TransactionValidationError,
)


router = APIRouter(prefix="/transactions", tags=["transactions"])


@router.post("", response_model=TransactionRead, status_code=status.HTTP_201_CREATED)
def create_transaction(
    data: TransactionCreate,
    user: CurrentUser,
    transaction_service: TransactionServiceDep,
    db: DbSession,
) -> Transaction:
    try:
        return transaction_service.create_transaction(user.id, data)
    except TransactionValidationError as exc:
        db.rollback()
        detail = str(exc)
        status_code = status.HTTP_404_NOT_FOUND if detail == "Account not found" else status.HTTP_422_UNPROCESSABLE_ENTITY
        raise HTTPException(status_code=status_code, detail=detail) from exc
    except AccountInsufficientFundsError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except TransactionConflictError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.get("", response_model=list[TransactionRead])
def list_transactions(
    user: CurrentUser,
    transaction_service: TransactionServiceDep,
    account_id: UUID | None = None,
    kind: Literal["income", "expense"] | None = None,
    category_id: int | None = None,
    from_date: date | None = None,
    to_date: date | None = None,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
) -> list[Transaction]:
    return transaction_service.list_transactions(
        user_id=user.id,
        account_id=account_id,
        kind=kind,
        category_id=category_id,
        from_date=from_date,
        to_date=to_date,
        offset=offset,
        limit=limit,
    )


@router.get("/{transaction_id}", response_model=TransactionRead)
def get_transaction(
    transaction_id: UUID,
    user: CurrentUser,
    transaction_service: TransactionServiceDep,
) -> Transaction:
    try:
        return transaction_service.get_transaction(user.id, transaction_id)
    except TransactionNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.patch("/{transaction_id}", response_model=TransactionRead)
def update_transaction(
    transaction_id: UUID,
    data: TransactionUpdate,
    user: CurrentUser,
    transaction_service: TransactionServiceDep,
    db: DbSession,
) -> Transaction:
    try:
        return transaction_service.update_transaction(user.id, transaction_id, data)
    except TransactionNotFoundError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except TransactionValidationError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except AccountInsufficientFundsError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except TransactionConflictError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.delete("/{transaction_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_transaction(
    transaction_id: UUID,
    user: CurrentUser,
    transaction_service: TransactionServiceDep,
    db: DbSession,
) -> Response:
    try:
        transaction_service.delete_transaction(user.id, transaction_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except TransactionNotFoundError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except AccountInsufficientFundsError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


# ------------------ Tag Endpoints for Transaction ------------------


@router.get("/{transaction_id}/tags", response_model=list[TagRead])
def list_transaction_tags(
    transaction_id: UUID,
    user: CurrentUser,
    tag_service: TagServiceDep,
) -> list[Tag]:
    try:
        return tag_service.list_transaction_tags(user.id, transaction_id)
    except TagNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post("/{transaction_id}/tags", response_model=list[TagRead])
def assign_transaction_tags(
    transaction_id: UUID,
    data: TransactionTagAssign,
    user: CurrentUser,
    tag_service: TagServiceDep,
    db: DbSession,
) -> list[Tag]:
    try:
        return tag_service.assign_tags(user.id, transaction_id, data.tag_ids)
    except TagNotFoundError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.delete("/{transaction_id}/tags/{tag_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_transaction_tag(
    transaction_id: UUID,
    tag_id: int,
    user: CurrentUser,
    tag_service: TagServiceDep,
    db: DbSession,
) -> Response:
    try:
        tag_service.remove_tag(user.id, transaction_id, tag_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except TagNotFoundError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


# ------------------ Attachment Endpoints for Transaction ------------------


@router.get("/{transaction_id}/attachments", response_model=list[AttachmentRead])
def list_transaction_attachments(
    transaction_id: UUID,
    user: CurrentUser,
    attachment_service: AttachmentServiceDep,
) -> list[TransactionAttachment]:
    try:
        return attachment_service.list_attachments(user.id, transaction_id)
    except AttachmentNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post(
    "/{transaction_id}/attachments",
    response_model=AttachmentRead,
    status_code=status.HTTP_201_CREATED,
)
async def upload_transaction_attachment(
    transaction_id: UUID,
    user: CurrentUser,
    attachment_service: AttachmentServiceDep,
    db: DbSession,
    file: UploadFile = File(...),
) -> TransactionAttachment:
    content = await file.read()
    try:
        return attachment_service.upload_attachment(
            user_id=user.id,
            transaction_id=transaction_id,
            file_name=file.filename or "attachment.bin",
            mime_type=file.content_type or "application/octet-stream",
            content=content,
        )
    except AttachmentNotFoundError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except AttachmentPayloadTooLargeError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail=str(exc)) from exc
    except AttachmentValidationError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc


@router.get("/{transaction_id}/attachments/{attachment_id}/download")
def download_transaction_attachment(
    transaction_id: UUID,
    attachment_id: UUID,
    user: CurrentUser,
    attachment_service: AttachmentServiceDep,
) -> FileResponse:
    try:
        attachment, file_path = attachment_service.get_attachment(
            user.id, transaction_id, attachment_id
        )
        return FileResponse(
            path=str(file_path),
            media_type=attachment.mime_type,
            filename=attachment.file_name,
        )
    except AttachmentNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.delete(
    "/{transaction_id}/attachments/{attachment_id}", status_code=status.HTTP_204_NO_CONTENT
)
def delete_transaction_attachment(
    transaction_id: UUID,
    attachment_id: UUID,
    user: CurrentUser,
    attachment_service: AttachmentServiceDep,
    db: DbSession,
) -> Response:
    try:
        attachment_service.delete_attachment(user.id, transaction_id, attachment_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except AttachmentNotFoundError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
