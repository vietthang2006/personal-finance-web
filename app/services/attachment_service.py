import os
from pathlib import Path
import re
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from app.models.transaction import TransactionAttachment
from app.repositories.attachment_repository import AttachmentRepository
from app.repositories.transaction_repository import TransactionRepository


MAX_ATTACHMENT_SIZE_BYTES = 10 * 1024 * 1024  # 10MB


class AttachmentServiceError(Exception):
    pass


class AttachmentNotFoundError(AttachmentServiceError):
    pass


class AttachmentValidationError(AttachmentServiceError):
    pass


class AttachmentPayloadTooLargeError(AttachmentServiceError):
    pass


class AttachmentService:
    def __init__(
        self,
        db: Session | None = None,
        attachment_repo: AttachmentRepository | None = None,
        transaction_repo: TransactionRepository | None = None,
        storage_dir: Path | str = "uploads/attachments",
    ) -> None:
        if attachment_repo is not None:
            self.attachment_repo = attachment_repo
            self.db = attachment_repo.db
        elif db is not None:
            self.db = db
            self.attachment_repo = AttachmentRepository(db)
        else:
            raise ValueError("Either db or attachment_repo must be provided to AttachmentService")

        self.transaction_repo = transaction_repo or TransactionRepository(self.db)
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def _sanitize_filename(self, filename: str) -> str:
        # Strip paths and keep only base safe filename
        name = os.path.basename(filename)
        cleaned = re.sub(r"[^A-Za-z0-9_.-]", "_", name)
        return cleaned[:200] or "attachment.bin"

    def upload_attachment(
        self,
        user_id: UUID,
        transaction_id: UUID,
        file_name: str,
        mime_type: str,
        content: bytes,
    ) -> TransactionAttachment:
        tx = self.transaction_repo.get_by_id(transaction_id, user_id)
        if tx is None:
            raise AttachmentNotFoundError("Transaction not found")

        size_bytes = len(content)
        if size_bytes > MAX_ATTACHMENT_SIZE_BYTES:
            raise AttachmentPayloadTooLargeError("Attachment size exceeds maximum limit of 10MB")
        if size_bytes == 0:
            raise AttachmentValidationError("Cannot upload an empty file")

        safe_name = self._sanitize_filename(file_name)
        storage_key = f"{uuid4().hex}_{safe_name}"
        file_path = self.storage_dir / storage_key

        with open(file_path, "wb") as f:
            f.write(content)

        attachment = TransactionAttachment(
            transaction_id=transaction_id,
            storage_key=storage_key,
            file_name=safe_name,
            mime_type=mime_type or "application/octet-stream",
            size_bytes=size_bytes,
        )

        try:
            self.attachment_repo.create_attachment(attachment)
            self.attachment_repo.commit()
        except Exception:
            self.attachment_repo.rollback()
            if file_path.exists():
                file_path.unlink()
            raise

        self.attachment_repo.refresh(attachment)
        return attachment

    def get_attachment(
        self, user_id: UUID, transaction_id: UUID, attachment_id: UUID
    ) -> tuple[TransactionAttachment, Path]:
        tx = self.transaction_repo.get_by_id(transaction_id, user_id)
        if tx is None:
            raise AttachmentNotFoundError("Transaction not found")

        attachment = self.attachment_repo.get_by_id(attachment_id)
        if attachment is None or attachment.transaction_id != transaction_id:
            raise AttachmentNotFoundError("Attachment not found")

        file_path = self.storage_dir / attachment.storage_key
        if not file_path.exists():
            raise AttachmentNotFoundError("Attachment file not found on disk")

        return attachment, file_path

    def list_attachments(
        self, user_id: UUID, transaction_id: UUID
    ) -> list[TransactionAttachment]:
        tx = self.transaction_repo.get_by_id(transaction_id, user_id)
        if tx is None:
            raise AttachmentNotFoundError("Transaction not found")

        return self.attachment_repo.list_by_transaction(transaction_id)

    def delete_attachment(
        self, user_id: UUID, transaction_id: UUID, attachment_id: UUID
    ) -> None:
        tx = self.transaction_repo.get_by_id(transaction_id, user_id)
        if tx is None:
            raise AttachmentNotFoundError("Transaction not found")

        attachment = self.attachment_repo.get_by_id(attachment_id)
        if attachment is None or attachment.transaction_id != transaction_id:
            raise AttachmentNotFoundError("Attachment not found")

        file_path = self.storage_dir / attachment.storage_key
        self.attachment_repo.delete_attachment(attachment)
        self.attachment_repo.commit()

        if file_path.exists():
            try:
                file_path.unlink()
            except OSError:
                pass

