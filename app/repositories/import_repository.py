from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.import_batch import ImportBatch, ImportRow
from app.repositories.base import BaseRepository


class ImportRepository(BaseRepository[ImportBatch]):
    def __init__(self, db: Session) -> None:
        super().__init__(db)

    def get_batch(self, batch_id: UUID, user_id: UUID) -> ImportBatch | None:
        stmt = select(ImportBatch).where(
            ImportBatch.id == batch_id,
            ImportBatch.user_id == user_id,
        )
        return self.db.scalar(stmt)

    def list_batches(
        self,
        user_id: UUID,
        account_id: UUID | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> list[ImportBatch]:
        stmt = select(ImportBatch).where(ImportBatch.user_id == user_id)
        if account_id is not None:
            stmt = stmt.where(ImportBatch.account_id == account_id)
        stmt = stmt.order_by(ImportBatch.created_at.desc()).offset(offset).limit(limit)
        return list(self.db.scalars(stmt).all())

    def get_confirmed_by_hash(self, account_id: UUID, file_hash: str) -> ImportBatch | None:
        stmt = select(ImportBatch).where(
            ImportBatch.account_id == account_id,
            ImportBatch.file_hash == file_hash,
            ImportBatch.status == "confirmed",
        )
        return self.db.scalar(stmt)

    def create_batch(self, batch: ImportBatch) -> ImportBatch:
        self.db.add(batch)
        self.db.flush()
        return batch

    def create_rows(self, rows: list[ImportRow]) -> list[ImportRow]:
        self.db.add_all(rows)
        self.db.flush()
        return rows

    def list_rows(self, batch_id: UUID) -> list[ImportRow]:
        stmt = (
            select(ImportRow)
            .where(ImportRow.batch_id == batch_id)
            .order_by(ImportRow.row_number.asc())
        )
        return list(self.db.scalars(stmt).all())

    def delete_batch(self, batch: ImportBatch) -> None:
        self.db.delete(batch)
        self.db.flush()

