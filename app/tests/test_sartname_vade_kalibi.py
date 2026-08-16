"""Şartname s.11 örnek metinlerinden VADE çıkarımı — s.12 tablosuyla karşılaştırma.

İlgili: src/extraction/rules/extract.py (`_vade_kurulusu`, `extract_vade`)
        raw/teknofest/2026-teknofest-tyda-sartname-2-senaryo.pdf s.11–12
        docs/sartname-kod-eslesme.md §5.3

## Bu testin varlık sebebi

Şartname s.11'de üç banka için birebir kampanya metni veriyor, s.12'de de o
metinlerden BEKLENEN çıktı tablosunu. Bu, jürinin elindeki tek resmî
girdi/çıktı çiftidir — "canlı çıkarım" butonuna yapıştırılacak metin budur.

Beklenen tablo (s.12):

    Banka       Ürün Türü          Kâr Payı Oranı   Vade
    A Bankası   Konut finansmanı   %1,89            120 ay
    B Bankası   Konut finansmanı   %1,95            120 ay
    C Bankası   Konut finansmanı   %1,87            96 ay

## Ölçülen hata (2026-08-16)

**A Bankası metni Vade hücresini BOŞ bırakıyordu.** Sebep: `extract_vade`
metinde "vade" sözcüğünü tetikleyici olarak arıyor, A metninde ise o sözcük
hiç geçmiyor —

    "…özel %1,89 kâr payı oranı ile 120 aya kadar konut finansmanı fırsatı…"

B ve C metinleri "vadeye" / "vadeli" içerdiği için çalışıyordu; yani hata tam
olarak şartnamenin İLK örneğinde, en görünür yerde duruyordu. Değerlendirme
ölçütü de birebir bunu ödüllendiriyor (Model Başarısı %30 — "farklı ifade
biçimlerini doğru yorumlayabilmesi").

Çözüm `_vade_kurulusu`: "sayı + yönelme hâli + sınır edatı + FİNANSMAN ÜRÜNÜ"
yapısı, "vade" sözcüğü hiç yokken ikinci tetikleyici olarak kabul edilir.
Ürün adı şartının neden zorunlu olduğu `RetBaglamlari` sınıfında ölçümle
birlikte yazılı.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.extraction.rules.extract import extract_kar_payi, extract_vade

# --------------------------------------------------------------------------- #
# Şartname s.11 — üç kampanya metni BİREBİR
# --------------------------------------------------------------------------- #
A_BANKASI = (
    "Yeni ev sahibi olmak isteyen müşterilerimize özel %1,89 kâr payı oranı "
    "ile 120 aya kadar konut finansmanı fırsatı sunulmaktadır. Kampanya "
    "kapsamında 50.000 TL'ye kadar dosya masrafı alınmamaktadır. Kampanya "
    "31 Aralık 2026 tarihine kadar geçerlidir."
)
B_BANKASI = (
    "Konut finansmanında avantajlı ödeme seçenekleri. %1,95 kâr payı oranı "
    "ile 120 ay vadeye kadar finansman imkanı sunulmaktadır. Kampanya "
    "kapsamında ekspertiz ücreti banka tarafından karşılanmaktadır."
)
C_BANKASI = (
    "Yeni konut alımlarına özel %1,87 kâr payı oranı ile 96 ay vadeli konut "
    "finansmanı fırsatı. Kampanya kapsamında 5.000 TL değerinde alışveriş "
    "çeki verilmektedir."
)

#: Şartname s.12 beklenen çıktı tablosu — (metin, vade_ay, kar_payi_orani)
SARTNAME_TABLOSU = (
    ("A Bankası", A_BANKASI, 120, 1.89),
    ("B Bankası", B_BANKASI, 120, 1.95),
    ("C Bankası", C_BANKASI, 96, 1.87),
)


def _vade(text: str):
    field = extract_vade(text)
    return field.canonical_value if field else None


class SartnameBeklenenCiktiTablosu(unittest.TestCase):
    """s.11 metinleri → s.12 tablosu. Jüriye gösterilebilir artefakt."""

    def test_vade_sutunu(self):
        for ad, metin, beklenen, _ in SARTNAME_TABLOSU:
            with self.subTest(banka=ad):
                self.assertEqual(
                    _vade(metin), beklenen,
                    f"{ad}: şartname s.12 Vade = {beklenen} ay bekliyor")

    def test_kar_payi_sutunu(self):
        """Vade düzeltmesi oran çıkarımını bozmamalı (aynı cümlede duruyorlar)."""
        for ad, metin, _, beklenen in SARTNAME_TABLOSU:
            with self.subTest(banka=ad):
                field = extract_kar_payi(metin)
                self.assertIsNotNone(field, f"{ad}: oran bulunamadı")
                self.assertEqual(field.canonical_value, beklenen)

    def test_a_bankasi_vade_sozcugu_ICERMEZ(self):
        """Testin dayanağı: A metni gerçekten 'vade' sözcüğü içermiyor.

        Bu doğrulama olmadan test, düzeltmenin ne yaptığını kanıtlamaz —
        metin "vade" içerseydi eski kod da geçerdi.
        """
        self.assertNotIn("vade", A_BANKASI.lower())
        self.assertIn("vade", B_BANKASI.lower())
        self.assertIn("vade", C_BANKASI.lower())

    def test_a_bankasi_kampanya_tarihi_vade_SANILMAZ(self):
        """A metninde '31 Aralık 2026' var; 2026 vade diye okunmamalı."""
        self.assertEqual(_vade(A_BANKASI), 120)


class YapiTetikleyicisi(unittest.TestCase):
    """'vade' sözcüğü olmadan vade kuran yapı — kabul edilen biçimler."""

    def test_aya_kadar_konut_finansmani(self):
        self.assertEqual(
            _vade("120 aya kadar konut finansmanı fırsatı sunulmaktadır"), 120)

    def test_aya_varan_ihtiyac_finansmani(self):
        self.assertEqual(_vade("36 aya varan ihtiyaç finansmanı"), 36)

    def test_kesme_isaretli_yazim(self):
        self.assertEqual(_vade("120 ay'a kadar konut finansmanı"), 120)

    def test_yila_kadar_finansman(self):
        self.assertEqual(_vade("10 yıla kadar konut finansmanı imkânı"), 120)

    def test_araya_sifat_girebilir(self):
        self.assertEqual(
            _vade("48 aya kadar avantajlı taşıt finansmanı fırsatı"), 48)

    def test_dek_edati(self):
        self.assertEqual(_vade("60 aya dek ihtiyaç finansmanı"), 60)

    def test_korpustan_kazanilan_tek_kayit(self):
        """albaraka/tatiliniz-icin — korpusta bu genişletmenin kazandığı tek kayıt.

        Pencere 48 karakterken kaçıyordu: reddin sebebi anlam değil, ürün
        adının ("kredidir") 54. karaktere düşmesiydi. Pencere ölçümle 72'ye
        çıkarıldı; 60'tan sonra kabul sayısı DOYUYOR (60/72/90 → hep 1).
        """
        self.assertEqual(_vade(
            "Devre Tatil finansmanı, ihtiyaçlarınız için 36 aya varan ödeme "
            "seçenekleriyle kullanabileceğiniz bir kredidir."), 36)


class CumleSiniri(unittest.TestCase):
    """Pencere cümle sınırını aşmaz — dosyadaki diğer kapılarla aynı disiplin."""

    def test_sonraki_cumlenin_urun_adi_bulasmaz(self):
        for metin in ("12 aya varan taksit. Konut finansmanı da sunulmaktadır.",
                      "9 aya varan taksit! Konut finansmanı fırsatı."):
            with self.subTest(metin=metin):
                self.assertIsNone(_vade(metin))


class RetBaglamlari(unittest.TestCase):
    """Kapının asıl işi burada — 'ay' geçen her sayı vade DEĞİLDİR.

    ÖLÇÜLDÜ (1782 belgelik korpus): `vade_ay` üretilmeyen belgelerdeki
    "X aya kadar/varan" eşleşmelerinin **65'inin 65'i** taksit bağlamındaydı,
    gerçek vade sıfır taneydi. Ürün adı şartı olmasaydı bu genişletme 62
    yanlış değer ekler, 0 doğru değer kazandırırdı.
    """

    def test_taksit_vade_degildir(self):
        """Korpustaki baskın vaka (62/65) — `taksit_sayisi` alanına ait."""
        for metin in ("12 aya varan taksit seçenekleri",
                      "60 aya kadar taksitlendirebilirsiniz",
                      "3 aya kadar kâr paysız taksit",
                      "faturanıza 3 aya kadar taksitlendirebilirler"):
            with self.subTest(metin=metin):
                self.assertIsNone(_vade(metin))

    def test_odemesiz_donem_vade_degildir(self):
        """CLAUDE.md §6 zor vakası: 'ilk 3 ay ödemesiz' bir vade değil."""
        for metin in ("ilk 3 ay ödemesiz konut finansmanı",
                      "3 ay erteleme imkânlı ihtiyaç finansmanı",
                      "ilk 6 aya kadar ödeme yok, konut finansmanı"):
            with self.subTest(metin=metin):
                self.assertIsNone(_vade(metin))

    def test_kampanya_suresi_vade_degildir(self):
        for metin in ("Kampanya 3 aya kadar geçerlidir",
                      "6 ay içerisinde başvuran müşterilere finansman",
                      "3 ay boyunca geçerli finansman kampanyası",
                      "2 ay süreyle finansman başvurusu alınacaktır"):
            with self.subTest(metin=metin):
                self.assertIsNone(_vade(metin))

    def test_kidem_kosulu_vade_degildir(self):
        for metin in ("son 6 ayda maaşını bankamızdan alan müşterilere finansman",
                      "son 3 aydır kredi kullanan müşterilerimize finansman"):
            with self.subTest(metin=metin):
                self.assertIsNone(_vade(metin))

    def test_urun_adi_YOKSA_uretilmez(self):
        """Yapının belkemiği: sınırlanan şey bir finansman ürünü olmalı."""
        for metin in ("120 aya kadar kullanabilirsiniz",
                      "36 aya varan avantaj",
                      "12 aya kadar dilediğiniz gibi"):
            with self.subTest(metin=metin):
                self.assertIsNone(_vade(metin))

    def test_kredi_KARTI_urun_sayilmaz(self):
        """Korpustaki 3 sınır vakası tam bu kalıptaydı."""
        self.assertIsNone(
            _vade("3 aya kadar ücretsiz kredi kartı kullanımı"))
        self.assertIsNone(
            _vade("12 aya varan taksit ile kredi kartından alışveriş"))


class GeriOdemeIstisnasi(unittest.TestCase):
    """`taksit` reddinin TEK istisnası: açık "geri ödeme" işareti.

    ## Neden bu istisna var

    CLAUDE.md §10 "Eşanlamlılar" satırı birebir: *"vade ≈ ödeme süresi ≈ geri
    ödeme süresi"*. `synonyms.py` içindeki `FIELD_TRIGGERS["vade_ay"]` listesi
    de bağımsız olarak "geri ödeme süresi"ni sayıyor. Yani projenin KENDİ
    terminolojisine göre "geri ödemelerinizi 60 aya kadar taksitlendirebilir-
    siniz" bir vadedir; `taksit` reddiyle dışarıda bırakmak iki belgelenmiş
    kuralla çelişiyordu.

    ## Ölçüldü — yazılmadan önce

    1782 belgelik korpusta istisna **tek** eşleşme üretiyor (sol pencere
    40/60/80/120 karakterin hepsinde aynı 1 kayıt) ve o kayıt gerçek bir
    vade. **Yanlış pozitif: 0.**
    """

    def test_korpustan_kazanilan_kayit(self):
        """cid=691 albaraka/2b-arazi-finansmani — korpustan birebir metin."""
        self.assertEqual(_vade(
            "2B Arazi Finansmanı 6292 sayılı kanun kapsamındaki 2B araziler "
            "için finansman desteği alabilir, geri ödemelerinizi 60 aya kadar "
            "taksitlendirebilirsiniz. Özellikler Hak sahipliği belgeniz"), 60)

    def test_urun_adi_SOLDAN_karsilanabilir(self):
        """Bu yolda ürün adı değerin solunda durur ("finansman desteği")."""
        self.assertEqual(
            _vade("konut finansmanı geri ödemelerinizi 120 aya kadar "
                  "taksitlendirebilirsiniz"), 120)

    def test_ciplak_taksitlendir_YETMEZ(self):
        """İşaret dar: açık 'geri ödeme' ibaresi olmadan istisna açılmaz."""
        self.assertIsNone(
            _vade("finansman tutarınızı 60 aya kadar taksitlendirebilirsiniz"))

    def test_urun_adi_yoksa_istisna_da_acilmaz(self):
        self.assertIsNone(_vade("geri ödemelerinizi 12 aya kadar taksitlendirin"))


class TaksitReddiAYAKTA(unittest.TestCase):
    """İstisna, `taksit` reddini genel olarak DELMEMELİ.

    Korpustaki 62 taksit vakası aynen dışarıda kalmalı — bu red kalkarsa
    `vade_ay` alanına 62 yanlış değer girer.
    """

    def test_alisveris_taksit_kampanyalari(self):
        for metin in ("12 aya varan taksit seçenekleri",
                      "12 aya varan taksit imkanı sizi bekliyor",
                      "incehesap.com'da 12 aya varan taksit seçenekleri",
                      "faturanıza 3 aya kadar kâr paysız taksit",
                      "alışverişlerinizde 36 aya varan taksit imkânı ile finansman",
                      "3 aya kadar taksitlendirebilirler. kredi kartından limit"):
            with self.subTest(metin=metin):
                self.assertIsNone(_vade(metin))

    def test_kosulsuz_retler_istisnayi_yener(self):
        """'geri ödeme' geçse bile ödemesiz/geçerli/boyunca reddi kalkmaz."""
        for metin in ("geri ödeme planınızı 3 aya kadar erteleyebilirsiniz",
                      "geri ödemesiz ilk 3 aya kadar finansman",
                      "geri ödeme kolaylığı 6 ay boyunca geçerli finansman",
                      "ilk 3 aya kadar geri ödeme yok, finansman"):
            with self.subTest(metin=metin):
                self.assertIsNone(_vade(metin))


class MevcutDavranisKORUNUR(unittest.TestCase):
    """'vade' sözcüğü GEÇEN belgelerde davranış birebir eskisi olmalı.

    Yeni kapı yalnızca tetikleyici HİÇ yokken devreye girer; girdiğinde de
    aday kümesini genişletmez, daraltır.
    """

    def test_vade_sozcugu_varken_eski_yol(self):
        self.assertEqual(_vade("36 ay vade ile finansman"), 36)
        self.assertEqual(_vade("120 ay vadeye kadar finansman"), 120)
        self.assertEqual(_vade("96 ay vadeli konut finansmanı"), 96)
        self.assertEqual(_vade("36 aya varan vade"), 36)

    def test_tetikleyicisiz_halusinasyon_hala_reddedilir(self):
        """Ölçülmüş 177 halüsinasyon sınıfı — yapı kurulmadığı için elenir."""
        for metin in ("1 Aylık TOD taraftar paketi hediye",
                      "3 ay boyunca ücretsiz üyelik",
                      "Bu bir çerezdir. 1 yıl saklanır.",
                      "Kampanya 2026 yılı sonuna kadar sürecektir"):
            with self.subTest(metin=metin):
                self.assertIsNone(_vade(metin))

    def test_takvim_yili_kapisi_bozulmadi(self):
        """'2026 yılı' vade değil tarihtir — mevcut kapı ayakta."""
        self.assertIsNone(_vade("Kampanya 2026 yılı boyunca geçerlidir"))


if __name__ == "__main__":
    unittest.main()
