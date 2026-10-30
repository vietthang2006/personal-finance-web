from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator, model_validator


CategoryKind = Literal["income", "expense"]
CategoryCode = Annotated[str, StringConstraints(min_length=2, max_length=50, pattern=r"^[a-z0-9_]+$")]


class CategoryCreate(BaseModel):
    code: CategoryCode
    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
    kind: CategoryKind
    icon: Annotated[str | None, StringConstraints(strip_whitespace=True, max_length=50)] = None

    @field_validator("code", mode="before")
    @classmethod
    def normalize_code(cls, value: object) -> object:
        return value.strip().lower() if isinstance(value, str) else value


class CategoryUpdate(BaseModel):
    name: Annotated[str | None, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)] = None
    icon: Annotated[str | None, StringConstraints(strip_whitespace=True, max_length=50)] = None
    is_active: bool | None = None

    @model_validator(mode="after")
    def require_update_field(self) -> "CategoryUpdate":
        if self.name is None and self.is_active is None and self.icon is None:
            raise ValueError("At least one field must be provided")
        return self


class CategoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: UUID | None
    code: str
    name: str
    kind: CategoryKind
    icon: str | None = None
    is_active: bool
    created_at: datetime


class SubcategoryCreate(BaseModel):
    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=80)]


class SubcategoryUpdate(BaseModel):
    name: Annotated[str | None, StringConstraints(strip_whitespace=True, min_length=1, max_length=80)] = None
    is_active: bool | None = None

    @model_validator(mode="after")
    def require_update_field(self) -> "SubcategoryUpdate":
        if self.name is None and self.is_active is None:
            raise ValueError("At least one field must be provided")
        return self


class SubcategoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    category_id: int
    name: str
    is_active: bool
