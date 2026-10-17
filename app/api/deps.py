from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import InvalidTokenError, decode_token
from app.models.user import User
from app.repositories.currency_repository import CurrencyRepository
from app.repositories.password_reset_token_repository import PasswordResetTokenRepository
from app.repositories.user_repository import UserRepository
from app.repositories.user_session_repository import UserSessionRepository
from app.services.auth_service import AuthService
from app.services.user_service import UserService

bearer_scheme = HTTPBearer(auto_error=False)
DbSession = Annotated[Session, Depends(get_db)]


def get_user_repository(db: DbSession) -> UserRepository:
    return UserRepository(db)


def get_user_session_repository(db: DbSession) -> UserSessionRepository:
    return UserSessionRepository(db)


def get_password_reset_token_repository(db: DbSession) -> PasswordResetTokenRepository:
    return PasswordResetTokenRepository(db)


def get_currency_repository(db: DbSession) -> CurrencyRepository:
    return CurrencyRepository(db)


UserRepositoryDep = Annotated[UserRepository, Depends(get_user_repository)]
UserSessionRepositoryDep = Annotated[UserSessionRepository, Depends(get_user_session_repository)]
PasswordResetTokenRepositoryDep = Annotated[
    PasswordResetTokenRepository, Depends(get_password_reset_token_repository)
]
CurrencyRepositoryDep = Annotated[CurrencyRepository, Depends(get_currency_repository)]


def get_auth_service(
    db: DbSession,
    user_repo: UserRepositoryDep,
    session_repo: UserSessionRepositoryDep,
    currency_repo: CurrencyRepositoryDep,
    reset_token_repo: PasswordResetTokenRepositoryDep,
) -> AuthService:
    return AuthService(
        db=db,
        user_repo=user_repo,
        session_repo=session_repo,
        currency_repo=currency_repo,
        reset_token_repo=reset_token_repo,
    )


def get_user_service(
    db: DbSession,
    user_repo: UserRepositoryDep,
    currency_repo: CurrencyRepositoryDep,
) -> UserService:
    return UserService(
        db=db,
        user_repo=user_repo,
        currency_repo=currency_repo,
    )


AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]
UserServiceDep = Annotated[UserService, Depends(get_user_service)]


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    user_repo: UserRepositoryDep,
) -> User:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credentials is None:
        raise unauthorized
    try:
        payload = decode_token(credentials.credentials, "access")
        user_id = UUID(str(payload["sub"]))
    except (InvalidTokenError, ValueError, KeyError) as exc:
        raise unauthorized from exc

    user = user_repo.get_active_by_id_with_roles(user_id)
    if user is None:
        raise unauthorized
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_role(role_code: str):
    def dependency(user: CurrentUser) -> User:
        if role_code not in {role.code for role in user.roles}:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
        return user

    return dependency