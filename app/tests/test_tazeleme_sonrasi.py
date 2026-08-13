"""Tazeleme sonrası uzlaştırma — bayat özet sessizce durmaz.

İlgili: ../src/tazeleme_sonrasi.py, ../src/scraping/tazeleme.py
        ../src/summarize/ozet.py, ../src/db/repository.py

## Bu dosyanın koruduğu değişmezler

1. **Değişmeyen belgeye dokunulmaz.** Aynı adresin başka bir kopyası (aynı
   `source_url`, farklı metin) korpusta duruyorsa onun özeti düşmez.
2. **Bayat özet kalmaz.** Metni değişen belgenin özeti düşer ve NEDEN düştüğü
   `ozet_sebep` ile yazılır — sessiz kayıp yasak.
3. **Yanlış satır yerine hiçbir satır.** Eşleşme bulunamazsa hiçbir şey
   yazılmaz ve kayıt raporda "eşleşmeyen" olarak görünür.
4. **Görünüm önbelleği haberdar edilir.** Aksi hâlde panel, veri tabanında
   artık olmayan özeti göstermeye devam ederdi.

Hiçbir test ağ kullanmaz ve GERÇEK `data/` altına dokunmaz: geçici dizinde
kurulan bir SQLite deposu kullanılır.
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.db.repository import Repository
from src.preprocessing.clean import normalize_text
from src.schemas import Campaign
from src.summarize.ozet import SEBEP_KAYNAK_DEGISTI, kalici_sebep
from src.tazeleme_sonrasi import alt_akis_kur, ozetleri_gecersizle

ESKI = "Kâr payı oranı %1,89 ve vade 120 aydır. " * 5
YENI = "Kâr payı oranı %1,59 ve vade 120 aydır. " * 5
URL = "https://ornek.example/kampanyalar/konut"


class _Temel(unittest.TestCase):

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.repo = Repository(str(Path(self._tmp.name) / "t.db"))

    def tearDown(self) -> None:
        self.repo.close()
        self._tmp.cleanup()

    def _ekle(self, metin: str, ozet: str | None, *, url: str = URL) -> int:
        """Korpus yolunun yaptığını yapar: metni `normalize_text`ten geçirir."""
        temiz = normalize_text(metin)
        cid = self.repo.insert_campaign(
            Campaign(bank_slug="ornek-katilim", raw_text=temiz, source_url=url),
            clean_text=temiz)
        if ozet is not None:
            self.repo.set_ozet({cid: ozet})
        return cid

    def _satir(self, cid: int) -> dict:
        for c in self.repo.all_campaigns():
            if int(c["id"]) == cid:
                return c
        raise AssertionError(f"kampanya bulunamadı: {cid}")


class TestGecersizleme(_Temel):

    def test_metni_degisen_belgenin_ozeti_duser_ve_sebebi_yazilir(self) -> None:
        cid = self._ekle(ESKI, "Konut kampanyası %1,89 kâr payı sunuyor.")
        rapor = ozetleri_gecersizle(
            self.repo, [{"source_url": URL, "onceki_metin": ESKI}])
        satir = self._satir(cid)
        self.assertFalse((satir["ozet"] or "").strip(),
                         "bayat özet veri tabanında kaldı")
        self.assertEqual(satir["ozet_sebep"], SEBEP_KAYNAK_DEGISTI)
        self.assertEqual(rapor["gecersizlenen_ozet"], 1)
        self.assertIn("düşürüldü", rapor["mesaj"])

    def test_sebep_kalici_degil(self) -> None:
        """Kalıcı işaretlenseydi belge sonsuza dek özetsiz kalırdı: metin veri
        tabanına aktarıldıktan sonra özet yeniden ÜRETİLEBİLİR olmalı."""
        self.assertFalse(kalici_sebep(SEBEP_KAYNAK_DEGISTI))

    def test_ayni_adresin_degismemis_kopyasina_dokunulmaz(self) -> None:
        """Aynı `source_url` birden fazla kayıtta geçiyor (`live/` + `archive/`
        kopyaları — `ozet_geri_yukle` başlığında 97 mükerrer olarak ölçüldü).
        Yalnız adrese bakılsaydı hiç değişmemiş arşiv kopyasının özeti de
        düşerdi."""
        degisen = self._ekle(ESKI, "Eski metni tarif eden özet.")
        arsiv = self._ekle("Bambaşka bir arşiv metni. " * 5, "Arşiv özeti.")
        ozetleri_gecersizle(self.repo,
                            [{"source_url": URL, "onceki_metin": ESKI}])
        self.assertFalse((self._satir(degisen)["ozet"] or "").strip())
        self.assertEqual(self._satir(arsiv)["ozet"], "Arşiv özeti.")

    def test_eslesmeyen_belge_yazmaz_ama_raporlanir(self) -> None:
        cid = self._ekle(ESKI, "Bozulmaması gereken özet.")
        rapor = ozetleri_gecersizle(
            self.repo,
            [{"source_url": "https://ornek.example/hic-aktarilmadi",
              "onceki_metin": YENI}])
        self.assertEqual(rapor["gecersizlenen_ozet"], 0)
        self.assertEqual(rapor["eslesmeyen_belge"], 1)
        self.assertIn("dokunulmadı", rapor["mesaj"])
        self.assertEqual(self._satir(cid)["ozet"], "Bozulmaması gereken özet.")

    def test_zaten_ozetsiz_belge_sebep_yazdirmaz(self) -> None:
        """Düşürülecek bir şey yoksa gerekçe de yazılmaz: olmayan bir olayın
        kaydını tutmak, kapsam sayacını yanlış kovaya iterdi."""
        cid = self._ekle(ESKI, None)
        rapor = ozetleri_gecersizle(
            self.repo, [{"source_url": URL, "onceki_metin": ESKI}])
        self.assertEqual(rapor["gecersizlenen_ozet"], 0)
        self.assertEqual(rapor["zaten_ozetsiz"], 1)
        self.assertIsNone(self._satir(cid)["ozet_sebep"])

    def test_bos_liste_hicbir_sey_yapmaz(self) -> None:
        cid = self._ekle(ESKI, "Duran özet.")
        rapor = ozetleri_gecersizle(self.repo, [])
        self.assertEqual(rapor["degisen_belge"], 0)
        self.assertIsNone(rapor["mesaj"])
        self.assertEqual(self._satir(cid)["ozet"], "Duran özet.")

    def test_onbellek_geri_cagrisi_etkilenen_idlerle_cagrilir(self) -> None:
        """API'nin görünüm önbelleği özeti OLAN kaydı taze sayıyor; haber
        verilmezse panel silinmiş özeti göstermeye devam eder."""
        cid = self._ekle(ESKI, "Bayat özet.")
        unutulan: list[list[int]] = []
        ozetleri_gecersizle(self.repo,
                            [{"source_url": URL, "onceki_metin": ESKI}],
                            unut=unutulan.append)
        self.assertEqual(unutulan, [[cid]])


class TestAltAkisKur(_Temel):
    """Geri çağrı fabrikası `TazelemeYoneticisi` sözleşmesine uyar."""

    def test_uretilen_geri_cagri_degisen_listesini_alir(self) -> None:
        cid = self._ekle(ESKI, "Bayat özet.")
        alt_akis = alt_akis_kur(lambda: self.repo)
        rapor = alt_akis([{"source_url": URL, "onceki_metin": ESKI}])
        self.assertEqual(rapor["gecersizlenen_ozet"], 1)
        self.assertEqual(self._satir(cid)["ozet_sebep"], SEBEP_KAYNAK_DEGISTI)


if __name__ == "__main__":
    unittest.main()
