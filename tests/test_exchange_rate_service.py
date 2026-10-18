import unittest
from decimal import Decimal

from app.services.exchange_rate_service import _parse_vcb_rates


class VcbRateParserTests(unittest.TestCase):
    def test_parses_transfer_buy_rate_and_source_date(self) -> None:
        content = (
            b"<ExrateList><DateTime>10/18/2026 2:12:11 PM</DateTime>"
            b'<Exrate CurrencyCode="USD" Buy="25,000.00" '
            b'Transfer="25,700.00" Sell="26,000.00" />'
            b"</ExrateList>"
        )

        source_time, rates = _parse_vcb_rates(content)

        self.assertEqual(source_time.date().isoformat(), "2026-10-18")
        self.assertEqual(rates["USD"]["cash_buy"], Decimal("25000.00"))
        self.assertEqual(rates["USD"]["transfer_buy"], Decimal("25700.00"))
        self.assertEqual(rates["USD"]["sell"], Decimal("26000.00"))

    def test_skips_unavailable_rate_fields(self) -> None:
        content = (
            b"<ExrateList><DateTime>10/18/2026 2:12:11 PM</DateTime>"
            b'<Exrate CurrencyCode="USD" Buy="-" '
            b'Transfer="25,700.00" Sell="" />'
            b"</ExrateList>"
        )

        _, rates = _parse_vcb_rates(content)

        self.assertEqual(rates, {"USD": {"transfer_buy": Decimal("25700.00")}})


if __name__ == "__main__":
    unittest.main()