from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.transaction import Transfer
from app.repositories.account_repository import AccountRepository
from app.repositories.transfer_repository import TransferRepository
from app.schemas.transfer import TransferCreate


class TransferServiceError(Exception):
    pass


class TransferNotFoundError(TransferServiceError):
    pass


class TransferValidationError(TransferServiceError):
    pass


class TransferConflictError(TransferServiceError):
    pass


class TransferService:
    def __init__(
        self,
        db: Session | None = None,
        transfer_repo: TransferRepository | None = None,
        account_repo: AccountRepository | None = None,
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

    def create_transfer(self, user_id: UUID, data: TransferCreate) -> Transfer:
        # Check idempotency first
        if data.idempotency_key:
            existing = self.transfer_repo.get_by_idempotency_key(data.idempotency_key, user_id)
            if existing is not None:
                return existing

        from_account = self.account_repo.get_by_id(data.from_account_id, user_id)
        to_account = self.account_repo.get_by_id(data.to_account_id, user_id)

        if from_account is None or to_account is None:
            raise TransferValidationError("Source and destination accounts must belong to the user")

        if from_account.is_archived or to_account.is_archived:
            raise TransferValidationError("Cannot transfer to or from an archived account")

        # Determine target amount and exchange rate
        if from_account.currency_code == to_account.currency_code:
            to_amount = data.amount
            exchange_rate = Decimal("1.00000000")
        else:
            if data.to_amount is not None:
                to_amount = data.to_amount
                exchange_rate = (
                    data.exchange_rate
                    if data.exchange_rate is not None
                    else (to_amount / data.amount).quantize(Decimal("0.00000001"))
                )
            elif data.exchange_rate is not None:
                exchange_rate = data.exchange_rate
                to_amount = (data.amount * exchange_rate).quantize(Decimal("0.01"))
            else:
                raise TransferValidationError(
                    "Cross-currency transfer requires to_amount or exchange_rate"
                )

        # Debit source account
        debited = self.account_repo.update_balance_atomic(
            data.from_account_id, user_id, -data.amount
        )
        if debited is None:
            raise TransferValidationError(
                "Source account has insufficient funds or exceeds credit limit"
            )

        # Credit destination account
        credited = self.account_repo.update_balance_atomic(
            data.to_account_id, user_id, to_amount
        )
        if credited is None:
            # Revert debit
            self.account_repo.update_balance_atomic(
                data.from_account_id, user_id, data.amount
            )
            raise TransferValidationError("Destination account cannot accept funds")

        transfer = Transfer(
            user_id=user_id,
            from_account_id=data.from_account_id,
            to_account_id=data.to_account_id,
            amount=data.amount,
            to_amount=to_amount,
            exchange_rate=exchange_rate,
            transaction_date=data.transaction_date,
            purpose=data.purpose,
            description=data.description,
            idempotency_key=data.idempotency_key,
        )

        try:
            self.transfer_repo.create_transfer(transfer)
            self.transfer_repo.commit()
        except IntegrityError as exc:
            self.transfer_repo.rollback()
            raise TransferConflictError("Transfer conflicts with existing record") from exc

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
