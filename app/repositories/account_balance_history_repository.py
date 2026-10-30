from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models.account import AccountBalanceHistory
from app.repositories.base import BaseRepository


class AccountBalanceHistoryRepository(BaseRepository[AccountBalanceHistory]):
    def __init__(self, db: Session) -> None:
        super().__init__(db)

    def upsert_snapshot(
        self, account_id: UUID, snapshot_date: date, balance: Decimal
    ) -> AccountBalanceHistory:
        stmt = (
            insert(AccountBalanceHistory)
            .values(account_id=account_id, snapshot_date=snapshot_date, balance=balance)
            .on_conflict_do_update(
                index_elements=["account_id", "snapshot_date"],
                set_={"balance": balance},
            )
            .returning(AccountBalanceHistory)
        )
        result = self.db.scalar(stmt)
        self.db.flush()
        return result

    def get_history(
        self,
        account_id: UUID,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[AccountBalanceHistory]:
        stmt = select(AccountBalanceHistory).where(AccountBalanceHistory.account_id == account_id)
        if start_date is not None:
            stmt = stmt.where(AccountBalanceHistory.snapshot_date >= start_date)
        if end_date is not None:
            stmt = stmt.where(AccountBalanceHistory.snapshot_date <= end_date)
        stmt = stmt.order_by(AccountBalanceHistory.snapshot_date.asc())
        return list(self.db.scalars(stmt).all())
