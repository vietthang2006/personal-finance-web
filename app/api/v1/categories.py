from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError

from app.api.deps import CategoryServiceDep, CurrentUser, DbSession
from app.models.transaction import TransactionCategory, TransactionSubcategory
from app.schemas.category import (
    CategoryCreate,
    CategoryKind,
    CategoryRead,
    CategoryUpdate,
    SubcategoryCreate,
    SubcategoryRead,
    SubcategoryUpdate,
)
from app.services.category_service import (
    CategoryConflictError,
    CategoryNotFoundError,
    CategoryValidationError,
)


router = APIRouter(prefix="/categories", tags=["categories"])


@router.get("", response_model=list[CategoryRead])
def list_categories(
    user: CurrentUser,
    category_service: CategoryServiceDep,
    kind: CategoryKind | None = None,
    include_inactive: bool = Query(default=False),
) -> list[TransactionCategory]:
    return category_service.list_categories(
        user.id,
        kind=kind,
        include_inactive=include_inactive,
    )


@router.post("", response_model=CategoryRead, status_code=status.HTTP_201_CREATED)
def create_category(
    data: CategoryCreate,
    user: CurrentUser,
    category_service: CategoryServiceDep,
    db: DbSession,
) -> TransactionCategory:
    try:
        return category_service.create_category(user.id, data)
    except CategoryConflictError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Category code already exists") from exc


@router.patch("/{category_id}", response_model=CategoryRead)
def update_category(
    category_id: int,
    data: CategoryUpdate,
    user: CurrentUser,
    category_service: CategoryServiceDep,
    db: DbSession,
) -> TransactionCategory:
    try:
        return category_service.update_category(user.id, category_id, data)
    except CategoryNotFoundError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except CategoryValidationError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Category update conflicts with existing data") from exc


@router.get("/{category_id}/subcategories", response_model=list[SubcategoryRead])
def list_subcategories(
    category_id: int,
    user: CurrentUser,
    category_service: CategoryServiceDep,
    include_inactive: bool = Query(default=False),
) -> list[TransactionSubcategory]:
    try:
        return category_service.list_subcategories(
            user.id,
            category_id,
            include_inactive=include_inactive,
        )
    except CategoryNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post(
    "/{category_id}/subcategories",
    response_model=SubcategoryRead,
    status_code=status.HTTP_201_CREATED,
)
def create_subcategory(
    category_id: int,
    data: SubcategoryCreate,
    user: CurrentUser,
    category_service: CategoryServiceDep,
    db: DbSession,
) -> TransactionSubcategory:
    try:
        return category_service.create_subcategory(user.id, category_id, data)
    except CategoryNotFoundError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except CategoryValidationError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except CategoryConflictError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Subcategory name already exists") from exc


@router.patch(
    "/{category_id}/subcategories/{subcategory_id}",
    response_model=SubcategoryRead,
)
def update_subcategory(
    category_id: int,
    subcategory_id: int,
    data: SubcategoryUpdate,
    user: CurrentUser,
    category_service: CategoryServiceDep,
    db: DbSession,
) -> TransactionSubcategory:
    try:
        return category_service.update_subcategory(
            user.id,
            category_id,
            subcategory_id,
            data,
        )
    except CategoryNotFoundError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except CategoryValidationError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except CategoryConflictError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Subcategory update conflicts with existing data") from exc