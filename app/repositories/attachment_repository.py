from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.transaction import TransactionAttachment
from app.repositories.base import BaseRepository


class AttachmentRepository(BaseRepository[TransactionAttachment]):
    def __init__(self, db: Session) -> None:
        super().__init__(db)

    def get_by_id(self, attachment_id: UUID) -> TransactionAttachment | None:
        stmt = select(TransactionAttachment).where(TransactionAttachment.id == attachment_id)
        return self.db.scalar(stmt)

    def list_by_transaction(self, transaction_id: UUID) -> list[TransactionAttachment]:
        stmt = (
            select(TransactionAttachment)
            .where(TransactionAttachment.transaction_id == transaction_id)
            .order_by(TransactionAttachment.created_at.asc())
        )
        return list(self.db.scalars(stmt).all())

    def create_attachment(self, attachment: TransactionAttachment) -> TransactionAttachment:
        self.db.add(attachment)
        self.db.flush()
        return attachment

    def delete_attachment(self, attachment: TransactionAttachment) -> None:
        self.db.delete(attachment)
        self.db.flush()

