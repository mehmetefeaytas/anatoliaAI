"""Koşula bağlı oran, koşulsuz oranla aynı kolonda sıralanmaz.

İlgili: ../src/comparison/compare.py (`_kosul_notu`, `NOT_KOSULLU`)
        CLAUDE.md §6 (zaman-koşullu oran = zor vaka), §17 (adil kıyas)

## Bu testlerin varlık sebebi — ÖLÇÜLDÜ (2026-08-11, `data/demo.db`)

"En düşük kâr payı oranı" sıralamasının ilk DÖRT satırı **%0**'dı ve dördü de
`comparable=True` idi. Değerler uydurma değil — metinde gerçekten yazıyor:

    "Mobilden yeni müşterilere özel %0 kâr payı ile 50.000 TL'ye varan…"
    "Albaraka Mobil'den müşteri olanlar, %0 kâr payı ile…"

Hiçbiri koşulsuz bir ürün oranı değil, ama herkese açık %1,69'luk bir konut
finansmanının ÜSTÜNDE duruyorlardı. Kullanıcı "en düşük oran" ekranında,
yalnız belirli bir kanaldan gelen yeni müşterinin alabileceği bir promosyonu
genel bir teklif sanıyordu.

Taban oranlar aynı kovada: "%1,89'**dan başlayan**" bir ALT SINIRDIR.

## Yanlış pozitifler de ÖLÇÜLDÜ — kapı bu yüzden yön duyarlı

İlk deneme koşul sözcüğünü kanıt penceresinde ARADI ve 54 satırın 11'ini
işaretledi. Dördü yanlıştı; koşul orana değil BAŞKA bir şeye bağlıydı:

    "…sabit %4.09 kâr payı oranı, 3 ay erteleme fırsatı ve YENİ MÜŞTERİLERE
     ÖZEL dosya masrafsızlık avantajı…"        -> koşul MASRAFSIZLIĞA ait
    "…%1,99 - %2,49 arasında, 48 aya kadar vade. İLK 3 AY ödemesiz."
                                                -> koşul ÖDEMEYE ait

İlkinde oran açıkça "sabit" diye niteleniyor. Bu satırları elemek gerçek bir
teklifi ekrandan silmek olurdu. Yön ayrımı + cümle sınırı eklendikten sonra:
7 doğru pozitif, 0 yanlış pozitif.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.comparison.compare import NOT_KOSULLU, _kosul_notu, rank

ALAN = "kar_payi_orani"


def _satir(ham: str, kanit: str, deger=None, **ek) -> dict:
    return {"bank": ek.pop("bank", "ornek"), "bank_name": "Örnek",
            "raw_value": ham, "source_span": kanit,
            "canonical_value": deger if deger is not None else 2.0,
            "confidence": 0.95, **ek}


class TestKosulYakalaniyor(unittest.TestCase):
    """Korpustan alınmış GERÇEK kanıtlar — hepsi işaretlenmeli."""

    VAKALAR = (
        ("%0", "ağlayın. Mobilden yeni müşterilere özel %0 kâr payı ile "
               "50.000 TL'ye varan İhtiyaç Finansma"),
        ("%0", "Şimdi mobilden Türkiye Finanslı olanlar %0 kar payı ile "
               "50.000 TL'ye varan İhtiyaç Finansma"),
        ("%0", "mdi Albaraka Mobil'den müşteri olanlar, %0 kâr payı ile "
               "40.000 TL'ye kadar Pratik Finansman"),
        ("%2,99", "alışverişlerinizde yeni müşteriye özel %2,99 kar payı "
                  "oranlı Taksitlio Alışveriş Finansmanı s"),
        ("%1,89", "izdeki eve kavuşun. Konut finansmanında kâr payı oranı "
                  "%1,89'dan başlayan oranlarla, 120 aya kadar v"),
    )

    def test_hepsi_kosullu_isaretleniyor(self) -> None:
        for ham, kanit in self.VAKALAR:
            with self.subTest(kanit=kanit[:45]):
                self.assertEqual(_kosul_notu(ALAN, ham, kanit), NOT_KOSULLU)


class TestYanlisPozitifYok(unittest.TestCase):
    """Koşul sözcüğü orana BAĞLI değilse işaretlenmez — ölçülen vakalar."""

    def test_kosul_baska_avantaja_aitse_ISARETLENMEZ(self) -> None:
        kanit = ("skorundan bağımsız tüm vadelerde sabit %4.09 kâr payı "
                 "oranı, 3 ay erteleme fırsatı ve yeni müşterilere özel "
                 "dosya masrafsızlık avantajı sizi bekliyor")
        self.assertIsNone(_kosul_notu(ALAN, "%4.09", kanit),
                          "'yeni müşterilere özel' MASRAFSIZLIĞA ait; oran "
                          "açıkça 'sabit' diye nitelenmiş")

    def test_cumle_siniri_kosulu_KOPARIR(self) -> None:
        kanit = ("Taşıt finansmanı kâr payı oranı %1,99 - %2,49 arasında, "
                 "48 aya kadar vade. İlk 3 ay ödemesiz.")
        self.assertIsNone(_kosul_notu(ALAN, "%1,99 - %2,49", kanit),
                          "'İlk 3 ay' NOKTADAN sonra ve ödemeye ait")

    def test_uzak_kosul_ISARETLENMEZ(self) -> None:
        kanit = ("kâr payı oranı %3,25 olarak uygulanır ve bu tutar hesaba "
                 "yansıtılır; ayrıca kampanya kapsamında mobilden başvuru "
                 "yapılabilir")
        self.assertIsNone(_kosul_notu(ALAN, "%3,25", kanit))

    def test_kosulsuz_oran_ISARETLENMEZ(self) -> None:
        kanit = ("Albaraka Türk konut finansmanında kâr payı oranı %2,49, "
                 "96 aya kadar vade. Dosya masrafı 1.000,00 TL")
        self.assertIsNone(_kosul_notu(ALAN, "%2,49", kanit))


class TestUcuncuTarafKosulu(unittest.TestCase):
    """"LCW'de %0" — oran bir ORTAĞA bağlı; bankanın kendi adı sayılmaz.

    Desen korpusta 115 yerde geçiyor ama oran alanının kanıtında yalnız BİR
    kez; gerisi indirim kampanyaları ("Civil'de %25 İndirim") ve onlar bu
    kapının kapsamında değil.
    """

    KANIT = ("olarak değişiklik gösterebilir LCW'de %0 kar payıyla "
             "kullanılmak üzere finansman API'ları")

    def test_ortak_kosulu_isaretleniyor(self) -> None:
        self.assertEqual(
            _kosul_notu(ALAN, "%0", self.KANIT, "Kuveyt Türk"), NOT_KOSULLU)

    def test_bankanin_KENDI_adi_kosul_DEGIL(self) -> None:
        """"Albaraka'da %2,49" bankanın kendi teklifidir, üçüncü taraf değil.

        Dışlama olmadan bu desen meşru bir oranı sessizce kıyas dışı
        bırakırdı — bir teklifi sessizce silmek, bir promosyonu fazla iyimser
        göstermekten kötüdür.
        """
        kanit = "Albaraka'da %2,49 kâr payı oranı ile konut finansmanı"
        self.assertIsNone(_kosul_notu(ALAN, "%2,49", kanit, "Albaraka Türk"))

    def test_iki_sozcuklu_banka_adi_da_dislaniyor(self) -> None:
        kanit = "Kuveyt Türk'te %1,89 kâr payı oranı sunulur"
        self.assertIsNone(_kosul_notu(ALAN, "%1,89", kanit, "Kuveyt Türk"))

    def test_banka_adi_bilinmiyorsa_ortak_sayilir(self) -> None:
        """Ad taşınmazsa dışlama yapılamaz; kapı yine de ateşlenir.

        Bu yön bilinçli: bilinmeyen bir adı "kendi bankası" saymak, kapıyı
        sessizce kapatmak olurdu.
        """
        self.assertEqual(_kosul_notu(ALAN, "%0", self.KANIT, None), NOT_KOSULLU)


class TestKapsam(unittest.TestCase):
    """Kapı YALNIZ kâr payı oranına uygulanır."""

    def test_vade_alaninda_ateslenmez(self) -> None:
        """"120 aya kadar" bir TAVANDIR; tavanları kıyaslamak anlamlıdır.

        Korpusta vade satırlarının %40'ı böyle bir ifade taşıyor; hepsini
        kıyas dışı bırakmak vade karşılaştırmasını yok ederdi.
        """
        kanit = "yeni müşterilerimize 120 aya kadar vade imkânı sunulur"
        self.assertIsNone(_kosul_notu("vade_ay", "120", kanit))

    def test_ham_deger_kanitta_bulunamazsa_ISARETLENMEZ(self) -> None:
        """Konum bilinmiyorsa yön kararı verilemez; sessizce elenmez."""
        self.assertIsNone(_kosul_notu(ALAN, "%9,99", "başka bir metin"))

    def test_bos_girdi_dayanikli(self) -> None:
        self.assertIsNone(_kosul_notu(ALAN, None, None))
        self.assertIsNone(_kosul_notu(ALAN, "", ""))


class TestSiralamayaEtkisi(unittest.TestCase):
    """Kapı sıralamayı değiştirmeli ama bilgiyi SAKLAMAMALI."""

    def _satirlar(self) -> list[dict]:
        return [
            _satir("%0", "Mobilden yeni müşterilere özel %0 kâr payı ile",
                   0.0, bank="promo"),
            _satir("%2,49", "konut finansmanında kâr payı oranı %2,49, 96 aya",
                   2.49, bank="sabit"),
        ]

    def test_kosullu_sifir_KAZANMAZ(self) -> None:
        sirali = rank(self._satirlar(), ALAN)
        ilk = next(r for r in sirali if r.comparable)
        self.assertEqual(ilk.bank, "sabit",
                         "koşullu %0, koşulsuz %2,49'un üstünde sıralanamaz")

    def test_deger_ve_gerekce_GORUNUR_kaliyor(self) -> None:
        sirali = {r.bank: r for r in rank(self._satirlar(), ALAN)}
        promo = sirali["promo"]
        self.assertEqual(promo.value, 0.0, "değer GİZLENMEMELİ")
        self.assertFalse(promo.comparable)
        self.assertEqual(promo.note, NOT_KOSULLU)

    def test_not_biciminin_sonu_diger_kapilarla_AYNI(self) -> None:
        """Arayüz "doğrudan kıyaslanamaz" desenini tanıyor."""
        self.assertTrue(NOT_KOSULLU.endswith("doğrudan kıyaslanamaz"))
        self.assertFalse(NOT_KOSULLU.startswith("not:"),
                         "'not:' önekini arayüz ekliyor; burada tekrarlanamaz")


if __name__ == "__main__":
    unittest.main()
