"""Özet sayı kapısı — özetteki finansal sayı kaynakta BULUNMAK ZORUNDA.

İlgili: ../src/summarize/ozet.py (`_sayi_ihlali`, `SEBEP_SAYI`)
        ../docs/evren-servisi.md §10 (ölçüm), CLAUDE.md §19 (halüsinasyon yasağı)

## Bu kapı niçin var — ölçülmüş uydurma

Alfabe ve terminoloji kapılarının eşi. `SISTEM_PROMPT` "yalnız metinde geçen
bilgileri kullan" diyor; bu bir YÖNERGEDİR, kapı değil ve model ona
uymayabilir.

Ölçüldü (2026-08-24, 14 gerçek kampanya, `llm-large`): EVREN özetleri mevcut
özetlerin iki katı sayı içeriyordu ve bunların **%16'sı kaynak metinde
bulunamadı** (mevcut yerel özetlerde oran %0). Finansal bir panelde uydurulmuş
bir kâr payı oranı, jürinin ilk yakalayacağı hatadır.

## Ölçüt neden ÇIPLAK BASAMAK

İlk ölçüm `%3.54` ile `%3,54`yi farklı saydı ve EVREN'i %23 halüsinasyonla
suçladı — oysa çıplak rakamlar kaynakta VARDI, fark yalnız ondalık
ayırıcıdaydı (EVREN nokta yazıyor, Türkçe metin virgül). Kapı bu yüzden
biçimi değil BASAMAK DİZİSİNİ karşılaştırır. Biçim ihlali ayrı bir konudur ve
bu kapının işi değildir.

## Asimetri kasıtlı

Özet tarafında yalnız FİNANSAL desenler denetlenir (yüzde, tutar, vade);
kaynak tarafında ise metindeki TÜM sayılar toplanır. Gerekçe: kaynakta bir
oran tabloda çıplak dururken (`3,45`) özette yüzde işaretiyle geçebilir
(`%3,45`) — bu uydurma değildir. Ters yön daraltılırsa kapı geçerli özetleri
düşürürdü; yanlış eleme, yanlış kabulden pahalıdır.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

KOK = Path(__file__).resolve().parents[1]
if str(KOK) not in sys.path:
    sys.path.insert(0, str(KOK))

from src.summarize.ozet import (
    KALICI_SEBEPLER,
    SEBEP_SAYI,
    _sayi_ihlali,
)

KAYNAK = (
    "Kuveyt Türk Katılım Bankası konut finansmanı kampanyası. 120 ay vadeli "
    "finansmanda kâr payı oranı %1,89 olarak uygulanır. Asgari tutar "
    "50.000 TL, azami 1.500.000 TL'dir. Dosya masrafı 500 TL. Kampanya "
    "31 Aralık 2026 tarihine kadar geçerlidir."
)


class TestUydurmaYAKALIYOR(unittest.TestCase):
    """KAPI 1 — kaynakta hiç geçmeyen finansal sayı reddedilmeli."""

    def test_uydurulan_kar_payi_orani(self):
        ihlal = _sayi_ihlali("Kâr payı oranı %2,75 olarak uygulanır.", KAYNAK)
        self.assertIsNotNone(ihlal)
        self.assertIn("2,75", ihlal)

    def test_uydurulan_tutar(self):
        self.assertIsNotNone(
            _sayi_ihlali("Asgari tutar 75.000 TL olarak belirlenmiştir.", KAYNAK))

    def test_uydurulan_vade(self):
        self.assertIsNotNone(
            _sayi_ihlali("Finansman 96 ay vadeli sunulmaktadır.", KAYNAK))

    def test_ilk_ihlalde_durur_etiket_TEK(self):
        """Sebep alanına tek etiket yazılır, envanter değil (terminoloji eşi)."""
        ihlal = _sayi_ihlali("Oran %2,75 ve tutar 88.000 TL.", KAYNAK)
        self.assertIsNotNone(ihlal)
        self.assertNotIn("|", ihlal)


class TestMESRU_OZETE_DOKUNMUYOR(unittest.TestCase):
    """KAPI 2 — karşı-örnekler. Bu sınıf olmadan kapı sessizce her şeyi eler
    ve "0 ihlal" raporu kapının çalıştığı sanılır; oysa kapsam çökmüş olur.
    """

    MESRU = (
        "Kâr payı oranı %1,89, vade 120 ay.",
        "Asgari tutar 50.000 TL, azami 1.500.000 TL.",
        "Dosya masrafı 500 TL olarak alınmaktadır.",
        "120 ay vadeli konut finansmanında oran %1,89.",
        "Kampanya 31 Aralık 2026 tarihine kadar sürüyor.",
        "Kuveyt Türk konut finansmanı kampanyası duyurulmuştur.",
        "Belgede herhangi bir sayısal değer bulunmamaktadır.",
    )

    def test_mesru_ozetler_gecer(self):
        for ozet in self.MESRU:
            with self.subTest(ozet=ozet[:45]):
                self.assertIsNone(_sayi_ihlali(ozet, KAYNAK))

    def test_ONDALIK_AYIRICI_farki_ihlal_DEGIL(self):
        """`%1.89` biçim ihlalidir, uydurma DEĞİL — kapı onu düşürmemeli.

        Bu, ilk ölçümümüzü yanlışlayan tam senaryodur.
        """
        self.assertIsNone(_sayi_ihlali("Kâr payı oranı %1.89 uygulanır.", KAYNAK))

    def test_BINLIK_AYIRICI_farki_ihlal_DEGIL(self):
        self.assertIsNone(
            _sayi_ihlali("Asgari tutar 50000 TL olarak geçer.", KAYNAK))

    def test_bos_ozet_ve_bos_kaynak_patlamaz(self):
        self.assertIsNone(_sayi_ihlali("", KAYNAK))
        self.assertIsNone(_sayi_ihlali("Sayısız bir özet.", ""))


class TestKAYNAKTA_CIPLAK_duran_sayi(unittest.TestCase):
    """Asimetri sınavı: kaynakta çıplak, özette yüzdeli — uydurma DEĞİL."""

    def test_kaynakta_tabloda_ciplak_oran(self):
        kaynak = "Ürün tablosu: konut 1,89 | taşıt 2,45 | ihtiyaç 3,10"
        self.assertIsNone(_sayi_ihlali("Konut oranı %1,89 olarak geçer.", kaynak))


class TestSebepKoduVeKALICILIK(unittest.TestCase):

    def test_sebep_kodu_tanimli(self):
        self.assertEqual("sayi_dogrulanmadi", SEBEP_SAYI)

    def test_KALICI_DEGIL(self):
        """Sıcaklık merdiveninde yeniden denenebilir; kalıcı işaretlenmemeli.

        Kalıcı sayılsa belge sonsuza dek özetsiz kalırdı — oysa farklı bir
        sıcaklıkta model sayı uydurmadan özetleyebilir.
        """
        self.assertNotIn(SEBEP_SAYI, KALICI_SEBEPLER)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
