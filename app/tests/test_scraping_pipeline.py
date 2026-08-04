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
        kt = banks["kuveyt-turk"]
        # 2026-07-30: eski /tr/kampanyalar yolu 404 dönüyordu, /kampanyalar ile
        # düzeltildi (bkz. data/raw/_collection_report.md). Liste tam eşitlikle
        # DEĞİL içerikle doğrulanır — kapsam genişledikçe (2026-08-03'te kategori
        # yolları eklendi) testin kırılmaması için.
        self.assertIn("/kampanyalar", kt.campaign_paths)
        self.assertNotIn("/tr/kampanyalar", kt.campaign_paths)
        self.assertTrue(kt.bddk_active)

    def test_ziraat_kart_kampanyalari_yolu_var(self):
        """2026-08-03: /bireysel/kampanyalar boş; gerçek katalog /kart-kampanyalari.

        Bu yol olmadan Ziraat'ten yalnızca 5 kampanya toplanabiliyordu
        (bkz. docs/rapor/banka-siteleri-veri-kaynagi-haritasi.md §5).
        """
        banks = {b.slug: b for b in load_banks(CONFIG)}
        paths = banks["ziraat-katilim"].campaign_paths
        self.assertIn("/kart-kampanyalari", paths)
        # Sektör kategorileri de giriş noktası (191 kampanya bağlantısı oradan)
        self.assertIn("/kampanyalar/market-ve-gida", paths)

    def test_yeni_tur_alanlari_ayristiriliyor(self):
        """archive_paths / document_paths / document_hosts okunabiliyor mu?"""
        banks = {b.slug: b for b in load_banks(CONFIG)}
        # Arşiv (süresi dolmuş kampanya) yayımlayan iki banka
        self.assertIn("/kampanyalar/kampanya-arsivi",
                      banks["kuveyt-turk"].archive_paths)
        self.assertTrue(banks["turkiye-finans"].archive_paths)
        # PDF ücret tarifeleri
        self.assertTrue(banks["turkiye-emlak-katilim"].document_paths)
        # Emlak'ın PDF'leri AYRI alan adında duruyor
        self.assertIn("asset.emlakkatilim.com.tr",
                      banks["turkiye-emlak-katilim"].document_hosts)
        # Arşiv yayımlamayan bankada liste boş olmalı (tur sessizce atlanır)
        self.assertEqual(banks["dunya-katilim"].archive_paths, [])


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
