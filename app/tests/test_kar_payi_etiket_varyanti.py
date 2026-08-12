""""kâr oranı" da bir kâr payı etiketidir; işaretsiz sayı ise oran değildir.

İlgili: ../src/extraction/rules/extract.py (`_KAR_PAYI_ETIKET`,
        `_KAR_PAYI_ONCE_RE`, `_extract_kar_payi_ileri`)
        ./test_kar_payi_yon.py (ileri/geri yön), ./test_oran_tablosu_kanit.py

## Bu testlerin varlık sebebi — ÖLÇÜLDÜ (2026-08-12, gold.v2 + demo.db)

`kar_payi_orani` P=1,000 / R=0,333 idi: yakaladığında her zaman doğru, ama üç
vakadan ikisini KAÇIRIYORDU. Kaçırmalardan biri şuydu:

    "Enerya ihtiyaç Finansmanı kâr oranı aylık %3,99'dur."   -> None (gold 3.99)

Sebep, dosyanın İÇİNDEKİ bir tutarsızlıktı. `_ORAN_TABLOSU_BASLIK_RE` "payı"yı
zaten opsiyonel yapmış ve gerekçesini yazmıştı ("Bankalar farklı etiket
kullanıyor"), ama düz cümle desenleri `pay[ıi]`yi ZORUNLU tutuyordu. Aynı
belgede tablo başlığında kabul edilen terim, cümle içinde reddediliyordu.

### "payı" opsiyonel, ama "kâr" tek başına YETMEZ

`_KAR_PAYI_ONCE_RE`'de "oranı" da opsiyoneldir ("%2,05 kâr payı"). İkisini
birden serbest bırakmak "%20 kâr elde edin" gibi pazarlama cümlelerini
finansman oranı yapardı. Kural: **"payı" veya "oranı"ndan en az biri**.

### İşaretsiz değere makullük bandı

İleri desende `%` opsiyoneldir ("kâr oranı 3,99"). Tablo başlıklarında
etiketten hemen sonra veri satırı geldiği için ilk sayı etiketin değeri
sanılıyordu:

    "Finansman Tutarı Vade Aylık Kar Oranı 250-TL-40.000-TL"  -> 250

`%` taşıyan değer bu kapıya girmez — işaretin kendisi oran olduğunu söyler.

## Ölçülen sonuç

    kar_payi_orani F1  0,500 -> 0,800   (R 0,333 -> 0,667, P 1,000 KORUNDU)
    demo.db üretimi      28  -> 44 belge
        eklenen 17 (0,0 ×7 · 1,0 · 1,99 · 2,99 · 3,75 · 3,99 ×4 · 4,25 · 10,0)
        kaybolan 1 — ve o değer ZATEN YANLIŞTI: "kart hamil(ler)ine 30 gün
        önceden bildirilir" cümlesinden üretilen 30,0
"""

from __future__ import annotations

import unittest

from src.extraction.rules.extract import extract_kar_payi


def _deger(metin: str):
    f = extract_kar_payi(metin)
    return f.canonical_value if f else None


class TestEtiketVaryanti(unittest.TestCase):
    """"kâr oranı" / "kâr payı" / "kâr payı oranı" — üçü de kabul."""

    KABUL = {
        "kâr oranı (payı yok)": ("Enerya ihtiyaç Finansmanı kâr oranı aylık "
                                 "%3,99'dur.", 3.99),
        "kar oranı (şapkasız)": ("kar oranı %1,89 ile finansman", 1.89),
        "kâr payı oranı": ("kâr payı oranı %1,99 ile 36 ay vade", 1.99),
        "kâr payı (oranı yok)": ("%2,05 kâr payı ile taşıt finansmanı", 2.05),
    }

    def test_varyantlar_kabul_edilir(self):
        for ad, (metin, beklenen) in self.KABUL.items():
            with self.subTest(varyant=ad):
                self.assertEqual(_deger(metin), beklenen)

    def test_kar_tek_basina_yetmez(self):
        """"payı" ve "oranı"nın İKİSİ birden opsiyonel olamaz."""
        for metin in ("%20 kâr elde edin", "kâr elde edin %20",
                      "%50 kâr marjıyla satış"):
            with self.subTest(metin=metin):
                self.assertIsNone(
                    _deger(metin),
                    "yalnız 'kâr' geçen pazarlama cümlesi oran sanıldı")


class TestIsaretsizDegereMakullukBandi(unittest.TestCase):
    """`%` yoksa değer makul bantta (0–15) olmalı."""

    def test_tablo_basligindan_tutar_kapilmaz(self):
        metin = ("Finansman Tutarı Vade Aylık Kar Oranı "
                 "250-TL-40.000-TL (3 ay ertelemeli) 1-6 ay")
        self.assertIsNone(
            _deger(metin),
            "tutar aralığının başlangıcı (250) kâr payı oranı sanıldı")

    def test_isaretsiz_makul_deger_kabul_edilir(self):
        self.assertEqual(_deger("kâr oranı 3,99 olarak uygulanır"), 3.99)

    def test_isaretli_deger_banda_takilmaz(self):
        """`%` taşıyan değer kapıya hiç girmez — işaret kanıttır.

        Bant dışı bir yüzde varsa onu eleyecek olan başka kapılardır
        (`_YABANCI_KAVRAM_RE`, `_CEZA_BAGLAMI_RE`), bu değil.
        """
        f = extract_kar_payi("kâr payı oranı %0 kampanyası")
        self.assertIsNotNone(f, "'%0 kâr payı' meşru bir değerdir")
        self.assertEqual(f.canonical_value, 0.0)


class TestMevcutKapilarBozulmadi(unittest.TestCase):
    """Etiket gevşetildi diye kurulu ayrımlar düşmemeli."""

    def test_vade_orana_sizmaz(self):
        # "ile" bağlaçtır, aralık ayırıcı değil (bkz. `_BIRIM_SONEKLI`).
        self.assertEqual(
            _deger("kâr payı oranı %1,89 ile 120 aya kadar vade"), 1.89)

    def test_aralik_korunur(self):
        self.assertEqual(
            _deger("kâr payı oranı %1,99–%2,49 arasında değişir"),
            {"min": 1.99, "max": 2.49})

    def test_paylasim_orani_hala_reddedilir(self):
        # Banka/müşteri kâr BÖLÜŞÜMÜ, finansman oranı değil.
        self.assertIsNone(_deger("Hesabın kâr payı oranı %40'a %60'dır"))

    def test_devlet_katkisi_hala_reddedilir(self):
        self.assertIsNone(
            _deger("hem kâr payı hem de %20'ye kadar devlet katkısıyla"))


if __name__ == "__main__":                                # pragma: no cover
    unittest.main()
