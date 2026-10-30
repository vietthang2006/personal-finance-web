import csv
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
import hashlib
import io
import json
from pathlib import PurePath
from uuid import UUID
from zipfile import BadZipFile

from openpyxl.utils.exceptions import InvalidFileException
import pandas as pd
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.account import Account
from app.models.import_batch import ImportBatch, ImportRow
from app.models.transaction import Transaction, TransactionCategory, TransactionSubcategory
from app.repositories.account_repository import AccountRepository
from app.repositories.category_repository import CategoryRepository
from app.repositories.import_repository import ImportRepository
from app.repositories.transaction_repository import TransactionRepository
from app.schemas.import_batch import ImportCategoryChoice


MAX_IMPORT_SIZE = 10 * 1024 * 1024  # 10 MB
MAX_IMPORT_ROWS = 10_000


class ImportServiceError(Exception):
    def __init__(self, detail: str, status_code: int = 422):
        super().__init__(detail)
        self.status_code = status_code


class ImportNotFoundError(ImportServiceError):
    def __init__(self, detail: str = "Import batch not found"):
        super().__init__(detail, 404)


class ImportConflictError(ImportServiceError):
    def __init__(self, detail: str = "Conflict with existing import"):
        super().__init__(detail, 409)


class ImportValidationError(ImportServiceError):
    def __init__(self, detail: str = "Validation error"):
        super().__init__(detail, 422)


class ImportPayloadTooLargeError(ImportServiceError):
    def __init__(self, detail: str = "File size exceeds the 10 MB limit"):
        super().__init__(detail, 413)


class ImportService:
    def __init__(
        self,
        db: Session | None = None,
        import_repo: ImportRepository | None = None,
        account_repo: AccountRepository | None = None,
        transaction_repo: TransactionRepository | None = None,
        category_repo: CategoryRepository | None = None,
    ) -> None:
        if import_repo is not None:
            self.import_repo = import_repo
            self.db = import_repo.db
        elif db is not None:
            self.db = db
            self.import_repo = ImportRepository(db)
        else:
            raise ValueError("Either db or import_repo must be provided to ImportService")

        self.account_repo = account_repo or AccountRepository(self.db)
        self.transaction_repo = transaction_repo or TransactionRepository(self.db)
        self.category_repo = category_repo or CategoryRepository(self.db)

    def preview_import(
        self, user_id: UUID, account_id: UUID, filename: str, content: bytes
    ) -> tuple[ImportBatch, list[ImportRow]]:
        if not content:
            raise ImportValidationError("Uploaded file is empty")
        if len(content) > MAX_IMPORT_SIZE:
            raise ImportPayloadTooLargeError("File size exceeds the 10 MB limit")

        account = self.account_repo.get_by_id(account_id, user_id)
        if account is None:
            raise ImportNotFoundError("Account not found")
        if account.is_archived:
            raise ImportValidationError("Cannot import statements into an archived account")

        file_hash = hashlib.sha256(content).hexdigest()
        confirmed = self.import_repo.get_confirmed_by_hash(account_id, file_hash)
        if confirmed is not None:
            raise ImportConflictError("This file has already been imported")

        records = self._read_records(filename, content)

        # Get existing dedup hashes for this user/account
        existing_hashes = set(
            self.db.scalars(
                select(Transaction.dedup_hash).where(
                    Transaction.account_id == account_id,
                    Transaction.dedup_hash.is_not(None),
                )
            ).all()
        )

        seen_in_file: set[str] = set()
        valid_rows = 0
        duplicate_rows = 0
        invalid_rows = 0
        row_entities: list[ImportRow] = []

        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(hours=24)

        batch = ImportBatch(
            user_id=user_id,
            account_id=account_id,
            file_name=filename or "statement.csv",
            file_hash=file_hash,
            status="staged",
            total_rows=len(records),
            valid_rows=0,
            duplicate_rows=0,
            invalid_rows=0,
            imported_rows=0,
            expires_at=expires_at,
        )
        self.import_repo.create_batch(batch)

        for idx, raw in enumerate(records, start=1):
            try:
                parsed = self._validate_and_parse_row(raw, account_id)
                dedup = parsed["dedup_hash"]
                if dedup in existing_hashes or dedup in seen_in_file:
                    status = "duplicate"
                    duplicate_rows += 1
                else:
                    status = "valid"
                    valid_rows += 1
                    seen_in_file.add(dedup)

                row_entities.append(
                    ImportRow(
                        batch_id=batch.id,
                        row_number=idx,
                        raw_data=raw,
                        parsed_data=parsed["canonical"],
                        tx_date=parsed["transaction_date"],
                        description=parsed["description"],
                        merchant=parsed["merchant"],
                        amount=parsed["amount"],
                        kind=parsed["kind"],
                        suggested_category_id=parsed["category_id"],
                        chosen_category_id=parsed["category_id"],
                        dedup_hash=dedup,
                        status=status,
                    )
                )
            except Exception as exc:
                invalid_rows += 1
                row_entities.append(
                    ImportRow(
                        batch_id=batch.id,
                        row_number=idx,
                        raw_data=raw,
                        status="invalid",
                        error_message=str(exc),
                    )
                )

        batch.valid_rows = valid_rows
        batch.duplicate_rows = duplicate_rows
        batch.invalid_rows = invalid_rows

        self.import_repo.create_rows(row_entities)
        self.import_repo.commit()
        self.import_repo.refresh(batch)

        return batch, row_entities

    def confirm_import(
        self,
        user_id: UUID,
        batch_id: UUID,
        category_choices: list[ImportCategoryChoice],
    ) -> ImportBatch:
        batch = self.import_repo.get_batch(batch_id, user_id)
        if batch is None:
            raise ImportNotFoundError("Import batch not found")
        if batch.status == "confirmed":
            raise ImportConflictError("Import batch has already been confirmed")

        now = datetime.now(timezone.utc)
        if batch.status == "expired" or batch.expires_at < now:
            batch.status = "expired"
            self.import_repo.commit()
            raise ImportValidationError("Import batch has expired")

        # Concurrency check
        confirmed_same_file = self.import_repo.get_confirmed_by_hash(
            batch.account_id, batch.file_hash
        )
        if confirmed_same_file is not None and confirmed_same_file.id != batch.id:
            raise ImportConflictError("This file has already been imported")

        rows = self.import_repo.list_rows(batch.id)
        valid_rows = [r for r in rows if r.status == "valid"]
        if not valid_rows:
            raise ImportValidationError("No valid rows to import")

        choices_map = {c.row_id: (c.category_id, c.subcategory_id) for c in category_choices}

        # Validate category choices and assign
        transactions: list[Transaction] = []
        net_delta = Decimal("0")

        for r in valid_rows:
            cat_id = None
            subcat_id = None
            if r.id in choices_map:
                cat_id, subcat_id = choices_map[r.id]
                # Validate category belongs/visible to user and matches kind
                category = self.category_repo.get_visible(cat_id, user_id)
                if category is None or category.kind != r.kind:
                    raise ImportValidationError(f"Invalid category for row {r.row_number}")
                subcategory = self.category_repo.get_subcategory(cat_id, subcat_id)
                if subcategory is None:
                    raise ImportValidationError(f"Invalid subcategory for row {r.row_number}")
                r.chosen_category_id = cat_id

            delta = r.amount if r.kind == "income" else -r.amount
            net_delta += delta

            tx = Transaction(
                user_id=user_id,
                account_id=batch.account_id,
                kind=r.kind,
                category_id=cat_id,
                subcategory_id=subcat_id,
                amount=r.amount,
                transaction_date=r.tx_date,
                description=r.description,
                merchant=r.merchant,
                source="import",
                import_batch_id=batch.id,
                dedup_hash=r.dedup_hash,
            )
            transactions.append(tx)

        # Atomic balance update on account
        updated_balance = self.account_repo.update_balance_atomic(
            batch.account_id, user_id, net_delta
        )
        if updated_balance is None:
            raise ImportConflictError(
                "Imported transactions exceed the account's balance or credit limit"
            )

        # Insert transactions
        self.db.add_all(transactions)
        self.db.flush()

        # Link rows to transactions and mark imported
        for r, tx in zip(valid_rows, transactions):
            r.transaction_id = tx.id
            r.status = "imported"

        batch.status = "confirmed"
        batch.confirmed_at = now
        batch.imported_rows = len(valid_rows)

        try:
            self.import_repo.commit()
        except IntegrityError as exc:
            self.import_repo.rollback()
            raise ImportConflictError("Duplicate transaction or conflicting import batch") from exc

        self.import_repo.refresh(batch)
        return batch

    def get_batch(
        self, user_id: UUID, batch_id: UUID
    ) -> tuple[ImportBatch, list[ImportRow]]:
        batch = self.import_repo.get_batch(batch_id, user_id)
        if batch is None:
            raise ImportNotFoundError("Import batch not found")
        rows = self.import_repo.list_rows(batch.id)
        return batch, rows

    def list_batches(
        self,
        user_id: UUID,
        account_id: UUID | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> list[ImportBatch]:
        return self.import_repo.list_batches(
            user_id=user_id, account_id=account_id, offset=offset, limit=limit
        )

    def cancel_batch(self, user_id: UUID, batch_id: UUID) -> None:
        batch = self.import_repo.get_batch(batch_id, user_id)
        if batch is None:
            raise ImportNotFoundError("Import batch not found")
        if batch.status == "confirmed":
            raise ImportValidationError("Cannot cancel a confirmed import batch")
        self.import_repo.delete_batch(batch)
        self.import_repo.commit()

    def _read_records(self, filename: str, content: bytes) -> list[dict[str, str]]:
        suffix = PurePath(filename).suffix.lower()
        if suffix == ".csv":
            try:
                text_content = content.decode("utf-8-sig")
                reader = csv.DictReader(io.StringIO(text_content))
                if reader.fieldnames is None:
                    raise ImportValidationError("CSV must include a header row")
                records = [
                    {str(key or "").strip().lower(): str(value or "").strip() for key, value in row.items()}
                    for row in reader
                ]
            except UnicodeDecodeError as exc:
                raise ImportValidationError("CSV must use UTF-8 encoding") from exc
        elif suffix == ".xlsx":
            try:
                frame = pd.read_excel(io.BytesIO(content), dtype=str, engine="openpyxl").fillna("")
            except (ValueError, OSError, BadZipFile, InvalidFileException) as exc:
                raise ImportValidationError("Could not read the XLSX file") from exc
            frame.columns = [str(column).strip().lower() for column in frame.columns]
            records = [
                {str(key): str(value).strip() for key, value in row.items()}
                for row in frame.to_dict(orient="records")
            ]
        else:
            raise ImportValidationError("Only CSV and XLSX files are supported")

        if not records:
            raise ImportValidationError("File contains no transaction rows")
        if not {"transaction_date", "kind", "amount"} <= records[0].keys():
            raise ImportValidationError("File must include transaction_date, kind, and amount columns")
        if len(records) > MAX_IMPORT_ROWS:
            raise ImportValidationError(f"File contains more than {MAX_IMPORT_ROWS} rows")
        return records

    def _validate_and_parse_row(self, raw: dict[str, str], account_id: UUID) -> dict[str, object]:
        missing = {"transaction_date", "kind", "amount"} - raw.keys()
        if missing:
            raise ValueError(f"Missing required columns: {', '.join(sorted(missing))}")

        kind = raw["kind"].strip().lower()
        if kind not in {"income", "expense"}:
            raise ValueError("kind must be income or expense")

        parsed_date = self._parse_date(raw["transaction_date"])

        try:
            amount = Decimal(raw["amount"].strip())
        except (InvalidOperation, ValueError):
            raise ValueError("Invalid amount number")

        if amount <= 0 or amount >= Decimal("10000000000000000") or amount.as_tuple().exponent < -2:
            raise ValueError("amount must be positive and fit numeric(18,2)")

        description = raw.get("description", "").strip() or None
        merchant = raw.get("merchant", "").strip() or None

        category_id = None
        if raw.get("category_id"):
            try:
                category_id = int(raw["category_id"])
            except ValueError:
                pass

        canonical = {
            "account_id": str(account_id),
            "date": parsed_date.isoformat(),
            "kind": kind,
            "amount": format(amount, ".2f"),
            "description": description,
            "merchant": merchant,
        }
        canonical_json = json.dumps(canonical, sort_keys=True, ensure_ascii=False)
        dedup_hash = hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()

        return {
            "canonical": canonical,
            "transaction_date": parsed_date,
            "kind": kind,
            "amount": amount,
            "description": description,
            "merchant": merchant,
            "category_id": category_id,
            "dedup_hash": dedup_hash,
        }

    def _parse_date(self, value: str) -> date:
        cleaned = value.strip()
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%Y/%m/%d"):
            try:
                return datetime.strptime(cleaned, fmt).date()
            except ValueError:
                continue
        raise ValueError(f"Invalid date format for '{cleaned}'. Expected YYYY-MM-DD or DD/MM/YYYY")
