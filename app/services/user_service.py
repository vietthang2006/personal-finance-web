from uuid import UUID

from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.models.user import User
from app.repositories.currency_repository import CurrencyRepository
from app.repositories.user_repository import UserRepository
from app.schemas.user import UserUpdate


class UserServiceError(Exception):
    pass


class UserNotFoundError(UserServiceError):
    pass


class UserValidationError(UserServiceError):
    pass


class InvalidPasswordError(UserServiceError):
    pass


class UserService:
    def __init__(
        self,
        db: Session | None = None,
        user_repo: UserRepository | None = None,
        currency_repo: CurrencyRepository | None = None,
    ) -> None:
        if db is not None:
            self.db = db
            self.user_repo = user_repo or UserRepository(db)
            self.currency_repo = currency_repo or CurrencyRepository(db)
        elif user_repo is not None:
            self.user_repo = user_repo
            self.db = user_repo.db
            self.currency_repo = currency_repo or CurrencyRepository(self.db)
        else:
            raise ValueError("Either db or user_repo must be provided to UserService")

    def get_by_id(self, user_id: UUID, load_roles: bool = False) -> User | None:
        if load_roles:
            return self.user_repo.get_by_id_with_roles(user_id)
        return self.user_repo.get_by_id(user_id)

    def get_active_user(self, user_id: UUID, load_roles: bool = False) -> User:
        user = (
            self.user_repo.get_active_by_id_with_roles(user_id)
            if load_roles
            else self.user_repo.get_by_id(user_id)
        )
        if user is None or user.status != "active":
            raise UserNotFoundError("User not found or inactive")
        return user

    def get_by_email(self, email: str, load_roles: bool = False) -> User | None:
        return self.user_repo.get_by_email(email, load_roles=load_roles)

    def get_by_username(self, username: str, load_roles: bool = False) -> User | None:
        return self.user_repo.get_by_username(username, load_roles=load_roles)

    def update_profile(self, user: User, data: UserUpdate) -> User:
        if data.default_currency is not None:
            if not self.currency_repo.exists(data.default_currency):
                raise UserValidationError(f"Unsupported default currency: {data.default_currency}")
            user.default_currency = data.default_currency

        if data.full_name is not None:
            user.full_name = data.full_name
        if data.timezone is not None:
            user.timezone = data.timezone
        if data.language is not None:
            user.language = data.language

        self.user_repo.update(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def change_password(self, user: User, current_password: str, new_password: str) -> None:
        if not verify_password(current_password, user.password_hash):
            raise InvalidPasswordError("Current password is not correct")

        user.password_hash = hash_password(new_password)
        self.user_repo.update(user)
        self.db.commit()

