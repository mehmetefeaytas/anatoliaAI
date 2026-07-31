"""Kaynak-span offset'lerinin veri tabanı turunda hayatta kaldığını doğrular.

## Neden bu dosya var

Projenin en özgün iddiası: *"her sayı bir karakter aralığına bağlı; halüsinasyon
yapamayız çünkü yapamadığımızı ispatlayabiliyoruz."* Bu iddia `ExtractedField`
üzerinde `span_start`/`span_end` ile kuruluydu — ama 31 Temmuz'a kadar
`extracted_fields` tablosunda **bu sütunlar yoktu**. Yani offset'ler çıkarımda
üretiliyor, veri tabanı sınırında sessizce düşüyor, arayüz de onları yeniden
tahmin etmek zorunda kalıyordu.

Kayıp sessizdi: hiçbir şey çökmüyordu, yalnızca vurgulama yapılamıyordu.
Bu testler o sessiz kaybın geri gelmesini engeller.
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.db.repository import Repository
from src.extraction.rules.extract import extract_all
from src.preprocessing.clean import normalize_text
from src.schemas import Campaign, ExtractedField, Extractor

ORNEK = (
    "Kuveyt Türk Konut Finansmanı kampanyası. Kâr payı oranı %1,89'dan "
    "başlayan oranlarla 120 aya varan vade. Tahsis ücreti 750 TL. "
    "Kampanya 31.12.2026 tarihine kadar geçerlidir."
)


class TestSpanKaliciligi(unittest.TestCase):

    def setUp(self) -> None:
        self.repo = Repository(":memory:")

    def tearDown(self) -> None:
        self.repo.close()

    def _yaz(self, metin: str) -> int:
        alanlar = extract_all(metin)
        self.assertTrue(alanlar, "örnek metinden hiç alan çıkmadı — test anlamsız")
        c = Campaign(bank_slug="kuveyt-turk", raw_text=metin,
                     source_url="https://ornek.test/konut", fields=alanlar)
        return self.repo.insert_campaign(c, clean_text=metin)

    def test_offsetler_db_turunda_kaybolmuyor(self) -> None:
        metin = normalize_text(ORNEK)
        cid = self._yaz(metin)
        d = self.repo.campaign_text(cid)
        self.assertIsNotNone(d)
        self.assertTrue(d["fields"])
        for alan in d["fields"]:
            self.assertIsNotNone(alan["span_start"],
                                 f"{alan['field_name']}: span_start kayboldu")
            self.assertIsNotNone(alan["span_end"],
                                 f"{alan['field_name']}: span_end kayboldu")

    def test_saklanan_offset_metinle_dogrulanir(self) -> None:
        """Asıl değişmez: text[span_start:span_end] == raw_value."""
        metin = normalize_text(ORNEK)
        cid = self._yaz(metin)
        d = self.repo.campaign_text(cid)
        for alan in d["fields"]:
            self.assertTrue(
                alan["span_verified"],
                f"{alan['field_name']}: offset metinle uyuşmuyor — "
                f"[{alan['span_start']},{alan['span_end']}) "
                f"metinde {d['text'][alan['span_start']:alan['span_end']]!r}, "
                f"beklenen {alan['raw_value']!r}")

    def test_confidence_source_kaybolmuyor(self) -> None:
        """Kalibrasyon (ECE) güvenin NEREDEN geldiğini bilmeden yapılamaz:
        sabit 0.95 ile kanıt tabanlı skoru aynı kovaya koymak güvenilirlik
        diyagramını bozar."""
        cid = self._yaz(normalize_text(ORNEK))
        d = self.repo.campaign_text(cid)
        for alan in d["fields"]:
            self.assertIsNotNone(alan["confidence_source"],
                                 f"{alan['field_name']}: confidence_source kayboldu")

    def test_bozuk_offset_dogrulanmis_isaretlenmez(self) -> None:
        """Saklanan offset metinle uyuşmuyorsa arayüz yanlış yeri
        vurgulamaktansa hiç vurgulamamalı."""
        metin = normalize_text(ORNEK)
        bozuk = ExtractedField(
            field_name="kar_payi_orani", raw_value="%1,89",
            canonical_value=1.89, confidence=0.9,
            source_span="…", extractor=Extractor.RULE,
            span_start=0, span_end=5)          # kasten yanlış yer
        c = Campaign(bank_slug="test-banka", raw_text=metin,
                     source_url="x", fields=[bozuk])
        cid = self.repo.insert_campaign(c, clean_text=metin)
        alan = self.repo.campaign_text(cid)["fields"][0]
        self.assertFalse(alan["span_verified"],
                         "bozuk offset 'doğrulandı' diye işaretlendi")

    def test_offsetsiz_alan_cokmez(self) -> None:
        """LLM katmanı offset üretemeyebilir; bu bir hata değil, null olmalı."""
        alan = ExtractedField(
            field_name="kampanya_kosullari", raw_value="ilk 3 ay ödemesiz",
            canonical_value="ilk 3 ay ödemesiz", confidence=0.6,
            source_span="…", extractor=Extractor.LLM)
        c = Campaign(bank_slug="test-banka", raw_text=ORNEK,
                     source_url="x", fields=[alan])
        cid = self.repo.insert_campaign(c, clean_text=ORNEK)
        d = self.repo.campaign_text(cid)["fields"][0]
        self.assertIsNone(d["span_start"])
        self.assertFalse(d["span_verified"])

    def test_span_referansi_bildirilir(self) -> None:
        """Offset'ler clean_text'e göre ölçülür; raw_text ile karıştırmak
        onları kaydırır. Hangisine göre olduğu yanıtta belirtilmeli."""
        cid = self._yaz(normalize_text(ORNEK))
        self.assertEqual(self.repo.campaign_text(cid)["span_reference"],
                         "clean_text")

    def test_olmayan_kampanya_none_doner(self) -> None:
        self.assertIsNone(self.repo.campaign_text(99999))

    def test_query_fields_offsetleri_tasir(self) -> None:
        """Karşılaştırma paneli span vurgulaması için bunları kullanıyor."""
        self._yaz(normalize_text(ORNEK))
        satirlar = self.repo.query_fields("kar_payi_orani")
        self.assertTrue(satirlar)
        for s in satirlar:
            for anahtar in ("span_start", "span_end", "confidence_source",
                            "raw_value", "extractor", "source_url"):
                self.assertIn(anahtar, s, f"query_fields '{anahtar}' döndürmüyor")


class TestSemaGocu(unittest.TestCase):
    """Diskteki eski bir demo DB'si açıldığında sütunlar tamamlanmalı."""

    def test_eski_db_dosyasi_gocurulur(self) -> None:
        import sqlite3
        with tempfile.TemporaryDirectory() as td:
            yol = str(Path(td) / "eski.db")
            # 31 Tem oncesi sema — yeni sutunlar yok
            eski = sqlite3.connect(yol)
            eski.executescript("""
                CREATE TABLE banks (id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL, slug TEXT UNIQUE NOT NULL,
                    website_url TEXT, bddk_active INTEGER DEFAULT 1);
                CREATE TABLE campaigns (id INTEGER PRIMARY KEY AUTOINCREMENT,
                    bank_id INTEGER, raw_text TEXT NOT NULL, clean_text TEXT,
                    source_url TEXT, scraped_at TEXT, campaign_type TEXT);
                CREATE TABLE extracted_fields (id INTEGER PRIMARY KEY AUTOINCREMENT,
                    campaign_id INTEGER, field_name TEXT NOT NULL, raw_value TEXT,
                    canonical_value TEXT, confidence REAL, source_span TEXT,
                    extractor TEXT);
            """)
            eski.commit()
            eski.close()

            repo = Repository(yol)                 # göç burada koşmalı
            sutunlar = {r["name"] for r in
                        repo.conn.execute("PRAGMA table_info(extracted_fields)")}
            for beklenen in ("span_start", "span_end", "confidence_source"):
                self.assertIn(beklenen, sutunlar,
                              f"{beklenen} eski DB'ye eklenmedi")

            # göçten sonra yazma/okuma çalışmalı
            metin = normalize_text(ORNEK)
            c = Campaign(bank_slug="kuveyt-turk", raw_text=metin,
                         source_url="x", fields=extract_all(metin))
            cid = repo.insert_campaign(c, clean_text=metin)
            self.assertTrue(repo.campaign_text(cid)["fields"])
            repo.close()

    def test_goc_idempotent(self) -> None:
        """Aynı DB iki kez açılınca ADD COLUMN hata vermemeli."""
        with tempfile.TemporaryDirectory() as td:
            yol = str(Path(td) / "tekrar.db")
            Repository(yol).close()
            Repository(yol).close()          # ikinci açılış patlamamalı


if __name__ == "__main__":
    unittest.main()
