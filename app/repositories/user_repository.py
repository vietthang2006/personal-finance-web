from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models.user import Role, User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    def __init__(self, db: Session) -> None:
        super().__init__(db)

    def get_by_id(self, user_id: UUID) -> User | None:
        return self.db.get(User, user_id)

    def get_by_id_for_update(self, user_id: UUID) -> User | None:
        stmt = select(User).where(User.id == user_id).with_for_update()
        return self.db.scalar(stmt)

    def get_by_id_with_roles(self, user_id: UUID) -> User | None:
        stmt = (
            select(User)
            .options(selectinload(User.roles))
            .where(User.id == user_id)
        )
        return self.db.scalar(stmt)

    def get_active_by_id_with_roles(self, user_id: UUID) -> User | None:
        stmt = (
            select(User)
            .options(selectinload(User.roles))
            .where(User.id == user_id, User.status == "active")
        )
        return self.db.scalar(stmt)

    def get_by_email(self, email: str, load_roles: bool = False) -> User | None:
        stmt = select(User).where(func.lower(User.email) == email.strip().lower())
        if load_roles:
            stmt = stmt.options(selectinload(User.roles))
        return self.db.scalar(stmt)

    def get_by_username(self, username: str, load_roles: bool = False) -> User | None:
        stmt = select(User).where(User.username == username.strip())
        if load_roles:
            stmt = stmt.options(selectinload(User.roles))
        return self.db.scalar(stmt)

    def exists_by_email(self, email: str) -> bool:
        stmt = select(select(User).where(func.lower(User.email) == email.strip().lower()).exists())
        return bool(self.db.scalar(stmt))

    def exists_by_username(self, username: str) -> bool:
        stmt = select(select(User).where(User.username == username.strip()).exists())
        return bool(self.db.scalar(stmt))

    def get_role_by_code(self, code: str) -> Role | None:
        stmt = select(Role).where(Role.code == code)
        return self.db.scalar(stmt)

    def create(self, user: User, role: Role | None = None) -> User:
        self.db.add(user)
        self.db.flush()
        if role is not None:
            user.roles.append(role)
            self.db.flush()
        return user

    def update_last_login(self, user: User, timestamp: datetime) -> None:
        user.last_login_at = timestamp
        self.db.flush()

    def update(self, user: User) -> User:
        self.db.flush()
        return user

