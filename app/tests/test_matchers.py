"""Eşleştirici testleri — strict vs tolerant, ve eski `_equal`'in yalanları.

İlgili: ../eval/matchers.py

Testlerin önemli bir kısmı, eski `run_eval._equal`'in SESSİZCE yanlış cevap
verdiği vakaları kilitler:

  * aralık `{min, max}` içinde float gürültüsü (düz `==` kaçırıyordu)
  * `{"has_fee": True}` ile `{"has_fee": 1}` (Python'da `True == 1`)
  * para biriminin hiç kontrol edilmemesi

`TestIkiModunFarki` bir META testtir: iki eşleştirici gerçekten FARKLI
davranıyor mu? İkisi aynı davranıyorsa "strict + tolerant birlikte
raporluyoruz" iddiası boştur.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from typing import ClassVar

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from eval.matchers import (
    MATCHER_NAMES,
    MatcherError,
    get_matcher,
    resolve_matchers,
    strict_match,
    tolerant_match,
)


class TestSayisalAlanlar(unittest.TestCase):
    """`vade_ay`, `taksit_sayisi` — düz tamsayı."""

    def test_tam_esitlik(self):
        self.assertTrue(strict_match("vade_ay", 120, 120))
        self.assertTrue(tolerant_match("vade_ay", 120, 120))

    def test_farkli_deger(self):
        self.assertFalse(strict_match("vade_ay", 120, 36))
        self.assertFalse(tolerant_match("vade_ay", 120, 36))

    def test_float_gurultusu_katida_bile_affedilir(self):
        """1.89 ile 1.8900000000000001 aynı ondalık sayının iki gösterimi."""
        self.assertTrue(strict_match("vade_ay", 12.000000000001, 12.0))

    def test_bool_sayi_ile_karistirilmaz(self):
        """Python'da True == 1; eşleştirici bunu KABUL ETMEMELİ."""
        self.assertFalse(strict_match("vade_ay", True, 1))
        self.assertFalse(tolerant_match("vade_ay", True, 1))


class TestOranAlanlari(unittest.TestCase):
    """`kar_payi_orani`, `indirim_orani` — düz sayı ya da aralık."""

    def test_duz_oran_esit(self):
        self.assertTrue(strict_match("kar_payi_orani", 1.89, 1.89))

    def test_duz_oran_farkli(self):
        self.assertFalse(strict_match("kar_payi_orani", 1.89, 2.49))

    def test_aralik_alan_alan_esit(self):
        pred = {"min": 1.99, "max": 2.49}
        gold = {"min": 1.99, "max": 2.49}
        self.assertTrue(strict_match("kar_payi_orani", pred, gold))
        self.assertTrue(tolerant_match("kar_payi_orani", pred, gold))

    def test_aralik_min_farkli(self):
        pred = {"min": 1.50, "max": 2.49}
        gold = {"min": 1.99, "max": 2.49}
        self.assertFalse(strict_match("kar_payi_orani", pred, gold))
        self.assertFalse(tolerant_match("kar_payi_orani", pred, gold))

    def test_aralikta_float_gurultusu_ESKI_HATA(self):
        """Eski `_equal` düz `==` yapıyordu: bu vaka SESSİZCE yanlış sayılıyordu."""
        pred = {"min": 1.9900000000000002, "max": 2.49}
        gold = {"min": 1.99, "max": 2.49}
        self.assertTrue(strict_match("kar_payi_orani", pred, gold))

    def test_aralik_vs_skaler_katida_hata(self):
        rng = {"min": 1.99, "max": 2.49}
        self.assertFalse(strict_match("kar_payi_orani", 1.99, rng))
        self.assertFalse(strict_match("kar_payi_orani", rng, 1.99))

    def test_aralik_vs_skaler_gevsekte_kismi_kredi(self):
        """Aralığın İÇİNDEKİ skaler gevşek modda kabul edilir."""
        rng = {"min": 1.99, "max": 2.49}
        self.assertTrue(tolerant_match("kar_payi_orani", 1.99, rng))
        self.assertTrue(tolerant_match("kar_payi_orani", 2.20, rng))
        self.assertTrue(tolerant_match("kar_payi_orani", 2.49, rng))

    def test_aralik_disindaki_skaler_gevsekte_de_hata(self):
        rng = {"min": 1.99, "max": 2.49}
        self.assertFalse(tolerant_match("kar_payi_orani", 5.0, rng))
        self.assertFalse(tolerant_match("kar_payi_orani", 0.5, rng))

    def test_yuzde_bir_tolerans(self):
        """%1,89 ile %1,90 arası fark ~%0,5 -> gevşek modda eşleşir."""
        self.assertTrue(tolerant_match("kar_payi_orani", 1.90, 1.89))
        self.assertFalse(strict_match("kar_payi_orani", 1.90, 1.89))

    def test_tolerans_buyuk_farki_yutmaz(self):
        """%1,89 ile %2,49 arası ~%32 — gevşek mod bunu ASLA affetmemeli."""
        self.assertFalse(tolerant_match("kar_payi_orani", 2.49, 1.89))


class TestParaAlanlari(unittest.TestCase):
    """`tahsis_ucreti`, `finansman_tutari`, `odul_miktari` — birim ZORUNLU."""

    def test_esit(self):
        pred = {"value": 500.0, "currency": "TRY"}
        gold = {"value": 500, "currency": "TRY"}
        self.assertTrue(strict_match("tahsis_ucreti", pred, gold))

    def test_birim_farkli_HER_IKI_MODDA_hata(self):
        """500 TRY ile 500 USD aynı değer DEĞİLDİR — tolerans konusu değil."""
        pred = {"value": 500, "currency": "USD"}
        gold = {"value": 500, "currency": "TRY"}
        self.assertFalse(strict_match("tahsis_ucreti", pred, gold))
        self.assertFalse(tolerant_match("tahsis_ucreti", pred, gold))

    def test_tutar_farkli(self):
        pred = {"value": 750, "currency": "TRY"}
        gold = {"value": 500, "currency": "TRY"}
        self.assertFalse(strict_match("tahsis_ucreti", pred, gold))
        self.assertFalse(tolerant_match("tahsis_ucreti", pred, gold))

    def test_tutar_yuzde_bir_icinde_gevsekte_esler(self):
        pred = {"value": 502, "currency": "TRY"}
        gold = {"value": 500, "currency": "TRY"}
        self.assertFalse(strict_match("tahsis_ucreti", pred, gold))
        self.assertTrue(tolerant_match("tahsis_ucreti", pred, gold))

    def test_eksik_anahtar(self):
        self.assertFalse(strict_match("tahsis_ucreti", {"value": 500},
                                      {"value": 500, "currency": "TRY"}))

    def test_sozluk_olmayan_girdi(self):
        self.assertFalse(strict_match("tahsis_ucreti", 500,
                                      {"value": 500, "currency": "TRY"}))

    def test_gerekce_metni_uretilir(self):
        result = strict_match("tahsis_ucreti", {"value": 500, "currency": "USD"},
                              {"value": 500, "currency": "TRY"})
        self.assertFalse(result.ok)
        self.assertIn("birim", result.reason)


class TestMasrafDurumu(unittest.TestCase):
    """`masraf_durumu` — `has_fee` ZORUNLU, `amount` toleranslı."""

    def test_esit(self):
        pred = {"has_fee": True, "amount": 500.0}
        gold = {"has_fee": True, "amount": 500}
        self.assertTrue(strict_match("masraf_durumu", pred, gold))

    def test_has_fee_ters_her_iki_modda_hata(self):
        """"masrafsız" ile "500 TL masraf" ZIT bilgidir."""
        pred = {"has_fee": False, "amount": 0}
        gold = {"has_fee": True, "amount": 500}
        self.assertFalse(strict_match("masraf_durumu", pred, gold))
        self.assertFalse(tolerant_match("masraf_durumu", pred, gold))

    def test_has_fee_bool_ile_int_karistirilmaz_ESKI_HATA(self):
        """Python'da True == 1; eski düz `==` bunu eşit sayardı."""
        pred = {"has_fee": 1, "amount": 500}
        gold = {"has_fee": True, "amount": 500}
        self.assertFalse(strict_match("masraf_durumu", pred, gold))
        self.assertFalse(tolerant_match("masraf_durumu", pred, gold))

    def test_masrafsiz_esit(self):
        fee = {"has_fee": False, "amount": 0.0}
        self.assertTrue(strict_match("masraf_durumu", fee, dict(fee)))

    def test_amount_null_karsilastirmasi(self):
        a = {"has_fee": True, "amount": None}
        b = {"has_fee": True, "amount": 500}
        self.assertFalse(strict_match("masraf_durumu", a, b))
        self.assertTrue(strict_match("masraf_durumu", a, dict(a)))


class TestAlisverisPuani(unittest.TestCase):
    """`alisveris_puani` — `kind` ZORUNLU (oran ≠ adet)."""

    def test_esit(self):
        self.assertTrue(strict_match("alisveris_puani",
                                     {"kind": "rate", "value": 5},
                                     {"kind": "rate", "value": 5}))

    def test_kind_farkli_her_iki_modda_hata(self):
        """%5 puan ile 5 chip-para aynı şey DEĞİLDİR."""
        pred = {"kind": "points", "value": 5}
        gold = {"kind": "rate", "value": 5}
        self.assertFalse(strict_match("alisveris_puani", pred, gold))
        self.assertFalse(tolerant_match("alisveris_puani", pred, gold))


class TestTarih(unittest.TestCase):
    """`kampanya_suresi` — ISO-8601, toleranssız."""

    def test_esit(self):
        self.assertTrue(strict_match("kampanya_suresi", "2026-12-31", "2026-12-31"))

    def test_farkli_gun_gevsekte_de_hata(self):
        """"Yakın tarih" diye bir şey yok; bir gün fark bir gün farktır."""
        self.assertFalse(strict_match("kampanya_suresi", "2026-12-30", "2026-12-31"))
        self.assertFalse(tolerant_match("kampanya_suresi", "2026-12-30",
                                        "2026-12-31"))


class TestEtiketListesi(unittest.TestCase):
    """`hedef_kitle` — etiket kümesi."""

    def test_ayni_sira_esit(self):
        v = ["yeni_musteri", "maas_musterisi"]
        self.assertTrue(strict_match("hedef_kitle", list(v), list(v)))

    def test_sira_farki_katida_hata_gevsekte_esit(self):
        pred = ["maas_musterisi", "yeni_musteri"]
        gold = ["yeni_musteri", "maas_musterisi"]
        self.assertFalse(strict_match("hedef_kitle", pred, gold))
        self.assertTrue(tolerant_match("hedef_kitle", pred, gold))

    def test_eksik_etiket_her_iki_modda_hata(self):
        self.assertFalse(tolerant_match("hedef_kitle", ["yeni_musteri"],
                                        ["yeni_musteri", "maas_musterisi"]))

    def test_fazla_etiket_her_iki_modda_hata(self):
        self.assertFalse(tolerant_match("hedef_kitle",
                                        ["yeni_musteri", "mevcut_musteri"],
                                        ["yeni_musteri"]))


class TestMetinListesi(unittest.TestCase):
    """`kampanya_kosullari` — serbest metin listesi."""

    def test_esit(self):
        v = ["Kampanya 31 Aralık'a kadar geçerlidir"]
        self.assertTrue(strict_match("kampanya_kosullari", list(v), list(v)))

    def test_sondaki_noktalama_gevsekte_onemsiz(self):
        pred = ["Banka değişiklik hakkını saklı tutar."]
        gold = ["Banka değişiklik hakkını saklı tutar"]
        self.assertFalse(strict_match("kampanya_kosullari", pred, gold))
        self.assertTrue(tolerant_match("kampanya_kosullari", pred, gold))

    def test_tr_yazim_biçimi_gevsekte_onemsiz(self):
        """ALL-CAPS banka başlıkları için: katlama TR-duyarlı olmalı."""
        pred = ["KAMPANYA KOŞULLARI GEÇERLİDİR"]
        gold = ["Kampanya koşulları geçerlidir"]
        self.assertFalse(strict_match("kampanya_kosullari", pred, gold))
        self.assertTrue(tolerant_match("kampanya_kosullari", pred, gold))

    def test_gercek_icerik_farki_gevsekte_de_hata(self):
        self.assertFalse(tolerant_match("kampanya_kosullari",
                                        ["Yalnız yeni müşteriler"],
                                        ["Tüm müşteriler"]))


class TestIkiModunFarki(unittest.TestCase):
    """META: strict ile tolerant GERÇEKTEN farklı davranıyor mu?

    İkisi aynı davranıyorsa "ikisini birlikte raporluyoruz" iddiası boştur ve
    rapordaki iki sütun okuyucuyu yanıltır.
    """

    # (alan, tahmin, gold) — katıda BAŞARISIZ, gevşekte BAŞARILI olmalı.
    AYRISAN: ClassVar[list] = [
        ("kar_payi_orani", 1.90, 1.89),
        ("kar_payi_orani", 1.99, {"min": 1.99, "max": 2.49}),
        ("tahsis_ucreti", {"value": 502, "currency": "TRY"},
         {"value": 500, "currency": "TRY"}),
        ("hedef_kitle", ["mevcut_musteri", "yeni_musteri"],
         ["yeni_musteri", "mevcut_musteri"]),
        ("kampanya_kosullari", ["Koşul geçerlidir."], ["Koşul geçerlidir"]),
    ]

    def test_gevsek_kati_dan_daha_hosgorulu(self):
        for name, pred, gold in self.AYRISAN:
            with self.subTest(field=name):
                self.assertFalse(strict_match(name, pred, gold),
                                 f"{name}: katı modda eşleşmemeliydi")
                self.assertTrue(tolerant_match(name, pred, gold),
                                f"{name}: gevşek modda eşleşmeliydi")

    def test_gevsek_mod_anlam_hatasini_asla_affetmez(self):
        """Gevşeklik biçime uygulanır, ANLAMA değil."""
        anlam_hatalari = [
            ("tahsis_ucreti", {"value": 500, "currency": "USD"},
             {"value": 500, "currency": "TRY"}),
            ("masraf_durumu", {"has_fee": False, "amount": 0},
             {"has_fee": True, "amount": 500}),
            ("alisveris_puani", {"kind": "points", "value": 5},
             {"kind": "rate", "value": 5}),
            ("kampanya_suresi", "2026-01-01", "2026-12-31"),
            ("vade_ay", 36, 120),
        ]
        for name, pred, gold in anlam_hatalari:
            with self.subTest(field=name):
                self.assertFalse(tolerant_match(name, pred, gold),
                                 f"{name}: gevşek mod anlam hatasını affetti!")

    def test_esit_degerler_iki_modda_da_esler(self):
        ayni = [
            ("vade_ay", 120, 120),
            ("kar_payi_orani", 1.89, 1.89),
            ("kar_payi_orani", {"min": 1.99, "max": 2.49},
             {"min": 1.99, "max": 2.49}),
            ("tahsis_ucreti", {"value": 500, "currency": "TRY"},
             {"value": 500.0, "currency": "TRY"}),
            ("kampanya_suresi", "2026-12-31", "2026-12-31"),
        ]
        for name, pred, gold in ayni:
            with self.subTest(field=name):
                self.assertTrue(strict_match(name, pred, gold))
                self.assertTrue(tolerant_match(name, pred, gold))


class TestKayit(unittest.TestCase):
    """Eşleştirici kayıt defteri (registry)."""

    def test_ada_gore_alinir(self):
        self.assertIs(get_matcher("strict"), strict_match)
        self.assertIs(get_matcher("tolerant"), tolerant_match)

    def test_bilinmeyen_ad_hata(self):
        """Sessizce varsayılana düşmek YOK — yanlış eşleştiriciyle üretilmiş
        bir metrik, hiç metrik olmamasından kötüdür."""
        with self.assertRaises(MatcherError):
            get_matcher("gevsek")

    def test_both_ikisini_dondurur(self):
        self.assertEqual(resolve_matchers("both"), list(MATCHER_NAMES))

    def test_tek_ad_tek_eleman(self):
        self.assertEqual(resolve_matchers("strict"), ["strict"])

    def test_gecersiz_spec_hata(self):
        with self.assertRaises(MatcherError):
            resolve_matchers("hepsi")

    def test_match_bool_gibi_davranir(self):
        """`if matcher(...)` yazılabilmeli — çağıranlar buna güveniyor."""
        self.assertTrue(bool(strict_match("vade_ay", 12, 12)))
        self.assertFalse(bool(strict_match("vade_ay", 12, 13)))


if __name__ == "__main__":
    unittest.main()
