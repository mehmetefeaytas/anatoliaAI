"""Kâr payı oranı: orandan TÜRETİLMİŞ büyüklükler reddedilir.

İlgili: src/extraction/rules/extract.py (`_TUREV_ORAN_RE`, `_turev_oran_baglami`)
        docs/rapor/genel-denetim.md §"B. Vitrin sorusu yanlış cevap veriyor"

## Bu testin varlık sebebi

Demonun manşet sorusu "en düşük kâr payı hangi bankada?" ve o sıralama
doğrudan `kar_payi_orani` alanına dayanıyor. Denetimde üç desen ölçüldü
(`data/demo.db`, 70 kayıt): değer, oranın KENDİSİ değil ondan türetilen bir
büyüklüktü ve tabloya girip bankayı yanlış konumlandırıyordu.

Bu üç desen **ceza maddesi değildir** — `_CEZA_BAGLAMI_RE`'yi genişletmek
yanlış teşhis olurdu. Ortak ayırt edici işaret İYELİK EKİdir:

    "kâr payı oranı %5"      -> oranın kendisi        TUT
    "kâr payı oranının %5'i" -> orandan türetilmiş    REDDET
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.extraction.rules.extract import extract_kar_payi


def _oran(text: str):
    field = extract_kar_payi(text)
    return field.canonical_value if field else None


class TurevOranReddedilir(unittest.TestCase):
    """Korpustan alınmış gerçek metinler — üçü de sıralamaya giriyordu."""

    def test_sozel_yuzde_carpani(self):
        """Erken ödeme tazminatı formülünün sözel hâli (korpusta 4 kayıt)."""
        self.assertIsNone(_oran(
            "Kredinin yıllık bileşik kâr payı oranının yüzde 5'i ile kalan "
            "ağırlıklı ortalama vadenin çarpımı sonucu bulunan tutar"))

    def test_cebirsel_carpan(self):
        """Aynı formülün cebirsel yazımı (korpusta 3 kayıt)."""
        self.assertIsNone(_oran(
            "Tazminat, anapara üzerinden (Finansmanın yıllık bileşik kâr payı "
            "oranı * 0,05) + ( Kalan ağırlıklı ortalama vade * 0,01) olarak"))

    def test_kar_paylasim_payi(self):
        """Banka ile müşteri arasındaki kâr BÖLÜŞÜMÜ (korpusta 4 kayıt)."""
        self.assertIsNone(_oran(
            "Mevzuat gereği Kuveyt Türk'ün verdiği brüt kâr payının %50'si "
            "geri alınır. Ara dönemde oluşan kâr dağıtılmaz."))

    def test_yuzde_isaretli_iyelik(self):
        self.assertIsNone(_oran("akdi kâr payı oranının %30'u kadar tazminat"))


class GercekOranTUTULUR(unittest.TestCase):
    """Kapı fazla geniş olmamalı — bunlar sıralamaya GİRMELİ."""

    def test_bitişik_oran(self):
        self.assertEqual(
            _oran("Taşıt finansmanında %4.19 kar payı oranı ile sahip olun"),
            4.19)

    def test_iki_noktali_tablo_bicimi(self):
        self.assertEqual(
            _oran("Aylık Kar payı oranı : %1,20 Efektif Yıllık Oran : %23,52"),
            1.2)

    def test_sifir_oran_gecikme_cumlesi_ONCESINDE(self):
        """"akdi kâr payı oranı %0" GERÇEK orandır; sonraki cümle onu bozmaz."""
        self.assertEqual(_oran(
            "Bankamızca, akdi kâr payı oranı %0 olarak belirlenmiştir. "
            "Gecikme Cezası Oranı ayrıca belirlenir."), 0.0)

    def test_gercek_oran_turev_cumlesinden_ONCE(self):
        """Cümle sınırı disiplini: sonraki cümlenin türev ifadesi bulaşmamalı."""
        self.assertEqual(_oran(
            "Kâr payı oranı %1,89'dur. Kâr payı oranının yüzde 5'i tazminat "
            "olarak alınır."), 1.89)

    def test_araligin_kendisi_turev_degildir(self):
        self.assertEqual(
            _oran("kâr payı oranı %1,99 - %2,49 arasında değişmektedir"),
            {"min": 1.99, "max": 2.49})


if __name__ == "__main__":
    unittest.main()
