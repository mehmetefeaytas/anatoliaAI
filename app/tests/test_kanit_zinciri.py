"""Gold kanıt zinciri doğrulayıcısının kapıları.

Çalıştır:  python -m unittest tests.test_kanit_zinciri  (app/ kökünden)

## Neden bu testler

`kanit_zinciri.py` bir KANIT aracıdır; yanlış "tamam" demesi, yanlış "kırık"
demesinden daha pahalıdır. İki hata biçimi ayrı ayrı kilitlenir:

1. **Yanlış tamam** — provenance eksikken zinciri onaylamak. Ölçümü
   savunulamaz kılar.
2. **Yanlış alarm** — sayfa anotasyondan sonra tazelendiği için hash tutmuyor
   diye "kanıt yok" demek. Gold DONMUŞ, korpus AKIYOR; bu ayrımı yapamayan
   rapor her tazelemede kırmızıya döner ve okunmaz hâle gelir.

Zincirin iki ayrı hash taşıdığı da burada kilitli: gold `content_hash`'i
çıkarılmış METNİN özeti, `.meta.json`'daki ham HTML'in özetidir. İkisinin
eşit olmaması BEKLENEN durumdur.
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from scripts.kanit_zinciri import _url_kanonik, dogrula
from src.preprocessing.clean import normalize_text
from src.scraping.collector import content_hash

METIN = "Konut finansmanı kampanyası. Kâr payı oranı %2,05. Vade 120 ay."
URL = "https://ornek-katilim.com.tr/Kampanyalar/Konut.aspx"


class Zemin(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.kok = Path(self.tmp.name)
        self.raw = self.kok / "raw" / "ornek-katilim"
        self.raw.mkdir(parents=True)
        self.addCleanup(self.tmp.cleanup)

    def _ham_yaz(self, metin: str, url: str = URL, scraped: str | None = "2026-08-01T10:00:00+00:00",
                 ad: str = "konut", meta: bool = True) -> None:
        (self.raw / f"{ad}.txt").write_text(metin, encoding="utf-8")
        if meta:
            d = {
                "bank_slug": "ornek-katilim",
                "source_url": url,
                # ham HTML'in özeti — gold'unkiyle KASTEN farklı taban
                "content_hash": content_hash("<html>farklı taban</html>"),
                "collection_method": "browser",
                "http_status": 200,
            }
            if scraped:
                d["scraped_at"] = scraped
            (self.raw / f"{ad}.txt.meta.json").write_text(
                json.dumps(d, ensure_ascii=False), encoding="utf-8")

    def _gold_yaz(self, metin: str = METIN, url: str = URL) -> str:
        kayit = [{
            "id": "ornek-katilim--konut",
            "source_url": url,
            "content_hash": content_hash(normalize_text(metin)),
            "text": metin,
            "fields": {},
        }]
        p = self.kok / "gold.json"
        p.write_text(json.dumps(kayit, ensure_ascii=False), encoding="utf-8")
        return str(p)

    def _calistir(self) -> dict:
        return dogrula(self._gold_yaz(), str(self.kok / "raw"))[0]


class TamZincir(Zemin):
    def test_tam_zincir_sorunsuz(self):
        self._ham_yaz(METIN)
        s = self._calistir()
        self.assertEqual(s["sorunlar"], [])
        self.assertFalse(s["kaymis"])
        self.assertEqual(s["scraped_at"], "2026-08-01T10:00:00+00:00")
        self.assertEqual(s["http_status"], 200)

    def test_ham_html_hashi_gold_ile_ayni_olmak_ZORUNDA_degil(self):
        """İki hash farklı katmanı özetler; eşitlik ŞART KOŞULMAZ."""
        self._ham_yaz(METIN)
        s = self._calistir()
        self.assertNotEqual(s["html_hash"], s["content_hash"])
        self.assertEqual(s["sorunlar"], [])


class YanlisTamamOlmasin(Zemin):
    def test_meta_yoksa_sorun(self):
        self._ham_yaz(METIN, meta=False)
        s = self._calistir()
        self.assertTrue(any("meta" in x for x in s["sorunlar"]), s["sorunlar"])

    def test_scraped_at_yoksa_sorun(self):
        self._ham_yaz(METIN, scraped=None)
        s = self._calistir()
        self.assertIn("scraped_at yok", s["sorunlar"])

    def test_scraped_at_bozuksa_sorun(self):
        self._ham_yaz(METIN, scraped="dün öğlen")
        s = self._calistir()
        self.assertTrue(any("ISO-8601" in x for x in s["sorunlar"]), s["sorunlar"])

    def test_kaynak_hic_yoksa_sorun(self):
        self._ham_yaz("bambaşka bir belge", url="https://baska.com/x")
        s = self._calistir()
        self.assertTrue(any("bulunabildi" in x for x in s["sorunlar"]), s["sorunlar"])

    def test_url_tutarsizsa_sorun(self):
        # Metin birebir tutuyor ama meta başka bir sayfayı gösteriyor.
        self._ham_yaz(METIN, url="https://ornek-katilim.com.tr/Baska/Sayfa.aspx")
        s = self._calistir()
        self.assertTrue(any("source_url tutarsız" in x for x in s["sorunlar"]), s["sorunlar"])


class YanlisAlarmOlmasin(Zemin):
    def test_icerik_kaymasi_KIRIK_sayilmaz(self):
        """Sayfa anotasyondan sonra değişmiş: kanıt duruyor, zincir kırık değil."""
        self._ham_yaz(METIN + " Güncelleme: kampanya 31 Aralık'a uzatıldı.")
        s = self._calistir()
        self.assertTrue(s["kaymis"])
        self.assertEqual(s["sorunlar"], [], "içerik kayması sorun sayılmamalı")
        self.assertIsNotNone(s["scraped_at"])

    def test_url_buyuk_kucuk_harf_varyanti_alarm_uretmez(self):
        self._ham_yaz(METIN, url="https://ornek-katilim.com.tr/kampanyalar/konut.aspx")
        s = self._calistir()
        self.assertEqual(s["sorunlar"], [])

    def test_port_varyanti_alarm_uretmez(self):
        self._ham_yaz(METIN, url="https://ornek-katilim.com.tr:443/Kampanyalar/Konut.aspx")
        s = self._calistir()
        self.assertEqual(s["sorunlar"], [])


class UrlKanonik(unittest.TestCase):
    def test_varyantlar_ayni_kanonige_duser(self):
        a = _url_kanonik("https://X.com.tr:443/Yol/Sayfa.aspx/")
        b = _url_kanonik("https://x.com.tr/yol/sayfa.aspx")
        self.assertEqual(a, b)


if __name__ == "__main__":
    unittest.main()
