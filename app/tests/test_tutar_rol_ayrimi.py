"""`finansman_tutari` ROL AYRIMI — dört farklı şey aynı kolona yazılıyordu.

İlgili: ../src/extraction/rules/tutar.py · ../src/extraction/rules/kar_payi.py
        (`_bozuk_hesaplama_araci`)

## Bu testin varlık sebebi

Jüri canlı sistemde *"hangi bankada en düşük konut finansmanı var"* diye sordu
ve cevap **"Türkiye Emlak Katılım — 100 TL"** oldu. Sebep tek bir regex kusuru
değil, `finansman_tutari` kolonunun **dört ayrı rolü** aynı yere yazmasıydı
(ölçüldü, canlı korpus):

| değer | kanıt | gerçek rol |
|---|---|---|
| 100 TL | `"Taksit Tutarı: 100TL … Finansman Tutarı: 100TL"` | boş hesaplama aracı yer tutucusu |
| 250 TL | `"pratik finansman kart ile asgari 250 TL, 125.000 TL'ye kadar"` | kart ALT limiti |
| 125.000 TL | `"125.000 TL ve altında ise 36 ay"` | vade kademesi EŞİĞİ |
| 1.250.000 TL | `"en fazla 1.250.000 TL'dir"` | gerçek üst sınır ✓ |

Yalnız dördüncüsü bu alana aittir. Karşılaştırma motoru "en düşük" sorusunu
`min` alarak cevapladığı için hata TAM OLARAK en görünür yerde patlıyordu:
sıralamanın başına bir yer tutucusu ya da bir kart alt limiti geçiyordu.

## Her desen için hem pozitif hem KARŞI-ÖRNEK

Üç korumanın hepsi gevşetme değil daraltmadır, yani her biri meşru bir kaydı
düşürme riski taşır. Bu yüzden her sınıfta iki test var: kalıbın tuttuğu vaka
ve tutmaMASI gereken en yakın komşusu. Karşı-örnekler uydurma değil, hepsi
canlı korpustan (`data/raw`, 1782 belge) ya da gold setinden geliyor —
`albaraka--eviniz-icin-prefabrik` kaydı ilk deneme sürümünde GERÇEKTEN
kırılmıştı (bkz. `_KADEME_ISE_RE` başlığı).
"""

from __future__ import annotations

import unittest

from src.extraction.rules.kar_payi import (
    _ayni_deger_cok_etiket,
    _bozuk_hesaplama_araci,
    extract_kar_payi,
)
from src.extraction.rules.tutar import extract_tutar


def _deger(metin: str):
    """`extract_tutar`in kanonik sayısal değeri (yok ise None)."""
    alan = extract_tutar(metin)
    if alan is None:
        return None
    kanon = alan.canonical_value
    return kanon.get("value") if isinstance(kanon, dict) else kanon


class AralikUstSinirTest(unittest.TestCase):
    """(1) Ayıraç listesi eksikti → aralığın ALT sınırı kanonik kalıyordu."""

    def test_dort_uyeli_aile_ust_siniri_dondurur(self):
        # Dördü de ESKİ kalıpla alt sınır döndürüyordu. Ayıraçlar farklı
        # (virgül / tire+sözcük) ama sınıf aynı: "asgari X, azami Y".
        aile = {
            "Pratik Finansman Kart ile asgari 250 TL, azami 150.000 TL "
            "finansman kullanılabilmektedir.": 150000.0,
            "Finansman tutarı asgari 250 TL - azami 150.000 TL arasındadır.":
                150000.0,
            "Finansman tutarı minimum 5.000 TL, maksimum 500.000 TL olabilir.":
                500000.0,
            "Finansman tutarı en az 5.000 TL, en fazla 500.000 TL olabilir.":
                500000.0,
        }
        for metin, beklenen in aile.items():
            with self.subTest(metin=metin[:48]):
                self.assertEqual(_deger(metin), beklenen)

    def test_canli_kart_alt_limiti_ust_sinira_yukselir(self):
        # data/raw/albaraka/products/ihtiyac-pratik-finansman-kart.txt
        # ÖNCE 250 (kart alt limiti) — SONRA 125.000 (ürünün tavanı).
        metin = ("Pratik finansman kart nedir? Pratik finansman kart ile asgari "
                 "250 TL, 125.000 TL'ye kadar 2 ay ödemesiz dönem seçeneği ile "
                 "finansman kullanabilirsiniz.")
        self.assertEqual(_deger(metin), 125000.0)

    def test_karsi_ornek_tek_degerli_alt_sinir_BOZULMAZ(self):
        # Üst sınır İLAN EDİLMEMİŞSE alt sınır kanoniktir; yükseltme
        # yapılacak ikinci bir tutar yok. Kılavuz: "tek değerli bir vaka
        # aralık sayılmaz".
        metin = ("Pratik finansman kart ile asgari 250 TL finansman "
                 "kullanabilirsiniz.")
        self.assertEqual(_deger(metin), 250.0)

    def test_karsi_ornek_virgulden_sonraki_KUCUK_tutar_kanonigi_degistirmez(self):
        # Virgül ayıracı gevşetildi; koruma "ikinci tutar BÜYÜK olmalı"
        # koşulu. Aksi hâlde ardından gelen bir masraf kalemi tavanı ezerdi.
        metin = ("Konut finansmanı tutarı en fazla 1.250.000 TL, 3.000 TL "
                 "tahsis ücreti ile kullandırılır.")
        self.assertEqual(_deger(metin), 1250000.0)

    def test_gercek_ust_sinir_tek_basina_korunur(self):
        metin = "Kentsel dönüşüm finansmanı tutarı en fazla 1.250.000 TL'dir."
        self.assertEqual(_deger(metin), 1250000.0)


class VadeKademesiEsigiTest(unittest.TestCase):
    """(2) Koruma doğruydu ama TEK ÇEKİME kilitliydi."""

    def test_ve_altinda_ise_cekimi_elenir(self):
        # data/raw/vakif-katilim/products/kendim-icin-detay-ihtiyac-finansmani
        # ÖNCE 125.000 (vade eşiği) — SONRA null.
        metin = ("Yasal düzenlemeler sonrasında kullanılan ihtiyaç finansmanı "
                 "125.000 TL ve altında ise 36 ay, 125.000 TL ve 250.000 TL "
                 "arasında ise 24 ay, 250.000 TL üzerinde ise 12 aydır.")
        self.assertIsNone(extract_tutar(metin))

    def test_olmasi_durumunda_cekimi_hala_elenir(self):
        # Kontrol testi: eski üç kol bozulmadı.
        metin = ("Finansman tutarının 125.000 TL'ye kadar olması durumunda "
                 "maksimum vade 36 aydır.")
        self.assertIsNone(extract_tutar(metin))

    def test_karsi_ornek_prefabrik_kaydi_BOZULMAZ(self):
        # gold.round1 `albaraka--eviniz-icin-prefabrik`, gold 50.000.
        # İlk deneme sürümü bu kaydı kırdı: kademe işareti PENCEREDE arandığı
        # için İKİNCİ 50.000'e ait "üstünde ise" birinci adayı da eliyordu.
        # Çapalı kalıp ayrımı kurar.
        metin = ("Prefabrik ev satın alma ihtiyacınız varsa Albaraka sizinle. "
                 "Özellikler Finansman tutarı 50.000 TL'ye kadar olan "
                 "ödemelerinizi 36 aya, 50.000 TL üstünde ise 24 aya kadar "
                 "vadelendirebilirsiniz.")
        self.assertEqual(_deger(metin), 50000.0)

    def test_karsi_ornek_ise_YOKSA_kademe_sayilmaz(self):
        # "ve altındaki harcamalar" bir harcama bandıdır, koşul-sonuç kurgusu
        # değil; `ise` sözcüğü olmadan kalıp tutmamalı.
        metin = ("Kampanya kapsamında finansman tutarı 40.000 TL ve altındaki "
                 "başvurular için 6 ay ödemesiz dönem sunulur.")
        self.assertEqual(_deger(metin), 40000.0)


class HesaplamaAraciKapisiTest(unittest.TestCase):
    """(3) Boş widget iskeleti hiç elenmiyordu — yer tutucusu 0 değil 100."""

    BELGE_1578 = (
        "Hesaplama Araçları Finansman Türü Seçiniz Finansman Tutarı Vade "
        "Aylık Taksit Tutarı: 100TL Toplam Geri Ödeme Tutarı: 100TL "
        "Finansman Tutarı: 100TL Toplam Masraflar: Finansman Tahsis Ücreti: "
        "Hesapla"
    )

    def test_ayni_deger_uc_etikette_elenir(self):
        self.assertIsNone(extract_tutar(self.BELGE_1578))

    def test_kanit_uc_etiketi_birden_gosterir(self):
        kanit = _ayni_deger_cok_etiket(self.BELGE_1578)
        self.assertIsNotNone(kanit)
        self.assertEqual(kanit.count("100"), 3)

    def test_karsi_ornek_iki_etiket_YETMEZ(self):
        # Eşik 3: "Ödenecek Toplam Tutar" ile "Toplam Geri Ödeme" aynı şeyin
        # iki adı olabilir. İki etiketin eşitliği bozukluk kanıtı değildir.
        pencere = ("Ödenecek Toplam Tutar: 100 TL Toplam Geri Ödeme: 100 TL")
        self.assertIsNone(_ayni_deger_cok_etiket(pencere))

    def test_karsi_ornek_gercek_hesaplama_araci_KORUNUR(self):
        # tom-katilim `hesaplama-araclari`: gizli hata kutusu var ama araç
        # gerçekten hesaplamış ve üç etiketin değerleri FARKLI.
        metin = ("Aylık Kâr Oranı: 3,99 % Taksit Tutarı: 1.981,98 TL Geri "
                 "Ödenecek Tutar 11.891,83 TL Finansman Tutarı 150.000 TL "
                 "Bir hata oluştu, lütfen tekrar deneyin")
        self.assertEqual(_deger(metin), 150000.0)
        self.assertFalse(_bozuk_hesaplama_araci(metin, 0, len(metin)))

    def test_kar_payi_alaninda_gercek_yuzde_sifir_kaydi_KORUNUR(self):
        # Kapı `extract_kar_payi`de de duruyor; yeni bacak oradaki meşru
        # kayıtları düşürmemeli.
        metin = ("%0 kâr payı ile 40.000 TL'ye kadar Pratik Finansman "
                 "Kart avantajı.")
        alan = extract_kar_payi(metin)
        self.assertIsNotNone(alan)


class UcretRoluTest(unittest.TestCase):
    """Dördüncü rol karışıklığı: finansmanın FİYATI tutarı değildir."""

    def test_finansman_ucreti_elenir(self):
        # data/raw/turkiye-finans/products/bireysel-urun-hizmet-ucretleri.txt
        # ÖNCE 0,00 TRY (halüsinasyon; gold `absent`) — SONRA null.
        metin = ("Yeniden Yapılandırma, Yapılandırılmış Finansman Ücreti "
                 "0.00 TL % 0 - TL % 2 Proje finansmanı, satın alma")
        self.assertIsNone(extract_tutar(metin))

    def test_tahsis_ucreti_tutar_sanilmaz(self):
        # data/raw/dunya-katilim/docs/2516-dk-bireysel-ucrt11-180526-pdf.txt
        metin = ("Ücreti BİREYSEL KREDİLER Tahsis Ücreti 20.778 TL 3.000 TL "
                 "3.000 TL 350,92 TL")
        self.assertIsNone(extract_tutar(metin))

    def test_sifir_finansman_tutari_yoktur(self):
        self.assertIsNone(extract_tutar("Finansman tutarı 0 TL olarak görünür."))

    def test_karsi_ornek_ucretsiz_gercek_tutar_KORUNUR(self):
        # "ücret" sözcüğü CÜMLEDE geçiyor ama tetikleyici ile tutar ARASINDA
        # değil; koruma yalnız 20 karakterlik boşluğa bakar.
        metin = ("Tahsis ücreti alınmaz. İhtiyaç finansmanı tutarı 500.000 TL'ye "
                 "kadar kullandırılır.")
        self.assertEqual(_deger(metin), 500000.0)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
