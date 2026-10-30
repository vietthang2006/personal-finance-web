from datetime import date
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.transaction import Transfer
from app.repositories.base import BaseRepository


class TransferRepository(BaseRepository[Transfer]):
    def __init__(self, db: Session) -> None:
        super().__init__(db)

    def get_by_id(self, transfer_id: UUID, user_id: UUID) -> Transfer | None:
        stmt = select(Transfer).where(
            Transfer.id == transfer_id,
            Transfer.user_id == user_id,
        )
        return self.db.scalar(stmt)

    def get_by_idempotency_key(self, idempotency_key: str, user_id: UUID) -> Transfer | None:
        stmt = select(Transfer).where(
            Transfer.idempotency_key == idempotency_key,
            Transfer.user_id == user_id,
        )
        return self.db.scalar(stmt)

    def list_by_user(
        self,
        user_id: UUID,
        from_account_id: UUID | None = None,
        to_account_id: UUID | None = None,
        from_date: date | None = None,
        to_date: date | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> list[Transfer]:
        stmt = select(Transfer).where(Transfer.user_id == user_id)
        if from_account_id is not None:
            stmt = stmt.where(Transfer.from_account_id == from_account_id)
        if to_account_id is not None:
            stmt = stmt.where(Transfer.to_account_id == to_account_id)
        if from_date is not None:
            stmt = stmt.where(Transfer.transaction_date >= from_date)
        if to_date is not None:
            stmt = stmt.where(Transfer.transaction_date <= to_date)

        stmt = (
            stmt.order_by(Transfer.transaction_date.desc(), Transfer.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(self.db.scalars(stmt).all())

    def create_transfer(self, transfer: Transfer) -> Transfer:
        self.db.add(transfer)
        self.db.flush()
        return transfer

