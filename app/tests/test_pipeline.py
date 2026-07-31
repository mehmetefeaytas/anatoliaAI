"""Dalga 1 testleri: preprocessing + reconcile + sınıflandırma (offline)."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.extraction.ner.classifier import RuleHintClassifier
from src.extraction.reconcile import build_campaign, reconcile
from src.preprocessing import clean


class TestPreprocessing(unittest.TestCase):
    def test_strip_html(self):
        self.assertEqual(clean.normalize_text("<p>%2,05 <b>kâr</b></p>"), "%2,05 kâr")

    def test_slug(self):
        self.assertEqual(clean.slugify_tr("Kâr Payı Oranı"), "kar-payi-orani")

    def test_sentence_split_keeps_decimal(self):
        s = clean.split_sentences("Oran %2,05. İkinci cümle burada.")
        self.assertEqual(len(s), 2)

    def test_abbrev_no_oversplit(self):
        s = clean.split_sentences("vb. ürünler mevcuttur. Sonraki cümle.")
        self.assertEqual(len(s), 2)


class TestReconcileOffline(unittest.TestCase):
    def test_rule_only_offline(self):
        # LLM yok → yalnız kurallar; yine de temel alanlar çıkar
        fields = {f.field_name: f for f in reconcile(
            "Konut finansmanı kâr payı oranı %1,89, 120 ay vade.")}
        self.assertEqual(fields["kar_payi_orani"].canonical_value, 1.89)
        self.assertEqual(fields["vade_ay"].canonical_value, 120)

    def test_build_campaign(self):
        c = build_campaign("%2,05 kâr payı, 36 ay vade.", bank_slug="kuveyt-turk")
        self.assertEqual(c.bank_slug, "kuveyt-turk")
        self.assertIsNotNone(c.get("kar_payi_orani"))


class TestClassifier(unittest.TestCase):
    def setUp(self):
        self.clf = RuleHintClassifier()

    def test_konut(self):
        label, conf = self.clf.classify("Konut finansmanında kâr payı %1,89")
        self.assertEqual(label, "Konut Finansmanı")
        self.assertGreater(conf, 0.5)

    def test_tasit(self):
        label, _ = self.clf.classify("Taşıt finansmanı kampanyası, araç kredisi")
        self.assertEqual(label, "Taşıt Finansmanı")

    def test_no_hint_returns_none(self):
        label, conf = self.clf.classify("Merhaba dünya")
        self.assertIsNone(label)
        self.assertEqual(conf, 0.0)


if __name__ == "__main__":
    unittest.main()
