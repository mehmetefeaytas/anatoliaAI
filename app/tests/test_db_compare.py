"""Dalga 2 testleri: DB (SQLite) + karşılaştırma + çelişki tespiti."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.db.repository import Repository  # noqa: E402
from src.extraction.reconcile import build_campaign  # noqa: E402
from src.comparison.compare import rank, best  # noqa: E402
from src.comparison.contradiction import detect  # noqa: E402
from src.schemas import Campaign, ExtractedField, Extractor  # noqa: E402


class TestRepository(unittest.TestCase):
    def setUp(self):
        self.repo = Repository(":memory:")

    def tearDown(self):
        self.repo.close()

    def test_insert_and_query(self):
        c1 = build_campaign("Konut finansmanı kâr payı %1,89, 120 ay vade.",
                            bank_slug="kuveyt-turk")
        c2 = build_campaign("Konut finansmanı kâr payı %2,49, 96 ay vade.",
                            bank_slug="albaraka")
        self.repo.insert_campaign(c1)
        self.repo.insert_campaign(c2)
        rows = self.repo.query_fields("kar_payi_orani")
        self.assertEqual(len(rows), 2)
        banks = {r["bank"] for r in rows}
        self.assertEqual(banks, {"kuveyt-turk", "albaraka"})


class TestComparison(unittest.TestCase):
    def test_lowest_rate_wins(self):
        rows = [
            {"bank": "a", "bank_name": "A", "canonical_value": 2.49, "source_span": ""},
            {"bank": "b", "bank_name": "B", "canonical_value": 1.89, "source_span": ""},
        ]
        b = best(rows, "kar_payi_orani")
        self.assertEqual(b.bank, "b")  # düşük kâr payı = en iyi

    def test_longest_term_wins(self):
        rows = [
            {"bank": "a", "canonical_value": 120, "source_span": ""},
            {"bank": "b", "canonical_value": 96, "source_span": ""},
        ]
        b = best(rows, "vade_ay")
        self.assertEqual(b.bank, "a")  # uzun vade = en iyi

    def test_range_marked_incomparable(self):
        rows = [
            {"bank": "a", "canonical_value": {"min": 1.99, "max": 2.49}, "source_span": ""},
            {"bank": "b", "canonical_value": 1.89, "source_span": ""},
        ]
        ranked = rank(rows, "kar_payi_orani")
        a_row = next(r for r in ranked if r.bank == "a")
        self.assertFalse(a_row.comparable)
        self.assertIn("aralık", a_row.note)


class TestContradiction(unittest.TestCase):
    def test_masrafsiz_but_fee(self):
        c = Campaign(bank_slug="x", raw_text="masrafsız ama tahsis ücreti 500 TL", fields=[
            ExtractedField("masraf_durumu", "masrafsız", {"has_fee": False, "amount": 0.0},
                           0.9, "", Extractor.RULE),
            ExtractedField("tahsis_ucreti", "500 TL", {"value": 500.0, "currency": "TRY"},
                           0.9, "", Extractor.RULE),
        ])
        cons = detect(c)
        self.assertTrue(any(k.kind == "masrafsiz_ama_ucret" for k in cons))

    def test_no_contradiction(self):
        c = build_campaign("Konut finansmanı kâr payı %1,89, 120 ay vade.", bank_slug="x")
        self.assertEqual(detect(c), [])


if __name__ == "__main__":
    unittest.main()
