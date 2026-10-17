from datetime import datetime
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models.user import PasswordResetToken
from app.repositories.base import BaseRepository


class PasswordResetTokenRepository(BaseRepository[PasswordResetToken]):
    def __init__(self, db: Session) -> None:
        super().__init__(db)

    def create(self, token: PasswordResetToken) -> PasswordResetToken:
        self.db.add(token)
        self.db.flush()
        return token

    def get_by_hash(
        self, token_hash: str, for_update: bool = False
    ) -> PasswordResetToken | None:
        stmt = select(PasswordResetToken).where(PasswordResetToken.token_hash == token_hash)
        if for_update:
            stmt = stmt.with_for_update()
        return self.db.scalar(stmt)

    def revoke_active_for_user(self, user_id: UUID, revoked_at: datetime) -> int:
        stmt = (
            update(PasswordResetToken)
            .where(
                PasswordResetToken.user_id == user_id,
                PasswordResetToken.used_at.is_(None),
                PasswordResetToken.revoked_at.is_(None),
            )
            .values(revoked_at=revoked_at)
        )
        result = self.db.execute(stmt)
        self.db.flush()
        return result.rowcount

    def mark_used(self, token: PasswordResetToken, used_at: datetime) -> None:
        token.used_at = used_at
        self.db.flush()