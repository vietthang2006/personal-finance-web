import unittest
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

from app.schemas.category import CategoryCreate, CategoryUpdate, SubcategoryCreate
from app.services.category_service import (
    CategoryConflictError,
    CategoryService,
    CategoryValidationError,
)


class CategoryServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.user_id = uuid4()
        self.service = CategoryService.__new__(CategoryService)
        self.service.db = Mock()
        self.service.category_repo = Mock()
        self.service.category_repo.code_exists.return_value = False
        self.service.category_repo.subcategory_name_exists.return_value = False

    def test_create_category_assigns_it_to_current_user(self) -> None:
        data = CategoryCreate(code="my_food", name="Ăn uống", kind="expense")

        category = self.service.create_category(self.user_id, data)

        created = self.service.category_repo.create_category.call_args.args[0]
        self.assertEqual(created.user_id, self.user_id)
        self.assertEqual(created.code, "my_food")
        self.assertEqual(created.kind, "expense")
        self.assertIs(category, created)
        self.service.category_repo.commit.assert_called_once()

    def test_create_category_rejects_duplicate_user_code(self) -> None:
        self.service.category_repo.code_exists.return_value = True

        with self.assertRaises(CategoryConflictError):
            self.service.create_category(
                self.user_id,
                CategoryCreate(code="food", name="Ăn uống", kind="expense"),
            )

        self.service.category_repo.create_category.assert_not_called()

    def test_system_category_is_visible_but_read_only(self) -> None:
        self.service.category_repo.get_visible.return_value = SimpleNamespace(
            id=10,
            user_id=None,
            name="Ăn uống",
            is_active=True,
        )

        with self.assertRaises(CategoryValidationError):
            self.service.update_category(
                self.user_id,
                10,
                CategoryUpdate(name="Tên mới"),
            )

        self.service.category_repo.update.assert_not_called()

    def test_create_subcategory_rejects_system_category(self) -> None:
        self.service.category_repo.get_visible.return_value = SimpleNamespace(
            id=10,
            user_id=None,
        )

        with self.assertRaises(CategoryValidationError):
            self.service.create_subcategory(
                self.user_id,
                10,
                SubcategoryCreate(name="Cà phê"),
            )

        self.service.category_repo.create_subcategory.assert_not_called()

    def test_create_subcategory_rejects_duplicate_name(self) -> None:
        self.service.category_repo.get_visible.return_value = SimpleNamespace(
            id=20,
            user_id=self.user_id,
        )
        self.service.category_repo.subcategory_name_exists.return_value = True

        with self.assertRaises(CategoryConflictError):
            self.service.create_subcategory(
                self.user_id,
                20,
                SubcategoryCreate(name="Cà phê"),
            )

        self.service.category_repo.create_subcategory.assert_not_called()


if __name__ == "__main__":
    unittest.main()