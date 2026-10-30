from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator


class TagCreate(BaseModel):
    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=50)]
    color: Annotated[str, StringConstraints(pattern=r"^#[0-9A-Fa-f]{6}$")] = "#808080"


class TagUpdate(BaseModel):
    name: Annotated[str | None, StringConstraints(strip_whitespace=True, min_length=1, max_length=50)] = None
    color: Annotated[str | None, StringConstraints(pattern=r"^#[0-9A-Fa-f]{6}$")] = None

    @model_validator(mode="after")
    def validate_non_empty(self) -> "TagUpdate":
        if self.name is None and self.color is None:
            raise ValueError("At least one field must be provided")
        return self


class TagRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: UUID | None
    name: str
    color: str
    created_at: datetime


class TransactionTagAssign(BaseModel):
    tag_ids: list[int] = Field(min_length=1)

