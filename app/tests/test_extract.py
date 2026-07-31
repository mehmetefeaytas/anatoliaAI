"""Kural çıkarımı testleri (stdlib unittest).

Çalıştır:  python -m unittest tests.test_extract  (app/ kökünden)
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.extraction.rules.extract import extract_all


def fields(text):
    return {f.field_name: f for f in extract_all(text)}


class TestRuleExtraction(unittest.TestCase):
    def test_realistic_konut(self):
        text = ("Konut finansmanında kâr payı oranı %1,89, 120 aya kadar vade. "
                "Tahsis ücreti 500 TL. Kampanya 31.12.2026 tarihine kadar geçerlidir.")
        f = fields(text)
        self.assertEqual(f["kar_payi_orani"].canonical_value, 1.89)
        self.assertEqual(f["vade_ay"].canonical_value, 120)
        self.assertEqual(f["finansman_tutari"] if "finansman_tutari" in f else None, None)
        self.assertEqual(f["masraf_durumu"].canonical_value, {"has_fee": True, "amount": 500.0})
        self.assertEqual(f["kampanya_suresi"].canonical_value, "2026-12-31")

    def test_masrafsiz_negation(self):
        f = fields("İhtiyaç finansmanında ilk 6 ay masrafsız, 36 ay vade.")
        self.assertEqual(f["masraf_durumu"].canonical_value, {"has_fee": False, "amount": 0.0})
        self.assertEqual(f["vade_ay"].canonical_value, 36)

    def test_rate_range(self):
        f = fields("Taşıt finansmanı kâr payı oranı %1,99 - %2,49 arasındadır.")
        self.assertEqual(f["kar_payi_orani"].canonical_value, {"min": 1.99, "max": 2.49})

    def test_source_span_present(self):
        f = fields("kâr payı oranı %2,05")
        self.assertIn("kâr", f["kar_payi_orani"].source_span.lower())
        self.assertGreater(f["kar_payi_orani"].confidence, 0.9)

    def test_no_hallucination(self):
        # oran geçmeyen metinde kar_payi_orani üretilmemeli
        f = fields("36 ay vade ile taşıt finansmanı fırsatı.")
        self.assertNotIn("kar_payi_orani", f)


if __name__ == "__main__":
    unittest.main()
