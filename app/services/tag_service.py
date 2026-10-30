from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.transaction import Tag
from app.repositories.tag_repository import TagRepository
from app.repositories.transaction_repository import TransactionRepository
from app.schemas.tag import TagCreate, TagUpdate


class TagServiceError(Exception):
    pass


class TagNotFoundError(TagServiceError):
    pass


class TagValidationError(TagServiceError):
    pass


class TagConflictError(TagServiceError):
    pass


class TagService:
    def __init__(
        self,
        db: Session | None = None,
        tag_repo: TagRepository | None = None,
        transaction_repo: TransactionRepository | None = None,
    ) -> None:
        if tag_repo is not None:
            self.tag_repo = tag_repo
            self.db = tag_repo.db
        elif db is not None:
            self.db = db
            self.tag_repo = TagRepository(db)
        else:
            raise ValueError("Either db or tag_repo must be provided to TagService")

        self.transaction_repo = transaction_repo or TransactionRepository(self.db)

    def list_tags(self, user_id: UUID) -> list[Tag]:
        return self.tag_repo.list_by_user(user_id)

    def create_tag(self, user_id: UUID, data: TagCreate) -> Tag:
        if self.tag_repo.name_exists(data.name, user_id):
            raise TagConflictError("Tag with this name already exists")
        tag = Tag(user_id=user_id, name=data.name, color=data.color)
        try:
            self.tag_repo.create_tag(tag)
            self.tag_repo.commit()
        except IntegrityError as exc:
            self.tag_repo.rollback()
            raise TagConflictError("Tag already exists") from exc
        self.tag_repo.refresh(tag)
        return tag

    def update_tag(self, user_id: UUID, tag_id: int, data: TagUpdate) -> Tag:
        tag = self.tag_repo.get_by_id(tag_id, user_id)
        if tag is None:
            raise TagNotFoundError("Tag not found")
        if tag.user_id is None:
            raise TagValidationError("System tags cannot be modified")
        if data.name is not None and data.name != tag.name:
            if self.tag_repo.name_exists(data.name, user_id, exclude_id=tag.id):
                raise TagConflictError("Tag with this name already exists")
            tag.name = data.name
        if data.color is not None:
            tag.color = data.color
        self.tag_repo.update(tag)
        self.tag_repo.commit()
        self.tag_repo.refresh(tag)
        return tag

    def delete_tag(self, user_id: UUID, tag_id: int) -> None:
        tag = self.tag_repo.get_by_id(tag_id, user_id)
        if tag is None:
            raise TagNotFoundError("Tag not found")
        if tag.user_id is None:
            raise TagValidationError("System tags cannot be deleted")
        self.tag_repo.delete_tag(tag)
        self.tag_repo.commit()

    def list_transaction_tags(self, user_id: UUID, transaction_id: UUID) -> list[Tag]:
        tx = self.transaction_repo.get_by_id(transaction_id, user_id)
        if tx is None:
            raise TagNotFoundError("Transaction not found")
        return self.tag_repo.list_tags_for_transaction(transaction_id)

    def assign_tags(
        self, user_id: UUID, transaction_id: UUID, tag_ids: list[int]
    ) -> list[Tag]:
        tx = self.transaction_repo.get_by_id(transaction_id, user_id)
        if tx is None:
            raise TagNotFoundError("Transaction not found")
        for tag_id in tag_ids:
            tag = self.tag_repo.get_by_id(tag_id, user_id)
            if tag is None:
                raise TagNotFoundError(f"Tag with id {tag_id} not found")
            self.tag_repo.add_transaction_tag(transaction_id, tag_id)
        self.tag_repo.commit()
        return self.tag_repo.list_tags_for_transaction(transaction_id)

    def remove_tag(self, user_id: UUID, transaction_id: UUID, tag_id: int) -> None:
        tx = self.transaction_repo.get_by_id(transaction_id, user_id)
        if tx is None:
            raise TagNotFoundError("Transaction not found")
        self.tag_repo.remove_transaction_tag(transaction_id, tag_id)
        self.tag_repo.commit()

