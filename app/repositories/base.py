from typing import Generic, TypeVar
from sqlalchemy.orm import Session

from app.core.database import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """Base repository providing common database operations."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def add(self, entity: ModelType) -> ModelType:
        self.db.add(entity)
        return entity

    def flush(self) -> None:
        self.db.flush()

    def refresh(self, entity: ModelType) -> ModelType:
        self.db.refresh(entity)
        return entity

    def commit(self) -> None:
        self.db.commit()

    def rollback(self) -> None:
        self.db.rollback()

