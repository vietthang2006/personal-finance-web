from fastapi import APIRouter, HTTPException, Response, status

from app.api.deps import CurrentUser, DbSession, UserServiceDep
from app.schemas.user import PasswordChangeRequest, UserRead, UserUpdate
from app.services.user_service import InvalidPasswordError, UserNotFoundError, UserValidationError


router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserRead)
def read_current_user(user: CurrentUser) -> UserRead:
    return UserRead.model_validate(user)

@router.patch("/me", response_model=UserRead)
def update_current_user(
    data: UserUpdate,
    user: CurrentUser,
    user_service: UserServiceDep,
    db: DbSession,
) -> UserRead:
    try:
        updated_user = user_service.update_profile(user, data)
        return UserRead.model_validate(updated_user)
    except UserValidationError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except UserNotFoundError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.put("/me/password", status_code=status.HTTP_204_NO_CONTENT)
def change_password(
    data: PasswordChangeRequest,
    user: CurrentUser,
    user_service: UserServiceDep,
    db: DbSession,
) -> Response:
    try:
        user_service.change_password(user, data.old_password, data.new_password)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except InvalidPasswordError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc