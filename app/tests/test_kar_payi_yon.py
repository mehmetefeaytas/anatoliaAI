"""Kâr payı oranı çıkarımı — iki yönlü arama ve birim koruması.

## Neden bu dosya var

Şartname §5.2'nin **manşet örneği** birebir şu: `"%2,05 kâr payı oranı"` —
sayı önce, anahtar kelime sonra. Şartnamenin A Bankası senaryosu da aynı
yapıda: *"özel %1,89 kâr payı oranı ile 120 aya kadar konut finansmanı"*.

31 Temmuz 2026'ya kadar `extract_kar_payi` yalnızca **ileri** bakıyordu ve
bu biçimi iki türlü ıskalıyordu:

    "%2,05 kâr payı oranı"                   -> hiçbir şey bulunamıyordu
    "%1,89 kâr payı oranı ile 120 aya kadar" -> 120.0 (VADEYİ oran sanıyordu)

İkincisi sessizce yanlış değer üreten sınıftan ve en ağırlıklı alanda
(`kar_payi_orani`, Model Başarısı %30) oluyordu.

Ayrıca birim koruması yalnız aralığın ikinci operandına uygulanmıştı; tek
değer korumasızdı ve Türkçe ekleri (`aya`, `aylık`) hesaba katmıyordu.

Korpus etkisi (849 belge): 54 -> 47 belge, makul olmayan değer 14 -> 9.
Azalma bir kayıp değil: elenen 7 kayıt vade/periyot/bölüşüm oranıydı.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.extraction.rules.extract import extract_kar_payi  # noqa: E402
from src.preprocessing.clean import normalize_text  # noqa: E402


def _ext(metin: str):
    alan = extract_kar_payi(normalize_text(metin))
    return alan.canonical_value if alan else None


class TestSayiOnceGelirse(unittest.TestCase):
    """Şartnamenin kendi ifade biçimi: sayı anahtar kelimeden önce."""

    def test_sartname_5_2_mansert_ornegi(self) -> None:
        self.assertEqual(_ext("%2,05 kâr payı oranı"), 2.05)

    def test_sartname_a_bankasi_senaryosu(self) -> None:
        """Vadeyi oran sanma hatası — en kritik regresyon."""
        self.assertEqual(
            _ext("özel %1,89 kâr payı oranı ile 120 aya kadar konut finansmanı"),
            1.89, "vade (120) oran olarak okundu")

    def test_oran_ve_devam_eden_cumle(self) -> None:
        self.assertEqual(_ext("%2,05 kâr payı oranı ile finansman"), 2.05)

    def test_kisa_bicim(self) -> None:
        self.assertEqual(_ext("%1,45 kâr payı"), 1.45)


class TestSayiSonraGelirse(unittest.TestCase):
    """Mevcut ileri yönlü davranış bozulmamalı."""

    def test_klasik_bicim(self) -> None:
        self.assertEqual(_ext("kâr payı oranı %2,05"), 2.05)

    def test_ek_alan_bicim(self) -> None:
        self.assertEqual(_ext("Kâr payı oranı %1,89'dan başlayan"), 1.89)

    def test_yuzde_isaretsiz(self) -> None:
        self.assertEqual(_ext("kâr payı oranı 2,05 seviyesinde"), 2.05)

    def test_aralik_korunur(self) -> None:
        self.assertEqual(_ext("kâr payı oranı %1,99 - %2,49 arası"),
                         {"min": 1.99, "max": 2.49})


class TestGeriYonluSikiTutulur(unittest.TestCase):
    """Geri yönlü arama gevşerse başka alanların değerini kapar."""

    def test_araya_kelime_girerse_kapilmaz(self) -> None:
        """'%15 indirim ve kâr payı oranı %1,89' -> indirim kapılmamalı."""
        self.assertEqual(_ext("%15 indirim ve kâr payı oranı %1,89"), 1.89)

    def test_yuzde_isareti_zorunlu(self) -> None:
        """Çıplak sayı geri yönde oran sayılmaz."""
        self.assertIsNone(_ext("120 ay kâr payı avantajı"))


class TestBirimKorumasi(unittest.TestCase):
    """Birim sözcüğü izleyen sayı oran değildir — Türkçe ekleriyle."""

    def test_aya_kadar_vade(self) -> None:
        self.assertIsNone(_ext("kâr payı oranlarıyla 36 aya kadar vade"))

    def test_aylik_periyot(self) -> None:
        self.assertIsNone(_ext("kâr payı ödemeleri 1 aylık periyotlarda"))

    def test_ay_ekleri(self) -> None:
        for metin in ("kâr payı oranı ve 24 ay vade",
                      "kâr payı ile 12 ayda ödeme",
                      "kâr payı oranları 48 aylık seçenek",
                      "kâr payı ve 5 yıla varan vade"):
            with self.subTest(metin=metin):
                self.assertIsNone(_ext(metin), f"{metin!r} birimli sayıyı oran saydı")

    def test_tam_sayi_tuketilir(self) -> None:
        """Geri izleme '36'dan '3' alıp birim kontrolünü atlatmamalı."""
        self.assertNotEqual(_ext("kâr payı oranlarıyla 36 aya kadar"), 3.0)


class TestPaylasimOraniAyriKavram(unittest.TestCase):
    """Katılma hesabında kâr BÖLÜŞÜMÜ, finansman oranı değildir."""

    def test_paylasim_orani_cikarilmaz(self) -> None:
        metin = ("Ziynet Altın Katılma Hesabı kâr payı paylaşım oranı "
                 "%55'e %45'dir.")
        self.assertIsNone(
            _ext(metin),
            "kâr paylaşım oranı (%55) finansman oranı olarak okundu — "
            "karşılaştırmada o bankayı en pahalı gösterirdi")

    def test_normal_oran_etkilenmez(self) -> None:
        self.assertEqual(_ext("konut finansmanı kâr payı oranı %1,89"), 1.89)


class TestBilinenSinir(unittest.TestCase):
    """Dürüst eksik kaydı — düzeltilmemiş vaka teste bağlanır.

    "Vakıf Katılım'ın kâr payı hem de %25'e kadar devlet desteğiyle"
    cümlesinde %25 devlet desteğidir, kâr payı oranı değil. Araya giren
    "hem de " ifadesi 15 karakterlik pencereye sığdığı için ayırt
    edilemiyor. Genel bir "araya kelime girmesin" kuralı, meşru
    "kâr payı oranı olarak %1,89" gibi ifadeleri de elerdi.
    """

    def test_devlet_destegi_hala_kapılabiliyor(self) -> None:
        metin = ("Vakıf Katılım'ın kâr payı hem de %25'e kadar devlet "
                 "desteğiyle birikim fırsatı")
        # Bugünkü davranışı KAYIT ALTINA alır; düzeltilirse test güncellenir.
        self.assertEqual(_ext(metin), 25.0)


if __name__ == "__main__":
    unittest.main()
