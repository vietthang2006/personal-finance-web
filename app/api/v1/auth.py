from fastapi import APIRouter, HTTPException, Request, Response, status
from sqlalchemy.exc import IntegrityError

from app.api.deps import DbSession
from app.schemas.user import LoginRequest, RefreshRequest, TokenPair, UserCreate
from app.services.auth_service import AuthService, AuthenticationError, RegistrationError


router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post("/register", response_model=TokenPair, status_code=status.HTTP_201_CREATED)
def register(data: UserCreate, request: Request, db: DbSession) -> TokenPair:
    try:
        _, pair = AuthService(db).register(data, request)
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
def login(data: LoginRequest, request: Request, db: DbSession) -> TokenPair:
    try:
        _, pair = AuthService(db).login(data, request)
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
def refresh(data: RefreshRequest, db: DbSession) -> TokenPair:
    try:
        return AuthService(db).rotate_refresh_token(data.refresh_token)
    except AuthenticationError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(data: RefreshRequest, db: DbSession) -> Response:
    try:
        AuthService(db).revoke_refresh_token(data.refresh_token)
    except AuthenticationError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)