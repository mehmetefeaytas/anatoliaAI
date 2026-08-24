"""LLM çıkarımının iki kabul kapısı — halüsinasyon ve yanlış-alan.

İlgili: ../src/extraction/llm/dayanak.py
        ../scripts/llm_bosluk_doldur.py

Her iki kapı da ÖLÇÜLMÜŞ vakalardan doğdu (2026-08-24, EVREN `llm-large`):

    "1 milyar TL limitli"       → 1000000000  DOĞRU, ama sayısal biçimi
                                  metinde geçmiyor → sözcük çarpanı gerekti
    "%0.4 Aval komisyon oranı"  → kar_payi_orani = 0.4
                                  sayı metinde VAR (dayanak geçer) ama aval
                                  komisyonu kâr payı oranı DEĞİLDİR
"""

from __future__ import annotations

import unittest

from src.extraction.llm.dayanak import (
    YASAK_IZLER,
    alan_uygun,
    kabul_edilir,
    metinde_dogrula,
    ozet,
    sayilari_topla,
    tr_katla,
)


class TestSayiToplama(unittest.TestCase):
    def test_duz_sayi(self):
        self.assertEqual(sayilari_topla(3.25), [3.25])
        self.assertEqual(sayilari_topla(0), [0.0])

    def test_tr_ondalikli_dize(self):
        self.assertEqual(sayilari_topla("31,38"), [31.38])
        self.assertEqual(sayilari_topla("1.500,25"), [1500.25])

    def test_aralik_HER_IKI_ucu(self):
        """Üst sınır uydurmaysa aralığın kendisi yanlıştır; bir uç yetmez."""
        self.assertEqual(sorted(sayilari_topla({"min": 0.0, "max": 4.82})),
                         [0.0, 4.82])

    def test_para_birimi_SAYI_DEGIL(self):
        self.assertEqual(sayilari_topla({"value": 500000, "currency": "TRY"}),
                         [500000.0])

    def test_bool_ve_None_sayi_uretmez(self):
        self.assertEqual(sayilari_topla(True), [])
        self.assertEqual(sayilari_topla(None), [])
        self.assertEqual(sayilari_topla({"has_fee": True, "amount": None}), [])

    def test_liste_dali(self):
        self.assertEqual(sorted(sayilari_topla([1, {"value": 2}])), [1.0, 2.0])

    def test_sayisal_olmayan_dize(self):
        self.assertEqual(sayilari_topla("masrafsız"), [])


class TestDayanakKapisi(unittest.TestCase):
    def test_metinde_gecen_deger_gecer(self):
        self.assertTrue(metinde_dogrula(3.25, "%3.25'ten başlayan oranlarla"))
        self.assertTrue(metinde_dogrula({"min": 3.25, "max": 3.25},
                                        "%3,25 ten başlayan"))

    def test_binlik_ayraci_iki_bicim(self):
        for metin in ("500.000 TL'ye kadar", "500,000 TL'ye kadar",
                      "500000 TL"):
            with self.subTest(metin=metin):
                self.assertTrue(metinde_dogrula(
                    {"value": 500000, "currency": "TRY"}, metin))

    def test_SOZCUKLE_yazilan_buyukluk(self):
        """Ölçülmüş vaka #642: '1 milyar TL limitli' → 1000000000 DOĞRU."""
        self.assertTrue(metinde_dogrula(
            {"value": 1_000_000_000, "currency": "TRY"}, "1 milyar TL limitli"))
        self.assertTrue(metinde_dogrula(
            {"value": 2_500_000, "currency": "TRY"}, "2,5 milyon TL'ye kadar"))

    def test_metinde_OLMAYAN_deger_dusrulur(self):
        self.assertFalse(metinde_dogrula(4.82, "Aylık Kâr Oranı %0"))

    def test_aralikta_bir_uc_kaciksa_TUMU_reddedilir(self):
        self.assertFalse(metinde_dogrula({"min": 0.0, "max": 4.82},
                                         "Aylık Kâr Oranı %0"))

    def test_sifir_gercek_bir_orandir(self):
        self.assertTrue(metinde_dogrula(0, "Aylık kar oranı %0"))

    def test_sayisiz_deger_None_dondurur(self):
        """Kapı UYGULANAMAZ — 'geçti' ile karıştırılmamalı."""
        self.assertIsNone(metinde_dogrula(["koşul metni"], "herhangi bir metin"))
        self.assertIsNone(metinde_dogrula(None, "metin"))


class TestSemantikKapi(unittest.TestCase):
    def test_aval_komisyonu_kar_payi_DEGIL(self):
        """Ölçülmüş vaka #19 — kapının varlık sebebi."""
        self.assertFalse(alan_uygun("kar_payi_orani", "%0.4 Aval komisyon oranı"))

    def test_vergi_ve_kesintiler_reddedilir(self):
        for kanit in ("KKDF oranı %15", "BSMV %5", "stopaj oranı %17,5",
                      "gecikme faizi oranı", "tahsis ücreti %0,5",
                      "ekspertiz masrafı"):
            with self.subTest(kanit=kanit):
                self.assertFalse(alan_uygun("kar_payi_orani", kanit))

    def test_gercek_kar_payi_kaniti_gecer(self):
        for kanit in ("%3.25'ten başlayan oranlarla", "Aylık kar oranı %0",
                      "kâr payı oranı %2,05"):
            with self.subTest(kanit=kanit):
                self.assertTrue(alan_uygun("kar_payi_orani", kanit))

    def test_odul_finansman_tutari_DEGIL(self):
        self.assertFalse(alan_uygun("finansman_tutari", "500 TL ödül"))
        self.assertFalse(alan_uygun("finansman_tutari", "200 TL iade"))

    def test_tanimsiz_alan_gecer(self):
        """Kapı yalnız ölçülmüş karışma vakaları için; tanımsız alan elenmez."""
        self.assertTrue(alan_uygun("vade_ay", "36 aya varan vade"))
        self.assertNotIn("vade_ay", YASAK_IZLER)

    def test_aksan_bagimsiz(self):
        self.assertFalse(alan_uygun("kar_payi_orani", "TEMERRÜT ORANI"))
        self.assertFalse(alan_uygun("kar_payi_orani", "temerrut orani"))


class TestKabulKapisi(unittest.TestCase):
    def test_iki_kapidan_gecen_KABUL(self):
        ok, g = kabul_edilir("kar_payi_orani", 3.25,
                             "%3.25'ten başlayan oranlarla",
                             "Kampanyada %3.25'ten başlayan oranlarla")
        self.assertTrue(ok)
        self.assertEqual(g, "kabul")

    def test_dayanaksiz_deger_REDDEDILIR(self):
        ok, g = kabul_edilir("kar_payi_orani", 4.82, "Aylık Kâr Oranı %0",
                             "Aylık Kâr Oranı %0")
        self.assertFalse(ok)
        self.assertEqual(g, "dayanaksiz")

    def test_yanlis_alan_REDDEDILIR(self):
        ok, g = kabul_edilir("kar_payi_orani", 0.4, "%0.4 Aval komisyon oranı",
                             "Aval komisyon oranı %0.4 olarak uygulanır")
        self.assertFalse(ok)
        self.assertEqual(g, "yanlis-alan")

    def test_sayisiz_deger_REDDEDILIR(self):
        """Bu koşumun konusu sayısal alanlar; dayanak kapısı uygulanamıyorsa yazma."""
        ok, g = kabul_edilir("kampanya_kosullari", ["koşul"], "koşul", "metin")
        self.assertFalse(ok)
        self.assertEqual(g, "sayisal-degil")


class TestOzet(unittest.TestCase):
    def test_gerekce_sayaclari(self):
        """Reddedilen değerler sessizce kaybolmasın."""
        self.assertEqual(
            ozet([(True, "kabul"), (True, "kabul"), (False, "yanlis-alan")]),
            {"kabul": 2, "yanlis-alan": 1})


class TestKatlama(unittest.TestCase):
    def test_turkce_aksan_dusurulur(self):
        self.assertEqual(tr_katla("KÂR PAYI"), "kar payi")
        self.assertEqual(tr_katla("Şüphe"), "suphe")


if __name__ == "__main__":
    unittest.main()
