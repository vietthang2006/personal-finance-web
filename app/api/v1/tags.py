from fastapi import APIRouter, HTTPException, Response, status

from app.api.deps import CurrentUser, DbSession, TagServiceDep
from app.models.transaction import Tag
from app.schemas.tag import TagCreate, TagRead, TagUpdate
from app.services.tag_service import (
    TagConflictError,
    TagNotFoundError,
    TagValidationError,
)


router = APIRouter(prefix="/tags", tags=["tags"])


@router.get("", response_model=list[TagRead])
def list_tags(user: CurrentUser, tag_service: TagServiceDep) -> list[Tag]:
    return tag_service.list_tags(user.id)


@router.post("", response_model=TagRead, status_code=status.HTTP_201_CREATED)
def create_tag(
    data: TagCreate,
    user: CurrentUser,
    tag_service: TagServiceDep,
    db: DbSession,
) -> Tag:
    try:
        return tag_service.create_tag(user.id, data)
    except TagConflictError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.patch("/{tag_id}", response_model=TagRead)
def update_tag(
    tag_id: int,
    data: TagUpdate,
    user: CurrentUser,
    tag_service: TagServiceDep,
    db: DbSession,
) -> Tag:
    try:
        return tag_service.update_tag(user.id, tag_id, data)
    except TagNotFoundError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except TagValidationError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except TagConflictError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.delete("/{tag_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_tag(
    tag_id: int,
    user: CurrentUser,
    tag_service: TagServiceDep,
    db: DbSession,
) -> Response:
    try:
        tag_service.delete_tag(user.id, tag_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except TagNotFoundError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except TagValidationError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc

