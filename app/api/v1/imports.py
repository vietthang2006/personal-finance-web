from uuid import UUID

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from sqlalchemy.exc import IntegrityError

from app.api.deps import CurrentUser, DbSession
from app.schemas.import_batch import ImportConfirmation, ImportConfirmRequest, ImportPreview
from app.services.import_service import ImportError, MAX_IMPORT_SIZE, confirm_import, preview_import


router = APIRouter(prefix="/imports", tags=["imports"])


@router.post("/preview", response_model=ImportPreview, status_code=201)
def create_import_preview(
    user: CurrentUser,
    db: DbSession,
    account_id: UUID = Form(...),
    file: UploadFile = File(...),
) -> ImportPreview:
    try:
        content = file.file.read(MAX_IMPORT_SIZE + 1)
        return preview_import(db, user, account_id, file.filename or "", content)
    except ImportError as exc:
        db.rollback()
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Import batch conflicts with an existing import") from exc
    finally:
        file.file.close()


@router.post("/{batch_id}/confirm", response_model=ImportConfirmation)
def confirm_import_batch(
    batch_id: UUID,
    data: ImportConfirmRequest,
    user: CurrentUser,
    db: DbSession,
) -> ImportConfirmation:
    try:
        state, created = confirm_import(db, user, batch_id, data.category_choices)
        return ImportConfirmation(id=batch_id, status=state, created_rows=created)
    except ImportError as exc:
        db.rollback()
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
