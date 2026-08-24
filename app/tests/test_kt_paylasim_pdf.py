"""Kuveyt Türk paylaşım PDF'i ayrıştırıcısı — segment × vade × para birimi.

İlgili: ../scripts/kt_paylasim_pdf.py

AĞSIZ ve PDF'SİZ: `pdftotext` çıktısının birebir biçimi teste gömülü. Gerçek
PDF'e bağlı bir test, dosya yoksa kırmızıya dönerdi ve bu kodun kusuru
olmazdı.
"""

from __future__ import annotations

import unittest

from scripts.kt_paylasim_pdf import PARA_KODU, VADELER, kayitlar

# `pdftotext -layout` çıktısının birebir kesiti (2026-08-24 sürümü).
METIN = """                                    TL KATILMA HESAPLARI
          Açılış Bakiyesi                          1 Aylık   3 Aylık   6 Aylık   1 Yıllık  1 Yıldan Uzun
           Alt Bakiye        2-6 Gün  7-20 Gün  21-29 Gün
Klasik Hesap    250-250        75-25     79-21     82-18     85-15     86-14     88-12     88-12     88-12
Gümüş Hesap   25.000-15.000    77-23     91-19     84-16     87-13     88-12     91-9      91-9      91-9
 Altın Hesap  100.000-75.000   80-20     84-16     87-13     90-10     91-9      93-7      93-7      93-7
Platin Hesap  500.000-375.000  82-18     86-14     89-11     92-8      93-7      94-6      94-6      94-6
Platin+ Hesap 1.250.000-1.000.000 84-16  88-12     91-9      94-6      94-6      95-5      95-5      95-5
                Stopaj Oranları   %17,5   %17,5    %17,5     %17,5     %17,5     %17,5     %15       %10

                                   EURO KATILMA HESAPLARI
Klasik Hesap    1.000-1.000     40-60    40-60     40-60     40-60     40-60     40-60     40-60     40-60

                     TL ARA DÖNEM KÂR PAYI ÖDEMELİ KATILMA HESAPLARI
                                          1 Aylık      3 Aylık     6 Aylık     1 Yıl
   Alternatif Yatırım Hesabı  20.000-10.000  90-10      90-10       90-10       90-10
        Yatırım Hesabı        150.000-75.000  95-5       95-5        95-5        95-5
"""


def _k():
    return list(kayitlar(METIN, toplandi="2026-08-24T00:00:00+00:00"))


class TestAyristirma(unittest.TestCase):
    def test_ana_tablolar_KACIRILMAZ(self):
        """Ölçülmüş kusur: 'Klasik HesaP' ama 'Yatırım HesaBı' — ünsüz
        yumuşaması. Yalnız 'Hesabı' aramak ANA TABLOLARIN TAMAMINI kaçırdı."""
        segmentler = {k["segment"] for k in _k()}
        for s in ("Klasik Hesabı", "Gümüş Hesabı", "Altın Hesabı",
                  "Platin Hesabı", "Platin+ Hesabı"):
            with self.subTest(s=s):
                self.assertIn(s, segmentler)

    def test_klasik_TL_degerleri(self):
        k = {x["term_label"]: x for x in _k()
             if x["segment"] == "Klasik Hesabı" and x["currency"] == "TRY"}
        self.assertEqual(k["1 Aylık"]["annual_rate"], 85.0)
        self.assertEqual(k["1 Aylık"]["bank_share"], 15.0)
        self.assertEqual(k["2-6 Gün"]["annual_rate"], 75.0)
        self.assertEqual(k["1 Yıldan Uzun"]["annual_rate"], 88.0)

    def test_para_birimi_bolumu_izlenir(self):
        eur = [x for x in _k() if x["currency"] == "EUR"]
        self.assertTrue(eur)
        self.assertEqual({x["annual_rate"] for x in eur}, {40.0})

    def test_ara_donem_urunu_AYRI_isaretlenir(self):
        ara = [x for x in _k()
               if x["product_name"].startswith("Ara Dönem")]
        self.assertEqual({x["segment"] for x in ara},
                         {"Alternatif Yatırım Hesabı", "Yatırım Hesabı"})
        # Ara dönem tablosunda 4 sütun var; ilk vade 1 ay olmalı
        self.assertEqual(min(x["term_months"] for x in ara), 1)

    def test_bakiye_dilimleri_okunur(self):
        gumus = next(x for x in _k() if x["segment"] == "Gümüş Hesabı")
        self.assertEqual(gumus["opening_balance"], 25000.0)
        self.assertEqual(gumus["min_balance"], 15000.0)

    def test_binlik_ayracli_buyuk_bakiye(self):
        p = next(x for x in _k() if x["segment"] == "Platin+ Hesabı")
        self.assertEqual(p["opening_balance"], 1_250_000.0)

    def test_buyukluk_PAY_olarak_isaretlenir(self):
        """'85-15' bir BÖLÜŞÜMDÜR; dağıtılan getiriyle kıyaslanamaz."""
        self.assertEqual({x["buyukluk"] for x in _k()}, {"pay"})

    def test_pay_ve_banka_payi_normalde_100_yapar(self):
        tutarli = [x for x in _k() if not x["toplam_tutarsiz"]]
        self.assertTrue(tutarli)
        for x in tutarli:
            with self.subTest(seg=x["segment"], vade=x["term_label"]):
                self.assertEqual(x["annual_rate"] + x["bank_share"], 100.0)

    def test_KAYNAKTAKI_tutarsizlik_isaretlenir_gizlenmez(self):
        """Ölçülmüş vaka: PDF'te Gümüş Hesap '7-20 Gün' = 91-19 → toplam 110.

        Değer DÜZELTİLMEZ (kaynağı çarpıtmak olurdu) ve satır ATILMAZ (bilgi
        kaybı olurdu); işaretlenir — CLAUDE.md HARD RULES §4.
        """
        tutarsiz = [x for x in _k() if x["toplam_tutarsiz"]]
        self.assertEqual(len(tutarsiz), 1)
        x = tutarsiz[0]
        self.assertEqual((x["segment"], x["term_label"]),
                         ("Gümüş Hesabı", "7-20 Gün"))
        self.assertEqual(x["toplam"], 110.0)
        # Ham değerler KORUNUR
        self.assertEqual((x["annual_rate"], x["bank_share"]), (91.0, 19.0))

    def test_provenance(self):
        x = _k()[0]
        self.assertEqual(x["method"], "banka-pdf")
        self.assertEqual(x["bank_slug"], "kuveyt-turk")
        self.assertIn("kuveytturk", x["source_url"])
        self.assertEqual(x["collected_at"], "2026-08-24T00:00:00+00:00")

    def test_stopaj_satiri_kayit_URETMEZ(self):
        """'Stopaj Oranları' bir segment değil; kayda girmemeli."""
        self.assertFalse([x for x in _k() if "Stopaj" in x["segment"]])

    def test_bos_metin_kayit_uretmez(self):
        self.assertEqual(list(kayitlar("", toplandi="z")), [])

    def test_bolum_basligi_olmadan_satir_ATLANIR(self):
        """Para birimi bölümü görülmeden gelen segment satırı kayda girmez —
        hangi para birimine ait olduğu bilinmez ve varsayılmamalı."""
        basliksiz = "Klasik Hesap    250-250   75-25   79-21   82-18\n"
        self.assertEqual(list(kayitlar(basliksiz, toplandi="z")), [])


class TestSabitler(unittest.TestCase):
    def test_para_kodu_eslemesi(self):
        self.assertEqual(PARA_KODU["TL"], "TRY")
        self.assertEqual(PARA_KODU["ALTIN"], "XAU")

    def test_sekiz_vade_sutunu(self):
        self.assertEqual(len(VADELER), 8)
        self.assertEqual([v[1] for v in VADELER[3:7]], [1, 3, 6, 12])


if __name__ == "__main__":
    unittest.main()
