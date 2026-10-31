import unittest
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

from app.schemas.tag import TagCreate, TagUpdate
from app.services.tag_service import (
    TagConflictError,
    TagNotFoundError,
    TagService,
    TagValidationError,
)


class TagServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.user_id = uuid4()
        self.service = TagService.__new__(TagService)
        self.service.db = Mock()
        self.service.tag_repo = Mock()
        self.service.transaction_repo = Mock()
        self.service.tag_repo.name_exists.return_value = False

    def test_create_tag_success(self) -> None:
        data = TagCreate(name="Urgent", color="#FF0000")
        tag = self.service.create_tag(self.user_id, data)

        created = self.service.tag_repo.create_tag.call_args.args[0]
        self.assertEqual(created.user_id, self.user_id)
        self.assertEqual(created.name, "Urgent")
        self.assertEqual(created.color, "#FF0000")
        self.service.tag_repo.commit.assert_called_once()
        self.assertIs(tag, created)

    def test_create_tag_rejects_duplicate_name(self) -> None:
        self.service.tag_repo.name_exists.return_value = True
        data = TagCreate(name="Urgent", color="#FF0000")

        with self.assertRaises(TagConflictError):
            self.service.create_tag(self.user_id, data)
        self.service.tag_repo.create_tag.assert_not_called()

    def test_update_tag_system_tag_is_read_only(self) -> None:
        self.service.tag_repo.get_by_id.return_value = SimpleNamespace(
            id=1, user_id=None, name="System Tag", color="#808080"
        )

        with self.assertRaises(TagValidationError):
            self.service.update_tag(self.user_id, 1, TagUpdate(name="New Name"))

    def test_assign_tags_to_transaction_success(self) -> None:
        tx_id = uuid4()
        self.service.transaction_repo.get_by_id.return_value = SimpleNamespace(id=tx_id, user_id=self.user_id)
        self.service.tag_repo.get_by_id.return_value = SimpleNamespace(id=1, user_id=self.user_id)
        self.service.tag_repo.list_tags_for_transaction.return_value = [SimpleNamespace(id=1, name="Tag 1")]

        tags = self.service.assign_tags(self.user_id, tx_id, [1])

        self.service.tag_repo.add_transaction_tag.assert_called_once_with(tx_id, 1)
        self.service.tag_repo.commit.assert_called_once()
        self.assertEqual(len(tags), 1)

