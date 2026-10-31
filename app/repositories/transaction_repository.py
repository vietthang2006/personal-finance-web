from datetime import date
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.transaction import Transaction
from app.repositories.base import BaseRepository


class TransactionRepository(BaseRepository[Transaction]):
    def __init__(self, db: Session) -> None:
        super().__init__(db)

    def get_by_id(self, transaction_id: UUID, user_id: UUID) -> Transaction | None:
        stmt = select(Transaction).where(
            Transaction.id == transaction_id,
            Transaction.user_id == user_id,
        )
        return self.db.scalar(stmt)

    def list_by_user(
        self,
        user_id: UUID,
        account_id: UUID | None = None,
        kind: str | None = None,
        category_id: int | None = None,
        from_date: date | None = None,
        to_date: date | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> list[Transaction]:
        stmt = select(Transaction).where(Transaction.user_id == user_id)
        if account_id is not None:
            stmt = stmt.where(Transaction.account_id == account_id)
        if kind is not None:
            stmt = stmt.where(Transaction.kind == kind)
        if category_id is not None:
            stmt = stmt.where(Transaction.category_id == category_id)
        if from_date is not None:
            stmt = stmt.where(Transaction.transaction_date >= from_date)
        if to_date is not None:
            stmt = stmt.where(Transaction.transaction_date <= to_date)

        stmt = (
            stmt.order_by(Transaction.transaction_date.desc(), Transaction.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(self.db.scalars(stmt).all())

    def create_transaction(self, transaction: Transaction) -> Transaction:
        self.db.add(transaction)
        self.db.flush()
        return transaction

    def delete_transaction(self, transaction: Transaction) -> None:
        self.db.delete(transaction)
        self.db.flush()

