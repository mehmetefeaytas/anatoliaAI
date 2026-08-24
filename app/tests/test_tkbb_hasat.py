"""TKBB hasat betikleri — ayrıştırma, birim çevrimi, güvenlik kapısı.

İlgili: ../scripts/tkbb_karpayi_hasat.py (tarihsel arşiv, 2012–2025)
        ../scripts/tkbb_guncel_hasat.py (bu haftanın oranları)

AĞSIZ: her test elle kurulmuş HTML/JSON üzerinde çalışır. Hasat uçlarına
bağlanan bir test, ağ koptuğunda kodun bozulduğunu söylerdi.
"""

from __future__ import annotations

import gzip
import io
import json
import pathlib
import tempfile
import unittest

from scripts import tkbb_guncel_hasat as guncel
from scripts import tkbb_karpayi_hasat as tarihsel

# Uçtan gelen tablonun birebir biçimi: 3 boyut kolonu + vade×para_birimi.
_HTML = """<table>
<tr><th>Yıl</th><th>Ay</th><th>Gün</th><th>Aylık</th></tr>
<tr><td>2024</td><td>Ocak</td><td>01 Ocak Pazartesi</td>
    <td>31,38</td><td>0,93</td><td>0,6</td><td>-</td>
    <td>32,68</td><td>0,92</td><td>0,61</td><td>-</td>
    <td>27,07</td><td>0,94</td><td>0,63</td><td>-</td>
    <td>24,16</td><td>1,43</td><td>1,06</td><td>0,01</td></tr>
</table>"""


class TestSayiCevrimi(unittest.TestCase):
    def test_tr_ondalik_ayraci(self):
        self.assertEqual(tarihsel._sayi("31,38"), 31.38)
        self.assertEqual(tarihsel._sayi("1.500,25"), 1500.25)

    def test_yokluk_None_dondurur(self):
        """0 bir ORANDIR, yokluk değil — ayrım korunmalı."""
        for t in ("", "  ", "-", "—", None):
            with self.subTest(t=t):
                self.assertIsNone(tarihsel._sayi(t))
        self.assertEqual(tarihsel._sayi("0"), 0.0)

    def test_ayristirilamayan_None(self):
        self.assertIsNone(tarihsel._sayi("yok"))


class TestTarih(unittest.TestCase):
    def test_iso_cevrimi(self):
        self.assertEqual(tarihsel._tarih("2024", "Ocak", "01 Ocak Pazartesi"),
                         "2024-01-01")
        self.assertEqual(tarihsel._tarih("2025", "Mayıs", "26 Mayıs Pazartesi"),
                         "2025-05-26")

    def test_gecersiz_tarih_None(self):
        self.assertIsNone(tarihsel._tarih("2024", "Ocak", ""))
        self.assertIsNone(tarihsel._tarih("abcd", "Ocak", "01 Ocak Pazartesi"))
        self.assertIsNone(tarihsel._tarih("2024", "Ocak", "32 Ocak Pazartesi"))


class TestTarihselAyristirma(unittest.TestCase):
    def test_kolon_duzeni_vade_dis_para_ic(self):
        k = list(tarihsel.kayitlar(_HTML, bank_slug="albaraka", sheet_index=0,
                                   toplandi="2026-08-24T00:00:00+00:00"))
        # 16 hücrenin 3'ü '-' → 13 kayıt
        self.assertEqual(len(k), 13)
        ilk = k[0]
        self.assertEqual((ilk["term_months"], ilk["currency"],
                          ilk["annual_rate"]), (1, "TRY", 31.38))
        # ikinci hücre AYNI vadenin USD'si (para birimi iç döngü)
        self.assertEqual((k[1]["term_months"], k[1]["currency"]), (1, "USD"))
        # dördüncü vadeye geçiş: 12 ay TRY = 24,16
        onikiay = [x for x in k if x["term_months"] == 12
                   and x["currency"] == "TRY"]
        self.assertEqual(onikiay[0]["annual_rate"], 24.16)

    def test_bos_hucre_kayit_URETMEZ(self):
        k = list(tarihsel.kayitlar(_HTML, bank_slug="albaraka", sheet_index=0,
                                   toplandi="x"))
        # XAU yalnız 12 ay vadede dolu (0,01); öteki üç vadede '-'
        xau = [x for x in k if x["currency"] == "XAU"]
        self.assertEqual(len(xau), 1)
        self.assertEqual(xau[0]["term_months"], 12)

    def test_buyukluk_alani_rapora_gore(self):
        """getiri ile pay aynı kolonda yarışmamalı; ayrım kayıtta taşınır."""
        g = next(iter(tarihsel.kayitlar(_HTML, bank_slug="a", sheet_index=0,
                                        toplandi="x")))
        p = next(iter(tarihsel.kayitlar(_HTML, bank_slug="a", sheet_index=1,
                                        toplandi="x")))
        self.assertEqual(g["buyukluk"], "getiri")
        self.assertEqual(p["buyukluk"], "pay")

    def test_provenance_alanlari(self):
        k = next(iter(tarihsel.kayitlar(_HTML, bank_slug="albaraka",
                                        sheet_index=0, toplandi="ZAMAN")))
        self.assertEqual(k["collected_at"], "ZAMAN")
        self.assertEqual(k["method"], "tkbb-veriseti")
        self.assertIn("tkbb.org.tr", k["source_url"])
        # TLS doğrulamasının atlandığı KAYDA GEÇMELİ
        self.assertEqual(k["tls_dogrulama"], "atlandi")


class TestGuvenlikKapisi(unittest.TestCase):
    def test_sertifika_bayragi_olmadan_CALISMAZ(self):
        """Doğrulama atlamak sessiz varsayılan OLAMAZ."""
        hata = io.StringIO()
        import contextlib
        with contextlib.redirect_stderr(hata):
            kod = tarihsel.main([])
        self.assertEqual(kod, 2)
        self.assertIn("sertifika", hata.getvalue().lower())

    def test_bankasya_listede_YOK(self):
        """Kapalı banka; uç boş yanıt veriyor."""
        self.assertNotIn("4e42976e7f8d238db263ff090660518a", tarihsel.BANKALAR)
        self.assertEqual(len(tarihsel.BANKALAR), 9)


class TestGzipYazma(unittest.TestCase):
    def test_gzip_yazilir_ve_okunur(self):
        with tempfile.TemporaryDirectory() as d:
            kok = pathlib.Path(d)
            n = tarihsel._yaz(kok, "albaraka", [{"a": 1}, {"a": 2}])
            hedef = kok / "data" / "raw" / "albaraka" / "rates" / \
                "tkbb-karpayi.jsonl.gz"
            self.assertEqual(n, 2)
            self.assertTrue(hedef.exists())
            with gzip.open(hedef, "rt", encoding="utf-8") as f:
                self.assertEqual([json.loads(x) for x in f],
                                 [{"a": 1}, {"a": 2}])


_PIVOT = {"data": [{"type": "data", "id": "DL-x", "attributes": {"rows": [
    {"banka": "Albaraka Türk Katılım Bankası A.Ş.",
     "Aylık|m0": 31.35, "3 Aylık|m0": 32.22, "Yıllık|m0": 40.85,
     "Aylık|m1": 0.93, "Aylık|m3": "", "Yıllık|m3": None},
    {"banka": "Bilinmeyen Banka A.Ş.", "Aylık|m0": 99.0},
]}}]}


class TestGuncelAyristirma(unittest.TestCase):
    def test_kolon_adindan_vade_ve_para_birimi(self):
        k = list(guncel.kayitlar(_PIVOT, dashlet="DL-FFC6K484A682B8I",
                                 toplandi="Z", donem="2026-08-24"))
        eslesen = {(x["term_months"], x["currency"]): x["annual_rate"]
                   for x in k}
        self.assertEqual(eslesen[(1, "TRY")], 31.35)
        self.assertEqual(eslesen[(3, "TRY")], 32.22)
        self.assertEqual(eslesen[(12, "TRY")], 40.85)
        self.assertEqual(eslesen[(1, "USD")], 0.93)

    def test_bos_ve_None_atlanir(self):
        k = list(guncel.kayitlar(_PIVOT, dashlet="DL-FFC6K484A682B8I",
                                 toplandi="Z", donem="2026-08-24"))
        self.assertFalse([x for x in k if x["currency"] == "XAU"])

    def test_bilinmeyen_banka_ATLANIR(self):
        """Slug eşlemesi olmayan banka sessizce dışta kalır, uydurulmaz."""
        k = list(guncel.kayitlar(_PIVOT, dashlet="DL-FFC6K484A682B8I",
                                 toplandi="Z", donem="2026-08-24"))
        self.assertEqual({x["bank_slug"] for x in k}, {"albaraka"})

    def test_buyukluk_dashlete_gore(self):
        g = next(iter(guncel.kayitlar(_PIVOT, dashlet="DL-FFC6K484A682B8I",
                                      toplandi="Z", donem="d")))
        p = next(iter(guncel.kayitlar(_PIVOT, dashlet="DL-0M0C2ABB615D062",
                                      toplandi="Z", donem="d")))
        self.assertEqual(g["buyukluk"], "getiri")
        self.assertEqual(p["buyukluk"], "pay")

    def test_period_date_turetilmis_oldugu_YAZILIR(self):
        """Uç tarih döndürmüyor; türetilmiş bir tarih ölçülmüş gibi durmamalı."""
        k = next(iter(guncel.kayitlar(_PIVOT, dashlet="DL-FFC6K484A682B8I",
                                      toplandi="Z", donem="2026-08-24")))
        self.assertEqual(k["period_date"], "2026-08-24")
        self.assertIn("turetilmis", k["period_date_kaynak"])

    def test_hafta_basi_pazartesiye_yuvarlar(self):
        import datetime
        # 2026-08-27 bir Perşembe → haftanın Pazartesi'si 2026-08-24
        self.assertEqual(guncel._hafta_basi(datetime.date(2026, 8, 27)),
                         "2026-08-24")
        self.assertEqual(guncel._hafta_basi(datetime.date(2026, 8, 24)),
                         "2026-08-24")

    def test_para_birimi_eslemesi_SABIT(self):
        """Sıra değişirse sessizce yanlış para birimine yazılmasın."""
        self.assertEqual(guncel.PARA_BIRIMI,
                         {"m0": "TRY", "m1": "USD", "m2": "EUR", "m3": "XAU"})

    def test_dokuz_banka_eslemesi(self):
        self.assertEqual(len(guncel.BANKA_SLUG), 9)
        self.assertEqual(guncel.BANKA_SLUG["T.O.M. Katılım Bankası A.Ş."],
                         "tom-katilim")


if __name__ == "__main__":
    unittest.main()
