"""Yüzde işaretinin ardındaki sayı TUTAR değildir.

İlgili: ../src/extraction/rules/_ortak.py (`_PARA_IFADESI`)
        ../src/extraction/rules/tutar.py (`_TUTAR_PAT`)

## Ölçülen yanlış pozitif

`turkiye-emlak-katilim--qr-temel-bankacilik-hizmetleri` belgesinde şu satır
var: *"Kapama (Türk Lirası Krediler) **Azami %2 TL** İşlem Başına"*. Banka
"%2" derken TL kolonuna taşmış; ifade bozuk bir ORAN yazımıdır. Sistem
oradan `finansman_tutari = 2 TL` çıkarıyordu — 2 TL'lik bir finansman tutarı
absürt ve gold da doğru olarak `absent` diyor.

Kök neden iki ayrı yerde aynıydı: para kalıplarının negatif geriye-bakışı
rakam, noktalama ve `:` yasaklıyordu ama **`%` yasaklamıyordu**.

## İki yer, çünkü ölçüldü

Düzeltme ilk olarak `_ortak._PARA_IFADESI`'ne konuldu — ama `finansman_tutari`
o kalıbı KULLANMIYOR, `tutar.py` kendi kalıbını taşıyor. Tek yere yazıp
"tamam" demek, düzeltmeyi yanlış yola koymak olurdu. Bu test iki yolu birden
korur ki ayrışma sessizce geri gelmesin.

## Ne ELENMEMELİ

Yasak yalnız PARA ifadesine konuldu. `_SAYI_BASI` değiştirilmedi: oran
modülleri onu kullanıyor ve orada `%` önce gelmesi tam olarak beklenen
şeydir ("%2,05"). Aşağıdaki karşı-örnekler bunu koruyor.
"""

from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.extraction.rules._ortak import _PARA_IFADESI
from src.extraction.rules.extract import extract_all

#: Canlı korpusta ölçülen üç vaka (2026-08-21, 7.032 alan taranarak).
#: Üçü de yanlıştı; meşru bir tutarı eleyen tek örnek bulunamadı.
YUZDE_TUTARI = (
    "Kapama (Türk Lirası Krediler) Azami %2 TL İşlem Başına",
    "Yıllık Ücret % 6,37 TL",
    "Komisyon %0,20125.000 TL",
)

#: Elenmemesi gereken gerçek tutarlar.
GERCEK_TUTAR = (
    "50.000 TL'ye kadar vade farksız finansman imkânı",
    "tahsis ücreti 1.500 TL olarak alınır",
    "Kâr payı oranı %2,05 ve azami finansman tutarı 250.000 TL",
)


class TestParaKalibi(unittest.TestCase):
    """`_ortak._PARA_IFADESI` — `tahsis_ucreti` / `odul_indirim` yolu."""

    def setUp(self) -> None:
        self.pat = re.compile(_PARA_IFADESI, re.IGNORECASE)

    def test_yuzdeden_sonra_tutar_yakalanmaz(self) -> None:
        for metin in YUZDE_TUTARI:
            with self.subTest(metin=metin[:40]):
                self.assertEqual(
                    [m.group(0) for m in self.pat.finditer(metin)], [],
                    "bozuk oran yazımı tutar sanılıyor")

    def test_gercek_tutar_hala_yakalanir(self) -> None:
        for metin in GERCEK_TUTAR:
            with self.subTest(metin=metin[:40]):
                self.assertTrue(self.pat.search(metin),
                                "kapı fazla hevesli: meşru tutar eleniyor")

    def test_ayni_cumlede_oran_ve_tutar_ayrilir(self) -> None:
        """"%2,05 ... 250.000 TL" — oran elenir, tutar kalır."""
        bulunan = [m.group(0) for m in self.pat.finditer(
            "Kâr payı oranı %2,05 ve azami finansman tutarı 250.000 TL")]
        self.assertEqual(len(bulunan), 1)
        self.assertIn("250.000", bulunan[0])


class TestFinansmanTutariYolu(unittest.TestCase):
    """`tutar.py` AYRI kalıp taşıyor — düzeltme oraya da gerekliydi."""

    def test_yuzde_tl_finansman_tutari_uretmez(self) -> None:
        metin = ("Ücret ve Masraflar Kapama (Türk Lirası Krediler) "
                 "Azami %2 TL İşlem Başına; Kalan toplam tutar Kapama")
        alanlar = [f for f in extract_all(metin)
                   if f.field_name == "finansman_tutari"]
        self.assertEqual(
            alanlar, [],
            "«%2 TL» hâlâ finansman tutarı olarak çıkarılıyor")

    def test_gercek_finansman_tutari_hala_cikariliyor(self) -> None:
        metin = ("Konut finansmanında azami finansman tutarı 1.250.000 TL "
                 "olarak uygulanır.")
        alanlar = [f for f in extract_all(metin)
                   if f.field_name == "finansman_tutari"]
        self.assertTrue(alanlar, "kapı meşru finansman tutarını da elemiş")
        self.assertEqual(alanlar[0].canonical_value,
                         {"value": 1250000.0, "currency": "TRY"})


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
