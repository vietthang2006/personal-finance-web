from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.currency import Currency
from app.repositories.base import BaseRepository


class CurrencyRepository(BaseRepository[Currency]):
    def __init__(self, db: Session) -> None:
        super().__init__(db)

    def get_by_code(self, code: str) -> Currency | None:
        return self.db.get(Currency, code.upper())

    def exists(self, code: str) -> bool:
        stmt = select(select(Currency).where(Currency.code == code.upper()).exists())
        return bool(self.db.scalar(stmt))

