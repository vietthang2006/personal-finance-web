from datetime import date, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


RateType = Literal["cash_buy", "transfer_buy", "sell", "unknown"]


class ExchangeRateRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    base_currency: str
    target_currency: str
    rate_date: date
    rate: Decimal
    source: str
    rate_type: RateType
    fetched_at: datetime


class ExchangeRateSyncResult(BaseModel):
    source: str
    inserted: int
    message: str