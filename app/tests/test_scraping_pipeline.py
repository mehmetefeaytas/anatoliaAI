"""Dalga 4 testleri: config loader + collector + uçtan uca pipeline (offline)."""

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.db.repository import Repository
from src.pipeline import build_demo_repo, make_chatbot, run_pipeline
from src.scraping.collector import collect
from src.scraping.config import load_banks

CONFIG = str(ROOT / "config" / "banks.yaml")
RAW = str(ROOT / "data" / "raw")


class TestConfig(unittest.TestCase):
    def test_loads_ten_banks(self):
        banks = load_banks(CONFIG)
        self.assertEqual(len(banks), 10)
        slugs = {b.slug for b in banks}
        self.assertIn("kuveyt-turk", slugs)
        self.assertIn("albaraka", slugs)

    def test_campaign_paths_parsed(self):
        banks = {b.slug: b for b in load_banks(CONFIG)}
        # 2026-07-30: eski /tr/kampanyalar yolu 404 dönüyordu, /kampanyalar ile
        # düzeltildi (bkz. data/raw/_collection_report.md).
        self.assertEqual(banks["kuveyt-turk"].campaign_paths, ["/kampanyalar"])
        self.assertTrue(banks["kuveyt-turk"].bddk_active)


class TestCollector(unittest.TestCase):
    def test_fixture_collection(self):
        banks = {b.slug: b for b in load_banks(CONFIG)}
        docs = collect(banks["albaraka"], raw_dir=RAW, mode="fixture")
        self.assertEqual(len(docs), 1)
        # HTML temizlenmiş olmalı (etiket kalmamalı)
        self.assertNotIn("<html>", docs[0].clean_text)
        self.assertIn("kâr payı", docs[0].clean_text)


class TestPipeline(unittest.TestCase):
    def test_end_to_end(self):
        repo = Repository(":memory:")
        res = run_pipeline(repo, CONFIG, raw_dir=RAW, mode="fixture")
        self.assertEqual(res.campaigns_stored, 3)
        rows = repo.query_fields("kar_payi_orani")
        self.assertEqual(len(rows), 3)
        repo.close()

    def test_demo_repo_and_chatbot(self):
        repo = build_demo_repo(CONFIG, RAW)
        bot = make_chatbot(repo)
        a = bot.ask("Hangi bankada en düşük kâr payı oranı var?")
        self.assertEqual(a.handler, "structured")
        self.assertIn("Kuveyt", a.text)
        repo.close()

    def test_tasit_classified(self):
        repo = build_demo_repo(CONFIG, RAW)
        types = {r["bank"]: r.get("campaign_type") for r in repo.all_campaigns()}
        self.assertEqual(types["turkiye-finans"], "Taşıt Finansmanı")
        repo.close()


if __name__ == "__main__":
    unittest.main()
