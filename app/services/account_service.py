from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.errors import AppError, round_currency
from app.models.account import Account, AccountBalanceHistory
from app.repositories.account_balance_history_repository import AccountBalanceHistoryRepository
from app.repositories.account_repository import AccountRepository
from app.repositories.audit_log_repository import AuditLogRepository
from app.repositories.currency_repository import CurrencyRepository
from app.schemas.account import (
    AccountCreate,
    AccountRead,
    AccountSummaryResponse,
    AccountUpdate,
)


class AccountServiceError(AppError):
    def __init__(self, message: str, status_code: int = 400, code: str = "ACCOUNT_ERROR"):
        super().__init__(code=code, status_code=status_code, message=message)


class AccountNotFoundError(AccountServiceError):
    def __init__(self, message: str = "Account not found"):
        super().__init__(message=message, status_code=404, code="ACCOUNT_NOT_FOUND")


class AccountValidationError(AccountServiceError):
    def __init__(self, message: str = "Account validation failed"):
        super().__init__(message=message, status_code=422, code="ACCOUNT_VALIDATION_ERROR")


class AccountConflictError(AccountServiceError):
    def __init__(self, message: str = "Account conflict"):
        super().__init__(message=message, status_code=409, code="ACCOUNT_CONFLICT")


class AccountService:
    def __init__(
        self,
        db: Session | None = None,
        account_repo: AccountRepository | None = None,
        history_repo: AccountBalanceHistoryRepository | None = None,
        currency_repo: CurrencyRepository | None = None,
        audit_repo: AuditLogRepository | None = None,
    ) -> None:
        if db is not None:
            self.db = db
            self.account_repo = account_repo or AccountRepository(db)
            self.history_repo = history_repo or AccountBalanceHistoryRepository(db)
            self.currency_repo = currency_repo or CurrencyRepository(db)
            self.audit_repo = audit_repo or AuditLogRepository(db)
        elif account_repo is not None:
            self.account_repo = account_repo
            self.db = account_repo.db
            self.history_repo = history_repo or AccountBalanceHistoryRepository(self.db)
            self.currency_repo = currency_repo or CurrencyRepository(self.db)
            self.audit_repo = audit_repo or AuditLogRepository(self.db)
        else:
            raise ValueError("Either db or account_repo must be provided to AccountService")

    def create_account(self, user_id: UUID, data: AccountCreate) -> Account:
        if not self.currency_repo.exists(data.currency_code):
            raise AccountValidationError(f"Unsupported currency: {data.currency_code}")

        if self.account_repo.exists_by_name(user_id, data.name):
            raise AccountConflictError(f"An account with name '{data.name}' already exists")

        today = datetime.now(timezone.utc).date()

        account = Account(
            user_id=user_id,
            name=data.name,
            kind=data.kind,
            currency_code=data.currency_code,
            bank_name=data.bank_name,
            opening_balance=data.opening_balance,
            current_balance=data.opening_balance,
            allow_negative=data.allow_negative,
            credit_limit=data.credit_limit,
            billing_day=data.billing_day,
            due_day=data.due_day,
            is_archived=False,
        )
        self.account_repo.create(account)
        if getattr(self, "history_repo", None) is not None:
            self.history_repo.upsert_snapshot(account.id, today, account.current_balance)
        if getattr(self, "audit_repo", None) is not None:
            self.audit_repo.log(
                action="CREATE",
                entity_type="account",
                actor_id=user_id,
                entity_id=str(account.id),
                changes={"name": data.name, "kind": data.kind, "balance": str(account.current_balance)},
            )
        self.account_repo.commit()
        self.account_repo.refresh(account)
        return account

    def get_account(self, user_id: UUID, account_id: UUID, for_update: bool = False) -> Account:
        account = self.account_repo.get_by_id(account_id, user_id, for_update=for_update)
        if account is None:
            raise AccountNotFoundError("Account not found")
        return account

    def list_accounts(self, user_id: UUID, include_archived: bool = False) -> list[Account]:
        return self.account_repo.list_by_user(user_id, include_archived=include_archived)

    def list_accounts_summary(
        self,
        user_id: UUID,
        default_currency: str = "VND",
        include_archived: bool = False,
    ) -> AccountSummaryResponse:
        accounts = self.list_accounts(user_id, include_archived=include_archived)
        target_curr_obj = self.currency_repo.get_by_code(default_currency)
        decimal_places = target_curr_obj.decimal_places if target_curr_obj else 0

        total_assets = Decimal("0.00")
        total_liabilities = Decimal("0.00")
        account_reads: list[AccountRead] = []

        for acc in accounts:
            base_bal = self.currency_repo.convert_currency(
                acc.current_balance, acc.currency_code, default_currency, preferred_type="transfer_buy"
            )
            read_item = AccountRead.model_validate(acc)
            read_item.balance_base = base_bal
            account_reads.append(read_item)

            if acc.current_balance < 0:
                total_liabilities += abs(base_bal)
            else:
                total_assets += base_bal

        total_assets = round_currency(total_assets, decimal_places)
        total_liabilities = round_currency(total_liabilities, decimal_places)
        net_worth = round_currency(total_assets - total_liabilities, decimal_places)

        return AccountSummaryResponse(
            default_currency=default_currency,
            total_assets_base=total_assets,
            total_liabilities_base=total_liabilities,
            net_worth_base=net_worth,
            accounts=account_reads,
        )

    def update_account(self, user_id: UUID, account_id: UUID, data: AccountUpdate) -> Account:
        account = self.get_account(user_id, account_id, for_update=True)

        # Check transaction history restrictions
        has_tx = self.account_repo.has_transactions(account_id, user_id)
        if has_tx:
            if data.kind is not None and data.kind != account.kind:
                raise AppError(
                    code="ACCOUNT_HAS_TRANSACTIONS",
                    status_code=409,
                    message="Cannot modify account kind because transaction history exists",
                )
            if data.currency_code is not None and data.currency_code.upper() != account.currency_code:
                raise AppError(
                    code="ACCOUNT_HAS_TRANSACTIONS",
                    status_code=409,
                    message="Cannot modify account currency because transaction history exists",
                )
            if data.opening_balance is not None and data.opening_balance != account.opening_balance:
                raise AppError(
                    code="ACCOUNT_HAS_TRANSACTIONS",
                    status_code=409,
                    message="Cannot modify opening balance because transaction history exists",
                )

        if data.name is not None and data.name.strip().lower() != account.name.strip().lower():
            if self.account_repo.exists_by_name(user_id, data.name, exclude_id=account.id):
                raise AccountConflictError(f"An account with name '{data.name}' already exists")
            account.name = data.name.strip()

        if data.bank_name is not None:
            account.bank_name = data.bank_name.strip() or None

        if data.is_archived is not None:
            account.is_archived = data.is_archived

        if account.kind == "credit_card":
            next_credit_limit = (
                data.credit_limit if data.credit_limit is not None else account.credit_limit
            )
            if next_credit_limit is not None and account.current_balance < -next_credit_limit:
                raise AccountValidationError(
                    "credit_limit cannot be lower than the current card debt"
                )
            if data.credit_limit is not None:
                account.credit_limit = data.credit_limit
            if data.billing_day is not None:
                account.billing_day = data.billing_day
            if data.due_day is not None:
                account.due_day = data.due_day

        self.account_repo.update(account)
        if getattr(self, "audit_repo", None) is not None:
            self.audit_repo.log(
                action="UPDATE",
                entity_type="account",
                actor_id=user_id,
                entity_id=str(account.id),
                changes=data.model_dump(exclude_unset=True),
            )
        self.account_repo.commit()
        self.account_repo.refresh(account)
        return account

    def delete_account(self, user_id: UUID, account_id: UUID) -> None:
        account = self.get_account(user_id, account_id, for_update=True)
        if self.account_repo.has_transactions(account_id, user_id):
            raise AppError(
                code="ACCOUNT_HAS_TRANSACTIONS",
                status_code=409,
                message="Cannot delete account with existing transactions; please archive it instead",
            )
        self.account_repo.delete(account)
        if getattr(self, "audit_repo", None) is not None:
            self.audit_repo.log(
                action="DELETE",
                entity_type="account",
                actor_id=user_id,
                entity_id=str(account_id),
            )
        self.account_repo.commit()

    def archive_account(self, user_id: UUID, account_id: UUID) -> Account:
        account = self.get_account(user_id, account_id, for_update=True)
        self.account_repo.archive(account)
        if getattr(self, "audit_repo", None) is not None:
            self.audit_repo.log(action="ARCHIVE", entity_type="account", actor_id=user_id, entity_id=str(account.id))
        self.account_repo.commit()
        self.account_repo.refresh(account)
        return account

    def unarchive_account(self, user_id: UUID, account_id: UUID) -> Account:
        account = self.get_account(user_id, account_id, for_update=True)
        self.account_repo.unarchive(account)
        if getattr(self, "audit_repo", None) is not None:
            self.audit_repo.log(action="UNARCHIVE", entity_type="account", actor_id=user_id, entity_id=str(account.id))
        self.account_repo.commit()
        self.account_repo.refresh(account)
        return account

    def get_balance_history(
        self,
        user_id: UUID,
        account_id: UUID,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[AccountBalanceHistory]:
        account = self.get_account(user_id, account_id)
        return self.history_repo.get_history(account.id, start_date=start_date, end_date=end_date)

    def take_snapshot(
        self,
        user_id: UUID,
        account_id: UUID,
        snapshot_date: date | None = None,
    ) -> AccountBalanceHistory:
        account = self.get_account(user_id, account_id)
        today = snapshot_date or datetime.now(timezone.utc).date()
        record = self.history_repo.upsert_snapshot(account.id, today, account.current_balance)
        self.account_repo.commit()
        return record
