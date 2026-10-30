from decimal import Decimal
from sqlalchemy import case, select
from sqlalchemy.orm import Session

from app.core.errors import round_currency
from app.models.currency import Currency, ExchangeRate
from app.repositories.base import BaseRepository


class CurrencyRepository(BaseRepository[Currency]):
    def __init__(self, db: Session) -> None:
        super().__init__(db)

    def get_by_code(self, code: str) -> Currency | None:
        return self.db.get(Currency, code.upper())

    def exists(self, code: str) -> bool:
        stmt = select(select(Currency).where(Currency.code == code.upper()).exists())
        return bool(self.db.scalar(stmt))

    def list_all(self) -> list[Currency]:
        return list(self.db.scalars(select(Currency).order_by(Currency.code.asc())).all())

    def get_exchange_rate(
        self, base: str, target: str, preferred_type: str = "transfer_buy"
    ) -> Decimal | None:
        base = base.upper()
        target = target.upper()
        if base == target:
            return Decimal("1.0")

        # 1. Try direct quote with preferred_type
        stmt = (
            select(ExchangeRate.rate)
            .where(
                ExchangeRate.base_currency == base,
                ExchangeRate.target_currency == target,
                ExchangeRate.rate_type == preferred_type,
            )
            .order_by(ExchangeRate.rate_date.desc(), ExchangeRate.created_at.desc())
            .limit(1)
        )
        rate = self.db.scalar(stmt)
        if rate is not None:
            return Decimal(str(rate))

        # 2. Try direct quote with fallback to 'sell' or any
        stmt_fallback = (
            select(ExchangeRate.rate)
            .where(
                ExchangeRate.base_currency == base,
                ExchangeRate.target_currency == target,
            )
            .order_by(
                case((ExchangeRate.rate_type == "sell", 1), else_=2),
                ExchangeRate.rate_date.desc(),
                ExchangeRate.created_at.desc(),
            )
            .limit(1)
        )
        rate = self.db.scalar(stmt_fallback)
        if rate is not None:
            return Decimal(str(rate))

        return None

    def convert_currency(
        self, amount: Decimal, from_curr: str, to_curr: str, preferred_type: str = "transfer_buy"
    ) -> Decimal:
        from_curr = from_curr.upper()
        to_curr = to_curr.upper()
        target_currency = self.get_by_code(to_curr)
        decimal_places = target_currency.decimal_places if target_currency else 2

        if from_curr == to_curr:
            return round_currency(amount, decimal_places)

        # 1. Direct rate
        rate = self.get_exchange_rate(from_curr, to_curr, preferred_type)
        if rate is not None:
            return round_currency(amount * rate, decimal_places)

        # 2. Inverse direct rate
        inv_rate = self.get_exchange_rate(to_curr, from_curr, preferred_type)
        if inv_rate is not None and inv_rate > 0:
            return round_currency(amount / inv_rate, decimal_places)

        # 3. Cross-rate via VND
        rate_from_vnd = self.get_exchange_rate(from_curr, "VND", preferred_type)
        rate_to_vnd = self.get_exchange_rate(to_curr, "VND", preferred_type)
        if rate_from_vnd is not None and rate_to_vnd is not None and rate_to_vnd > 0:
            vnd_amount = amount * rate_from_vnd
            converted = vnd_amount / rate_to_vnd
            return round_currency(converted, decimal_places)

        # Fallback if no rate available
        return round_currency(amount, decimal_places)
