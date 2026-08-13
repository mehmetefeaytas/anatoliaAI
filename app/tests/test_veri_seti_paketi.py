"""Yayına hazır veri seti paketinin kapıları.

Çalıştır:  python -m unittest tests.test_veri_seti_paketi  (app/ kökünden)

## Neden

Veri seti şartname §6.3'te zorunlu teslimdir ve bir kez yayımlandıktan sonra
indirilen kopya geri alınamaz. En pahalı iki hata:

1. **Provenance'sız kayıt yayımlamak** — kaynağı gösterilemeyen bir gold,
   veri setinin bütün iddiasını çürütür. Kırık zincir çıkış kodunu 1 yapar.
2. **`absent` bilgisini kaybetmek** — "kontrol ettim, yok" kararı
   halüsinasyon oranının paydasıdır. Pakette taşınmazsa dışarıdan hiç kimse
   o oranı yeniden üretemez.
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

from scripts.veri_seti_paketi import paketle
from src.preprocessing.clean import normalize_text
from src.scraping.collector import content_hash

METIN = "Konut finansmanı. Kâr payı oranı %2,05. Vade 120 ay."


class Paket(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.kok = Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)
        raw = self.kok / "raw" / "ornek"
        raw.mkdir(parents=True)
        (raw / "k.txt").write_text(METIN, encoding="utf-8")
        (raw / "k.txt.meta.json").write_text(json.dumps({
            "source_url": "https://ornek.com.tr/k",
            "scraped_at": "2026-08-01T10:00:00+00:00",
            "http_status": 200,
            "collection_method": "browser",
            "content_hash": content_hash("<html/>"),
        }), encoding="utf-8")
        self.gold = self.kok / "gold.json"
        self.gold.write_text(json.dumps([{
            "id": "ornek--k",
            "bank_slug": "ornek",
            "source_url": "https://ornek.com.tr/k",
            "content_hash": content_hash(normalize_text(METIN)),
            "text": METIN,
            "hard": True,
            "fields": {"vade_ay": 120},
            "field_spans": {"vade_ay": "Vade 120 ay"},
            "absent_fields": ["tahsis_ucreti"],
        }], ensure_ascii=False), encoding="utf-8")

    def _paketle(self):
        out = self.kok / "dist"
        ozet = paketle(str(self.gold), str(out), str(self.kok / "raw"))
        return out, ozet

    def test_paket_beklenen_dosyalari_uretir(self):
        out, ozet = self._paketle()
        for ad in ("gold.json", "gold.csv", "README.md"):
            self.assertTrue((out / ad).is_file(), f"{ad} yok")
        self.assertTrue((out / "belgeler" / "ornek--k.txt").is_file())
        self.assertEqual(ozet["kirik_zincir"], 0)

    def test_provenance_pakete_giriyor(self):
        out, _ = self._paketle()
        m = json.loads((out / "belgeler" / "ornek--k.meta.json").read_text(encoding="utf-8"))
        self.assertEqual(m["scraped_at"], "2026-08-01T10:00:00+00:00")
        self.assertEqual(m["source_url"], "https://ornek.com.tr/k")
        self.assertEqual(m["http_status"], 200)

    def test_absent_bilgisi_kaybolmuyor(self):
        """Halüsinasyon oranının paydası bu alandır; taşınmazsa yeniden üretilemez."""
        out, _ = self._paketle()
        kayit = json.loads((out / "gold.json").read_text(encoding="utf-8"))[0]
        self.assertEqual(kayit["absent_fields"], ["tahsis_ucreti"])

    def test_kanit_alintisi_csvye_giriyor(self):
        out, _ = self._paketle()
        icerik = (out / "gold.csv").read_text(encoding="utf-8-sig")
        self.assertIn("Vade 120 ay", icerik)

    def test_kirik_zincir_kapiyi_kapatir(self):
        """Kaynağı bulunamayan kayıt varsa paket 'yayımlanabilir' demez."""
        self.gold.write_text(json.dumps([{
            "id": "ornek--yok",
            "bank_slug": "ornek",
            "source_url": "https://ornek.com.tr/bulunamaz",
            "content_hash": content_hash("arşivde olmayan metin"),
            "text": "arşivde olmayan metin",
            "fields": {},
        }], ensure_ascii=False), encoding="utf-8")
        _, ozet = self._paketle()
        self.assertEqual(ozet["kirik_zincir"], 1)


if __name__ == "__main__":
    unittest.main()
