"""Vade kademesi eşiği tutar değildir; çapası SONRA gelen üst sınır tutardır.

İlgili: ../src/extraction/rules/extract.py
        (`_VADE_KADEMESI_RE`, `_ARALIK_FINANSMAN_PAT`,
         `_UST_SINIR_FINANSMAN_PAT`, `_ORNEK_TABLO_RE`)

## Neden bu dosya var

`_TUTAR_PAT` tetikleyici→tutar sırası bekler ve ilk geçerli adayda `break`
eder. İki kör noktası ölçüldü (19 Ağu 2026):

**1. Vade kademesi eşiği birinci aday oluyordu.** Türk banka metinlerinde
çok yaygın kalıp:

    "Finansman tutarının 125.000 TL'ye kadar olması durumunda maksimum
     vade 36 aydır. … 125.000 TL – 250.000 TL arasında olması durumunda
     maksimum vade 24 ayı aşamaz."

Buradaki 125.000 bir VADE EŞİĞİdir; cümle 250.000 üstü finansmanın da
mümkün olduğunu söylüyor, dolayısıyla üst sınır olamaz. Tetikleyici tam da
aradığımız çapa ("Finansman tutarı") olduğu için aday birinci sıraya
geçiyor ve `break` aynı belgedeki gerçek sınırı hiç değerlendirmiyordu.

**2. Çapası SONRA gelen sınır hiç aday olamıyordu.** Sıra ters olduğunda
`_TUTAR_PAT` eşleşmiyor:

    "400.000 TL'ye Kadar İhtiyaç Finansmanı Kullanın"
    "1.000 TL-1.000.000 TL arasında … İhtiyaç Finansmanı başvurusu"

## Ürün yüzeyindeki etki

Kendi gold setimizde ölçüldü
(`turkiye-finans--kampanyalar-turkiye-finans-avantajlariyla-`): gold
400.000 TL derken çıkarım 125.000 TL üretiyordu — yani "en yüksek finansman
hangi bankada?" sorusuna bu banka için üçte bir tutarla cevap veriliyordu.
Hata korpus bağımsız: aynı kalıp harici bir karşılaştırma korpusunda da
aynı şekilde kırılıyordu.

## Neden ÇAPA zorunlu

Aynı "…'ye kadar" ve "…arası" kurgusu HARCAMA bantlarında da geçiyor ve
orada tutar finansman tutarı DEĞİLDİR (taksitli alışveriş limiti). Ayrımı
`finansman` çapası taşır; kalıbı çapasız yazmak harcama bantlarını içeri
alırdı. `Reddedilenler` sınıfı bunu kilitler.

Üç kapı ayrı ayrı kilitlenir; biri kaldırılırsa diğerleri hatayı tek başına
yakalayamaz.
"""

import unittest

from src.extraction.rules.extract import extract_tutar


def _deger(metin: str):
    f = extract_tutar(metin)
    return f.canonical_value["value"] if f else None


class TestVadeKademesiReddedilir(unittest.TestCase):
    """KAPI 1 — "… olması durumunda … vade/N ay" bir eşiktir, sınır değil."""

    def test_kademe_vade_sozcugu_ile(self) -> None:
        self.assertIsNone(_deger(
            "Finansman tutarının 125.000 TL'ye kadar olması durumunda "
            "maksimum vade 36 aydır."))

    def test_kademe_vade_sozcugu_olmadan(self) -> None:
        """Korpusta "vade" hiç geçmeyip "maksimum 36 ay" diyen varyant var."""
        self.assertIsNone(_deger(
            "Finansman tutarının 125.000 TL'ye kadar olması durumunda "
            "maksimum 36 ay taksit yapılabilir."))

    def test_kademe_asamaz_kalibi(self) -> None:
        self.assertIsNone(_deger(
            "Finansman tutarının 125.000 TL – 250.000 TL arasında olması "
            "durumunda vade 24 ayı aşamaz."))

    def test_kademe_mesru_tutari_bastirmaz(self) -> None:
        """Asıl kazanç: kademe elenince aynı belgedeki gerçek sınır görünür."""
        self.assertEqual(_deger(
            "400.000 TL'ye Kadar İhtiyaç Finansmanı Kullanın. Finansman "
            "tutarının 125.000 TL'ye kadar olması durumunda maksimum vade "
            "36 aydır."), 400000.0)


class TestTersSiraUstSinir(unittest.TestCase):
    """KAPI 2 — tutar önce, çapa sonra gelen sınır kurgusu yakalanır."""

    def test_tek_ust_sinir(self) -> None:
        self.assertEqual(_deger(
            "400.000 TL'ye Kadar İhtiyaç Finansmanı Kullanın, 3 Ay Öteleme "
            "Fırsatı"), 400000.0)

    def test_aralik_ust_sinir_alinir(self) -> None:
        """Aralıkta istenen ÜST sınır; alt sınır (1.000) değil."""
        self.assertEqual(_deger(
            "Kampanya kapsamında 1.000 TL-1.000.000 TL arasında "
            "ihtiyaçlarınız için size özel koşullarla İhtiyaç Finansmanı "
            "başvurusu yapabilirsiniz."), 1000000.0)


class TestTersSiraReddedilenler(unittest.TestCase):
    """KAPI 3 — çapa yoksa ya da tablo bağlamıysa üretilmez."""

    def test_harcama_limiti_finansman_degil(self) -> None:
        """"…'ye kadar" tek başına yetmez; çapa ("finansman") şart."""
        self.assertIsNone(_deger(
            "Sağlam Kart Troy müşterilerine özel 50.000 TL'ye kadar vade "
            "farksız 5 taksit fırsatını kaçırmayın!"))

    def test_harcama_bandi_finansman_degil(self) -> None:
        self.assertIsNone(_deger(
            "TROY kredi kartınız ile 1.000 TL- 100.000 TL tutarları "
            "arasında sağlık harcamanızı yapın."))

    def test_maliyet_tablosu_satiri_alinmaz(self) -> None:
        """Temsili tablo satırı kampanyanın sınırı değildir."""
        self.assertIsNone(_deger(
            "İhtiyaç Finansmanı Maliyet Tablosu 50.000 TL'ye Kadar "
            "Sigortalı İhtiyaç Finansmanı"))


if __name__ == "__main__":
    unittest.main()
