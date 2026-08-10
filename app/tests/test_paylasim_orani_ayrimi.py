"""Kâr PAYLAŞIM oranı `kar_payi_orani` DEĞİLDİR.

Katılma hesabında banka ile müşteri kârı bölüşür ("%40'a %60"). Bu bir
finansman maliyeti değil bir bölüşüm oranıdır; anotasyon tarafındaki karar
`kar_payi_orani = absent` (`data/gold/ANNOTATION_GUIDE.md`, biçim kartı §3
kural 7). Çıkarıcı bu kararı uygulamıyordu.

Ölçülmüş dedektör (`data/gold/review/_uyusmazlik-kaliplari.md` §2b):
**toplamı 100 eden iki yüzde + paylaşım fiili**. Dizgi araması ("paylaşım
oran") kullanılamaz — kalibrasyonda 3 isabetin 2'si gezinme menüsüne takıldı ve
en güçlü vaka kaçtı.

Bu dosya dedektörün üç yönünü kilitler: yakaladığı vakalar, yakalamaması
gereken (aşırı düzeltme) vakalar, ve biçim kuralları (tam sayı + bağlaç).
"""

import unittest

from src.extraction.rules.extract import (
    extract_kar_payi,
    paylasim_cifti_araliklari,
)


class PaylasimOraniReddedilir(unittest.TestCase):

    def _yok(self, metin: str) -> None:
        f = extract_kar_payi(metin)
        self.assertIsNone(
            f, f"beklenmedik oran: {f.canonical_value if f else None}")

    def test_tamlamasiz_en_guclu_vaka(self):
        # Kuveyt Türk, Altına Altın Katılma Hesabı. Belge "paylaşım oranı"
        # tamlamasını bu cümlede HİÇ kullanmıyor; dizgi araması kaçırırdı.
        # %40 "en yüksek kâr payı" sıralamasının tepesine çıkıyordu.
        self._yok(
            "Vade tarihinde tahakkuk eden kâr, hesap sahibi ile kurum "
            "arasında %40'a %60 şeklinde paylaşılır. Altına Altın Katılma "
            "Hesabı kâr payı oranı nedir? Hesabın kâr payı oranı %40'a "
            "%60'dır.")

    def test_iyelikli_baglac(self):
        self._yok("Ziynet Altın Katılma Hesabı kâr payı oranı %55'e %45'dir. "
                  "Kâr, banka ile müşteri arasında paylaşılır.")

    def test_tire_baglaci_ikinci_yuzde_isaretsiz(self):
        self._yok("Dijital Katılma Hesabı: %95-5'e varan avantajlı paylaşım "
                  "oranlarıyla birikiminizi değerlendirin. Kâr payı oranı bu "
                  "orandan hesaplanır.")

    def test_bolu_baglaci(self):
        self._yok("Katılma hesabı %98/2 kar paylaşım oranından açılır ve "
                  "kâr payı oranı buna göre belirlenir.")


class PaylasimOraniAsiriDuzeltmeKorumasi(unittest.TestCase):
    """Meşru oranlar düşmemeli — dedektörün 0 yanlış alarmı korunuyor."""

    def _oran(self, metin: str):
        f = extract_kar_payi(metin)
        self.assertIsNotNone(f, "meşru oran düştü")
        return f.canonical_value

    def test_gercek_sifir_kampanyasi(self):
        self.assertEqual(
            self._oran("Mobilden Türkiye Finanslı olanlar %0 kâr payı ile "
                       "50.000 TL'ye varan İhtiyaç Finansmanı kullanabilir."),
            0.0)

    def test_normal_oran(self):
        self.assertEqual(
            self._oran("Konut finansmanında kâr payı oranı %1,89'dan "
                       "başlayan oranlarla, 120 aya kadar vade."),
            1.89)

    def test_gercek_aralik_100_etmez(self):
        # 1,99 + 2,49 = 4,48. Gerçek oran çiftleri asla 100 etmez.
        self.assertEqual(
            self._oran("Taşıt finansmanı kâr payı oranı %1,99 - %2,49 "
                       "arasında, 48 aya kadar vade."),
            {"min": 1.99, "max": 2.49})

    def test_ondalik_virgul_baglac_sanilmaz(self):
        # "%1,99 ya da 25 Gün Blokeli %0" — virgül BAĞLAÇ değildir. Ondalığa
        # izin veren bir desen burada 1 + 99 = 100 okuyup belgeyi elerdi;
        # korpusta 18 belgede ölçüldü.
        self.assertEqual(
            self._oran("Ertesi Gün %1,99 ya da 25 Gün Blokeli %0 POS "
                       "fırsatı! Kâr payı oranı %1,99'dur."),
            1.99)

    def test_paylasim_fiili_olmayan_cift_belgeyi_elemez(self):
        # Fiil yoksa BELGE kapısı çalışmaz; yalnız çiftin İÇİNDEKİ değer
        # reddedilir. Belgedeki gerçek oran ayakta kalmalı.
        f = extract_kar_payi(
            "Vade dağılımı %40-%60 olarak tablolanmıştır. "
            "Kâr payı oranı %2,45'tir.")
        self.assertIsNotNone(f)
        self.assertEqual(f.canonical_value, 2.45)


class PaylasimCiftiBicimKurallari(unittest.TestCase):
    """Desenin ölçümden gelen iki biçim kuralı."""

    def test_toplami_100_olmayan_cift_sayilmaz(self):
        self.assertEqual(paylasim_cifti_araliklari("%20-%70 dağılımı"), [])

    def test_ondalikli_yuzde_cift_sayilmaz(self):
        self.assertEqual(
            paylasim_cifti_araliklari("aylık maliyet %2,98 - %97,02"), [])

    def test_virgul_baglac_degil(self):
        self.assertEqual(paylasim_cifti_araliklari("%1,99 komisyon"), [])

    def test_gecerli_cift_bulunur(self):
        self.assertEqual(len(paylasim_cifti_araliklari("oran %98-%2 olarak")), 1)


if __name__ == "__main__":
    unittest.main()
