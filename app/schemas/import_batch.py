from decimal import Decimal
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


class ImportCategoryChoice(BaseModel):
    row_id: UUID
    category_id: int = Field(gt=0)
    subcategory_id: int = Field(gt=0)


class ImportConfirmRequest(BaseModel):
    category_choices: list[ImportCategoryChoice] = Field(default_factory=list, max_length=10000)


class ImportPreviewRow(BaseModel):
    id: UUID
    row_number: int
    status: str
    parsed_data: dict[str, object] | None
    error_message: str | None


class ImportPreview(BaseModel):
    id: UUID
    status: str
    valid_rows: int
    duplicate_rows: int
    invalid_rows: int
    rows: list[ImportPreviewRow]


class ImportConfirmation(BaseModel):
    id: UUID
    status: str
    created_rows: int


class ParsedImportRow(BaseModel):
    kind: str
    amount: Annotated[Decimal, Field(gt=0, max_digits=18, decimal_places=2)]

    @model_validator(mode="after")
    def validate_kind(self) -> "ParsedImportRow":
        if self.kind not in {"income", "expense"}:
            raise ValueError("kind must be income or expense")
        return self
