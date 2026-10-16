from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, Date, ForeignKeyConstraint, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Currency(Base):
    __tablename__ = "currencies"
    __table_args__ = (
        CheckConstraint("decimal_places BETWEEN 0 AND 4", name="ck_currencies_decimal_places"),
    )

    code: Mapped[str] = mapped_column(String(3), primary_key=True)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    symbol: Mapped[str] = mapped_column(String(8), nullable=False)
    decimal_places: Mapped[int] = mapped_column(nullable=False, server_default="2")


class ExchangeRate(Base):
    __tablename__ = "exchange_rates"
    __table_args__ = (
        ForeignKeyConstraint(
            ["base_currency"], ["currencies.code"], ondelete="RESTRICT",
            name="fk_exchange_rates_base_currency",
        ),
        ForeignKeyConstraint(
            ["target_currency"], ["currencies.code"], ondelete="RESTRICT",
            name="fk_exchange_rates_target_currency",
        ),
        CheckConstraint("rate > 0", name="ck_exchange_rates_positive_rate"),
    )

    base_currency: Mapped[str] = mapped_column(String(3), primary_key=True)
    target_currency: Mapped[str] = mapped_column(String(3), primary_key=True)
    rate_date: Mapped[date] = mapped_column(Date, primary_key=True)
    rate: Mapped[Decimal] = mapped_column(Numeric(18, 8), nullable=False)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)