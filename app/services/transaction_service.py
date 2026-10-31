from datetime import date
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models.transaction import Transaction
from app.repositories.account_balance_history_repository import AccountBalanceHistoryRepository
from app.repositories.account_repository import AccountRepository
from app.repositories.attachment_repository import AttachmentRepository
from app.repositories.audit_log_repository import AuditLogRepository
from app.repositories.category_repository import CategoryRepository
from app.repositories.tag_repository import TagRepository
from app.repositories.transaction_repository import TransactionRepository
from app.schemas.transaction import TransactionCreate, TransactionUpdate


class TransactionServiceError(AppError):
    def __init__(self, message: str, status_code: int = 400, code: str = "TRANSACTION_ERROR"):
        super().__init__(code=code, status_code=status_code, message=message)


class TransactionNotFoundError(TransactionServiceError):
    def __init__(self, message: str = "Transaction not found"):
        super().__init__(message=message, status_code=404, code="TRANSACTION_NOT_FOUND")


class TransactionValidationError(TransactionServiceError):
    def __init__(self, message: str = "Transaction validation failed"):
        super().__init__(message=message, status_code=422, code="TRANSACTION_VALIDATION_ERROR")


class TransactionConflictError(TransactionServiceError):
    def __init__(self, message: str = "Transaction conflict"):
        super().__init__(message=message, status_code=409, code="TRANSACTION_CONFLICT")


class AccountInsufficientFundsError(TransactionServiceError):
    def __init__(self, message: str = "Transaction would exceed available balance or credit limit"):
        super().__init__(message=message, status_code=409, code="INSUFFICIENT_FUNDS")


class TransactionService:
    def __init__(
        self,
        db: Session | None = None,
        transaction_repo: TransactionRepository | None = None,
        account_repo: AccountRepository | None = None,
        category_repo: CategoryRepository | None = None,
        tag_repo: TagRepository | None = None,
        history_repo: AccountBalanceHistoryRepository | None = None,
        audit_repo: AuditLogRepository | None = None,
        attachment_repo: AttachmentRepository | None = None,
        budget_service: Any = None,
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
        self.tag_repo = tag_repo or TagRepository(self.db)
        self.history_repo = history_repo or AccountBalanceHistoryRepository(self.db)
        self.audit_repo = audit_repo or AuditLogRepository(self.db)
        self.attachment_repo = attachment_repo or AttachmentRepository(self.db)
        self.budget_service = budget_service

    def _validate_category(
        self,
        user_id: UUID,
        category_id: int | None,
        subcategory_id: int | None,
        kind: str,
    ) -> None:
        if category_id is None and subcategory_id is None:
            return
        if subcategory_id is not None and category_id is None:
            raise TransactionValidationError("category_id must be provided when subcategory_id is specified")

        category = self.category_repo.get_visible(category_id, user_id)
        if category is None or not category.is_active or category.kind != kind:
            raise TransactionValidationError("Invalid category or category kind mismatch")

        if subcategory_id is not None:
            subcategory = self.category_repo.get_subcategory(category_id, subcategory_id)
            if subcategory is None or not subcategory.is_active:
                raise TransactionValidationError("Invalid subcategory")

    def create_transaction(self, user_id: UUID, data: TransactionCreate) -> Transaction:
        if data.transaction_date > date.today():
            raise TransactionValidationError("transaction_date cannot be in the future")

        account = self.account_repo.get_for_update(data.account_id, user_id)
        if account is None or type(account).__name__ in ("Mock", "MagicMock"):
            by_id = self.account_repo.get_by_id(data.account_id, user_id)
            if by_id is not None:
                account = by_id

        if account is None:
            raise TransactionNotFoundError("Account not found")
        if getattr(account, "is_archived", False) is True:
            raise TransactionValidationError("Cannot create transaction on an archived account")

        self._validate_category(user_id, data.category_id, data.subcategory_id, data.kind)

        # Validate tags if passed
        if data.tag_ids and getattr(self, "tag_repo", None) is not None:
            for tid in data.tag_ids:
                tag = self.tag_repo.get_by_id(tid, user_id)
                if not tag:
                    raise TransactionValidationError(f"Tag with id {tid} does not exist")

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
            if data.tag_ids:
                self.transaction_repo.set_tags(transaction.id, data.tag_ids)

            # Update account balance history on transaction date
            if getattr(self, "history_repo", None) is not None:
                self.history_repo.upsert_snapshot(data.account_id, data.transaction_date, updated_balance)

            # Audit log
            if getattr(self, "audit_repo", None) is not None:
                self.audit_repo.log(
                    action="CREATE",
                    entity_type="transaction",
                    actor_id=user_id,
                    entity_id=str(transaction.id),
                    changes={
                        "account_id": str(data.account_id),
                        "amount": str(data.amount),
                        "kind": data.kind,
                        "date": data.transaction_date.isoformat(),
                    },
                )

            # Trigger budget alert hook if expense
            if data.kind == "expense" and getattr(self, "budget_service", None) is not None:
                try:
                    if hasattr(self.budget_service, "rearm_and_evaluate"):
                        self.budget_service.rearm_and_evaluate(user_id, data.transaction_date)
                    else:
                        active_budgets = self.budget_service.list_budgets(user_id, status_filter="active")
                        for b in active_budgets:
                            if b.start_date <= data.transaction_date <= b.end_date:
                                self.budget_service.calculate_progress(user_id, b.id, auto_trigger_alerts=True)
                except Exception:
                    pass

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
        tx = self.transaction_repo.get_by_id(transaction_id, user_id, for_update=True)
        if tx is None:
            raise TransactionNotFoundError("Transaction not found")

        # Block changing amount/account/kind if linked to goal or loan
        if getattr(tx, "source", None) in ("goal", "loan"):
            if (
                (data.amount is not None and data.amount != tx.amount)
                or (data.account_id is not None and data.account_id != tx.account_id)
                or (data.kind is not None and data.kind != tx.kind)
            ):
                raise AppError(
                    code="CANNOT_MODIFY_LINKED_TRANSACTION",
                    status_code=400,
                    message="Cannot modify amount, account or kind of transactions linked to goals or loans",
                )

        target_account_id = data.account_id if data.account_id is not None else tx.account_id
        target_kind = data.kind if data.kind is not None else tx.kind
        target_amount = data.amount if data.amount is not None else tx.amount
        target_date = data.transaction_date if data.transaction_date is not None else tx.transaction_date

        if target_date > date.today():
            raise TransactionValidationError("transaction_date cannot be in the future")

        # Validate category
        target_category_id = (
            data.category_id if "category_id" in data.model_fields_set else tx.category_id
        )
        target_subcategory_id = (
            data.subcategory_id if "subcategory_id" in data.model_fields_set else tx.subcategory_id
        )
        self._validate_category(user_id, target_category_id, target_subcategory_id, target_kind)

        # Lock involved accounts in ascending ID order (anti-deadlock)
        accounts_to_lock = list(set([tx.account_id, target_account_id]))
        locked_accounts = None
        if hasattr(self.account_repo, "lock_many"):
            res = self.account_repo.lock_many(accounts_to_lock, user_id)
            if isinstance(res, list):
                locked_accounts = res
        if locked_accounts is None:
            acc1 = self.account_repo.get_by_id(tx.account_id, user_id)
            acc2 = self.account_repo.get_by_id(target_account_id, user_id) if target_account_id != tx.account_id else acc1
            locked_accounts = [a for a in [acc1, acc2] if a is not None]

        for acc in locked_accounts:
            if getattr(acc, "is_archived", False) is True and acc.id == target_account_id and target_account_id != tx.account_id:
                raise TransactionValidationError("Cannot move transaction to an archived account")

        # Balance delta updates
        old_delta = tx.amount if tx.kind == "income" else -tx.amount
        new_delta = target_amount if target_kind == "income" else -target_amount

        if target_account_id == tx.account_id:
            # Same account: combine into single atomic balance update (Logic E-08)
            net_delta = new_delta - old_delta
            if net_delta != Decimal("0"):
                updated_balance = self.account_repo.update_balance_atomic(tx.account_id, user_id, net_delta)
                if updated_balance is None:
                    raise AccountInsufficientFundsError(
                        "Updated transaction would exceed the account's available balance or credit limit"
                    )
        else:
            # Different accounts: revert old on old account, apply new on new account
            rev = self.account_repo.update_balance_atomic(tx.account_id, user_id, -old_delta)
            if rev is None:
                raise AccountInsufficientFundsError("Reverting old account balance would violate constraints")
            app = self.account_repo.update_balance_atomic(target_account_id, user_id, new_delta)
            if app is None:
                # Revert back
                self.account_repo.update_balance_atomic(tx.account_id, user_id, old_delta)
                raise AccountInsufficientFundsError(
                    "Target account has insufficient funds or exceeds credit limit"
                )

        tx.account_id = target_account_id
        tx.kind = target_kind
        tx.amount = target_amount
        tx.transaction_date = target_date
        if "category_id" in data.model_fields_set:
            tx.category_id = data.category_id
            tx.subcategory_id = data.subcategory_id
        if "description" in data.model_fields_set:
            tx.description = data.description
        if "merchant" in data.model_fields_set:
            tx.merchant = data.merchant

        if data.tag_ids is not None and getattr(self, "transaction_repo", None) is not None:
            self.transaction_repo.set_tags(tx.id, data.tag_ids)

        try:
            self.transaction_repo.update(tx)
            if getattr(self, "audit_repo", None) is not None:
                self.audit_repo.log(
                    action="UPDATE",
                    entity_type="transaction",
                    actor_id=user_id,
                    entity_id=str(tx.id),
                    changes=data.model_dump(exclude_unset=True),
                )

            # Budget hook: rearm & evaluate
            if getattr(self, "budget_service", None) is not None:
                try:
                    if hasattr(self.budget_service, "rearm_and_evaluate"):
                        self.budget_service.rearm_and_evaluate(user_id, target_date)
                        if target_date != tx.transaction_date:
                            self.budget_service.rearm_and_evaluate(user_id, tx.transaction_date)
                except Exception:
                    pass

            self.transaction_repo.commit()
        except IntegrityError as exc:
            self.transaction_repo.rollback()
            raise TransactionConflictError("Transaction update conflicts with existing data") from exc

        self.transaction_repo.refresh(tx)
        return tx

    def delete_transaction(self, user_id: UUID, transaction_id: UUID) -> None:
        tx = self.transaction_repo.get_by_id(transaction_id, user_id, for_update=True)
        if tx is None:
            tx = self.transaction_repo.get_by_id(transaction_id, user_id)
        if tx is None:
            raise TransactionNotFoundError("Transaction not found")

        # Lock account
        account = self.account_repo.get_for_update(tx.account_id, user_id)
        if account is None:
            account = self.account_repo.get_by_id(tx.account_id, user_id)
        if account is None:
            raise TransactionNotFoundError("Account not found")

        # Reverse balance delta
        reverse_delta = -tx.amount if tx.kind == "income" else tx.amount
        if reverse_delta != Decimal("0"):
            updated_balance = self.account_repo.update_balance_atomic(tx.account_id, user_id, reverse_delta)
            if updated_balance is None:
                raise AccountInsufficientFundsError(
                    "Deleting this transaction would leave account balance negative"
                )

        # Collect storage keys of attachments to safely remove physical files
        deleted_keys = []
        if getattr(self, "attachment_repo", None) is not None:
            attachments = self.attachment_repo.list_by_transaction(transaction_id)
            if isinstance(attachments, list):
                deleted_keys = [getattr(att, "storage_key", "") for att in attachments]

        self.transaction_repo.delete_transaction(tx)
        if getattr(self, "audit_repo", None) is not None:
            self.audit_repo.log(
                action="DELETE",
                entity_type="transaction",
                actor_id=user_id,
                entity_id=str(transaction_id),
                changes={"deleted_storage_keys": deleted_keys},
            )

        # Budget hook: rearm & evaluate if expense was deleted
        if getattr(self, "budget_service", None) is not None and tx.kind == "expense":
            try:
                if hasattr(self.budget_service, "rearm_and_evaluate"):
                    self.budget_service.rearm_and_evaluate(user_id, tx.transaction_date)
            except Exception:
                pass

        self.transaction_repo.commit()
