"""`scripts/onarim_recetesi.py` — mekanik öneri kurallarının testleri.

En kritik testler ÜRETİLMEYEN önerilere aittir. Linter'ı geçen ama gold'a
yanlış değer sokan bir öneri, hatanın kendisinden tehlikelidir: anotatör
"öneri var, biçim de doğru" diye onaylayıp geçer ve yanlış değer gold'a
sessizce girer. O yüzden `%20-%70` ve uzak yıl korumaları burada kilitlenir.
"""

from __future__ import annotations

import unittest

from scripts.gold_schema import parse_gold_value
from scripts.onarim_recetesi import (
    KURALLAR,
    kalip,
    tr_sayilar,
    tr_tarihler,
)


def uygula(field: str, ham: str, satir: dict | None = None):
    """Kural zincirini sırayla dener; ilk eşleşenin sonucunu döndürür."""
    satir = satir if satir is not None else {}
    for kural in KURALLAR:
        sonuc = kural(field, ham, satir)
        if sonuc is not None:
            return sonuc
    return None


class TrSayiTest(unittest.TestCase):
    def test_binlik_ayraci_nokta(self):
        self.assertEqual(tr_sayilar("1.250.000 TL"), [1250000.0])

    def test_ondalik_ayraci_virgul(self):
        self.assertEqual(tr_sayilar("1.500,50"), [1500.5])

    def test_birden_cok_sayi(self):
        self.assertEqual(tr_sayilar("600.000 TL - 1.700.000 TL"),
                         [600000.0, 1700000.0])

    def test_sade_tamsayi(self):
        self.assertEqual(tr_sayilar("3-120"), [3.0, 120.0])


class TrTarihTest(unittest.TestCase):
    def test_turkce_ay_adi_araligi(self):
        self.assertIn("2026-07-31", tr_tarihler("1-31 Temmuz 2026"))

    def test_iki_tam_tarih(self):
        out = tr_tarihler("01 Ocak 2026 - 31 Aralık 2026")
        self.assertIn("2026-12-31", out)

    def test_noktali_bicim(self):
        out = tr_tarihler("1.07.2023-31.08.23")
        self.assertIn("2023-08-31", out)
        self.assertIn("2023-07-01", out)


class AralikKuraliTest(unittest.TestCase):
    def test_vade_araligi_en_buyugu_alir(self):
        # Kart §3-2: aralık yazılmışsa en büyük değer.
        self.assertEqual(uygula("vade_ay", "3-120")[0], "120")

    def test_taksit_araligi_metinli(self):
        self.assertEqual(uygula("taksit_sayisi", "2 ile 3 taksit arasında")[0], "3")

    def test_alt_cizgili_aralik(self):
        self.assertEqual(uygula("vade_ay", "3_48")[0], "48")

    def test_tek_deger_oneri_uretmez(self):
        self.assertIsNone(uygula("vade_ay", "36"))


class VadeSizintisiTest(unittest.TestCase):
    """`taksit_sayisi` hücresine VADE yazılmışsa aralık düzeltmesi yapılmaz.

    Aralığı doğru daraltıp yanlış alana yazmak, `%20-%70` tuzağının aynısıdır:
    linter kabul eder, anotatör onaylar, vade sessizce taksit sayısı olur.
    """

    def test_ay_birimi_tasiyan_taksit_hucresi_oneri_uretmez(self):
        # B: vade_ay=`1-36 ay` ve taksit_sayisi=`1- 36 Ay` — aynı aralık, iki alan.
        self.assertIsNone(uygula("taksit_sayisi", "1- 36 Ay"))

    def test_vade_kardesi_ayni_araligi_tasiyorsa_oneri_uretmez(self):
        # Birim yok ama aynı anotatörün `vade_ay` hücresi aynı sayıları taşıyor.
        satir = {"_vade_ay_gold": "12ile 48 arasında değişiyor"}
        self.assertIsNone(uygula("taksit_sayisi", "12-48", satir))

    def test_gercek_taksit_araligi_ONERILIR(self):
        # "taksit" sözcüğü açıkça geçiyor, vade kardeşi farklı -> koruma susar.
        satir = {"_vade_ay_gold": "120"}
        self.assertEqual(uygula("taksit_sayisi", "3-6 taksit", satir)[0], "6")

    def test_vade_alaninda_ay_birimi_normaldir(self):
        # Koruma yalnız `taksit_sayisi` için; `vade_ay`de "ay" beklenen birimdir.
        self.assertEqual(uygula("vade_ay", "1-36 ay")[0], "36")


class TutarKuraliTest(unittest.TestCase):
    def test_ust_sinir_alinir(self):
        onerilen, _ = uygula("finansman_tutari", "600.000 TL - 1.700.000 TL")
        self.assertEqual(parse_gold_value("finansman_tutari", onerilen),
                         {"value": 1700000.0, "currency": "TRY"})

    def test_dortlu_liste_en_buyugu(self):
        onerilen, _ = uygula(
            "finansman_tutari",
            "400.000 TL, 800.000 TL, 1.200.000 TL, 2.000.000 TL")
        self.assertEqual(
            parse_gold_value("finansman_tutari", onerilen)["value"], 2000000.0)

    def test_YUZDE_iceren_hucreye_ONERI_URETILMEZ(self):
        """`%20-%70` bir ORAN'dır; tutar şemasına çevrilmesi gold'u bozar.

        Koruma kaldırılırsa `{"value": 70, "currency": "TRY"}` önerilir, linter
        bunu KABUL eder ve yanlış değer gold'a sessizce girer.
        """
        self.assertIsNone(uygula("finansman_tutari", "%20-%70"))
        self.assertIsNone(uygula("odul_miktari", "%5 - %10"))


class TarihKuraliTest(unittest.TestCase):
    def test_bitis_tarihi_alinir(self):
        self.assertEqual(uygula("kampanya_suresi", "01 Ocak 2026 - 31 Aralık 2026")[0],
                         "2026-12-31")

    def test_UZAK_YIL_ONERI_URETMEZ(self):
        """`31 Aralık 2072` büyük olasılıkla 2027 yazım hatası — betik karar vermez."""
        self.assertIsNone(
            uygula("kampanya_suresi", "14 Aralık 2021 - 31 Aralık 2072"))


class TurKuraliTest(unittest.TestCase):
    def test_katilma_hesabi_yatirim_urunu(self):
        # Kart §3-8.
        self.assertEqual(uygula("campaign_type", "Altın Katılma Hesabı")[0],
                         "Yatırım Ürünü")

    def test_leasing_finansman(self):
        self.assertEqual(uygula("campaign_type", "Leasing")[0], "Finansman")

    def test_bilinmeyen_tur_oneri_uretmez(self):
        self.assertIsNone(uygula("campaign_type", "Hediye kampanyası"))


class MasrafVePuanTest(unittest.TestCase):
    def test_ucretli_tutar_bilinmiyorsa_null(self):
        onerilen, _ = uygula("masraf_durumu", "Ücretli")
        self.assertEqual(parse_gold_value("masraf_durumu", onerilen),
                         {"has_fee": True, "amount": None})

    def test_bozuk_json_onarilir_sayi_degismez(self):
        onerilen, _ = uygula("masraf_durumu", '{"amount": 157.50}, "has_fee": true}')
        self.assertEqual(parse_gold_value("masraf_durumu", onerilen)["amount"], 157.5)

    def test_puan_TL_ile_adet_sayilir(self):
        onerilen, _ = uygula("alisveris_puani", "1.500 TL ParafPara")
        self.assertEqual(parse_gold_value("alisveris_puani", onerilen),
                         {"kind": "points", "value": 1500.0})

    def test_yuzde_iceren_puan_oneri_uretmez(self):
        self.assertIsNone(uygula("alisveris_puani", "%5 puan"))


class SemaAnahtarTest(unittest.TestCase):
    def test_rate_anahtari_duz_sayiya(self):
        self.assertEqual(uygula("kar_payi_orani", '{"rate": 3.99}')[0], "3.99")

    def test_oransal_tahsis_ucreti_bosaltilir(self):
        # Kart §3-6: para şeması oran tutamaz -> unclear.
        onerilen, gerekce = uygula("tahsis_ucreti", '{"rate": 0.5}')
        self.assertEqual(onerilen, "__BOSALT__")
        self.assertIn("unclear", gerekce)


class AbsentTest(unittest.TestCase):
    def test_absent_satirinda_deger_bosaltilir(self):
        onerilen, _ = uygula("kampanya_kosullari", "konut finansmani",
                             {"verdict": "absent"})
        self.assertEqual(onerilen, "__BOSALT__")

    def test_absent_kurali_bicim_kuralindan_once_calisir(self):
        """`absent` satırında aralık kuralı işletilmemeli — karar korunur."""
        onerilen, _ = uygula("vade_ay", "3-120", {"verdict": "absent"})
        self.assertEqual(onerilen, "__BOSALT__")


class KalipTest(unittest.TestCase):
    def test_bilinen_kaliplar(self):
        self.assertEqual(kalip("verdict=absent ama gold_value dolu ('x')"),
                         "absent-ama-deger-dolu")
        self.assertEqual(kalip("vade_ay tek deger alir ama 2 deger yazilmis"),
                         "tek-alana-coklu-deger")
        self.assertEqual(kalip("verdict=fix ama gold_value bos — build_gold"),
                         "fix-ama-deger-bos")


if __name__ == "__main__":
    unittest.main()
