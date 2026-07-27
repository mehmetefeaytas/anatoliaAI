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
)


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
