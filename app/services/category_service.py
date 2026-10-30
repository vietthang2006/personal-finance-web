from uuid import UUID

from sqlalchemy.orm import Session

from app.models.transaction import TransactionCategory, TransactionSubcategory
from app.repositories.category_repository import CategoryRepository
from app.schemas.category import (
    CategoryCreate,
    CategoryUpdate,
    SubcategoryCreate,
    SubcategoryUpdate,
)


class CategoryServiceError(Exception):
    pass


class CategoryNotFoundError(CategoryServiceError):
    pass


class CategoryConflictError(CategoryServiceError):
    pass


class CategoryValidationError(CategoryServiceError):
    pass


class CategoryService:
    def __init__(
        self,
        db: Session | None = None,
        category_repo: CategoryRepository | None = None,
    ) -> None:
        if category_repo is not None:
            self.category_repo = category_repo
            self.db = category_repo.db
        elif db is not None:
            self.db = db
            self.category_repo = CategoryRepository(db)
        else:
            raise ValueError("Either db or category_repo must be provided to CategoryService")

    def list_categories(
        self,
        user_id: UUID,
        kind: str | None = None,
        include_inactive: bool = False,
    ) -> list[TransactionCategory]:
        return self.category_repo.list_visible(user_id, kind, include_inactive)

    def create_category(self, user_id: UUID, data: CategoryCreate) -> TransactionCategory:
        if self.category_repo.code_exists(data.code, data.kind, user_id):
            raise CategoryConflictError("Category code already exists")
        category = TransactionCategory(
            user_id=user_id,
            code=data.code,
            name=data.name,
            kind=data.kind,
            icon=data.icon,
        )
        self.category_repo.create_category(category)
        self.category_repo.commit()
        self.category_repo.refresh(category)
        return category

    def update_category(
        self, user_id: UUID, category_id: int, data: CategoryUpdate
    ) -> TransactionCategory:
        category = self.category_repo.get_visible(category_id, user_id)
        if category is None:
            raise CategoryNotFoundError("Category not found")
        if category.user_id is None:
            raise CategoryValidationError("System categories cannot be modified")
        if data.name is not None:
            category.name = data.name
        if data.icon is not None:
            category.icon = data.icon
        if data.is_active is not None:
            category.is_active = data.is_active
        self.category_repo.update(category)
        self.category_repo.commit()
        self.category_repo.refresh(category)
        return category

    def list_subcategories(
        self,
        user_id: UUID,
        category_id: int,
        include_inactive: bool = False,
    ) -> list[TransactionSubcategory]:
        category = self.category_repo.get_visible(category_id, user_id)
        if category is None:
            raise CategoryNotFoundError("Category not found")
        return self.category_repo.list_subcategories(category.id, include_inactive)

    def create_subcategory(
        self, user_id: UUID, category_id: int, data: SubcategoryCreate
    ) -> TransactionSubcategory:
        category = self.category_repo.get_visible(category_id, user_id)
        if category is None:
            raise CategoryNotFoundError("Category not found")
        if category.user_id is None:
            raise CategoryValidationError("Subcategories of system categories are read-only")
        if self.category_repo.subcategory_name_exists(category.id, data.name):
            raise CategoryConflictError("Subcategory name already exists")
        subcategory = TransactionSubcategory(category_id=category.id, name=data.name)
        self.category_repo.create_subcategory(subcategory)
        self.category_repo.commit()
        self.category_repo.refresh(subcategory)
        return subcategory

    def update_subcategory(
        self,
        user_id: UUID,
        category_id: int,
        subcategory_id: int,
        data: SubcategoryUpdate,
    ) -> TransactionSubcategory:
        category = self.category_repo.get_visible(category_id, user_id)
        if category is None:
            raise CategoryNotFoundError("Category not found")
        if category.user_id is None:
            raise CategoryValidationError("Subcategories of system categories are read-only")
        subcategory = self.category_repo.get_subcategory(category.id, subcategory_id)
        if subcategory is None:
            raise CategoryNotFoundError("Subcategory not found")
        if data.name is not None:
            if self.category_repo.subcategory_name_exists(
                category.id, data.name, exclude_id=subcategory.id
            ):
                raise CategoryConflictError("Subcategory name already exists")
            subcategory.name = data.name
        if data.is_active is not None:
            subcategory.is_active = data.is_active
        self.category_repo.update(subcategory)
        self.category_repo.commit()
        self.category_repo.refresh(subcategory)
        return subcategory
