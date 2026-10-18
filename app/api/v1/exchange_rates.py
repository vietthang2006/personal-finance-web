from typing import Annotated

import httpx
from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select
from xml.etree.ElementTree import ParseError

from app.api.deps import CurrentUser, DbSession
from app.models.currency import ExchangeRate
from app.schemas.exchange_rate import ExchangeRateRead, ExchangeRateSyncResult, RateType
from app.services.exchange_rate_service import VCB_SOURCE, sync_vcb_exchange_rates


router = APIRouter(prefix="/exchange-rates", tags=["exchange rates"])


@router.get("/latest", response_model=ExchangeRateRead)
def get_latest_exchange_rate(
    user: CurrentUser,
    db: DbSession,
    base_currency: Annotated[str, Query(min_length=3, max_length=3, pattern=r"^[A-Za-z]{3}$")],
    target_currency: Annotated[str, Query(min_length=3, max_length=3, pattern=r"^[A-Za-z]{3}$")],
    source: Annotated[str, Query(min_length=1, max_length=30)] = VCB_SOURCE,
    rate_type: RateType = "transfer_buy",
) -> ExchangeRate:
    rate = db.scalar(
        select(ExchangeRate)
        .where(
            ExchangeRate.base_currency == base_currency.upper(),
            ExchangeRate.target_currency == target_currency.upper(),
            ExchangeRate.source == source.upper(),
            ExchangeRate.rate_type == rate_type,
        )
        .order_by(ExchangeRate.fetched_at.desc())
        .limit(1)
    )
    if rate is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exchange rate not found")
    return rate


@router.post("/sync", response_model=ExchangeRateSyncResult)
def sync_exchange_rates(user: CurrentUser) -> ExchangeRateSyncResult:
    try:
        inserted = sync_vcb_exchange_rates()
    except (httpx.HTTPError, ParseError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Could not retrieve valid exchange rates from VCB",
        ) from exc

    message = (
        "Exchange rates updated"
        if inserted
        else "No new rate snapshots; rates may be unchanged or recently synchronized"
    )
    return ExchangeRateSyncResult(source=VCB_SOURCE, inserted=inserted, message=message)