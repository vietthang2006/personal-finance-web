from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, or_, select, update
from sqlalchemy.orm import Session

from app.models.account import Account
from app.models.transaction import Transaction, Transfer
from app.repositories.base import BaseRepository


class AccountRepository(BaseRepository[Account]):
    def __init__(self, db: Session) -> None:
        super().__init__(db)

    def create(self, account: Account) -> Account:
        self.db.add(account)
        self.db.flush()
        return account

    def get_by_id(
        self, account_id: UUID, user_id: UUID, for_update: bool = False
    ) -> Account | None:
        stmt = select(Account).where(Account.id == account_id, Account.user_id == user_id)
        if for_update:
            stmt = stmt.with_for_update()
        return self.db.scalar(stmt)

    def get_for_update(self, account_id: UUID, user_id: UUID) -> Account | None:
        return self.get_by_id(account_id, user_id, for_update=True)

    def lock_many(self, account_ids: list[UUID], user_id: UUID) -> list[Account]:
        """Locks multiple accounts in ascending ID order to prevent deadlocks."""
        unique_sorted_ids = sorted(list(set(account_ids)))
        stmt = (
            select(Account)
            .where(Account.user_id == user_id, Account.id.in_(unique_sorted_ids))
            .with_for_update()
            .order_by(Account.id.asc())
        )
        return list(self.db.scalars(stmt).all())

    def has_transactions(self, account_id: UUID, user_id: UUID) -> bool:
        """Checks if account has any recorded transactions or transfers."""
        tx_exists = self.db.scalar(
            select(
                select(Transaction.id)
                .where(Transaction.account_id == account_id, Transaction.user_id == user_id)
                .exists()
            )
        )
        if tx_exists:
            return True
        transfer_exists = self.db.scalar(
            select(
                select(Transfer.id)
                .where(
                    Transfer.user_id == user_id,
                    or_(
                        Transfer.from_account_id == account_id,
                        Transfer.to_account_id == account_id,
                    ),
                )
                .exists()
            )
        )
        return bool(transfer_exists)

    def list_by_user(self, user_id: UUID, include_archived: bool = False) -> list[Account]:
        stmt = select(Account).where(Account.user_id == user_id)
        if not include_archived:
            stmt = stmt.where(Account.is_archived.is_(False))
        stmt = stmt.order_by(Account.is_archived.asc(), Account.created_at.desc())
        return list(self.db.scalars(stmt).all())

    def exists_by_name(
        self, user_id: UUID, name: str, exclude_id: UUID | None = None
    ) -> bool:
        stmt = select(
            select(Account)
            .where(
                Account.user_id == user_id,
                func.lower(Account.name) == name.strip().lower(),
            )
            .exists()
        )
        if exclude_id is not None:
            stmt = select(
                select(Account)
                .where(
                    Account.user_id == user_id,
                    func.lower(Account.name) == name.strip().lower(),
                    Account.id != exclude_id,
                )
                .exists()
            )
        return bool(self.db.scalar(stmt))

    def update(self, account: Account) -> Account:
        self.db.flush()
        return account

    def delete(self, account: Account) -> None:
        self.db.delete(account)
        self.db.flush()

    def archive(self, account: Account) -> Account:
        account.is_archived = True
        self.db.flush()
        return account

    def unarchive(self, account: Account) -> Account:
        account.is_archived = False
        self.db.flush()
        return account

    def update_balance_atomic(
        self, account_id: UUID, user_id: UUID, delta: Decimal
    ) -> Decimal | None:
        """Atomically updates account balance with overdraft check.

        Returns updated current_balance if successful, or None if constraint would be violated.
        """
        stmt = (
            update(Account)
            .where(
                Account.id == account_id,
                Account.user_id == user_id,
                Account.is_archived.is_(False),
                or_(
                    (Account.allow_negative.is_(False) & (Account.current_balance + delta >= 0)),
                    (
                        Account.allow_negative.is_(True)
                        & (
                            Account.credit_limit.is_(None)
                            | (Account.current_balance + delta >= -Account.credit_limit)
                        )
                    ),
                ),
            )
            .values(current_balance=Account.current_balance + delta)
            .returning(Account.current_balance)
        )
        return self.db.scalar(stmt)
