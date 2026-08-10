"""`finansman_tutari` tetikleyicisi finansmana ÇAPALI olmak zorunda.

Ölçülmüş kusur (2026-08-10, `data/demo.db`, 1774 belge): güven kapısını
(`comparison/compare.py`, eşik 0,65) geçen 237 `finansman_tutari` kaydının
132'si çıplak `tutar`/`limit` tetikleyicisinden, 54'ü de **kredi KARTI**
bağlamından geliyordu. Hepsi 0,95 güvenle — yani güven kapısı bu sınıfı
göremez, çünkü çıkarıcı kendinden emin. Düzeltme çıkarım katmanında.

Bu dosya iki yönü birden kilitler:
  * YANLIŞ alan artık üretilmiyor (aşağıdaki `Reddedilenler`),
  * MEŞRU kayıtlar düşmedi (`Korunanlar`) — aşırı düzeltme koruması.

Kanıt pencerelerinin tamamı korpustan birebir alındı.
"""

import unittest

from src.extraction.rules.extract import extract_tutar


class TutarCapasiReddedilenler(unittest.TestCase):
    """Finansmana çapalı olmayan tetikleyici artık tutar üretmez."""

    def _yok(self, metin: str) -> None:
        f = extract_tutar(metin)
        self.assertIsNone(
            f, f"beklenmedik değer: {f.canonical_value if f else None}")

    def test_kazanim_tavani(self):
        # Ödül tavanı finansman tutarı değil (korpusta 11 belge).
        self._yok("Kampanyadan maksimum kazanım tutarı 500 TL'dir.")

    def test_indirim_tavani(self):
        self._yok("Müşteri bazlı toplam indirim tutarı 1.000 TL'yi aşmayacaktır.")

    def test_iade_tavani(self):
        self._yok("Kampanya kapsamında kazanılabilecek maksimum iade "
                  "tutarı 1000 TL'dir.")

    def test_odenecek_toplam_tutar(self):
        # Toplam geri ödeme, §5.5'te AYRI bir kavram: finansman maliyeti.
        self._yok("Aylık maliyet %2,58, yıllık maliyet %77,2551. "
                  "Ödenecek toplam tutar: 133.746,12 TL.")

    def test_hesap_acilis_asgarisi(self):
        self._yok("Hesap açılışı için gereken minimum tutar 50.000 TL'dir.")

    def test_teminat_mektubu_limiti(self):
        self._yok("Mektup tutarı üst limiti 15.000.000 TL'dir.")

    def test_atm_para_cekme_limiti(self):
        self._yok("Banka kartınızla günlük para çekme limiti 25.000 TL'dir.")

    def test_kredi_karti_harcama_esigi(self):
        # "kredi kartı" bir ödeme aracıdır; yanındaki tutar harcama eşiğidir.
        self._yok("Miles&Smiles Kuveyt Türk kredi kartınız ile 1.000 TL ve "
                  "üzeri harcamanıza 10.000 Mil'e varan fırsat.")

    def test_kredi_karti_odulu(self):
        self._yok("İlk Ek Kredi Kartınıza 1.000 TL Bankkart Lira!")

    def test_aylik_taksit_tutari(self):
        self._yok("Oranı kendim gireceğim. Aylık Taksit Tutarı 11.349,76 TL")


class TutarCapasiKorunanlar(unittest.TestCase):
    """Meşru finansman tutarları düşmedi — aşırı düzeltme koruması."""

    def _deger(self, metin: str):
        f = extract_tutar(metin)
        self.assertIsNotNone(f, "meşru kayıt düştü")
        self.assertEqual(f.field_name, "finansman_tutari")
        return f.canonical_value["value"]

    def test_finansman_tutari_duz(self):
        self.assertEqual(
            self._deger("Özellikler Finansman tutarı 50.000 TL'ye kadar olan "
                        "ödemelerinizi 36 aya kadar taksitlendirin."),
            50000.0)

    def test_finansman_tutari_iyelik_ekli(self):
        self.assertEqual(
            self._deger("Finansman tutarının 125.000 TL'ye kadar olması "
                        "durumunda maksimum vade 36 aydır."),
            125000.0)

    def test_tablo_basligi_tutar_kuyrugu_yutulur(self):
        # "Finansman Tutarı" tek parça tetikleyicidir; kuyruk olmasa
        # 20 karakterlik boşluk "Tutarı Kar Oranı Vade "yi aşar ve bu
        # DOĞRU kayıt kaybolurdu.
        self.assertEqual(
            self._deger("Finansman Oranları Finansman Tutarı Kar Oranı Vade "
                        "150.000 TL % 1,60 12 Ay"),
            150000.0)

    def test_urun_adi_capa_sayilir(self):
        self.assertEqual(
            self._deger("Enerya İhtiyaç Finansmanı, maksimum 250.000 TL ve "
                        "36 ay vade ile sınırlıdır."),
            250000.0)

    def test_finansman_ust_limiti(self):
        self.assertEqual(
            self._deger("Söz konusu ürün kapsamında firma başına finansman "
                        "üst limiti 5.000.000 TL'dir."),
            5000000.0)

    def test_kullandirim_limiti(self):
        # "kullandırım" katılım bankacılığında finansmanın kendisini adlandırır.
        self.assertEqual(
            self._deger("İşlem bazlı kullandırım limiti en fazla "
                        "5.000.000 TL'dir."),
            5000000.0)

    def test_kredi_limiti_kart_degil(self):
        # "kredi limiti" meşrudur; reddedilen yalnız "kredi KARTI".
        self.assertEqual(
            self._deger("Kampanya kapsamında tahsis edilebilecek maksimum "
                        "kredi limiti tutarı 3.000.000 TL'dir."),
            3000000.0)

    def test_aralik_ust_siniri_korundu(self):
        # `tom-katilim` hesaplama aracı: aralığın ÜST sınırı kanonik.
        self.assertEqual(
            self._deger("Finansman Tutarı TL 5.000 TL 150.000 TL Vade Ay"),
            150000.0)


if __name__ == "__main__":
    unittest.main()
