"""Aralık değerlerde sıralama anahtarı, alanın YÖNÜNE göre uç seçer.

İlgili: ../src/comparison/compare.py `_numeric_key` (:41)

## Bu testin varlık sebebi

`_numeric_key(field_name, value)` imzasında `field_name` alıyordu ama gövdede
HİÇ KULLANMIYORDU: aralıklarda her zaman `min` dönüyordu. Sonuç, `vade_ay`
gibi "yüksek iyi" bir alanda görünür bir yanlıştı — `{min: 12, max: 120}`
taşıyan bir kampanya arayüzde **12 ay** gibi görünüyordu, ürünün ilan ettiği
en uzun vade 120 iken.

Satır zaten `comparable=False` olduğu için sıralamaya girmiyordu, yani hata
sıralamayı bozmuyordu; GÖSTERİLEN SAYIYI bozuyordu. Bu daha sinsi bir
kusurdur: yanlış sıralama gözle yakalanır, yanlış tek sayı yakalanmaz.

İkiz fonksiyon `_composite_numeric` aynı ilkeyi doğru uyguluyordu
(`compare.py:290-295`). Bu test, iki yolun ayrışmasını kalıcı olarak kapatır.
"""

from __future__ import annotations

import unittest

from src.comparison.compare import (
    _HIGHER_IS_BETTER,
    _LOWER_IS_BETTER,
    _numeric_key,
    rank,
)


class AralikUcSecimi(unittest.TestCase):
    """Aralığın hangi ucu sıralama anahtarı olur."""

    def test_yuksek_iyi_alanda_UST_sinir(self) -> None:
        anahtar, kiyaslanabilir, not_ = _numeric_key("vade_ay", {"min": 12, "max": 120})
        self.assertEqual(anahtar, 120.0, "vade_ay yüksek-iyi: üst sınır beklenir")
        self.assertFalse(kiyaslanabilir)
        self.assertIn("aralık", not_ or "")

    def test_dusuk_iyi_alanda_ALT_sinir(self) -> None:
        anahtar, kiyaslanabilir, _ = _numeric_key(
            "kar_payi_orani", {"min": 1.99, "max": 2.49}
        )
        self.assertEqual(anahtar, 1.99, "kar_payi_orani düşük-iyi: alt sınır beklenir")
        self.assertFalse(kiyaslanabilir)

    def test_tahsis_ucreti_de_alt_sinir(self) -> None:
        anahtar, _, _ = _numeric_key("tahsis_ucreti", {"min": 500, "max": 2000})
        self.assertEqual(anahtar, 500.0)

    def test_finansman_tutari_ust_sinir(self) -> None:
        anahtar, _, _ = _numeric_key("finansman_tutari", {"min": 5000, "max": 150000})
        self.assertEqual(anahtar, 150000.0)

    def test_bilinmeyen_alan_UST_sinira_duser(self) -> None:
        """Yön tanımlı değilse davranış belirlenmiş olmalı, rastgele değil."""
        anahtar, _, _ = _numeric_key("bilinmeyen_alan", {"min": 1, "max": 9})
        self.assertEqual(anahtar, 9.0)

    def test_her_yonlu_alan_icin_uc_tutarli(self) -> None:
        """Yön kümelerindeki her alan doğru ucu seçmeli — tek tek değil, toplu."""
        for alan in _LOWER_IS_BETTER:
            with self.subTest(alan=alan, yon="düşük iyi"):
                self.assertEqual(_numeric_key(alan, {"min": 3, "max": 7})[0], 3.0)
        for alan in _HIGHER_IS_BETTER:
            with self.subTest(alan=alan, yon="yüksek iyi"):
                self.assertEqual(_numeric_key(alan, {"min": 3, "max": 7})[0], 7.0)


class DavranisKorundu(unittest.TestCase):
    """Aralık dışındaki yollar DEĞİŞMEDİ."""

    def test_aralik_hala_kiyas_disi(self) -> None:
        """Uç seçimi düzeldi diye aralık kıyaslanabilir OLMADI (CLAUDE.md §17)."""
        self.assertFalse(_numeric_key("vade_ay", {"min": 12, "max": 120})[1])

    def test_duz_sayi_etkilenmedi(self) -> None:
        self.assertEqual(_numeric_key("vade_ay", 36), (36.0, True, None))

    def test_dejenere_aralik_hala_duz_sayiya_iniyor(self) -> None:
        """{"min": X, "max": X} kıyaslanabilir bir sayıdır, aralık değil."""
        anahtar, kiyaslanabilir, not_ = _numeric_key("vade_ay", {"min": 36, "max": 36})
        self.assertEqual(anahtar, 36.0)
        self.assertTrue(kiyaslanabilir)
        self.assertIsNone(not_)

    def test_para_ve_masraf_yollari_etkilenmedi(self) -> None:
        self.assertEqual(
            _numeric_key("tahsis_ucreti", {"value": 500, "currency": "TRY"}),
            (500.0, True, None),
        )
        self.assertEqual(
            _numeric_key("masraf_durumu", {"has_fee": False, "amount": 0}),
            (0.0, True, None),
        )

    def test_aralik_satiri_siralamanin_SONUNDA_kaliyor(self) -> None:
        """Uç büyüdü diye aralık, kıyaslanabilir satırların önüne geçmemeli."""
        satirlar = [
            {"bank": "A", "bank_name": "A", "canonical_value": 24, "source_span": None},
            {
                "bank": "B",
                "bank_name": "B",
                "canonical_value": {"min": 12, "max": 120},
                "source_span": None,
            },
        ]
        sonuc = rank(satirlar, "vade_ay")
        self.assertEqual(
            [r.bank for r in sonuc],
            ["A", "B"],
            "aralık satırı 120 uç değerine rağmen sona alınmalı",
        )
        self.assertEqual(sonuc[1].sort_key, 120.0)


if __name__ == "__main__":
    unittest.main()
