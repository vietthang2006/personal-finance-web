from uuid import UUID

from fastapi import APIRouter, File, Form, HTTPException, Query, Response, UploadFile, status
from sqlalchemy.exc import IntegrityError

from app.api.deps import CurrentUser, DbSession, ImportServiceDep
from app.schemas.import_batch import (
    ImportBatchRead,
    ImportConfirmation,
    ImportConfirmRequest,
    ImportPreviewResponse,
    ImportRowRead,
)
from app.services.import_service import (
    MAX_IMPORT_SIZE,
    ImportConflictError,
    ImportNotFoundError,
    ImportPayloadTooLargeError,
    ImportServiceError,
    ImportValidationError,
)


router = APIRouter(prefix="/imports", tags=["imports"])


@router.post("/preview", response_model=ImportPreviewResponse, status_code=status.HTTP_201_CREATED)
async def create_import_preview(
    user: CurrentUser,
    import_service: ImportServiceDep,
    db: DbSession,
    account_id: UUID = Form(...),
    file: UploadFile = File(...),
) -> ImportPreviewResponse:
    content = await file.read(MAX_IMPORT_SIZE + 1)
    try:
        batch, rows = import_service.preview_import(
            user_id=user.id,
            account_id=account_id,
            filename=file.filename or "statement.csv",
            content=content,
        )
        return ImportPreviewResponse(
            id=batch.id,
            account_id=batch.account_id,
            file_name=batch.file_name,
            file_hash=batch.file_hash,
            status=batch.status,
            total_rows=batch.total_rows,
            valid_rows=batch.valid_rows,
            duplicate_rows=batch.duplicate_rows,
            invalid_rows=batch.invalid_rows,
            expires_at=batch.expires_at,
            rows=[ImportRowRead.model_validate(r) for r in rows],
        )
    except ImportNotFoundError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ImportPayloadTooLargeError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail=str(exc)) from exc
    except ImportConflictError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except ImportValidationError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Import batch conflicts with an existing import") from exc
    finally:
        await file.close()


@router.get("/batches", response_model=list[ImportBatchRead])
def list_import_batches(
    user: CurrentUser,
    import_service: ImportServiceDep,
    account_id: UUID | None = None,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
) -> list[ImportBatchRead]:
    batches = import_service.list_batches(
        user_id=user.id,
        account_id=account_id,
        offset=offset,
        limit=limit,
    )
    return [ImportBatchRead.model_validate(b) for b in batches]


@router.get("/batches/{batch_id}", response_model=ImportPreviewResponse)
def get_import_batch(
    batch_id: UUID,
    user: CurrentUser,
    import_service: ImportServiceDep,
) -> ImportPreviewResponse:
    try:
        batch, rows = import_service.get_batch(user.id, batch_id)
        return ImportPreviewResponse(
            id=batch.id,
            account_id=batch.account_id,
            file_name=batch.file_name,
            file_hash=batch.file_hash,
            status=batch.status,
            total_rows=batch.total_rows,
            valid_rows=batch.valid_rows,
            duplicate_rows=batch.duplicate_rows,
            invalid_rows=batch.invalid_rows,
            expires_at=batch.expires_at,
            rows=[ImportRowRead.model_validate(r) for r in rows],
        )
    except ImportNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post("/batches/{batch_id}/confirm", response_model=ImportConfirmation)
def confirm_import_batch(
    batch_id: UUID,
    data: ImportConfirmRequest,
    user: CurrentUser,
    import_service: ImportServiceDep,
    db: DbSession,
) -> ImportConfirmation:
    try:
        batch = import_service.confirm_import(
            user_id=user.id,
            batch_id=batch_id,
            category_choices=data.category_choices,
        )
        return ImportConfirmation(
            id=batch.id,
            status=batch.status,
            imported_rows=batch.imported_rows,
        )
    except ImportNotFoundError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ImportConflictError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except ImportValidationError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc


@router.delete("/batches/{batch_id}", status_code=status.HTTP_204_NO_CONTENT)
def cancel_import_batch(
    batch_id: UUID,
    user: CurrentUser,
    import_service: ImportServiceDep,
    db: DbSession,
) -> Response:
    try:
        import_service.cancel_batch(user.id, batch_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except ImportNotFoundError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ImportValidationError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
