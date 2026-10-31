from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.transaction import Transaction
from app.repositories.account_repository import AccountRepository
from app.repositories.category_repository import CategoryRepository
from app.repositories.transaction_repository import TransactionRepository
from app.schemas.transaction import TransactionCreate, TransactionUpdate


class TransactionServiceError(Exception):
    pass


class TransactionNotFoundError(TransactionServiceError):
    pass


class TransactionValidationError(TransactionServiceError):
    pass


class TransactionConflictError(TransactionServiceError):
    pass


class AccountInsufficientFundsError(TransactionServiceError):
    pass


class TransactionService:
    def __init__(
        self,
        db: Session | None = None,
        transaction_repo: TransactionRepository | None = None,
        account_repo: AccountRepository | None = None,
        category_repo: CategoryRepository | None = None,
    ) -> None:
        if transaction_repo is not None:
            self.transaction_repo = transaction_repo
            self.db = transaction_repo.db
        elif db is not None:
            self.db = db
            self.transaction_repo = TransactionRepository(db)
        else:
            raise ValueError("Either db or transaction_repo must be provided to TransactionService")

        self.account_repo = account_repo or AccountRepository(self.db)
        self.category_repo = category_repo or CategoryRepository(self.db)

    def _validate_category(
        self,
        user_id: UUID,
        category_id: int | None,
        subcategory_id: int | None,
        kind: str,
    ) -> None:
        if category_id is None and subcategory_id is None:
            return
        if category_id is None or subcategory_id is None:
            raise TransactionValidationError("category_id and subcategory_id must be provided together")

        category = self.category_repo.get_visible(category_id, user_id)
        if category is None or not category.is_active or category.kind != kind:
            raise TransactionValidationError("Invalid category or category kind mismatch")

        subcategory = self.category_repo.get_subcategory(category_id, subcategory_id)
        if subcategory is None or not subcategory.is_active:
            raise TransactionValidationError("Invalid subcategory")

    def create_transaction(self, user_id: UUID, data: TransactionCreate) -> Transaction:
        account = self.account_repo.get_by_id(data.account_id, user_id)
        if account is None:
            raise TransactionValidationError("Account not found")
        if account.is_archived:
            raise TransactionValidationError("Cannot create transaction on an archived account")

        self._validate_category(user_id, data.category_id, data.subcategory_id, data.kind)

        delta = data.amount if data.kind == "income" else -data.amount
        updated_balance = self.account_repo.update_balance_atomic(data.account_id, user_id, delta)
        if updated_balance is None:
            raise AccountInsufficientFundsError(
                "Transaction would exceed the account's available balance or credit limit"
            )

        transaction = Transaction(
            user_id=user_id,
            account_id=data.account_id,
            kind=data.kind,
            category_id=data.category_id,
            subcategory_id=data.subcategory_id,
            amount=data.amount,
            transaction_date=data.transaction_date,
            description=data.description,
            merchant=data.merchant,
            dedup_hash=data.dedup_hash,
        )

        try:
            self.transaction_repo.create_transaction(transaction)
            self.transaction_repo.commit()
        except IntegrityError as exc:
            self.transaction_repo.rollback()
            raise TransactionConflictError(
                "Duplicate transaction or invalid transaction reference"
            ) from exc

        self.transaction_repo.refresh(transaction)
        return transaction

    def get_transaction(self, user_id: UUID, transaction_id: UUID) -> Transaction:
        tx = self.transaction_repo.get_by_id(transaction_id, user_id)
        if tx is None:
            raise TransactionNotFoundError("Transaction not found")
        return tx

    def list_transactions(
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
        return self.transaction_repo.list_by_user(
            user_id=user_id,
            account_id=account_id,
            kind=kind,
            category_id=category_id,
            from_date=from_date,
            to_date=to_date,
            offset=offset,
            limit=limit,
        )

    def update_transaction(
        self, user_id: UUID, transaction_id: UUID, data: TransactionUpdate
    ) -> Transaction:
        tx = self.transaction_repo.get_by_id(transaction_id, user_id)
        if tx is None:
            raise TransactionNotFoundError("Transaction not found")

        target_kind = data.kind if data.kind is not None else tx.kind
        target_amount = data.amount if data.amount is not None else tx.amount

        # Validate category pairing and kind matching
        target_category_id = (
            data.category_id if "category_id" in data.model_fields_set else tx.category_id
        )
        target_subcategory_id = (
            data.subcategory_id if "subcategory_id" in data.model_fields_set else tx.subcategory_id
        )

        self._validate_category(user_id, target_category_id, target_subcategory_id, target_kind)

        # Calculate net balance change
        old_delta = tx.amount if tx.kind == "income" else -tx.amount
        new_delta = target_amount if target_kind == "income" else -target_amount
        net_delta = new_delta - old_delta

        if net_delta != Decimal("0"):
            updated_balance = self.account_repo.update_balance_atomic(tx.account_id, user_id, net_delta)
            if updated_balance is None:
                raise AccountInsufficientFundsError(
                    "Updated transaction would exceed the account's available balance or credit limit"
                )

        tx.kind = target_kind
        tx.amount = target_amount
        if "category_id" in data.model_fields_set:
            tx.category_id = data.category_id
            tx.subcategory_id = data.subcategory_id
        if data.transaction_date is not None:
            tx.transaction_date = data.transaction_date
        if "description" in data.model_fields_set:
            tx.description = data.description
        if "merchant" in data.model_fields_set:
            tx.merchant = data.merchant

        try:
            self.transaction_repo.update(tx)
            self.transaction_repo.commit()
        except IntegrityError as exc:
            self.transaction_repo.rollback()
            raise TransactionConflictError("Transaction update conflicts with existing data") from exc

        self.transaction_repo.refresh(tx)
        return tx

    def delete_transaction(self, user_id: UUID, transaction_id: UUID) -> None:
        tx = self.transaction_repo.get_by_id(transaction_id, user_id)
        if tx is None:
            raise TransactionNotFoundError("Transaction not found")

        # Reverse balance delta
        reverse_delta = -tx.amount if tx.kind == "income" else tx.amount
        if reverse_delta != Decimal("0"):
            updated_balance = self.account_repo.update_balance_atomic(tx.account_id, user_id, reverse_delta)
            if updated_balance is None:
                raise AccountInsufficientFundsError(
                    "Deleting this transaction would leave account balance negative"
                )

        self.transaction_repo.delete_transaction(tx)
        self.transaction_repo.commit()

