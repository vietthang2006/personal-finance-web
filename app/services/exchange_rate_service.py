from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from xml.etree import ElementTree

import httpx
from sqlalchemy import func, select, text

from app.core.database import SessionLocal
from app.models.currency import Currency, ExchangeRate


VCB_RATE_URL = "https://portal.vietcombank.com.vn/Usercontrols/TVPortal.TyGia/pXML.aspx"
VCB_SOURCE = "VCB"
VCB_MIN_REQUEST_INTERVAL = timedelta(minutes=5)
VCB_RATE_TYPES = {
    "Buy": "cash_buy",
    "Transfer": "transfer_buy",
    "Sell": "sell",
}


def _parse_vcb_rates(content: bytes) -> tuple[datetime, dict[str, dict[str, Decimal]]]:
    root = ElementTree.fromstring(content)
    source_time = datetime.strptime(
        root.findtext("DateTime", ""),
        "%m/%d/%Y %I:%M:%S %p",
    )
    rates: dict[str, dict[str, Decimal]] = {}

    for entry in root.findall("Exrate"):
        currency_code = entry.get("CurrencyCode")
        if not currency_code:
            continue

        for field, rate_type in VCB_RATE_TYPES.items():
            raw_rate = entry.get(field, "").replace(",", "").strip()
            try:
                rate = Decimal(raw_rate)
            except InvalidOperation:
                continue
            if rate > 0:
                rates.setdefault(currency_code, {})[rate_type] = rate

    return source_time, rates


def sync_vcb_exchange_rates() -> int:
    with SessionLocal() as db:
        db.execute(text("SELECT pg_advisory_xact_lock(20261018, 1)"))
        last_fetch = db.scalar(
            select(func.max(ExchangeRate.fetched_at)).where(
                ExchangeRate.source == VCB_SOURCE
            )
        )
        fetched_at = datetime.now(timezone.utc)
        if last_fetch is not None and fetched_at - last_fetch < VCB_MIN_REQUEST_INTERVAL:
            db.rollback()
            return 0

        response = httpx.get(
            VCB_RATE_URL,
            timeout=15,
            headers={"User-Agent": "PersonalFinanceWeb/1.0"},
        )
        response.raise_for_status()
        source_time, provider_rates = _parse_vcb_rates(response.content)
        rate_date = source_time.date()
        supported_codes = set(db.scalars(select(Currency.code)).all())
        inserted = 0

        for currency_code, rate_types in provider_rates.items():
            if currency_code not in supported_codes or currency_code == "VND":
                continue

            for rate_type, rate in rate_types.items():
                latest = db.scalar(
                    select(ExchangeRate)
                    .where(
                        ExchangeRate.base_currency == currency_code,
                        ExchangeRate.target_currency == "VND",
                        ExchangeRate.source == VCB_SOURCE,
                        ExchangeRate.rate_type == rate_type,
                        ExchangeRate.rate_date == rate_date,
                    )
                    .order_by(ExchangeRate.fetched_at.desc())
                    .limit(1)
                )
                if latest is not None and latest.rate == rate:
                    latest.fetched_at = fetched_at
                    continue

                db.add(
                    ExchangeRate(
                        base_currency=currency_code,
                        target_currency="VND",
                        rate_date=rate_date,
                        rate=rate,
                        source=VCB_SOURCE,
                        rate_type=rate_type,
                        fetched_at=fetched_at,
                    )
                )
                inserted += 1

        db.commit()
        return inserted