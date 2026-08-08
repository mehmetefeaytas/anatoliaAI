"""`masraf_durumu` iki sıralama yolunda AYNI kararı vermeli.

İlgili: ../src/comparison/compare.py (`_numeric_key`, `_composite_numeric`),
        ../web/app/components/FairnessNotice.tsx (arayüzdeki vaat)

## Neden bu dosya var — ölçülmüş yanlış cevap

`_numeric_key` `{"has_fee": True, "amount": None}` değerini **0,0** sayıyordu
ve `comparable=True` işaretliyordu. `masraf_durumu` "düşük daha iyi" alanı
olduğu için 0,0 sıralamanın **tepesidir**.

Sonuç, demonun manşet ekranında görünüyordu: kanıt metninde *"1.000 TL
başvuru ücreti tahsil edilecektir"* yazan bir kampanya, "En Düşük Masraf"
sıralamasında gerçekten ücretsiz olanların **önünde** duruyordu.
Ölçüldü: `sort_key == 0.0` olan 509 satırın **35'i** ücretliydi.

İkiz fonksiyon `_composite_numeric` bunu zaten doğru yapıyordu. Yani ilke
doğru yazılmış, tek alanlı yola uygulanmamıştı — ve `rank()` dashboard ile
chatbot'un kullandığı yoldur.

Bu testler iki yolu **birbirine bağlar**: biri değişirse diğeri kırılır.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.comparison import compare

#: Üç kanonik masraf durumu ve beklenen kıyaslanabilirlik.
VAKALAR = [
    ({"has_fee": False, "amount": 0.0}, True,  "gerçekten ücretsiz"),
    ({"has_fee": True, "amount": 750.0}, True, "ücret var ve biliniyor"),
    ({"has_fee": True, "amount": None}, False, "ücret var, tutarı YOK"),
]


class TestMasrafSifirSayilmaz(unittest.TestCase):
    """Tutarı bilinmeyen ücret 0 TL gibi sıralanamaz."""

    def test_tutari_bilinmeyen_ucret_KIYASLANAMAZ(self) -> None:
        deger, kiyas, not_ = compare._numeric_key(
            "masraf_durumu", {"has_fee": True, "amount": None})
        self.assertIsNone(deger, "sıralama anahtarı üretilmemeli")
        self.assertFalse(kiyas, "kıyaslanabilir işaretlenmemeli")
        self.assertIsNotNone(not_, "sebep yazılmalı — kullanıcı neden bilmeli")

    def test_gercekten_ucretsiz_HALA_sifir(self) -> None:
        """Düzeltme, meşru sıfırı bozmamalı."""
        deger, kiyas, _ = compare._numeric_key(
            "masraf_durumu", {"has_fee": False, "amount": 0.0})
        self.assertEqual(deger, 0.0)
        self.assertTrue(kiyas)

    def test_bilinen_tutar_KORUNUR(self) -> None:
        deger, kiyas, _ = compare._numeric_key(
            "masraf_durumu", {"has_fee": True, "amount": 750.0})
        self.assertEqual(deger, 750.0)
        self.assertTrue(kiyas)


class TestIkiYolAyniKarariVerir(unittest.TestCase):
    """Parite: `_numeric_key` ile `_composite_numeric` ayrışmamalı.

    Ayrışma bu kusurun kök nedeniydi — doğru semantik bir yolda kilitliydi,
    karşı semantik diğer yolda serbest.
    """

    def test_kiyaslanabilirlik_karari_ortusur(self) -> None:
        for deger, beklenen_kiyas, ad in VAKALAR:
            with self.subTest(vaka=ad):
                _, kiyas, _ = compare._numeric_key("masraf_durumu", deger)
                bilesik, sebep = compare._composite_numeric(
                    "masraf_durumu", deger)
                self.assertEqual(
                    kiyas, beklenen_kiyas,
                    f"_numeric_key {ad!r} vakasında yanlış karar verdi")
                self.assertEqual(
                    bilesik is not None, beklenen_kiyas,
                    f"_composite_numeric {ad!r} vakasında ayrıştı")
                # Skorlanamayan vakada İKİ yol da sebep yazmalı.
                if not beklenen_kiyas:
                    self.assertIsNotNone(sebep)


class TestSiralamaTepesindeUcretliYok(unittest.TestCase):
    """Uçtan uca: sıralamanın en iyi ucunda tutarsız ücret bulunmamalı."""

    def test_sifir_anahtarli_satirlarin_hicbiri_ucretli_degil(self) -> None:
        satirlar = [
            {"bank": "a", "bank_name": "A", "canonical_value":
             {"has_fee": True, "amount": None}, "source_span": "1.000 TL ücret"},
            {"bank": "b", "bank_name": "B", "canonical_value":
             {"has_fee": False, "amount": 0.0}, "source_span": "ücretsiz"},
        ]
        sirali = compare.rank(satirlar, "masraf_durumu")
        sifirlar = [r for r in sirali if r.sort_key == 0.0]
        for r in sifirlar:
            self.assertNotEqual(
                (r.value or {}).get("has_fee"), True,
                "ücretli bir kayıt sıralamanın en avantajlı ucunda")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
