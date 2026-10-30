from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import AppError, round_currency
from app.models.transaction import Transfer
from app.repositories.account_balance_history_repository import AccountBalanceHistoryRepository
from app.repositories.account_repository import AccountRepository
from app.repositories.audit_log_repository import AuditLogRepository
from app.repositories.currency_repository import CurrencyRepository
from app.repositories.transfer_repository import TransferRepository
from app.schemas.transfer import TransferCreate


class TransferServiceError(AppError):
    def __init__(self, message: str, status_code: int = 400, code: str = "TRANSFER_ERROR"):
        super().__init__(code=code, status_code=status_code, message=message)


class TransferNotFoundError(TransferServiceError):
    def __init__(self, message: str = "Transfer not found"):
        super().__init__(message=message, status_code=404, code="TRANSFER_NOT_FOUND")


class TransferValidationError(TransferServiceError):
    def __init__(self, message: str = "Transfer validation failed"):
        super().__init__(message=message, status_code=422, code="TRANSFER_VALIDATION_ERROR")


class TransferConflictError(TransferServiceError):
    def __init__(self, message: str = "Transfer conflict"):
        super().__init__(message=message, status_code=409, code="TRANSFER_CONFLICT")


class TransferService:
    def __init__(
        self,
        db: Session | None = None,
        transfer_repo: TransferRepository | None = None,
        account_repo: AccountRepository | None = None,
        history_repo: AccountBalanceHistoryRepository | None = None,
        audit_repo: AuditLogRepository | None = None,
        currency_repo: CurrencyRepository | None = None,
    ) -> None:
        if transfer_repo is not None:
            self.transfer_repo = transfer_repo
            self.db = transfer_repo.db
        elif db is not None:
            self.db = db
            self.transfer_repo = TransferRepository(db)
        else:
            raise ValueError("Either db or transfer_repo must be provided to TransferService")

        self.account_repo = account_repo or AccountRepository(self.db)
        self.history_repo = history_repo or AccountBalanceHistoryRepository(self.db)
        self.audit_repo = audit_repo or AuditLogRepository(self.db)
        self.currency_repo = currency_repo or CurrencyRepository(self.db)

    def create_transfer(self, user_id: UUID, data: TransferCreate) -> Transfer:
        # Check idempotency first
        if data.idempotency_key:
            existing = self.transfer_repo.get_by_idempotency_key(data.idempotency_key, user_id)
            if existing is not None:
                return existing

        if data.from_account_id == data.to_account_id:
            raise TransferValidationError("Source and destination accounts must be distinct")

        # Anti-Deadlock: lock accounts in ascending ID order
        locked_accounts = None
        if hasattr(self.account_repo, "lock_many"):
            res = self.account_repo.lock_many([data.from_account_id, data.to_account_id], user_id)
            if isinstance(res, list):
                locked_accounts = res
        if locked_accounts is None:
            from_account = self.account_repo.get_by_id(data.from_account_id, user_id)
            to_account = self.account_repo.get_by_id(data.to_account_id, user_id)
        else:
            acc_map = {acc.id: acc for acc in locked_accounts}
            from_account = acc_map.get(data.from_account_id)
            to_account = acc_map.get(data.to_account_id)

        if from_account is None or to_account is None:
            raise TransferValidationError("Source and destination accounts must belong to the user")

        if getattr(from_account, "is_archived", False) is True or getattr(to_account, "is_archived", False) is True:
            raise TransferValidationError("Cannot transfer to or from an archived account")

        # Target currency decimal places
        to_decimal_places = 2
        if getattr(self, "currency_repo", None) is not None:
            to_curr_obj = self.currency_repo.get_by_code(to_account.currency_code)
            if to_curr_obj:
                to_decimal_places = to_curr_obj.decimal_places

        # Determine target amount and exchange rate
        if from_account.currency_code == to_account.currency_code:
            to_amount = data.amount
            exchange_rate = Decimal("1.00000000")
        else:
            if data.to_amount is not None:
                to_amount = round_currency(data.to_amount, to_decimal_places)
                exchange_rate = (
                    data.exchange_rate
                    if data.exchange_rate is not None
                    else (to_amount / data.amount).quantize(Decimal("0.00000001"))
                )
            elif data.exchange_rate is not None:
                exchange_rate = data.exchange_rate
                to_amount = round_currency(data.amount * exchange_rate, to_decimal_places)
            elif getattr(self, "currency_repo", None) is not None:
                # Use exchange rate from currency repo
                rate = self.currency_repo.get_exchange_rate(
                    from_account.currency_code, to_account.currency_code
                )
                if rate is not None:
                    exchange_rate = rate
                    to_amount = round_currency(data.amount * exchange_rate, to_decimal_places)
                else:
                    raise TransferValidationError(
                        "Cross-currency transfer requires to_amount or exchange_rate"
                    )
            else:
                raise TransferValidationError(
                    "Cross-currency transfer requires to_amount or exchange_rate"
                )

        # Debit source account atomically
        debited_balance = self.account_repo.update_balance_atomic(
            data.from_account_id, user_id, -data.amount
        )
        if debited_balance is None:
            raise TransferValidationError(
                "Source account has insufficient funds or exceeds credit limit"
            )

        # Credit destination account atomically
        credited_balance = self.account_repo.update_balance_atomic(
            data.to_account_id, user_id, to_amount
        )
        if credited_balance is None:
            # Revert debit
            self.account_repo.update_balance_atomic(
                data.from_account_id, user_id, data.amount
            )
            raise TransferValidationError("Destination account cannot accept transferred amount")

        # Upsert balance history for both accounts
        if getattr(self, "history_repo", None) is not None:
            self.history_repo.upsert_snapshot(from_account.id, data.transaction_date, debited_balance)
            self.history_repo.upsert_snapshot(to_account.id, data.transaction_date, credited_balance)

        transfer = Transfer(
            user_id=user_id,
            from_account_id=data.from_account_id,
            to_account_id=data.to_account_id,
            amount=data.amount,
            to_amount=to_amount,
            exchange_rate=exchange_rate,
            transaction_date=data.transaction_date,
            purpose=data.purpose if hasattr(data, "purpose") and data.purpose else "normal",
            description=data.description,
            idempotency_key=data.idempotency_key,
        )

        try:
            self.transfer_repo.create_transfer(transfer)
            if getattr(self, "audit_repo", None) is not None:
                self.audit_repo.log(
                    action="CREATE",
                    entity_type="transfer",
                    actor_id=user_id,
                    entity_id=str(transfer.id),
                    changes={
                        "from_account_id": str(data.from_account_id),
                        "to_account_id": str(data.to_account_id),
                        "amount": str(data.amount),
                        "to_amount": str(to_amount),
                    },
                )
            self.transfer_repo.commit()
        except IntegrityError as exc:
            self.transfer_repo.rollback()
            raise TransferConflictError("Transfer could not be processed due to a duplicate request") from exc

        self.transfer_repo.refresh(transfer)
        return transfer

    def get_transfer(self, user_id: UUID, transfer_id: UUID) -> Transfer:
        transfer = self.transfer_repo.get_by_id(transfer_id, user_id)
        if transfer is None:
            raise TransferNotFoundError("Transfer not found")
        return transfer

    def list_transfers(
        self,
        user_id: UUID,
        from_account_id: UUID | None = None,
        to_account_id: UUID | None = None,
        from_date: date | None = None,
        to_date: date | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> list[Transfer]:
        return self.transfer_repo.list_by_user(
            user_id=user_id,
            from_account_id=from_account_id,
            to_account_id=to_account_id,
            from_date=from_date,
            to_date=to_date,
            offset=offset,
            limit=limit,
        )
