from uuid import UUID

from sqlalchemy import delete, func, or_, select
from sqlalchemy.orm import Session

from app.models.transaction import Tag, TransactionTag
from app.repositories.base import BaseRepository


class TagRepository(BaseRepository[Tag]):
    def __init__(self, db: Session) -> None:
        super().__init__(db)

    def list_by_user(self, user_id: UUID) -> list[Tag]:
        stmt = (
            select(Tag)
            .where(or_(Tag.user_id == user_id, Tag.user_id.is_(None)))
            .order_by(Tag.name)
        )
        return list(self.db.scalars(stmt).all())

    def get_by_id(self, tag_id: int, user_id: UUID) -> Tag | None:
        stmt = select(Tag).where(
            Tag.id == tag_id,
            or_(Tag.user_id == user_id, Tag.user_id.is_(None)),
        )
        return self.db.scalar(stmt)

    def name_exists(self, name: str, user_id: UUID, exclude_id: int | None = None) -> bool:
        stmt = select(
            select(Tag.id)
            .where(
                or_(Tag.user_id == user_id, Tag.user_id.is_(None)),
                func.lower(Tag.name) == name.strip().lower(),
            )
            .exists()
        )
        if exclude_id is not None:
            stmt = select(
                select(Tag.id)
                .where(
                    or_(Tag.user_id == user_id, Tag.user_id.is_(None)),
                    func.lower(Tag.name) == name.strip().lower(),
                    Tag.id != exclude_id,
                )
                .exists()
            )
        return bool(self.db.scalar(stmt))

    def create_tag(self, tag: Tag) -> Tag:
        self.db.add(tag)
        self.db.flush()
        return tag

    def delete_tag(self, tag: Tag) -> None:
        self.db.delete(tag)
        self.db.flush()

    def list_tags_for_transaction(self, transaction_id: UUID) -> list[Tag]:
        stmt = (
            select(Tag)
            .join(TransactionTag, TransactionTag.tag_id == Tag.id)
            .where(TransactionTag.transaction_id == transaction_id)
            .order_by(Tag.name)
        )
        return list(self.db.scalars(stmt).all())

    def has_transaction_tag(self, transaction_id: UUID, tag_id: int) -> bool:
        stmt = select(
            select(TransactionTag.transaction_id)
            .where(
                TransactionTag.transaction_id == transaction_id,
                TransactionTag.tag_id == tag_id,
            )
            .exists()
        )
        return bool(self.db.scalar(stmt))

    def add_transaction_tag(self, transaction_id: UUID, tag_id: int) -> None:
        if not self.has_transaction_tag(transaction_id, tag_id):
            tx_tag = TransactionTag(transaction_id=transaction_id, tag_id=tag_id)
            self.db.add(tx_tag)
            self.db.flush()

    def remove_transaction_tag(self, transaction_id: UUID, tag_id: int) -> None:
        stmt = delete(TransactionTag).where(
            TransactionTag.transaction_id == transaction_id,
            TransactionTag.tag_id == tag_id,
        )
        self.db.execute(stmt)
        self.db.flush()

