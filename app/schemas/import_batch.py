from datetime import date, datetime
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ImportCategoryChoice(BaseModel):
    row_id: UUID
    category_id: int = Field(gt=0)
    subcategory_id: int = Field(gt=0)


class ImportConfirmRequest(BaseModel):
    category_choices: list[ImportCategoryChoice] = Field(default_factory=list, max_length=10000)


class ImportRowRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    batch_id: UUID
    row_number: int
    raw_data: dict[str, object]
    parsed_data: dict[str, object] | None
    tx_date: date | None
    description: str | None
    merchant: str | None
    amount: Decimal | None
    kind: str | None
    suggested_category_id: int | None
    chosen_category_id: int | None
    dedup_hash: str | None
    status: str
    error_message: str | None
    transaction_id: UUID | None
    created_at: datetime


class ImportBatchRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    account_id: UUID
    file_name: str
    file_hash: str
    status: str
    total_rows: int
    valid_rows: int
    duplicate_rows: int
    invalid_rows: int
    imported_rows: int
    error_message: str | None
    created_at: datetime
    expires_at: datetime
    confirmed_at: datetime | None


class ImportPreviewResponse(BaseModel):
    id: UUID
    account_id: UUID
    file_name: str
    file_hash: str
    status: str
    total_rows: int
    valid_rows: int
    duplicate_rows: int
    invalid_rows: int
    expires_at: datetime
    rows: list[ImportRowRead]


class ImportConfirmation(BaseModel):
    id: UUID
    status: str
    imported_rows: int


class ParsedImportRow(BaseModel):
    kind: str
    amount: Annotated[Decimal, Field(gt=0, max_digits=18, decimal_places=2)]

    @model_validator(mode="after")
    def validate_kind(self) -> "ParsedImportRow":
        if self.kind not in {"income", "expense"}:
            raise ValueError("kind must be income or expense")
        return self
