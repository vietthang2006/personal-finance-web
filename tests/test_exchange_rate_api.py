import unittest
from datetime import date, datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import Mock, patch
from uuid import uuid4

import httpx
from fastapi.testclient import TestClient

from app.api.deps import get_current_user
from app.core.database import get_db
from app.main import app


class ExchangeRateApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.db = Mock()
        self.previous_overrides = dict(app.dependency_overrides)
        app.dependency_overrides[get_db] = lambda: self.db
        app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=uuid4())
        self.client = TestClient(app)

    def tearDown(self) -> None:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(self.previous_overrides)

    def test_latest_returns_requested_rate(self) -> None:
        self.db.scalar.return_value = SimpleNamespace(
            id=uuid4(),
            base_currency="EUR",
            target_currency="VND",
            rate_date=date(2026, 10, 18),
            rate=Decimal("28679.93"),
            source="VCB",
            rate_type="transfer_buy",
            fetched_at=datetime(2026, 10, 18, 14, 0, tzinfo=timezone.utc),
        )

        response = self.client.get(
            "/api/v1/exchange-rates/latest",
            params={
                "base_currency": "eur",
                "target_currency": "vnd",
                "source": "vcb",
                "rate_type": "transfer_buy",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["base_currency"], "EUR")
        self.assertEqual(response.json()["rate"], "28679.93")

    def test_latest_returns_404_when_rate_is_missing(self) -> None:
        self.db.scalar.return_value = None

        response = self.client.get(
            "/api/v1/exchange-rates/latest",
            params={"base_currency": "EUR", "target_currency": "VND"},
        )

        self.assertEqual(response.status_code, 404)

    @patch("app.api.v1.exchange_rates.sync_vcb_exchange_rates", return_value=17)
    def test_sync_returns_insert_count(self, sync_rates: Mock) -> None:
        response = self.client.post("/api/v1/exchange-rates/sync")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["source"], "VCB")
        self.assertEqual(response.json()["inserted"], 17)
        sync_rates.assert_called_once_with()

    @patch(
        "app.api.v1.exchange_rates.sync_vcb_exchange_rates",
        side_effect=httpx.ConnectError("offline"),
    )
    def test_sync_returns_502_when_provider_is_unavailable(self, sync_rates: Mock) -> None:
        response = self.client.post("/api/v1/exchange-rates/sync")

        self.assertEqual(response.status_code, 502)
        self.assertEqual(response.json()["detail"], "Could not retrieve valid exchange rates from VCB")
        sync_rates.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()