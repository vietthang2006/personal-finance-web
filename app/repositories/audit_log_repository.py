from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.system import AuditLog
from app.repositories.base import BaseRepository


class AuditLogRepository(BaseRepository[AuditLog]):
    def __init__(self, db: Session) -> None:
        super().__init__(db)

    def log(
        self,
        action: str,
        entity_type: str,
        actor_id: UUID | None = None,
        entity_id: str | None = None,
        changes: dict[str, Any] | None = None,
        ip_address: str | None = None,
    ) -> AuditLog:
        audit = AuditLog(
            actor_id=actor_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            changes=changes,
            ip_address=ip_address,
        )
        self.db.add(audit)
        self.db.flush()
        return audit

