"""`scripts/build_demo_db.py` + Repository özet yardımcılarının testleri.

İlgili: scripts/build_demo_db.py, src/db/repository.py, CLAUDE.md §11

Avlanan hata sınıfları:
1. Yeniden kurulumda kampanyaların ÇİFTLENMESİ (şemada UNIQUE yok).
2. Belge bulunamadığında boş DB üretip "kuruldu" demek (sessiz yalan).
3. Var olan DB'nin uyarısız ezilmesi.
4. Özet raporun DB'deki gerçek sayılarla uyuşmaması.
"""

import io
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.build_demo_db import build, format_report
from src.db.repository import Repository
from src.schemas import Campaign, ExtractedField, Extractor


def _yaz(kok: Path, rel: str, icerik: str) -> None:
    yol = kok / rel
    yol.parent.mkdir(parents=True, exist_ok=True)
    yol.write_text(icerik, encoding="utf-8")


class _KorpusOrtami(unittest.TestCase):
    """Sentetik 3 belgelik korpus + 2 bankalı config."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.kok = Path(self.tmp.name)
        self.raw = self.kok / "raw"
        _yaz(self.raw, "a-bank/live/1.txt",
             "Konut finansmanı kâr payı oranı %1,89, 120 ay vade.")
        _yaz(self.raw, "a-bank/products/2.txt",
             "Taşıt finansmanı kâr payı %2,05, 36 ay vade.")
        _yaz(self.raw, "b-bank/live/1.txt",
             "Masrafsız ihtiyaç finansmanı. Tahsis ücreti 500 TL.")
        self.cfg = self.kok / "banks.yaml"
        self.cfg.write_text(
            "banks:\n"
            "  - slug: a-bank\n    name: A Bank\n"
            "    website_url: https://a.invalid\n    scrape_mode: manual\n"
            "  - slug: b-bank\n    name: B Bank\n"
            "    website_url: https://b.invalid\n    scrape_mode: manual\n",
            encoding="utf-8")
        self.out = self.kok / "demo.db"
        self.log = io.StringIO()

    def tearDown(self):
        self.tmp.cleanup()

    def _build(self, **kw):
        return build(self.out, config=str(self.cfg), raw_dir=str(self.raw),
                     stream=self.log, quiet=True, **kw)


class TestBuild(_KorpusOrtami):
    def test_db_uretilir_ve_dolar(self):
        rep, code = self._build()
        self.assertEqual(code, 0)
        self.assertTrue(self.out.is_file())
        self.assertEqual(rep["documents_loaded"], 3)
        self.assertEqual(rep["counts"]["campaigns"], 3)
        self.assertEqual(rep["db_bytes"], self.out.stat().st_size)

    def test_rapor_db_ile_uyusur(self):
        """Rapordaki sayı DB'den bağımsız üretilmemeli."""
        rep, _ = self._build()
        con = sqlite3.connect(self.out)
        try:
            n = con.execute("SELECT COUNT(*) FROM campaigns").fetchone()[0]
            f = con.execute("SELECT COUNT(*) FROM extracted_fields").fetchone()[0]
        finally:
            con.close()
        self.assertEqual(rep["counts"]["campaigns"], n)
        self.assertEqual(rep["counts"]["fields"], f)

    def test_celiski_sayilir(self):
        rep, _ = self._build()
        self.assertEqual(rep["contradiction_count"], 1)
        self.assertEqual(rep["contradictions_by_kind"]["masrafsiz_ama_ucret"], 1)

    def test_provenance_db_ye_yazilir(self):
        """`.meta.json` yanındaysa source_url + scraped_at korunmalı."""
        _yaz(self.raw, "a-bank/live/1.txt.meta.json",
             '{"source_url": "https://a.invalid/kampanya/konut", '
             '"scraped_at": "2026-07-30T09:00:00+00:00"}')
        self._build()
        con = sqlite3.connect(self.out)
        try:
            satir = con.execute(
                "SELECT source_url, scraped_at FROM campaigns "
                "WHERE source_url LIKE 'https://%'").fetchone()
        finally:
            con.close()
        self.assertEqual(satir,
                         ("https://a.invalid/kampanya/konut",
                          "2026-07-30T09:00:00+00:00"))

    def test_var_olan_dosya_force_olmadan_reddedilir(self):
        self._build()
        boyut = self.out.stat().st_size
        rep, code = self._build()
        self.assertIsNone(rep)
        self.assertEqual(code, 1)
        self.assertEqual(self.out.stat().st_size, boyut, "dosyaya dokunulmamalı")
        self.assertIn("--force", self.log.getvalue())

    def test_force_ciftlemez(self):
        """Asıl hata: aynı dosyaya ikinci koşu kampanyaları iki katına çıkarır."""
        ilk, _ = self._build()
        ikinci, code = self._build(force=True)
        self.assertEqual(code, 0)
        self.assertEqual(ikinci["counts"]["campaigns"],
                         ilk["counts"]["campaigns"])
        self.assertEqual(ikinci["counts"]["banks"], ilk["counts"]["banks"])

    def test_bos_korpus_kod_2_ve_dosya_birakmaz(self):
        bos = self.kok / "bos"
        bos.mkdir()
        bos_rapor, code = build(self.out, config=str(self.cfg),
                                raw_dir=str(bos), stream=self.log, quiet=True)
        self.assertIsNone(bos_rapor)
        self.assertEqual(code, 2)
        self.assertFalse(self.out.exists(), "boş DB dosyası bırakılmamalı")

    def test_deterministik(self):
        """İki koşu aynı kampanya sırasını ve aynı alan sayısını vermeli."""
        rep1, _ = self._build()
        siralar1 = _kampanya_sirasi(self.out)
        rep2, _ = self._build(force=True)
        self.assertEqual(siralar1, _kampanya_sirasi(self.out))
        self.assertEqual(rep1["field_coverage"], rep2["field_coverage"])

    def test_format_report_turkce_basliklari_icerir(self):
        rep, _ = self._build()
        metin = format_report(rep)
        for beklenen in ("DEMO VERİ TABANI ÖZETİ", "BANKA BAŞINA KAMPANYA",
                         "ALAN KAPSAMI", "KATMAN BAŞINA ALAN"):
            self.assertIn(beklenen, metin)

    def test_alt_dizin_olusturulur(self):
        hedef = self.kok / "yeni" / "alt" / "demo.db"
        _rapor, code = build(hedef, config=str(self.cfg),
                             raw_dir=str(self.raw), stream=self.log, quiet=True)
        self.assertEqual(code, 0)
        self.assertTrue(hedef.is_file())


def _kampanya_sirasi(db: Path) -> list[tuple]:
    con = sqlite3.connect(db)
    try:
        return con.execute(
            "SELECT id, source_url FROM campaigns ORDER BY id").fetchall()
    finally:
        con.close()


class TestRepositoryOzet(unittest.TestCase):
    """`counts` / `field_coverage` / `campaigns_per_bank` doğruluğu."""

    def setUp(self):
        self.repo = Repository(":memory:")
        self.repo.upsert_bank("A Bank", "a-bank")
        self.repo.upsert_bank("Bos Bank", "bos-bank")
        self.repo.insert_campaign(_kampanya("a-bank", ["kar_payi_orani", "vade_ay"]))
        self.repo.insert_campaign(_kampanya("a-bank", ["vade_ay"]))
        self.repo.insert_campaign(_kampanya("a-bank", []))

    def tearDown(self):
        self.repo.close()

    def test_counts(self):
        c = self.repo.counts()
        self.assertEqual(c["banks"], 2)
        self.assertEqual(c["banks_with_campaigns"], 1)
        self.assertEqual(c["campaigns"], 3)
        self.assertEqual(c["fields"], 3)
        self.assertEqual(c["campaigns_with_fields"], 2)

    def test_field_coverage_kampanya_sayar(self):
        self.assertEqual(self.repo.field_coverage(),
                         {"vade_ay": 2, "kar_payi_orani": 1})

    def test_campaigns_per_bank_bos_bankayi_gosterir(self):
        """Belge çıkmayan banka 0 ile görünmeli — sessizce kaybolmamalı."""
        self.assertEqual(self.repo.campaigns_per_bank(),
                         {"a-bank": 3, "bos-bank": 0})


def _kampanya(slug: str, alanlar: list[str]) -> Campaign:
    return Campaign(
        bank_slug=slug, raw_text="metin", source_url=None, campaign_type=None,
        fields=[ExtractedField(field_name=a, raw_value="x", canonical_value=1,
                               confidence=0.9, source_span="x",
                               extractor=Extractor.RULE)
                for a in alanlar])


class TestMigrateKorundu(unittest.TestCase):
    """31 Tem'de eklenen `_migrate` kalıcı DB dosyalarında hâlâ çalışmalı."""

    def test_eski_dosyaya_sutunlar_eklenir(self):
        with tempfile.TemporaryDirectory() as d:
            yol = Path(d) / "eski.db"
            con = sqlite3.connect(yol)
            con.executescript(
                "CREATE TABLE banks (id INTEGER PRIMARY KEY AUTOINCREMENT, "
                "name TEXT, slug TEXT UNIQUE, website_url TEXT, "
                "bddk_active INTEGER);"
                "CREATE TABLE campaigns (id INTEGER PRIMARY KEY AUTOINCREMENT, "
                "bank_id INTEGER, raw_text TEXT, clean_text TEXT, "
                "source_url TEXT, scraped_at TEXT, campaign_type TEXT);"
                "CREATE TABLE extracted_fields (id INTEGER PRIMARY KEY "
                "AUTOINCREMENT, campaign_id INTEGER, field_name TEXT, "
                "raw_value TEXT, canonical_value TEXT, confidence REAL, "
                "source_span TEXT, extractor TEXT);")
            con.commit()
            con.close()

            repo = Repository(str(yol))
            try:
                sutunlar = {r["name"] for r in
                            repo.conn.execute("PRAGMA table_info(extracted_fields)")}
                for beklenen in ("span_start", "span_end", "confidence_source"):
                    self.assertIn(beklenen, sutunlar)
                # migrate sonrası yazma gerçekten çalışmalı
                repo.upsert_bank("A Bank", "a-bank")
                cid = repo.insert_campaign(_kampanya("a-bank", ["vade_ay"]))
                self.assertIsNotNone(repo.field_value(cid, "vade_ay"))
            finally:
                repo.close()


if __name__ == "__main__":
    unittest.main()
