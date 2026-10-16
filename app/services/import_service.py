import csv
import hashlib
import io
import json
from zipfile import BadZipFile
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from pathlib import PurePath
from uuid import UUID

import pandas as pd
from openpyxl.utils.exceptions import InvalidFileException
from sqlalchemy import or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.account import Account
from app.models.import_batch import ImportBatch, ImportRow
from app.models.transaction import Transaction, TransactionCategory, TransactionSubcategory
from app.models.user import User
from app.schemas.import_batch import ImportCategoryChoice, ImportPreview


MAX_IMPORT_SIZE = 10 * 1024 * 1024
MAX_IMPORT_ROWS = 10_000


class ImportError(Exception):
    def __init__(self, detail: str, status_code: int = 422):
        super().__init__(detail)
        self.status_code = status_code


def preview_import(
    db: Session, user: User, account_id: UUID, filename: str, content: bytes
) -> ImportPreview:
    if not content:
        raise ImportError("Uploaded file is empty")
    if len(content) > MAX_IMPORT_SIZE:
        raise ImportError("File size exceeds the 10 MB limit", 413)
    account = db.scalar(
        select(Account).where(Account.id == account_id, Account.user_id == user.id)
    )
    if account is None:
        raise ImportError("Account not found", 404)

    file_hash = hashlib.sha256(content).hexdigest()
    confirmed = db.scalar(
        select(ImportBatch).where(
            ImportBatch.account_id == account_id,
            ImportBatch.file_hash == file_hash,
            ImportBatch.status == "confirmed",
        )
    )
    if confirmed is not None:
        raise ImportError("This file has already been imported", 409)

    records = _read_records(filename, content)
    batch = ImportBatch(
        user_id=user.id,
        account_id=account_id,
        file_hash=file_hash,
        status="previewed",
        expires_at=datetime.now(timezone.utc) + timedelta(days=1),
    )
    db.add(batch)
    db.flush()

    parsed_rows: list[tuple[int, dict[str, object] | None, str | None, str | None]] = []
    hashes: set[str] = set()
    for number, raw in enumerate(records, start=1):
        try:
            parsed = _validate_row(raw, account_id)
            dedup_hash = str(parsed.pop("dedup_hash"))
            status_value = "valid" if dedup_hash not in hashes else "duplicate"
            hashes.add(dedup_hash)
            parsed_rows.append((number, parsed, dedup_hash, status_value))
        except (ValueError, InvalidOperation, KeyError) as exc:
            parsed_rows.append((number, None, None, str(exc)[:500]))

    category_ids = {
        int(parsed["category_id"])
        for _, parsed, _, _ in parsed_rows
        if parsed is not None and parsed.get("category_id") is not None
    }
    if category_ids:
        valid_categories = {
            category_id: kind
            for category_id, kind in db.execute(
                select(TransactionCategory.id, TransactionCategory.kind).where(
                    TransactionCategory.id.in_(category_ids),
                    or_(
                        TransactionCategory.user_id == user.id,
                        TransactionCategory.user_id.is_(None),
                    ),
                    TransactionCategory.is_active.is_(True),
                )
            ).all()
        }
        valid_subcategories = {
            (category_id, subcategory_id)
            for category_id, subcategory_id in db.execute(
                select(TransactionSubcategory.category_id, TransactionSubcategory.id)
                .join(
                    TransactionCategory,
                    TransactionCategory.id == TransactionSubcategory.category_id,
                )
                .where(
                    TransactionSubcategory.category_id.in_(category_ids),
                    TransactionSubcategory.is_active.is_(True),
                    or_(
                        TransactionCategory.user_id == user.id,
                        TransactionCategory.user_id.is_(None),
                    ),
                    TransactionCategory.is_active.is_(True),
                )
            ).all()
        }
        for index, (number, parsed, dedup_hash, outcome) in enumerate(parsed_rows):
            if parsed is None or parsed.get("category_id") is None:
                continue
            category_id = int(parsed["category_id"])
            subcategory_id = int(parsed["subcategory_id"])
            if (
                valid_categories.get(category_id) != parsed["kind"]
                or (category_id, subcategory_id) not in valid_subcategories
            ):
                parsed_rows[index] = (number, None, None, "Invalid category selection")

    dedup_hashes = [row[2] for row in parsed_rows if row[2]]
    known_hashes = (
        set(
            db.scalars(
                select(Transaction.dedup_hash).where(
                    Transaction.user_id == user.id,
                    Transaction.account_id == account_id,
                    Transaction.dedup_hash.in_(dedup_hashes),
                )
            ).all()
        )
        if dedup_hashes
        else set()
    )
    rows: list[ImportRow] = []
    for number, parsed, dedup_hash, outcome in parsed_rows:
        if parsed is None:
            row_status = "invalid"
            error_message = outcome
        elif dedup_hash in known_hashes or outcome == "duplicate":
            row_status = "duplicate"
            error_message = None
        else:
            row_status = "valid"
            error_message = None
        rows.append(
            ImportRow(
                batch_id=batch.id,
                row_number=number,
                raw_data=records[number - 1],
                parsed_data=parsed,
                suggested_category_id=parsed.get("category_id") if parsed else None,
                dedup_hash=dedup_hash,
                status=row_status,
                error_message=error_message,
            )
        )
    db.add_all(rows)
    batch.valid_rows = sum(row.status == "valid" for row in rows)
    batch.duplicate_rows = sum(row.status == "duplicate" for row in rows)
    batch.invalid_rows = sum(row.status == "invalid" for row in rows)
    db.commit()
    return ImportPreview(
        id=batch.id,
        status=batch.status,
        valid_rows=batch.valid_rows,
        duplicate_rows=batch.duplicate_rows,
        invalid_rows=batch.invalid_rows,
        rows=[
            {
                "id": row.id,
                "row_number": row.row_number,
                "status": row.status,
                "parsed_data": row.parsed_data,
                "error_message": row.error_message,
            }
            for row in rows
        ],
    )


def confirm_import(
    db: Session,
    user: User,
    batch_id: UUID,
    category_choices: list[ImportCategoryChoice],
) -> tuple[str, int]:
    batch = db.scalar(
        select(ImportBatch)
        .where(ImportBatch.id == batch_id, ImportBatch.user_id == user.id)
        .with_for_update()
    )
    if batch is None:
        raise ImportError("Import batch not found", 404)
    if batch.status == "confirmed":
        return batch.status, 0
    now = datetime.now(timezone.utc)
    if batch.status != "previewed" or batch.expires_at <= now:
        raise ImportError("Import batch is not available for confirmation", 409)
    account = db.scalar(
        select(Account)
        .where(Account.id == batch.account_id, Account.user_id == user.id)
        .with_for_update()
    )
    if account is None:
        raise ImportError("Account not found", 404)
    rows = list(
        db.scalars(
            select(ImportRow)
            .where(ImportRow.batch_id == batch.id, ImportRow.status == "valid")
            .order_by(ImportRow.row_number)
            .with_for_update()
        ).all()
    )
    choices = {choice.row_id: choice for choice in category_choices}
    if len(choices) != len(category_choices):
        raise ImportError("Category choices contain duplicate row IDs")
    if not choices.keys() <= {row.id for row in rows}:
        raise ImportError("Category choice references a row that cannot be imported")

    transactions: list[Transaction] = []
    for row in rows:
        parsed = row.parsed_data
        if parsed is None:
            continue
        choice = choices.get(row.id)
        category_id = choice.category_id if choice else parsed.get("category_id")
        subcategory_id = choice.subcategory_id if choice else parsed.get("subcategory_id")
        row.chosen_category_id = category_id
        if (category_id is None) != (subcategory_id is None):
            raise ImportError(f"Row {row.row_number}: category and subcategory must be selected together")
        if category_id is not None:
            category = db.scalar(
                select(TransactionCategory).where(
                    TransactionCategory.id == category_id,
                    TransactionCategory.kind == parsed["kind"],
                    or_(
                        TransactionCategory.user_id == user.id,
                        TransactionCategory.user_id.is_(None),
                    ),
                    TransactionCategory.is_active.is_(True),
                )
            )
            subcategory = db.scalar(
                select(TransactionSubcategory).where(
                    TransactionSubcategory.id == subcategory_id,
                    TransactionSubcategory.category_id == category_id,
                    TransactionSubcategory.is_active.is_(True),
                )
            )
            if category is None or subcategory is None:
                raise ImportError(f"Row {row.row_number}: invalid category selection")
        transactions.append(
            Transaction(
                user_id=user.id,
                account_id=batch.account_id,
                kind=str(parsed["kind"]),
                category_id=category_id,
                subcategory_id=subcategory_id,
                amount=Decimal(str(parsed["amount"])),
                transaction_date=date.fromisoformat(str(parsed["transaction_date"])),
                description=parsed.get("description"),
                merchant=parsed.get("merchant"),
                source="import",
                dedup_hash=row.dedup_hash,
            )
        )

    delta = sum(
        (tx.amount if tx.kind == "income" else -tx.amount for tx in transactions),
        Decimal("0"),
    )
    if transactions:
        next_balance = Account.current_balance + delta
        balance_condition = or_(
            (Account.allow_negative.is_(False) & (next_balance >= 0)),
            (
                Account.allow_negative.is_(True)
                & or_(Account.credit_limit.is_(None), next_balance >= -Account.credit_limit)
            ),
        )
        updated = db.scalar(
            update(Account)
            .where(
                Account.id == account.id,
                Account.user_id == user.id,
                balance_condition,
            )
            .values(current_balance=Account.current_balance + delta)
            .returning(Account.id)
        )
        if updated is None:
            raise ImportError("Imported transactions exceed the account's balance or credit limit", 409)
        db.add_all(transactions)
    batch.status = "confirmed"
    batch.confirmed_at = now
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ImportError("Duplicate transaction or conflicting import batch", 409) from exc
    return batch.status, len(transactions)


def _read_records(filename: str, content: bytes) -> list[dict[str, str]]:
    suffix = PurePath(filename).suffix.lower()
    if suffix == ".csv":
        try:
            text_content = content.decode("utf-8-sig")
            reader = csv.DictReader(io.StringIO(text_content))
            if reader.fieldnames is None:
                raise ImportError("CSV must include a header row")
            records = [
                {str(key or "").strip().lower(): str(value or "").strip() for key, value in row.items()}
                for row in reader
            ]
        except UnicodeDecodeError as exc:
            raise ImportError("CSV must use UTF-8 encoding") from exc
    elif suffix == ".xlsx":
        try:
            frame = pd.read_excel(io.BytesIO(content), dtype=str, engine="openpyxl").fillna("")
        except (ValueError, OSError, BadZipFile, InvalidFileException) as exc:
            raise ImportError("Could not read the XLSX file") from exc
        frame.columns = [str(column).strip().lower() for column in frame.columns]
        records = [
            {str(key): str(value).strip() for key, value in row.items()}
            for row in frame.to_dict(orient="records")
        ]
    else:
        raise ImportError("Only CSV and XLSX files are supported")
    if not records:
        raise ImportError("File contains no transaction rows")
    if not {"transaction_date", "kind", "amount"} <= records[0].keys():
        raise ImportError("File must include transaction_date, kind, and amount columns")
    if len(records) > MAX_IMPORT_ROWS:
        raise ImportError(f"File contains more than {MAX_IMPORT_ROWS} rows")
    return records


def _validate_row(raw: dict[str, str], account_id: UUID) -> dict[str, object]:
    missing = {"transaction_date", "kind", "amount"} - raw.keys()
    if missing:
        raise ValueError(f"Missing required columns: {', '.join(sorted(missing))}")
    kind = raw["kind"].strip().lower()
    if kind not in {"income", "expense"}:
        raise ValueError("kind must be income or expense")
    parsed_date = _parse_date(raw["transaction_date"])
    amount = Decimal(raw["amount"].strip())
    if (
        amount <= 0
        or amount >= Decimal("10000000000000000")
        or amount.as_tuple().exponent < -2
    ):
        raise ValueError("amount must be positive and fit numeric(18,2)")
    description = raw.get("description", "").strip() or None
    merchant = raw.get("merchant", "").strip() or None
    category_id = _optional_positive_int(raw.get("category_id"), "category_id")
    subcategory_id = _optional_positive_int(raw.get("subcategory_id"), "subcategory_id")
    if (category_id is None) != (subcategory_id is None):
        raise ValueError("category_id and subcategory_id must be provided together")
    canonical = json.dumps(
        {
            "account_id": str(account_id),
            "date": parsed_date.isoformat(),
            "kind": kind,
            "amount": format(amount, ".2f"),
            "description": description,
            "merchant": merchant,
        },
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return {
        "transaction_date": parsed_date.isoformat(),
        "kind": kind,
        "amount": format(amount, ".2f"),
        "description": description,
        "merchant": merchant,
        "category_id": category_id,
        "subcategory_id": subcategory_id,
        "dedup_hash": hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
    }


def _optional_positive_int(value: str | None, field_name: str) -> int | None:
    if value is None or value.strip() == "":
        return None
    parsed = int(value)
    if parsed <= 0:
        raise ValueError(f"{field_name} must be positive")
    return parsed


def _parse_date(value: str) -> date:
    cleaned = value.strip()
    try:
        return date.fromisoformat(cleaned)
    except ValueError:
        return datetime.fromisoformat(cleaned).date()