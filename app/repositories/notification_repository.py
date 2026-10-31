import uuid
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models.system import Notification
from app.repositories.base import BaseRepository


class NotificationRepository(BaseRepository[Notification]):
    def __init__(self, db: Session) -> None:
        super().__init__(db)

    def create(self, notification: Notification) -> Notification:
        self.db.add(notification)
        self.db.flush()
        return notification

    def get_by_id(self, notification_id: UUID, user_id: UUID) -> Notification | None:
        stmt = select(Notification).where(
            Notification.id == notification_id,
            Notification.user_id == user_id,
        )
        return self.db.scalar(stmt)

    def get_by_idempotency_key(self, user_id: UUID, idempotency_key: str) -> Notification | None:
        stmt = select(Notification).where(
            Notification.user_id == user_id,
            Notification.idempotency_key == idempotency_key,
        )
        return self.db.scalar(stmt)

    def list_by_user(
        self,
        user_id: UUID,
        status: str | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> list[Notification]:
        stmt = select(Notification).where(Notification.user_id == user_id)
        if status is not None:
            stmt = stmt.where(Notification.status == status)
        stmt = stmt.order_by(Notification.created_at.desc()).offset(offset).limit(limit)
        return list(self.db.scalars(stmt).all())

    def mark_as_read(self, notification_id: UUID, user_id: UUID) -> Notification | None:
        notification = self.get_by_id(notification_id, user_id)
        if notification:
            notification.status = "read"
            notification.read_at = datetime.now(timezone.utc)
            self.db.flush()
        return notification

