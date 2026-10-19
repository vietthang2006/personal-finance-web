from datetime import datetime, timezone
from typing import Any, cast
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models.user import UserSession
from app.repositories.base import BaseRepository


class UserSessionRepository(BaseRepository[UserSession]):
    def __init__(self, db: Session) -> None:
        super().__init__(db)

    def create(self, session: UserSession) -> UserSession:
        self.db.add(session)
        self.db.flush()
        return session

    def get_by_id(self, session_id: UUID, for_update: bool = False) -> UserSession | None:
        stmt = select(UserSession).where(UserSession.id == session_id)
        if for_update:
            stmt = stmt.with_for_update()
        return self.db.scalar(stmt)

    def revoke(self, session: UserSession, revoked_at: datetime | None = None) -> None:
        session.revoked_at = revoked_at or datetime.now(timezone.utc)
        self.db.flush()

    def update_hash(self, session: UserSession, new_hash: str) -> None:
        session.refresh_token_hash = new_hash
        self.db.flush()

    def revoke_all_by_user_id(self, user_id: UUID, revoked_at: datetime | None = None) -> int:
        now = revoked_at or datetime.now(timezone.utc)
        stmt = (
            update(UserSession)
            .where(UserSession.user_id == user_id, UserSession.revoked_at.is_(None))
            .values(revoked_at=now)
        )
        result = self.db.execute(stmt)
        self.db.flush()
        return result.rowcount

