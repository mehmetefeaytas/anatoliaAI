"""Kampanya Bilgileri + Hedef Kitle alanları (şartname §5.3, 2. ve 3. kolon).

İlgili: raw/teknofest/...pdf §5.3 (beklenen bilgiler), §5.7 (karşılaştırma)
        ../src/extraction/rules/extract.py

Kural katmanı bu 5 alanı üretmiyordu; sonuç olarak §5.7'nin 5 karşılaştırma
kriterinden "En Yüksek Ödül Miktarı" hiç cevaplanamıyordu ve §5.3'ün "Kampanya
Bilgileri" ile "Hedef Kitle" kolonları tamamen boştu.

Bu testler özellikle AYIRT ETME tuzaklarını korur — çünkü alanı üretmek kolay,
doğru üretmek zordur:
  - koşul mu ödül mü?        "500 TL alışveriş yapana 50 TL hediye"
  - indirim mi puan mı?      "%5 puan iadesi" indirim DEĞİLDİR
  - oran mı adet mi?         "%5 puan" ile "1.000 chip-para" farklı şeylerdir
  - segment mi negasyon mu?  "yeni müşteri olmayanlar" etiket ÜRETMEZ
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.extraction.rules.extract import (
    extract_alisveris_puani,
    extract_all,
    extract_hedef_kitle,
    extract_indirim_orani,
    extract_kampanya_kosullari,
    extract_odul_miktari,
    extract_tutar,
)


class TestFinansmanTutariGoldRegresyonu(unittest.TestCase):
    """İlk gerçek ölçümde `finansman_tutari` F1=0.000 aldı; sebepleri burada çitli.

    Her metin gold setinden ALINMIŞ gerçek bir belgenin ilgili parçasıdır
    (`eval/reports/20260804-202009` teşhisi,
    `data/gold/review/_hakem-turu-01-finansman-tutari.md`).
    """

    def _deger(self, metin: str):
        f = extract_tutar(metin)
        return None if f is None else f.canonical_value["value"]

    def test_cumle_siniri_asilmaz(self) -> None:
        """Tetikleyici bir cümlede, sayı başka cümlede → eşleşme OLMAMALI.

        Ölçülen halüsinasyon: sayı bir cep telefonu FİYATI.
        """
        metin = ("Bu ürün bir tüketici ihtiyaç finansmanı ürünüdür. "
                 "Fiyatı 20.000 TL'ye kadar olan cep telefonu alımı amacıyla "
                 "kullandırılan kredilerin vadesi 12 ayı geçemez.")
        self.assertIsNone(extract_tutar(metin))

    def test_varlik_fiyati_tutar_sayilmaz(self) -> None:
        """Konutun DEĞERİ finansman tutarı değildir (gold da bunu karıştırmış)."""
        self.assertIsNone(extract_tutar("Konut finansmanı değeri 3.000.000 TL"))

    def test_ornek_tablosu_atlanir(self) -> None:
        """'Örnek ... Tablosu' temsili bir hesap örneğidir, kampanya tutarı değil."""
        metin = ("Örnek İhtiyaç Finansmanı Tablosu Finansman Tutarı Vade "
                 "Kar Oranı Taksit Tutarı 30.000,00 ₺ 12 Ay 1,69%")
        self.assertIsNone(extract_tutar(metin))

    def test_aralikta_ust_sinir_secilir(self) -> None:
        """Biçim kartı §3.4: para aralığında ÜST sınır kanoniktir.

        Gerçek vaka bir hesaplama aracının kaydırıcı sınırlarıydı.
        """
        metin = "Finansman Hesaplama Finansman Tutarı TL 5.000 TL 150.000 TL Vade Ay"
        self.assertEqual(self._deger(metin), 150000.0)

    def test_belgedeki_en_buyuk_tutar_secilmez(self) -> None:
        """ÖLÇÜLMÜŞ YANLIŞ DENEME çiti — bu test o denemeyi geri gelmekten korur.

        Bir tur "adayların en büyüğünü seç" denendi ve hesaplama aracının
        'Geri Ödenecek Tutar' satırını (11.891,83) tutar sandı. §3.4 *bir
        aralığın* üst sınırını ister, belgedeki en büyük sayıyı değil.
        """
        metin = ("Finansman Tutarı TL 5.000 TL 150.000 TL Vade Ay 1 Ay 36 Ay "
                 "Taksit Tutarı: 1.981,98 TL Geri Ödenecek Tutar 211.891,83 TL")
        self.assertEqual(self._deger(metin), 150000.0)

    def test_toplam_azami_birim_sinirini_ezer(self) -> None:
        """Belge iki sınır veriyorsa TOPLAM sınır kanoniktir.

        Bu ayrı bir kalıpla çözülüyor çünkü o cümlede tetikleyici sözcük
        sayıdan 20 karakterden uzak kalıyor ve aday hiç oluşmuyor.
        """
        metin = ("Hak sahiplerine kullandırılacak kâr payı destekli finansman "
                 "tutarı azami 1.250.000 TL'dir. Toplam finansman tutarı her bir "
                 "bağımsız bölüm için 1.250.000 TL'yi aşmamak koşulu ile "
                 "toplamda azami 3.000.000 TL olabilecektir.")
        self.assertEqual(self._deger(metin), 3000000.0)

    def test_duz_tutar_hala_bulunur(self) -> None:
        """Düzeltmeler temel davranışı bozmamalı."""
        self.assertEqual(self._deger("Konut finansmanı tutarı 500.000 TL"),
                         500000.0)


class TestAlisverisPuaniKromHalusinasyonu(unittest.TestCase):
    """Ölçülen 19 halüsinasyonun 2'si bu iki mekanizmadan geliyordu."""

    def test_gezinme_bagi_odul_sayilmaz(self) -> None:
        """Site kromundaki SSS bağlantısı ödül DEĞİLDİR.

        İki Türkiye Finans sayfasında `puan` sözcüğünün geçtiği TEK yer buydu
        ve ikisinde de ilgisiz bir sayı üretiliyordu.
        """
        metin = ("3D Secure Nedir, Ne İşe Yarar? Kredi Notu (Kredi Puanı) Nedir? "
                 "Türkiye Finans'ın 100'ünde Gelecek Olan 5 Üyesi")
        self.assertIsNone(extract_alisveris_puani(metin))

    def test_sayi_birime_komsu_olmali(self) -> None:
        """Eskiden birim opsiyoneldi, yani ±30 karakterdeki her sayı kabuldü."""
        self.assertIsNone(extract_alisveris_puani(
            "Kampanya 15 Eylül tarihine kadar geçerlidir. Puan kullanımı serbesttir."))

    def test_markali_puan_taninir(self) -> None:
        """ParafPara sözlükte yoktu; ödül sistematik olarak kaçıyordu."""
        f = extract_alisveris_puani(
            "Alışverişlerinize toplamda 1.500 TL ParafPara verilecektir.")
        self.assertIsNotNone(f)
        self.assertEqual(f.canonical_value, {"kind": "points", "value": 1500.0})

    def test_madde_numarasi_odul_sayilmaz(self) -> None:
        """Sözleşme madde numarası ödül değildir.

        Ölçülen yanlış pozitif: "24. Puan Uygulaması 24.1. Banka Kartı..."
        Eski desen sonu serbest bıraktığı için "24." yutuluyor ve madde
        numarası 24 puanlık ödül sanılıyordu.
        """
        metin = ("Kart hamili vadesi dolmuş olsa dahi mesuldür. "
                 "24. Puan Uygulaması 24.1. Banka Kartı ile yapılan işlemler")
        self.assertIsNone(extract_alisveris_puani(metin))

    def test_binlik_ayirac_bozulmaz(self) -> None:
        """Madde-numarası çiti binlik ayıraçlı tutarı bozmamalı."""
        f = extract_alisveris_puani("Harcamalarınıza 3.000 TL ParafPara!")
        self.assertIsNotNone(f)
        self.assertEqual(f.canonical_value["value"], 3000.0)

    def test_gercek_puan_odulu_hala_bulunur(self) -> None:
        f = extract_alisveris_puani("Alışverişlerinizde 1.000 chip-para kazanın")
        self.assertIsNotNone(f)
        self.assertEqual(f.canonical_value["kind"], "points")


class TestOdulMiktari(unittest.TestCase):
    """§5.7 'En Yüksek Ödül Miktarı' bu alana dayanır."""

    def test_temel_bicimler(self):
        for text, beklenen in [
            ("500 TL hediye çeki kazanın", 500.0),
            ("hediye 250 TL", 250.0),
            ("1.000 TL para puan", 1000.0),
            ("2.500 TL nakit iade", 2500.0),
        ]:
            f = extract_odul_miktari(text)
            self.assertIsNotNone(f, text)
            self.assertEqual(f.canonical_value["value"], beklenen, text)

    def test_kosul_odul_ayrimi(self):
        # 500 TL bir KOŞUL, 50 TL ise ÖDÜL. Ödül sözcüğüne en yakın tutar alınır.
        f = extract_odul_miktari("500 TL alışveriş yapana 50 TL hediye")
        self.assertEqual(f.canonical_value["value"], 50.0)

    def test_odul_yoksa_uydurmaz(self):
        self.assertIsNone(extract_odul_miktari("hava güzel"))
        self.assertIsNone(extract_odul_miktari("kâr payı oranı %1,89"))


class TestIndirimOrani(unittest.TestCase):
    def test_temel_bicimler(self):
        for text, beklenen in [
            ("%20 indirim fırsatı", 20.0),
            ("indirim oranı %15", 15.0),
            ("%25'e varan indirim", 25.0),
        ]:
            self.assertEqual(extract_indirim_orani(text).canonical_value,
                             beklenen, text)

    def test_puan_iadesi_indirim_degildir(self):
        # "%5 puan iadesi" alisveris_puani'dır, indirim değil.
        self.assertIsNone(extract_indirim_orani("%5 puan iadesi"))

    def test_indirim_yoksa_uydurmaz(self):
        self.assertIsNone(extract_indirim_orani("hava güzel"))


class TestAlisverisPuani(unittest.TestCase):
    """Oran ve adet AYRI kanonik şekiller — adil kıyas için (CLAUDE.md §17)."""

    def test_oran_bicimi(self):
        f = extract_alisveris_puani("%5 puan iadesi")
        self.assertEqual(f.canonical_value, {"kind": "rate", "value": 5.0})

    def test_adet_bicimi(self):
        f = extract_alisveris_puani("1.000 chip-para hediye")
        self.assertEqual(f.canonical_value, {"kind": "points", "value": 1000.0})

    def test_oran_ve_adet_karistirilmaz(self):
        oran = extract_alisveris_puani("%5 puan iadesi").canonical_value
        adet = extract_alisveris_puani("1.000 chip-para").canonical_value
        self.assertNotEqual(oran["kind"], adet["kind"])

    def test_puan_yoksa_uydurmaz(self):
        self.assertIsNone(extract_alisveris_puani("hava güzel"))


class TestHedefKitle(unittest.TestCase):
    """§5.3 3. kolon — 4 segment, çok etiketli."""

    def test_tekil_segmentler(self):
        self.assertEqual(extract_hedef_kitle("Yeni müşterilere özel").canonical_value,
                         ["yeni_musteri"])
        self.assertEqual(extract_hedef_kitle("emekli ve öğrencilere özel").canonical_value,
                         ["belirli_segment"])

    def test_cok_etiketli(self):
        f = extract_hedef_kitle("maaş müşterilerimize özel kampanya")
        self.assertIn("maas_musterisi", f.canonical_value)

    def test_negasyon_etiket_uretmez(self):
        # "yeni müşteri OLMAYANLAR" -> yeni_musteri etiketi verilmemeli
        f = extract_hedef_kitle("yeni müşteri olmayanlar için geçerli değildir")
        self.assertIsNone(f)

    def test_sinyal_yoksa_varsayilan_yapmaz(self):
        # 'mevcut müşteri' varsayılanına DÜŞMEMELİ (halüsinasyon yasağı)
        self.assertIsNone(extract_hedef_kitle("kâr payı oranı %1,89, 36 ay vade"))


class TestKampanyaKosullari(unittest.TestCase):
    """Skaler değil, cümle listesi."""

    def test_kosul_cumleleri_toplanir(self):
        text = ("Kâr payı oranı %1,89. Kampanyadan yararlanmak için asgari "
                "3 işlem yapılması gerekmektedir. Kampanya 31.12.2026 tarihine "
                "kadar geçerlidir.")
        f = extract_kampanya_kosullari(text)
        self.assertIsInstance(f.canonical_value, list)
        self.assertTrue(any("asgari" in s for s in f.canonical_value))

    def test_kosul_yoksa_none(self):
        self.assertIsNone(extract_kampanya_kosullari("Kâr payı oranı %1,89."))


class TestUctanUcaKapsam(unittest.TestCase):
    """Gerçekçi kart kampanyası — 7 alan, hepsinin span'i doğrulanmalı."""

    METIN = (
        "YENİ MÜŞTERİLERE ÖZEL KREDİ KARTI KAMPANYASI. "
        "Kartınızla yapacağınız alışverişlerde %5 puan iadesi ve 1.000 TL "
        "hediye çeki kazanın. Market alışverişlerinde %20 indirim fırsatı. "
        "Yıllık kart ücreti alınmaz. "
        "Kampanya 31 Aralık 2026 tarihine kadar geçerlidir."
    )

    def test_kampanya_alanlari_cikar(self):
        got = {f.field_name for f in extract_all(self.METIN)}
        for beklenen in ["odul_miktari", "indirim_orani", "alisveris_puani",
                         "hedef_kitle", "kampanya_suresi", "masraf_durumu"]:
            self.assertIn(beklenen, got)

    def test_fiil_negasyonu_hayali_ucret_uretmez(self):
        # REGRESYON: "ücreti alınmaz. Kampanya 31 Aralık" -> has_fee True,
        # amount 31.0 (tarihten uydurma) üretiliyordu. İki hata birden:
        # fiil negasyonu bilinmiyordu ve pencere cümle sınırını aşıyordu.
        d = {f.field_name: f.canonical_value for f in extract_all(self.METIN)}
        self.assertEqual(d["masraf_durumu"], {"has_fee": False, "amount": 0.0})

    def test_finansman_alanlari_uydurulmaz(self):
        # Kart kampanyasında vade/taksit/tutar YOK — üretilmemeli.
        got = {f.field_name for f in extract_all(self.METIN)}
        for olmamali in ["vade_ay", "taksit_sayisi", "finansman_tutari",
                         "kar_payi_orani"]:
            self.assertNotIn(olmamali, got)

    def test_tum_spanlar_dogrulanir(self):
        for f in extract_all(self.METIN):
            self.assertTrue(f.verify_span(self.METIN), f.field_name)


if __name__ == "__main__":
    unittest.main()
