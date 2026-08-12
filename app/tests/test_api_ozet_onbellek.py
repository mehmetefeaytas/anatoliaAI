"""Özet sonradan yazıldığında belge ekranında GÖRÜNÜR.

İlgili: ../src/api/main.py (`_campaign_view` önbelleği)
        ../scripts/build_summaries.py (özetleri parça parça yazan koşu)

## Bu testin varlık sebebi

`/campaigns/{id}/text` kampanya başına önbellekli ve önbellek `ozet` alanını da
tutuyordu. Özetler toplu koşumda parça parça yazılıyor; koşu SÜRERKEN açılan
bir belge "özet yok" hâliyle önbelleğe giriyor ve özet veri tabanına düşse bile
API yeniden başlayana kadar öyle kalıyordu.

Demo sırasında bunun karşılığı şu: jüri bir belgeyi açıyor, "AI özeti henüz
üretilmedi" görüyor; on dakika sonra aynı belgeyi tekrar açıyor ve özet ARTIK
VAR olmasına rağmen yine "üretilmedi" görüyor.

Düzeltme: özeti olmayan kayıt önbellekten servis edilmez, her istekte tazelenir.
Özet bir kez geldiğinde kayıt normal biçimde önbellekte kalır — maliyet yalnız
eksik özetli belgelerde ödenir.
"""

from __future__ import annotations

import importlib
import os
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# fastapi `setUp` içinde import ediliyordu: modül yüklenir ama her test HATA
# verir, atlanmaz. 12 Ağu CI koşusunda bu dosya 4 hata üretti. Probe modül
# seviyesine alındı. Desen: `test_api_startup.py:37-41`.
try:  # pragma: no cover - ortama bağlı
    import fastapi  # noqa: F401
    FASTAPI_VAR = True
except ModuleNotFoundError:  # pragma: no cover
    FASTAPI_VAR = False


def _db_kur(yol: Path) -> None:
    conn = sqlite3.connect(yol)
    conn.executescript("""
        CREATE TABLE banks (id INTEGER PRIMARY KEY, slug TEXT, name TEXT,
                            website_url TEXT, bddk_active INTEGER DEFAULT 1);
        CREATE TABLE campaigns (
            id INTEGER PRIMARY KEY, bank_id INTEGER, raw_text TEXT,
            clean_text TEXT, source_url TEXT, scraped_at TEXT,
            campaign_type TEXT, belge_turu TEXT, ozet TEXT, ozet_kaynak TEXT);
        CREATE TABLE extracted_fields (
            id INTEGER PRIMARY KEY, campaign_id INTEGER, field_name TEXT,
            raw_value TEXT, canonical_value TEXT, confidence REAL,
            source_span TEXT, extractor TEXT, confidence_source TEXT,
            span_start INTEGER, span_end INTEGER);
        INSERT INTO banks (id, slug, name) VALUES (1, 'test-katilim', 'Test Katılım');
        INSERT INTO campaigns (id, bank_id, raw_text, source_url, belge_turu)
        VALUES (1, 1, 'Konut finansmanı kampanyası. Kâr payı oranı %2,05.',
                'https://ornek.test/kampanya', 'kampanya');
    """)
    conn.commit()
    conn.close()


@unittest.skipUnless(FASTAPI_VAR, "fastapi kurulu değil — API testi atlanıyor")
class TestOzetOnbellegi(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.db = Path(self._tmp.name) / "t.db"
        _db_kur(self.db)
        self._eski = os.environ.get("DATABASE_PATH")
        os.environ["DATABASE_PATH"] = str(self.db)

        from fastapi.testclient import TestClient

        from src.api import main as M
        importlib.reload(M)
        self.M = M
        self.client = TestClient(M.app)

    def tearDown(self) -> None:
        if self._eski is None:
            os.environ.pop("DATABASE_PATH", None)
        else:
            os.environ["DATABASE_PATH"] = self._eski
        self._tmp.cleanup()

    def _ozet_yaz(self, metin: str) -> None:
        """Toplu koşumun yaptığını yapar: DB'ye özet yazar."""
        conn = sqlite3.connect(self.db)
        conn.execute("UPDATE campaigns SET ozet=?, ozet_kaynak='llm' WHERE id=1",
                     (metin,))
        conn.commit()
        conn.close()

    def test_sonradan_yazilan_ozet_GORUNUR(self) -> None:
        """Asıl iddia: önbellek bayat 'özet yok' cevabını dondurmamalı."""
        ilk = self.client.get("/campaigns/1/text").json()
        self.assertIn(ilk.get("ozet"), (None, ""),
                      "başlangıçta özet olmamalı")

        self._ozet_yaz("Konut finansmanı kampanyası, kâr payı %2,05.")

        ikinci = self.client.get("/campaigns/1/text").json()
        self.assertEqual(ikinci.get("ozet"),
                         "Konut finansmanı kampanyası, kâr payı %2,05.",
                         "özet DB'ye yazıldıktan sonra API onu GÖSTERMELİ; "
                         "önbellek eski 'özet yok' cevabını dondurmuş")

    def test_ozet_geldikten_sonra_ONBELLEKLENIR(self) -> None:
        """Tazeleme maliyeti yalnız eksik özetli belgede ödenmeli.

        Özet geldikten sonra DB'yi değiştirip cevabın DEĞİŞMEDİĞİNİ görmek,
        kaydın gerçekten önbellekte kaldığını kanıtlar.
        """
        self._ozet_yaz("İlk özet.")
        self.assertEqual(self.client.get("/campaigns/1/text").json()["ozet"],
                         "İlk özet.")

        self._ozet_yaz("İKİNCİ özet — önbellek bunu GÖRMEMELİ.")
        self.assertEqual(self.client.get("/campaigns/1/text").json()["ozet"],
                         "İlk özet.",
                         "özetli kayıt önbellekte kalmalıydı")

    def test_bilinmeyen_kampanya_404(self) -> None:
        """`None` önbelleği tazelenmez: o cevap değişmez."""
        for _ in range(2):
            self.assertEqual(self.client.get("/campaigns/9999/text").status_code,
                             404)

    def test_metin_ve_alanlar_bozulmadan_doner(self) -> None:
        """Tazeleme, cevabın geri kalanını etkilememeli."""
        once = self.client.get("/campaigns/1/text").json()
        self._ozet_yaz("Özet.")
        sonra = self.client.get("/campaigns/1/text").json()
        for anahtar in ("campaign_id", "bank", "text", "text_length"):
            self.assertEqual(once[anahtar], sonra[anahtar], anahtar)


if __name__ == "__main__":
    unittest.main()
