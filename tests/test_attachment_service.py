import shutil
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

from app.services.attachment_service import (
    AttachmentPayloadTooLargeError,
    AttachmentService,
    AttachmentValidationError,
)


class AttachmentServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.mkdtemp()
        self.user_id = uuid4()
        self.tx_id = uuid4()
        self.service = AttachmentService.__new__(AttachmentService)
        self.service.db = Mock()
        self.service.attachment_repo = Mock()
        self.service.transaction_repo = Mock()
        self.service.storage_dir = Path(self.temp_dir)

        self.service.transaction_repo.get_by_id.return_value = SimpleNamespace(
            id=self.tx_id, user_id=self.user_id
        )

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_upload_attachment_success(self) -> None:
        content = b"sample receipt data"
        attachment = self.service.upload_attachment(
            user_id=self.user_id,
            transaction_id=self.tx_id,
            file_name="receipt.pdf",
            mime_type="application/pdf",
            content=content,
        )

        created = self.service.attachment_repo.create_attachment.call_args.args[0]
        self.assertEqual(created.transaction_id, self.tx_id)
        self.assertEqual(created.file_name, "receipt.pdf")
        self.assertEqual(created.mime_type, "application/pdf")
        self.assertEqual(created.size_bytes, len(content))
        self.service.attachment_repo.commit.assert_called_once()
        self.assertIs(attachment, created)

        # File is written to disk
        file_path = self.service.storage_dir / created.storage_key
        self.assertTrue(file_path.exists())
        self.assertEqual(file_path.read_bytes(), content)

    def test_upload_attachment_empty_file_rejected(self) -> None:
        with self.assertRaises(AttachmentValidationError):
            self.service.upload_attachment(
                user_id=self.user_id,
                transaction_id=self.tx_id,
                file_name="empty.txt",
                mime_type="text/plain",
                content=b"",
            )

    def test_upload_attachment_exceeds_size_limit(self) -> None:
        oversized = b"x" * (10 * 1024 * 1024 + 1)
        with self.assertRaises(AttachmentPayloadTooLargeError):
            self.service.upload_attachment(
                user_id=self.user_id,
                transaction_id=self.tx_id,
                file_name="big.dat",
                mime_type="application/octet-stream",
                content=oversized,
            )

