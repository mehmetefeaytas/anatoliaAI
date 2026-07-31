"""Normalizasyon katmanı testleri (stdlib unittest — sıfır bağımlılık).

Çalıştır:  python -m unittest tests.test_normalize  (app/ kökünden)
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.normalization import normalize as N


class TestTrNumber(unittest.TestCase):
    def test_thousands_and_decimal(self):
        self.assertEqual(N.parse_tr_number("1.500,00"), 1500.0)

    def test_decimal_comma(self):
        self.assertEqual(N.parse_tr_number("%2,05"), 2.05)

    def test_decimal_dot(self):
        self.assertEqual(N.parse_tr_number("2.05"), 2.05)

    def test_thousands_dot(self):
        self.assertEqual(N.parse_tr_number("1.500"), 1500.0)

    def test_plain(self):
        self.assertEqual(N.parse_tr_number("500"), 500.0)

    def test_none_on_garbage(self):
        self.assertIsNone(N.parse_tr_number("abc"))


class TestRate(unittest.TestCase):
    def test_simple(self):
        self.assertEqual(N.normalize_rate("%2,05"), 2.05)

    def test_trailing_percent(self):
        self.assertEqual(N.normalize_rate("2,05%"), 2.05)

    def test_range_preserved(self):
        self.assertEqual(N.normalize_rate("%1,99 - %2,49"), {"min": 1.99, "max": 2.49})


class TestMoney(unittest.TestCase):
    def test_tl(self):
        self.assertEqual(N.normalize_money("500 TL"), {"value": 500.0, "currency": "TRY"})

    def test_symbol_thousands(self):
        self.assertEqual(N.normalize_money("1.500,00₺"), {"value": 1500.0, "currency": "TRY"})

    def test_words(self):
        self.assertEqual(N.normalize_money("500 Türk Lirası"),
                         {"value": 500.0, "currency": "TRY"})


class TestTerm(unittest.TestCase):
    def test_months(self):
        self.assertEqual(N.normalize_term_months("12 ay"), 12)

    def test_years(self):
        self.assertEqual(N.normalize_term_months("1 yıl"), 12)

    def test_fractional_year(self):
        self.assertEqual(N.normalize_term_months("1,5 yıl"), 18)


class TestDate(unittest.TestCase):
    def test_dotted(self):
        self.assertEqual(N.normalize_date("31.12.2026"), "2026-12-31")

    def test_slash(self):
        self.assertEqual(N.normalize_date("31/12/2026"), "2026-12-31")

    def test_tr_month(self):
        self.assertEqual(N.normalize_date("31 Aralık 2026"), "2026-12-31")

    def test_iso_passthrough(self):
        self.assertEqual(N.normalize_date("2026-12-31"), "2026-12-31")


class TestFeeNegation(unittest.TestCase):
    def test_free(self):
        self.assertEqual(N.normalize_fee_status("masrafsız konut finansmanı"),
                         {"has_fee": False, "amount": 0.0})

    def test_has_fee_with_amount(self):
        self.assertEqual(N.normalize_fee_status("tahsis ücreti 500 TL alınır"),
                         {"has_fee": True, "amount": 500.0})

    def test_absent_is_none(self):
        # masraf hiç geçmiyorsa bilgi yok → None (uydurma yok)
        self.assertIsNone(N.normalize_fee_status("36 ay vade ile konut finansmanı"))


if __name__ == "__main__":
    unittest.main()
