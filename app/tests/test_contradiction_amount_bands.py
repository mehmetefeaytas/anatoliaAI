"""Tutar bandı çelişkisi (`celisen_tutar_bandi`) regresyon testleri.

İlgili: ../src/comparison/contradiction.py `_rule_conflicting_amount_bands`
        ../docs/rapor/banka-siteleri-veri-kaynagi-haritasi.md §8

## Arka plan — bu kural neden var

2026-08-03 tarayıcı keşfinde Kuveyt Türk TOGG Finansmanı sayfasında GERÇEK bir
sayfa-içi çelişki bulundu: sayfa gövdesindeki tablo ile AYNI SAYFANIN SSS
bölümü farklı tutar bantları yayımlıyor.

    tablo : 6.500.001 – 7.500.000 TL → %20 ;  7.500.001 TL ve üzeri → %0
    SSS   : 6.000.001 – 7.000.000 TL → %20 ;  7.000.001 TL ve üzeri → %0

Kanıt dosyası (repoda mevcut):
    data/raw/kuveyt-turk/products/arac-finansmanlari-togg-finansmani.txt

Bu, sentetik olmayan, kaynaklanabilir bir çelişki vakasıdır — CLAUDE.md §18-2
(bankalar arası/içi çelişki tespiti) için jüriye gösterilebilir kanıt.

## Neden bu testler bu şekilde

Kural iki hassas dengeyi tutmak zorunda:

1. **Yakalamalı:** çakışan ama aynı olmayan bantlar (gerçek çelişki).
2. **Susmalı:** birebir aynı bantlar (aynı cetvel iki kez yazılmış) ve ayrık
   bantlar (meşru cetvel) ve LİSTELEME sayfaları (bağımsız kampanyaların
   eşikleri). Liste koruması olmadan korpusta 15 bulgunun 13'ü hayaletti.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.comparison.contradiction import _parse_bands, detect
from src.normalization.normalize import parse_tr_number
from src.schemas import Campaign

REPO_ROOT = Path(__file__).resolve().parents[1]
TOGG_DOC = (REPO_ROOT / "data" / "raw" / "kuveyt-turk" / "products"
            / "arac-finansmanlari-togg-finansmani.txt")

# TOGG sayfasının tablo + SSS bölümlerinin çelişen çekirdeği (gerçek metinden
# alıntı). Ham dosya olmadan da testin koşabilmesi için gömülü tutulur.
TOGG_EXCERPT = (
    "Kasko/Satış Değeri Finansman Tutarının Taşıt Tutarına Oranı Vade Üst "
    "Sınırı (Ay) 0 - 2.500.000 TL %70 48 2.500.001 - 5.000.000 TL %50 36 "
    "5.000.001 - 6.500.000 TL %30 24 6.500.001 - 7.500.000 TL %20 12 "
    "7.500.001 TL ve üzeri %0 Kullandırım yapılmayacaktır. "
    "TOGG Finansmanı ile İlgili Sıkça Sorulan Sorular "
    "Kaç TL tutarında TOGG Finansmanı kullanılabilir? "
    "Değeri 2.500.001 ila 5.000.000 TL aralığındaki araçlar için maksimum %50 "
    "Değeri 5.000.001 ila 6.500.000 TL aralığındaki araçlar için maksimum %30 "
    "Değeri 6.000.001 ila 7.000.000 TL aralığındaki araçlar için maksimum %20 "
    "Değeri 7.000.001 TL ve üzeri aralığındaki araçlar için %0"
)


def _campaign(text: str) -> Campaign:
    """Kural ham metin üzerinden çalışır; alan çıkarımına ihtiyaç yok."""
    return Campaign(bank_slug="kuveyt-turk", raw_text=text,
                    source_url="https://www.kuveytturk.com.tr/kendim-icin/"
                               "finansmanlar/arac-finansmanlari/togg-finansmani")


def _band_kinds(text: str) -> list:
    return [c for c in detect(_campaign(text)) if c.kind == "celisen_tutar_bandi"]


class TestTrNumberMultiGroup(unittest.TestCase):
    """`parse_tr_number` çok gruplu binlik ayıracını çözmeli.

    Bu bir GERÇEK HATA düzeltmesiydi: "2.500.001" gibi 1 milyon üstü TR-biçimli
    tutarlar `None` dönüyordu (tek nokta grubu varsayılıyordu), yani şartnamenin
    manşet alanı `finansman_tutari` bu aralıkta hiç normalize edilemiyordu.
    """

    def test_iki_nokta_grubu(self):
        self.assertEqual(parse_tr_number("2.500.001"), 2500001.0)
        self.assertEqual(parse_tr_number("5.000.000"), 5000000.0)
        self.assertEqual(parse_tr_number("7.500.001"), 7500001.0)

    def test_ondalikli_cok_gruplu(self):
        self.assertEqual(parse_tr_number("1.234.567,89"), 1234567.89)

    def test_eski_davranis_korunuyor(self):
        """Tek nokta ayrımı bozulmadı: 3 hane binlik, 1-2 hane ondalık."""
        self.assertEqual(parse_tr_number("1.500"), 1500.0)
        self.assertEqual(parse_tr_number("2.05"), 2.05)
        self.assertEqual(parse_tr_number("1.500,00"), 1500.0)


class TestBandParsing(unittest.TestCase):
    """Bant ayrıştırıcı iki farklı yazımı da okumalı."""

    def test_tablo_yazimi(self):
        bands = _parse_bands("2.500.001 - 5.000.000 TL %50 36")
        self.assertEqual(len(bands), 1)
        self.assertEqual((bands[0].low, bands[0].high, bands[0].rate),
                         (2500001.0, 5000000.0, 50.0))

    def test_sss_yazimi_ila(self):
        bands = _parse_bands(
            "Değeri 6.000.001 ila 7.000.000 TL aralığındaki araçlar için maksimum %20")
        self.assertEqual(len(bands), 1)
        self.assertEqual((bands[0].low, bands[0].high, bands[0].rate),
                         (6000001.0, 7000000.0, 20.0))

    def test_ust_sinirsiz_bant(self):
        bands = _parse_bands("7.500.001 TL ve üzeri %0")
        self.assertEqual(len(bands), 1)
        self.assertEqual(bands[0].low, 7500001.0)
        self.assertEqual(bands[0].high, float("inf"))
        self.assertEqual(bands[0].rate, 0.0)

    def test_ters_bant_atlanir(self):
        """Alt sınır üst sınırdan büyükse (OCR/yazım hatası) kayıt alınmaz."""
        self.assertEqual(_parse_bands("5.000.000 - 2.500.000 TL %50"), [])


class TestToggContradiction(unittest.TestCase):
    """Gerçek vaka: TOGG sayfasında tablo ↔ SSS ayrışması."""

    def test_iki_celiski_yakalanir(self):
        found = _band_kinds(TOGG_EXCERPT)
        self.assertEqual(len(found), 2, f"beklenen 2 bulgu, gelen: {found}")
        rates = sorted(d for c in found for d in _rates_in(c.detail))
        self.assertEqual(rates, ["%0", "%20"])

    def test_ayni_bantlar_celiski_uretmez(self):
        """%50 ve %30 bantları TOGG metninde İKİ KEZ birebir aynı geçiyor.

        Bunlar aynı cetvelin iki yazımıdır; çelişki DEĞİL. Kural bunlarda
        sessiz kalmazsa her cetvel sayfası hayalet bulgu üretir.
        """
        details = " ".join(c.detail for c in _band_kinds(TOGG_EXCERPT))
        self.assertNotIn("%50", details)
        self.assertNotIn("%30", details)

    def test_kanit_alintisi_iki_tarafi_gosterir(self):
        found = _band_kinds(TOGG_EXCERPT)
        self.assertTrue(found)
        for c in found:
            self.assertEqual(len(c.evidence), 2)
            for e in c.evidence:
                self.assertTrue(e.raw_value, "kanıt alıntısı boş olmamalı")
                self.assertIsNotNone(e.span_start)
                self.assertEqual(e.bank_slug, "kuveyt-turk")

    @unittest.skipUnless(TOGG_DOC.is_file(), "ham TOGG belgesi repoda yok")
    def test_ham_belge_uzerinde_de_ayni_sonuc(self):
        """Gömülü alıntı değil, korpustaki GERÇEK dosya üzerinde doğrulama."""
        text = TOGG_DOC.read_text(encoding="utf-8")
        found = [c for c in detect(_campaign(text))
                 if c.kind == "celisen_tutar_bandi"]
        self.assertEqual(len(found), 2, f"beklenen 2 bulgu, gelen: {found}")


class TestGuards(unittest.TestCase):
    """Hayalet bulgu korumaları."""

    def test_ayrik_bantlar_celiski_uretmez(self):
        """Aynı oran ayrık bantlara verilebilir — meşru cetvel."""
        text = ("Ürün A: 0 - 1.000.000 TL %50 "
                "Ürün B: 2.000.000 - 3.000.000 TL %50")
        self.assertEqual(_band_kinds(text), [])

    def test_listeleme_sayfasi_atlanir(self):
        """Birden çok kampanyanın geçerlilik penceresi varsa sayfa listedir.

        Ölçüm: bu koruma olmadan korpusta 15 bulgunun 13'ü hayaletti (Kuveyt
        Türk kampanya liste sayfaları).
        """
        text = ("Kampanya 1 Ağustos 2026 - 31 Ağustos 2026 tarihleri arasında "
                "1.000.000 - 2.000.000 TL %5 "
                "Kampanya 1 Eylül 2026 - 30 Eylül 2026 tarihleri arasında "
                "1.500.000 - 2.500.000 TL %5")
        self.assertEqual(_band_kinds(text), [])

    def test_tek_bant_celiski_uretmez(self):
        self.assertEqual(_band_kinds("0 - 2.500.000 TL %70"), [])

    def test_acik_uclu_harcama_esikleri_celiski_uretmez(self):
        """Bağımsız kampanyaların harcama eşikleri cetvel DEĞİLDİR.

        Gerçek hayalet vakası (2026-08-03 Ağustos hasadı): Kuveyt Türk kampanya
        liste sayfalarında üç ayrı kampanyanın eşiği yan yana duruyor. Hepsi
        AÇIK UÇLU ("ve üzeri") ve tek bir kapalı aralık yok → cetvel yok →
        "iki cetvel çelişiyor" iddiası anlamsız. Bu koruma olmadan 6 hayalet
        bulgu üretiliyordu.
        """
        text = ("1.000 TL ve üzeri harcamanızda %5 iade "
                "2.000 TL ve üzeri her harcamanıza %5 iade "
                "20.000 TL ve üzeri toptancı harcamalarınızda ekstra %5 iade")
        self.assertEqual(_band_kinds(text), [])

    def test_cetvel_varsa_acik_uclu_kuyruk_da_degerlendirilir(self):
        """Kapalı aralıklar cetveli kanıtlıyorsa açık uçlu son bant da sayılır.

        TOGG'daki %0 çelişkisi tam olarak bu: iki taraf da açık uçlu
        ("7.500.001 TL ve üzeri" / "7.000.001 TL ve üzeri") ama belgede
        6 kapalı aralık var, yani gerçek bir cetvel söz konusu.
        """
        text = ("0 - 2.500.000 TL %70 2.500.001 - 5.000.000 TL %50 "
                "7.500.001 TL ve üzeri %0 "
                "Değeri 7.000.001 TL ve üzeri araçlar için %0")
        found = _band_kinds(text)
        self.assertEqual(len(found), 1)
        self.assertIn("%0", found[0].detail)

    def test_ayni_celiski_bir_kez_raporlanir(self):
        """Aynı bant çifti sayfada iki kez yazılsa da bulgu tekilleştirilir."""
        text = ("1.000.000 - 2.000.000 TL %20 "
                "1.500.000 - 2.500.000 TL %20 "
                "1.000.000 - 2.000.000 TL %20 "
                "1.500.000 - 2.500.000 TL %20")
        self.assertEqual(len(_band_kinds(text)), 1)


def _rates_in(detail: str) -> list[str]:
    import re

    return re.findall(r"%\d+(?:[.,]\d+)?(?= oranı)", detail)


if __name__ == "__main__":
    unittest.main()
