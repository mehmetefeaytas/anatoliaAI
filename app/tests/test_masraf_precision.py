"""`masraf_durumu` precision testleri — çıplak isim ücret kanıtı değildir.

## Neden bu dosya var

31 Temmuz 2026 korpus ölçümü (849 belge): `masraf_durumu` 370 çıkarım
üretiyordu ve bunların **158'i (%43) yanlış pozitifti**. Hepsi aynı kök
nedenden: `normalize_fee_status` "ücret/masraf/tahsis" kelimesinin
GEÇMESİNİ, ücret ALINDIĞININ kanıtı sayıyordu.

    "Uçak bileti ücreti dışında yapılan ödemeler kampanya kapsamı dışındadır"
    "kredi ve tahsis politikaları çerçevesinde"
    "Masrafları görüntüleyin ve onay verin"

Üçü de `{"has_fee": True}` okunuyordu. Etkisi tek alanla sınırlı değildi:
`contradiction.detect()` bunları hayalet çelişki üretmekte kullanıyor,
karşılaştırma da bankayı haksız yere pahalı gösteriyordu.

Bu, daha önce bir kez düzeltilmiş olan işaret-ters hatasının
('ÜCRETSİZ' -> has_fee=True) aynı sınıfı: kelimenin varlığını kanıt sanmak.
Bu testler o sınıfın geri gelmesini engeller.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.extraction.rules.extract import (  # noqa: E402
    _truncate_at_next_column,
    extract_masraf,
)
from src.normalization.normalize import normalize_fee_status  # noqa: E402


class TestCiplakIsimKanitDegil(unittest.TestCase):
    """Kanıtsız bahis: ücret olduğunu da olmadığını da söylemez -> None."""

    KANITSIZ = [
        "Ücret Tarifesi",
        "Ücretler ve Komisyonlar",
        "kredi ve tahsis politikaları çerçevesinde değerlendirilir",
        "Masrafları görüntüleyin ve onay verin",
        "Uçak bileti ücreti dışında yapılan ödemeler kampanya kapsamı dışındadır",
        "Tahsis süreci hakkında bilgi alın",
    ]

    def test_kanitsiz_bahis_none_doner(self) -> None:
        for metin in self.KANITSIZ:
            with self.subTest(metin=metin):
                self.assertIsNone(
                    normalize_fee_status(metin),
                    f"{metin!r} ücret kanıtı sayıldı — çıplak isim yeterli olmamalı")

    def test_kanitsiz_bahisten_alan_uretilmez(self) -> None:
        """Uçtan uca: çıkarıcı da bu metinlerden alan üretmemeli."""
        for metin in self.KANITSIZ:
            with self.subTest(metin=metin):
                self.assertIsNone(extract_masraf(metin))


class TestOlumluKanit(unittest.TestCase):
    """Tutar, oran ya da tahsil fiili -> has_fee=True."""

    def test_tutar_kaniti(self) -> None:
        r = normalize_fee_status("tahsis ücreti 500 TL")
        self.assertEqual(r, {"has_fee": True, "amount": 500.0})

    def test_oran_kaniti(self) -> None:
        r = normalize_fee_status("tahsis ücreti %0,5 oranında")
        self.assertIsNotNone(r)
        self.assertTrue(r["has_fee"])

    def test_tahsil_fiili_kaniti(self) -> None:
        for metin in ("tahsis ücreti alınır",
                      "dosya masrafı tahsil edilir",
                      "işlem ücrete tabidir",
                      "hesap işletim ücreti uygulanır",
                      "kart ücreti yansıtılır"):
            with self.subTest(metin=metin):
                r = normalize_fee_status(metin)
                self.assertIsNotNone(r, f"{metin!r} kanıt sayılmadı")
                self.assertTrue(r["has_fee"], f"{metin!r} has_fee=True vermeli")


class TestNegasyonBozulmadi(unittest.TestCase):
    """Düzeltme, çalışan negasyon mantığını bozmamalı."""

    def test_sifat_negasyonu(self) -> None:
        for metin in ("masrafsız", "ÜCRETSİZ", "Masrafsız kampanya",
                      "dosya masrafı yok"):
            with self.subTest(metin=metin):
                self.assertEqual(normalize_fee_status(metin),
                                 {"has_fee": False, "amount": 0.0})

    def test_fiil_negasyonu(self) -> None:
        for metin in ("tahsis ücreti alınmaz",
                      "dosya masrafı talep edilmez",
                      "kart ücreti yansıtılmayacaktır",
                      "yıllık kart ücreti yoktur"):
            with self.subTest(metin=metin):
                r = normalize_fee_status(metin)
                self.assertIsNotNone(r, f"{metin!r} negasyon kaçtı")
                self.assertFalse(r["has_fee"], f"{metin!r} has_fee=False vermeli")

    def test_negasyon_tahsil_fiilini_yener(self) -> None:
        """'alınmaz' hem negasyon hem 'alın' kökü içerir; negasyon kazanmalı."""
        r = normalize_fee_status("tahsis ücreti alınmaz")
        self.assertEqual(r, {"has_fee": False, "amount": 0.0})

    def test_masraf_hic_gecmiyorsa_none(self) -> None:
        self.assertIsNone(normalize_fee_status("Kâr payı oranı %1,89"))
        self.assertIsNone(normalize_fee_status(""))
        self.assertIsNone(normalize_fee_status(None))


class TestTabloSutunSiniri(unittest.TestCase):
    """İleri pencere komşu sütunun sayısını yutmamalı."""

    def test_pencere_sonraki_sutun_basliginda_kesilir(self) -> None:
        p = _truncate_at_next_column("Tahsis Ücreti Yıllık Maliyet Oranı 100.000 TL")
        self.assertNotIn("100.000", p)
        self.assertIn("Tahsis", p)

    def test_baslik_yoksa_pencere_korunur(self) -> None:
        metin = "tahsis ücreti 750 TL"
        self.assertEqual(_truncate_at_next_column(metin), metin)

    def test_tablo_basligindan_hayali_tutar_uretilmez(self) -> None:
        """Gerçek korpustan: finansman tutarı sütunu ücret sanılıyordu."""
        tablo = ("Finansman Tutarı Vade Kâr Oranı Tahsis Ücreti "
                 "Yıllık Maliyet Oranı 100.000 TL 36 Ay 2,49%")
        alan = extract_masraf(tablo)
        if alan is not None and isinstance(alan.canonical_value, dict):
            tutar = alan.canonical_value.get("amount")
            self.assertNotEqual(tutar, 100000.0,
                                "komşu sütunun finansman tutarı ücret sanıldı")

    def test_gercek_ucret_hala_cikariliyor(self) -> None:
        """Düzeltme aşırıya kaçıp doğru tutarları elememeli."""
        alan = extract_masraf("Konut finansmanında tahsis ücreti 750 TL'dir.")
        self.assertIsNotNone(alan)
        self.assertEqual(alan.canonical_value["amount"], 750.0)


class TestBilinenSinir(unittest.TestCase):
    """Dürüst eksik kaydı — düzeltilemeyen vaka teste bağlanır.

    Tetikleyici başlık satırının SONUNDAysa ardından gelen ilk sayı veri
    satırının ilk hücresidir ve arada kesilecek bir başlık yoktur. Bunu
    bir tutar eşiğiyle bastırmak, konut finansmanındaki gerçek
    "Ücretler Toplamı 28.076,27" değerini de elerdi; uydurma eşik yerine
    sınır dokümante ediliyor.
    """

    def test_baslik_sonundaki_tetikleyici_hala_yaniltabiliyor(self) -> None:
        tablo = ("Vade Kar Oranı Taksit Tutarı Finansman Tahsis Ücreti "
                 "30.000,00 ₺ 12 Ay 1,69%")
        alan = extract_masraf(tablo)
        # Bugünkü davranışı KAYIT ALTINA alır; düzeltilirse test güncellenir.
        self.assertIsNotNone(alan, "bu vaka bugün alan üretiyor")


if __name__ == "__main__":
    unittest.main()
