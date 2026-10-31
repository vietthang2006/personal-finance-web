from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.transaction import TransactionCategory, TransactionSubcategory
from app.repositories.base import BaseRepository


class CategoryRepository(BaseRepository[TransactionCategory]):
    def __init__(self, db: Session) -> None:
        super().__init__(db)

    def list_visible(
        self,
        user_id: UUID,
        kind: str | None = None,
        include_inactive: bool = False,
    ) -> list[TransactionCategory]:
        stmt = select(TransactionCategory).where(
            or_(TransactionCategory.user_id == user_id, TransactionCategory.user_id.is_(None))
        )
        if kind is not None:
            stmt = stmt.where(TransactionCategory.kind == kind)
        if not include_inactive:
            stmt = stmt.where(TransactionCategory.is_active.is_(True))
        stmt = stmt.order_by(TransactionCategory.kind, TransactionCategory.name)
        return list(self.db.scalars(stmt).all())

    def get_visible(self, category_id: int, user_id: UUID) -> TransactionCategory | None:
        stmt = select(TransactionCategory).where(
            TransactionCategory.id == category_id,
            or_(TransactionCategory.user_id == user_id, TransactionCategory.user_id.is_(None)),
        )
        return self.db.scalar(stmt)

    def code_exists(self, code: str, kind: str, user_id: UUID) -> bool:
        stmt = select(
            select(TransactionCategory.id)
            .where(
                TransactionCategory.user_id == user_id,
                TransactionCategory.code == code,
                TransactionCategory.kind == kind,
            )
            .exists()
        )
        return bool(self.db.scalar(stmt))

    def create_category(self, category: TransactionCategory) -> TransactionCategory:
        self.db.add(category)
        self.db.flush()
        return category

    def list_subcategories(
        self, category_id: int, include_inactive: bool = False
    ) -> list[TransactionSubcategory]:
        stmt = select(TransactionSubcategory).where(
            TransactionSubcategory.category_id == category_id
        )
        if not include_inactive:
            stmt = stmt.where(TransactionSubcategory.is_active.is_(True))
        stmt = stmt.order_by(TransactionSubcategory.name)
        return list(self.db.scalars(stmt).all())

    def get_subcategory(
        self, category_id: int, subcategory_id: int
    ) -> TransactionSubcategory | None:
        stmt = select(TransactionSubcategory).where(
            TransactionSubcategory.category_id == category_id,
            TransactionSubcategory.id == subcategory_id,
        )
        return self.db.scalar(stmt)

    def subcategory_name_exists(
        self, category_id: int, name: str, exclude_id: int | None = None
    ) -> bool:
        stmt = select(
            select(TransactionSubcategory.id)
            .where(
                TransactionSubcategory.category_id == category_id,
                func.lower(TransactionSubcategory.name) == name.strip().lower(),
            )
            .exists()
        )
        if exclude_id is not None:
            stmt = select(
                select(TransactionSubcategory.id)
                .where(
                    TransactionSubcategory.category_id == category_id,
                    func.lower(TransactionSubcategory.name) == name.strip().lower(),
                    TransactionSubcategory.id != exclude_id,
                )
                .exists()
            )
        return bool(self.db.scalar(stmt))

    def create_subcategory(self, subcategory: TransactionSubcategory) -> TransactionSubcategory:
        self.db.add(subcategory)
        self.db.flush()
        return subcategory

    def update(self, entity: TransactionCategory | TransactionSubcategory):
        self.db.flush()
        return entity

    def commit(self) -> None:
        self.db.commit()

    def refresh(self, entity: TransactionCategory | TransactionSubcategory):
        self.db.refresh(entity)
        return entity