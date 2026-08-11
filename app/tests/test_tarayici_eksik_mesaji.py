"""Tarayıcı yoksa: banka zarifçe atlanır, ekrana HAM HATA sızmaz.

İlgili: ../src/scraping/fetcher.py, ../src/scraping/collector.py,
        ../src/scraping/tazeleme.py, ../config/banks.yaml (`scrape_mode: js`)

## Bu dosyanın koruduğu değişmezler

1. **Ham istisna metni ve dosya yolu ekrana çıkmaz.** Operatör şunu görüyordu:

       Bu banka için toplama katmanı hazır değil: tarayici baslatilamadi:
       Error: BrowserType.launch: Executable doesn't exist at
       /Users/<kullanici>/Library/Caches/ms-playwright/…

   Hem okunmaz hem de makinedeki mutlak bir yolu — kullanıcı adı dahil —
   arayüze taşıyor.

2. **Mesaj Türkçe, kısa ve EYLEME DÖNÜK.** Neyin eksik olduğunu ve nasıl
   kurulacağını söyler; kurulumu KENDİ ÇALIŞTIRMAZ (internet gerektirir,
   kararı operatör verir).

3. **Eksiklik türü ayrışır.** "Sürücü hiç kurulu değil" ile "tarayıcı bileşeni
   indirilmemiş" farklı komutlar gerektirir; tek mesaja indirmek operatöre
   yapılacak işi söylemez.

4. **Diğer bankalar bozulmaz.** Tarayıcı isteyen banka atlanır; statik
   bankaların toplaması ve veri tabanından okuyan ekranlar etkilenmez.
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.scraping import fetcher as F
from src.scraping.collector import collect_live
from src.scraping.config import BankConfig
from src.scraping.fetcher import FetcherBundle, FetchResult
from src.scraping.robots import RobotsCache
from src.scraping.tazeleme import (
    DURUM_HATA,
    TARAYICI_MESAJLARI,
    TazelemeDurumu,
    tazele,
    toplama_katmani_mesaji,
)

#: Playwright'in gerçek çıktısı (2026-08-11, bu makinede ölçüldü). Testin
#: yakaladığı şey uydurma bir metin değil, sahadan alınmış olanıdır.
GERCEK_IKILI_YOK = (
    "Error: BrowserType.launch: Executable doesn't exist at "
    "/Users/ornek/Library/Caches/ms-playwright/chromium_headless_shell-1228/"
    "chrome-headless-shell-mac-arm64/chrome-headless-shell\n"
    "Please run the following command to download new browsers:\n"
    "    playwright install"
)

JS_BANKA = BankConfig(
    slug="ornek-js-katilim",
    name="Örnek JS Katılım",
    website_url="https://ornek.example",
    campaign_paths=["/kampanyalar"],
    detail_patterns=["kampanya"],
    max_docs=10,
    scrape_mode="js",
)


class _OlmayanTarayici(F.BrowserFetcher):
    """Başlatma denemesinde gerçek Playwright hatasını atan çekici."""

    def __init__(self, hata: Exception) -> None:
        super().__init__()
        self._hata = hata

    def _ensure(self):  # type: ignore[override]
        if self.unavailable_reason is not None:
            return self.unavailable_reason
        detay = f"{type(self._hata).__name__}: {self._hata}"
        kod = (F.KOD_IKILI_YOK if F._IKILI_YOK_RE.search(detay)
               else F.KOD_BASLATILAMADI)
        return self._yok(kod, detay)


class _StatikCekici:
    """Statik yol çalışıyor — tarayıcı yokluğu onu bozmamalı."""

    method = "live"
    available = True

    def fetch(self, url: str) -> FetchResult:
        return FetchResult(url, status=200, html="<html></html>",
                           method=self.method, final_url=url)

    def close(self) -> None:
        pass


class TestCekiciKodUretir(unittest.TestCase):
    """Yokluk sonlu bir KODA indirgenir; ham metin ayrı bir alanda kalır."""

    def test_ikili_yok_ayri_kod_alir(self) -> None:
        c = _OlmayanTarayici(RuntimeError(GERCEK_IKILI_YOK))
        self.assertFalse(c.available)
        self.assertEqual(c.unavailable_code, F.KOD_IKILI_YOK)

    def test_baska_hata_baslatilamadi_kodu_alir(self) -> None:
        c = _OlmayanTarayici(RuntimeError("Target page crashed"))
        self.assertFalse(c.available)
        self.assertEqual(c.unavailable_code, F.KOD_BASLATILAMADI)

    def test_surucu_yoksa_kendi_kodu(self) -> None:
        """`playwright` paketi hiç kurulu değilse ayrı bir çözüm gerekir."""
        c = F.BrowserFetcher()
        c._yok(F.KOD_SURUCU_YOK)
        self.assertEqual(c.unavailable_code, F.KOD_SURUCU_YOK)
        self.assertIsNone(c.unavailable_detail)

    def test_kisa_sebep_dosya_yolu_tasimaz(self) -> None:
        c = _OlmayanTarayici(RuntimeError(GERCEK_IKILI_YOK))
        self.assertFalse(c.available)
        self.assertNotIn("/Users/", c.unavailable_reason or "")
        self.assertNotIn("Executable", c.unavailable_reason or "")
        self.assertLess(len(c.unavailable_reason or ""), 80)

    def test_ham_ayrinti_KAYBOLMAZ_ayri_alanda_durur(self) -> None:
        """Hata ayıklama bilgisi silinmez; yalnız kullanıcı yolundan çıkarılır."""
        c = _OlmayanTarayici(RuntimeError(GERCEK_IKILI_YOK))
        self.assertFalse(c.available)
        self.assertIn("Executable doesn't exist", c.unavailable_detail or "")


class TestToplayiciKoduTasir(unittest.TestCase):
    """`collect_live` bankayı atlar ve kodu tanılamaya yazar."""

    def test_atlanan_bankada_kod_ve_temiz_sebep(self) -> None:
        bundle = FetcherBundle(
            static=_StatikCekici(),  # type: ignore[arg-type]
            browser=_OlmayanTarayici(RuntimeError(GERCEK_IKILI_YOK)))
        rapor: dict = {}
        docs = collect_live(JS_BANKA, bundle=bundle,
                            robots=RobotsCache(fetcher=lambda u: (200, "")),
                            report=rapor)
        self.assertEqual(docs, [])
        self.assertEqual(rapor["skipped_code"], F.KOD_IKILI_YOK)
        self.assertNotIn("/Users/", rapor["skipped_reason"])
        self.assertNotIn("/Users/", " ".join(rapor["notes"]))


class TestEkranMesaji(unittest.TestCase):
    """Operatörün gördüğü cümle: Türkçe, kısa, eyleme dönük, yolsuz."""

    def test_ikili_yok_kurulum_komutunu_soyler(self) -> None:
        m = toplama_katmani_mesaji(F.KOD_IKILI_YOK)
        self.assertIn("playwright install chromium", m)
        self.assertIn("internet gerektirir", m)

    def test_surucu_yok_iki_adimi_da_soyler(self) -> None:
        m = toplama_katmani_mesaji(F.KOD_SURUCU_YOK)
        self.assertIn("pip install playwright", m)
        self.assertIn("playwright install chromium", m)

    def test_baslatilamadi_gunluge_yonlendirir(self) -> None:
        m = toplama_katmani_mesaji(F.KOD_BASLATILAMADI)
        self.assertIn("günlüğ", m)
        self.assertNotIn("playwright install", m)

    def test_bilinmeyen_kod_ham_metne_DUSMEZ(self) -> None:
        """Sızıntının geri geleceği tek delik burasıydı."""
        for kod in (None, "", "hic_boyle_bir_kod_yok"):
            m = toplama_katmani_mesaji(kod)
            self.assertIn("toplama katmanı hazır değil", m)
            self.assertNotIn("Error:", m)

    def test_mesajlarda_dosya_yolu_ve_istisna_izi_yok(self) -> None:
        for kod in list(TARAYICI_MESAJLARI) + [None]:
            m = toplama_katmani_mesaji(kod)
            for sizinti in ("/Users/", "Traceback", "Error:", "Exception",
                            "ms-playwright", ".py:"):
                self.assertNotIn(sizinti, m, f"{kod} mesajında sızıntı: {sizinti}")

    def test_diger_bankalarin_etkilenmedigi_soylenir(self) -> None:
        m = toplama_katmani_mesaji(F.KOD_IKILI_YOK)
        self.assertIn("etkilenmez", m)


class TestUctanUca(unittest.TestCase):
    """`tazele()` sonucu: hata durumu + temiz mesaj, çökme YOK."""

    def test_tazeleme_cokmeden_temiz_mesajla_biter(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            bundle = FetcherBundle(
                static=_StatikCekici(),  # type: ignore[arg-type]
                browser=_OlmayanTarayici(RuntimeError(GERCEK_IKILI_YOK)))
            kayit = TazelemeDurumu(is_id="t1", bank=JS_BANKA.slug,
                                   bank_name=JS_BANKA.name)
            durum = tazele(JS_BANKA, tmp, kayit, bundle=bundle,
                           robots=RobotsCache(fetcher=lambda u: (200, "")))
            d = durum.to_dict()
            self.assertEqual(d["durum"], DURUM_HATA)
            self.assertEqual(d["cekilen"], 0)
            self.assertIn("playwright install chromium", d["mesaj"])
            self.assertNotIn("/Users/", d["mesaj"])
            # Ham arşive hiçbir şey yazılmadı — banka gerçekten ATLANDI.
            self.assertEqual(list(Path(tmp).rglob("*.txt")), [])


class TestBanksYamlOlcumu(unittest.TestCase):
    """Kaç banka tarayıcı gerektiriyor — iddia değil, dosyadan ÖLÇÜM."""

    def test_js_bankalari_yapilandirmadan_okunur(self) -> None:
        from src.scraping.config import load_banks

        bankalar = load_banks(str(ROOT / "config" / "banks.yaml"))
        js = sorted(b.slug for b in bankalar if b.scrape_mode == "js")
        self.assertEqual(js, ["adil-katilim", "hayat-finans", "tom-katilim",
                              "turkiye-finans"])
        # Geri kalanın hiçbiri tarayıcıya bağlı değil: tarayıcı yokluğu
        # korpusun tamamını değil, yalnız bu dört bankayı durdurur.
        self.assertGreater(len(bankalar) - len(js), len(js))


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
