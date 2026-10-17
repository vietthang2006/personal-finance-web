from fastapi import APIRouter, HTTPException, Request, Response, status
from sqlalchemy.exc import IntegrityError

from app.api.deps import AuthServiceDep, DbSession
from app.schemas.user import LoginRequest, RefreshRequest, TokenPair, UserCreate
from app.services.auth_service import AuthenticationError, RegistrationError


router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post("/register", response_model=TokenPair, status_code=status.HTTP_201_CREATED)
def register(
    data: UserCreate,
    request: Request,
    auth_service: AuthServiceDep,
    db: DbSession,
) -> TokenPair:
    try:
        _, pair = auth_service.register(data, request)
        return pair
    except RegistrationError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email or username is already registered",
        ) from exc


@router.post("/login", response_model=TokenPair)
def login(
    data: LoginRequest,
    request: Request,
    auth_service: AuthServiceDep,
    db: DbSession,
) -> TokenPair:
    try:
        _, pair = auth_service.login(data, request)
        return pair
    except AuthenticationError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Could not create session") from exc


@router.post("/refresh", response_model=TokenPair)
def refresh(
    data: RefreshRequest,
    auth_service: AuthServiceDep,
    db: DbSession,
) -> TokenPair:
    try:
        return auth_service.rotate_refresh_token(data.refresh_token)
    except AuthenticationError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    data: RefreshRequest,
    auth_service: AuthServiceDep,
    db: DbSession,
) -> Response:
    try:
        auth_service.revoke_refresh_token(data.refresh_token)
    except AuthenticationError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)