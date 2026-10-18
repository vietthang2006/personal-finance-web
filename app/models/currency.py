import uuid
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID as UUIDType

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKeyConstraint,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Currency(Base):
    __tablename__ = "currencies"
    __table_args__ = (
        CheckConstraint(
            "decimal_places BETWEEN 0 AND 4",
            name="ck_currencies_decimal_places",
        ),
    )

    code: Mapped[str] = mapped_column(String(3), primary_key=True)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    symbol: Mapped[str] = mapped_column(String(8), nullable=False)
    decimal_places: Mapped[int] = mapped_column(
        nullable=False,
        server_default="2",
    )


class ExchangeRate(Base):
    __tablename__ = "exchange_rates"
    __table_args__ = (
        ForeignKeyConstraint(
            ["base_currency"],
            ["currencies.code"],
            ondelete="RESTRICT",
            name="fk_exchange_rates_base_currency",
        ),
        ForeignKeyConstraint(
            ["target_currency"],
            ["currencies.code"],
            ondelete="RESTRICT",
            name="fk_exchange_rates_target_currency",
        ),
        CheckConstraint(
            "base_currency <> target_currency",
            name="ck_exchange_rates_different_currencies",
        ),
        CheckConstraint(
            "rate > 0",
            name="ck_exchange_rates_positive_rate",
        ),
        CheckConstraint(
            "rate_type IN ('cash_buy', 'transfer_buy', 'sell', 'unknown')",
            name="ck_exchange_rates_rate_type",
        ),
        UniqueConstraint(
            "base_currency",
            "target_currency",
            "source",
            "rate_type",
            "rate_date",
            "fetched_at",
            name="uq_exchange_rates_quote_snapshot",
        ),
    )

    id: Mapped[UUIDType] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    base_currency: Mapped[str] = mapped_column(String(3), nullable=False)
    target_currency: Mapped[str] = mapped_column(String(3), nullable=False)
    rate_date: Mapped[date] = mapped_column(Date, nullable=False)
    rate: Mapped[Decimal] = mapped_column(Numeric(18, 8), nullable=False)
    source: Mapped[str] = mapped_column(String(30), nullable=False)
    rate_type: Mapped[str] = mapped_column(String(20), nullable=False)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(),
        nullable=False,
        server_default=func.now(),
    )