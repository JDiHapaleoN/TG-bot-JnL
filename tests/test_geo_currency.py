"""Unit tests for offline geolocation, timezone, and ISO 4217 currency formatting."""

from decimal import Decimal
import unittest

from bot.services.currencies import format_money, is_valid_currency
from bot.services.geo import is_valid_timezone, resolve_location_offline


class TestGeoAndCurrency(unittest.TestCase):
    def test_format_money_spec_examples(self):
        self.assertEqual(format_money(Decimal("1245.50"), "EUR"), "€1,245.50")
        self.assertEqual(
            format_money(Decimal("2000.00"), "EUR", tx_type="income"), "+ €2,000.00"
        )
        self.assertEqual(
            format_money(Decimal("754.50"), "EUR", tx_type="expense"), "− €754.50"
        )
        self.assertEqual(
            format_money(Decimal("5.00"), "EUR", tx_type="expense"), "− €5.00"
        )
        self.assertEqual(
            format_money(Decimal("50000"), "UZS", tx_type="expense"), "− 50,000.00 UZS"
        )

    def test_valid_iso_currencies(self):
        for code in ["EUR", "USD", "UZS", "RUB", "GBP", "CHF", "TRY", "CNY", "JPY"]:
            self.assertTrue(is_valid_currency(code))
        self.assertFalse(is_valid_currency("INVALID"))
        self.assertFalse(is_valid_currency("123"))

    def test_offline_location_resolution(self):
        # Berlin, Germany
        berlin_prof, berlin_tz = resolve_location_offline(52.5200, 13.4050)
        self.assertEqual(berlin_prof.code, "DE")
        self.assertEqual(berlin_prof.currency, "EUR")
        self.assertIn("Europe/", berlin_tz)

        # Tashkent, Uzbekistan
        tashkent_prof, tashkent_tz = resolve_location_offline(41.2995, 69.2401)
        self.assertEqual(tashkent_prof.code, "UZ")
        self.assertEqual(tashkent_prof.currency, "UZS")
        self.assertEqual(tashkent_tz, "Asia/Tashkent")

        # Moscow, Russia
        moscow_prof, moscow_tz = resolve_location_offline(55.7558, 37.6173)
        self.assertEqual(moscow_prof.code, "RU")
        self.assertEqual(moscow_prof.currency, "RUB")
        self.assertEqual(moscow_tz, "Europe/Moscow")

    def test_timezone_validation(self):
        self.assertTrue(is_valid_timezone("Europe/Berlin"))
        self.assertTrue(is_valid_timezone("Asia/Tashkent"))
        self.assertFalse(is_valid_timezone("Invalid/Timezone_Name"))


if __name__ == "__main__":
    unittest.main()

