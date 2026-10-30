from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import InvalidTokenError, decode_token
from app.repositories.category_repository import CategoryRepository
from app.models.user import User
from app.repositories.account_balance_history_repository import AccountBalanceHistoryRepository
from app.repositories.account_repository import AccountRepository
from app.repositories.attachment_repository import AttachmentRepository
from app.repositories.currency_repository import CurrencyRepository
from app.repositories.import_repository import ImportRepository
from app.repositories.password_reset_token_repository import PasswordResetTokenRepository
from app.repositories.tag_repository import TagRepository
from app.repositories.transaction_repository import TransactionRepository
from app.repositories.transfer_repository import TransferRepository
from app.repositories.user_repository import UserRepository
from app.repositories.user_session_repository import UserSessionRepository
from app.services.account_service import AccountService
from app.services.attachment_service import AttachmentService
from app.services.category_service import CategoryService
from app.services.auth_service import AuthService
from app.services.import_service import ImportService
from app.services.tag_service import TagService
from app.services.transaction_service import TransactionService
from app.services.transfer_service import TransferService
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


def get_account_repository(db: DbSession) -> AccountRepository:
    return AccountRepository(db)


def get_account_balance_history_repository(db: DbSession) -> AccountBalanceHistoryRepository:
    return AccountBalanceHistoryRepository(db)


def get_category_repository(db: DbSession) -> CategoryRepository:
    return CategoryRepository(db)


def get_transaction_repository(db: DbSession) -> TransactionRepository:
    return TransactionRepository(db)


def get_transfer_repository(db: DbSession) -> TransferRepository:
    return TransferRepository(db)


def get_tag_repository(db: DbSession) -> TagRepository:
    return TagRepository(db)


def get_attachment_repository(db: DbSession) -> AttachmentRepository:
    return AttachmentRepository(db)


def get_import_repository(db: DbSession) -> ImportRepository:
    return ImportRepository(db)


UserRepositoryDep = Annotated[UserRepository, Depends(get_user_repository)]
UserSessionRepositoryDep = Annotated[UserSessionRepository, Depends(get_user_session_repository)]
PasswordResetTokenRepositoryDep = Annotated[
    PasswordResetTokenRepository, Depends(get_password_reset_token_repository)
]
CurrencyRepositoryDep = Annotated[CurrencyRepository, Depends(get_currency_repository)]
AccountRepositoryDep = Annotated[AccountRepository, Depends(get_account_repository)]
AccountBalanceHistoryRepositoryDep = Annotated[
    AccountBalanceHistoryRepository, Depends(get_account_balance_history_repository)
]
CategoryRepositoryDep = Annotated[CategoryRepository, Depends(get_category_repository)]
TransactionRepositoryDep = Annotated[TransactionRepository, Depends(get_transaction_repository)]
TransferRepositoryDep = Annotated[TransferRepository, Depends(get_transfer_repository)]
TagRepositoryDep = Annotated[TagRepository, Depends(get_tag_repository)]
AttachmentRepositoryDep = Annotated[AttachmentRepository, Depends(get_attachment_repository)]
ImportRepositoryDep = Annotated[ImportRepository, Depends(get_import_repository)]


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


def get_account_service(
    db: DbSession,
    account_repo: AccountRepositoryDep,
    history_repo: AccountBalanceHistoryRepositoryDep,
    currency_repo: CurrencyRepositoryDep,
) -> AccountService:
    return AccountService(
        db=db,
        account_repo=account_repo,
        history_repo=history_repo,
        currency_repo=currency_repo,
    )


def get_category_service(
    db: DbSession,
    category_repo: CategoryRepositoryDep,
) -> CategoryService:
    return CategoryService(db=db, category_repo=category_repo)


def get_transaction_service(
    db: DbSession,
    transaction_repo: TransactionRepositoryDep,
    account_repo: AccountRepositoryDep,
    category_repo: CategoryRepositoryDep,
) -> TransactionService:
    return TransactionService(
        db=db,
        transaction_repo=transaction_repo,
        account_repo=account_repo,
        category_repo=category_repo,
    )


def get_transfer_service(
    db: DbSession,
    transfer_repo: TransferRepositoryDep,
    account_repo: AccountRepositoryDep,
) -> TransferService:
    return TransferService(
        db=db,
        transfer_repo=transfer_repo,
        account_repo=account_repo,
    )


def get_tag_service(
    db: DbSession,
    tag_repo: TagRepositoryDep,
    transaction_repo: TransactionRepositoryDep,
) -> TagService:
    return TagService(
        db=db,
        tag_repo=tag_repo,
        transaction_repo=transaction_repo,
    )


def get_attachment_service(
    db: DbSession,
    attachment_repo: AttachmentRepositoryDep,
    transaction_repo: TransactionRepositoryDep,
) -> AttachmentService:
    return AttachmentService(
        db=db,
        attachment_repo=attachment_repo,
        transaction_repo=transaction_repo,
    )


def get_import_service(
    db: DbSession,
    import_repo: ImportRepositoryDep,
    account_repo: AccountRepositoryDep,
    transaction_repo: TransactionRepositoryDep,
    category_repo: CategoryRepositoryDep,
) -> ImportService:
    return ImportService(
        db=db,
        import_repo=import_repo,
        account_repo=account_repo,
        transaction_repo=transaction_repo,
        category_repo=category_repo,
    )


AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]
UserServiceDep = Annotated[UserService, Depends(get_user_service)]
AccountServiceDep = Annotated[AccountService, Depends(get_account_service)]
CategoryServiceDep = Annotated[CategoryService, Depends(get_category_service)]
TransactionServiceDep = Annotated[TransactionService, Depends(get_transaction_service)]
TransferServiceDep = Annotated[TransferService, Depends(get_transfer_service)]
TagServiceDep = Annotated[TagService, Depends(get_tag_service)]
AttachmentServiceDep = Annotated[AttachmentService, Depends(get_attachment_service)]
ImportServiceDep = Annotated[ImportService, Depends(get_import_service)]


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
