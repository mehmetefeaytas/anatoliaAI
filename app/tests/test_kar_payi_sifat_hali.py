"""`kâr paylı` sıfat hâli de kâr payı etiketidir — ama pencere gevşemez.

İlgili: ../src/extraction/rules/extract.py (`_KAR_PAYI_ETIKET`,
        `_KAR_PAYI_ONCE_RE`), tests/test_kar_payi_yon.py

## Neden bu dosya var

Korpus taraması (19 Ağu 2026, 1.782 belge) `kar_payi_orani` alanının yalnız
**60 belgede** (%3,4) çıktığını gösterdi — senaryonun kalp alanı için düşük.
Metninde hem bir oran hem "kâr payı" geçtiği hâlde alan üretilmeyen **77
belge** vardı. Bunların bir sınıfı tek bir ek yüzünden kaçıyordu:

    "Kuveyt Türk Müşterilerine Özel %1,99 Oranlı Kar Paylı Taksitlendirme"

`_KAR_PAYI_ETIKET` yalnız "payı" ekini tanıyordu; "paylı" sıfat hâli aynı
terimdir ama desene girmiyordu. Ayrıca oran ile etiket arasına "Oranlı "
sözcüğü giriyordu ve geri yönlü pencere sadece boşluk kabul ediyordu.

## ÖLÇÜLMÜŞ YANLIŞ DENEME — tekrarlanmasın

İlk çözüm pencereyi 12 karakterlik serbest bir aralığa açmaktı. Anında
`test_kar_payi_yon.py::test_araya_kelime_girerse_kapilmaz` kırıldı:

    "%15 indirim ve kâr payı oranı %1,89"

Araya giren " indirim ve " TAM 12 karakter; gevşetme indirimin oranını kâr
payı oranı olarak kapıyordu. Doğru çözüm pencereyi büyütmek değil, araya
girmesine izin verilen sözcüğü ADIYLA saymaktı ("oranlı"). Bu dosya iki
kapıyı ayrı ayrı kilitler; biri kaldırılırsa diğeri hatayı tek başına
yakalayamaz.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.extraction.rules.extract import extract_kar_payi


def _deger(metin: str):
    f = extract_kar_payi(metin)
    return f.canonical_value if f else None


class TestSifatHaliTaninir(unittest.TestCase):
    """KAPI 1 — "kâr paylı" da etikettir, "kâr payı" kadar geçerli."""

    def test_korpus_basligi_birebir(self) -> None:
        self.assertEqual(_deger(
            "Kuveyt Türk Müşterilerine Özel %1,99 Oranlı Kar Paylı "
            "Taksitlendirme Fırsatı!"), 1.99)

    def test_diyakritikli_yazim(self) -> None:
        self.assertEqual(_deger("%2,69 Oranlı Kâr Paylı Taksitlendirme"), 2.69)

    def test_oranli_sozcugu_olmadan_da(self) -> None:
        self.assertEqual(_deger("%1,45 kâr paylı finansman"), 1.45)

    def test_eski_ek_bozulmadi(self) -> None:
        """"payı" ekinin davranışı birebir korunmalı."""
        self.assertEqual(_deger("%1,45 kâr payı"), 1.45)
        self.assertEqual(_deger("kâr payı oranı %2,05"), 2.05)


class TestPencereGevsemez(unittest.TestCase):
    """KAPI 2 — araya YALNIZ "oranlı" girebilir; serbest mesafe yok."""

    def test_indirim_orani_kapilmaz(self) -> None:
        """Yanlış denemenin kanıt cümlesi — 12 karakterlik pencere bunu kırdı."""
        self.assertEqual(_deger("%15 indirim ve kâr payı oranı %1,89"), 1.89)

    def test_baska_sozcuk_gecis_saglamaz(self) -> None:
        """"oranlı" beyaz listede; "iadeli" değil."""
        self.assertIsNone(_deger("%15 iadeli kâr paylı"))

    def test_cumle_siniri_asilmaz(self) -> None:
        self.assertIsNone(_deger("%15 indirim. Kâr paylı taksit imkânı"))

    def test_yuzde_isareti_zorunlu_kaldi(self) -> None:
        self.assertIsNone(_deger("120 ay kâr payı avantajı"))


if __name__ == "__main__":
    unittest.main()
