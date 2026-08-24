"""Vakıf Katılım kâr paylaşım PDF ayrıştırıcısı.

İlgili: ../scripts/vakif_paylasim_pdf.py
        test_kt_paylasim_pdf.py (aynı işin Kuveyt Türk hâli, aynı çıktı şeması)

AĞSIZ: PDF metninin birebir iskeleti teste gömülü. Gerçek PDF'e bağlı bir test,
banka belgeyi güncellediği gün kodun kusuru varmış gibi kırmızıya dönerdi.

## Bu dosyanın kilitlediği ölçülmüş iki hata

1. **Uydurma kayıt.** «ÇEYİZ VE KONUT HESABI» tablosunun 95/5 oranı, kendinden
   önceki `USD ARA DÖNEM` bölümünün bağlamını devralıp «USD · 3 ay · 95/5»
   diye SAHTE bir kayıt üretiyordu. PDF'te öyle bir satır yok.
2. **Kayıp açılış bakiyesi.** Ara dönem satırları ürün adıyla başladığı için
   dilim deseni bakiyeyi (20.000 / 150.000) yakalayamıyordu.
"""

from __future__ import annotations

import unittest

from scripts.vakif_paylasim_pdf import ayristir

# Gerçek PDF'in `pdftotext -layout` çıktısının iskeleti (2026-08-24 sürümü).
PDF_METNI = """                         KÂR PAYLAŞIM ORANLARI TABLOSU
                                        TL KATILMA HESAPLARI
            TL              1 Ay (%)      3 Ay (%)     6 Ay (%)   1 Yıl (%)   1 Yıldan Uzun Vade (%)
       250-99.999             85/15         85/15        85/15      85/15            85/15
    100.000-249.999           90/10         90/10        90/10      90/10            90/10
       Stopaj Oranı                       17.5%                      15%              10%
                                        USD KATILMA HESAPLARI
           USD              1 Ay (%)      3 Ay (%)     6 Ay (%)   1 Yıl (%)   1 Yıldan Uzun Vade (%)
        250-49.999            40/60         40/60        40/60      40/60            40/60
       Stopaj Oranı                         25%                      25%              25%
                                       ALTIN KATILMA HESAPLARI
          ALTIN               3 Ay (%)     6 Ay (%)    1 Yıl (%)          1 Yıldan Uzun Vade (%)
      50 gr ve üzeri            10/90        10/90        10/90                    10/90
                          TL ARA DÖNEM KÂR PAYI ÖDEMELİ KATILMA HESABI
       AÇILIŞ BAKİYESİ    Açılış Bakiyesi  1 Ay (31 Gün)  3 Ay (93 Gün)  6 Ay (186 Gün)  1 Yıl (372 Gün)   Stopaj Oranı
      Alternatif Yatırım (TL)   20.000        85/15          86/14          88/12           92/8              10%
        Yatırım (TL)           150.000        90/10          90/10          91/9            93/7              10%
                                        ÇEYİZ VE KONUT HESABI
                     Hesap Tipi              Birikim Tutarları        Asgari 3 Yıl-Azami 10 Yıl
                                     Asgari    1,804.57      5,413.78
Çeyiz Hesabı
                                                                            95/5
"""


class TestBolumVeParaBirimi(unittest.TestCase):
    def setUp(self) -> None:
        self.k = list(ayristir(PDF_METNI, damga="2026-08-24T00:00:00+00:00"))

    def test_dort_para_birimi_ayri_ayri(self) -> None:
        self.assertEqual({x["currency"] for x in self.k}, {"TRY", "USD", "XAU"})

    def test_altin_tablosunda_bir_ay_sutunu_YOK(self) -> None:
        """ALTIN tablosu 3 Ay'dan başlıyor; sabit sıra varsayımı hepsini kaydırırdı."""
        altin = [x for x in self.k if x["currency"] == "XAU"]
        self.assertEqual(sorted(x["term_months"] for x in altin
                                if x["term_months"]), [3, 6, 12])
        self.assertNotIn(1, [x["term_months"] for x in altin])

    def test_uzun_vade_None(self) -> None:
        """«1 Yıldan Uzun Vade» bir kovadır; ona sayı atamak uydurma olurdu."""
        self.assertTrue(any(x["term_months"] is None for x in self.k))


class TestPaylar(unittest.TestCase):
    def setUp(self) -> None:
        self.k = list(ayristir(PDF_METNI, damga="2026-08-24T00:00:00+00:00"))

    def test_kucuk_bakiye_bes_puan_dusuk(self) -> None:
        """Segment ayrımının kendisi: 250-99.999 → %85, 100.000+ → %90."""
        tl12 = {x["segment"]: x["annual_rate"] for x in self.k
                if x["currency"] == "TRY" and x["term_months"] == 12
                and x["product_name"] == "Katılma Hesabı"}
        self.assertEqual(tl12["250-99.999"], 85.0)
        self.assertEqual(tl12["100.000-249.999"], 90.0)

    def test_banka_payi_da_kaydedilir(self) -> None:
        x = next(x for x in self.k if x["segment"] == "250-99.999")
        self.assertEqual((x["annual_rate"], x["bank_share"]), (85.0, 15.0))

    def test_hepsi_pay_buyuklugu(self) -> None:
        """Getiri ile aynı kolonda kıyaslanmasınlar diye ETİKETLİ."""
        self.assertEqual({x["buyukluk"] for x in self.k}, {"pay"})

    def test_stopaj_satiri_kayit_URETMEZ(self) -> None:
        self.assertFalse([x for x in self.k
                          if x["segment"] and "stopaj" in x["segment"].lower()])


class TestCeyizBolumuUYDURMAZ(unittest.TestCase):
    """ÖLÇÜLMÜŞ HATA: 95/5 oranı USD bağlamını devralıp sahte kayıt üretiyordu."""

    def setUp(self) -> None:
        self.k = list(ayristir(PDF_METNI, damga="2026-08-24T00:00:00+00:00"))

    def test_95_5_kaydi_YOK(self) -> None:
        self.assertFalse([x for x in self.k if x["annual_rate"] == 95.0],
                         "Çeyiz/Konut tablosundan kayıt üretilmemeli — satır ile "
                         "oranı metinden güvenle bağlayamıyoruz")

    def test_ceyiz_baslıgindan_sonra_USD_bağlami_KAPANIR(self) -> None:
        usd = [x for x in self.k if x["currency"] == "USD"]
        self.assertTrue(all(x["annual_rate"] == 40.0 for x in usd),
                        "USD tablosunda yalnız 40/60 var; başka oran sızmış")


class TestAraDonem(unittest.TestCase):
    def setUp(self) -> None:
        self.k = [x for x in ayristir(PDF_METNI, damga="2026-08-24T00:00:00+00:00")
                  if "Ara Dönem" in x["product_name"]]

    def test_urun_adi_ayri(self) -> None:
        self.assertEqual({x["product_name"] for x in self.k},
                         {"Ara Dönem Kâr Payı Ödemeli Katılma Hesabı"})

    def test_acilis_bakiyesi_okunur(self) -> None:
        """ÖLÇÜLMÜŞ HATA: satır ürün adıyla başladığı için bakiye kaçıyordu."""
        b = {x["segment"]: x["opening_balance"] for x in self.k}
        self.assertEqual(b["Alternatif Yatırım (TL)"], 20000.0)
        self.assertEqual(b["Yatırım (TL)"], 150000.0)

    def test_vade_ilerledikce_pay_artar(self) -> None:
        """Ara dönem ürününün tezi bu: uzun vade daha yüksek pay."""
        alt = {x["term_months"]: x["annual_rate"] for x in self.k
               if x["segment"] == "Alternatif Yatırım (TL)"}
        self.assertEqual([alt[1], alt[3], alt[6], alt[12]], [85.0, 86.0, 88.0, 92.0])


class TestProvenance(unittest.TestCase):
    def setUp(self) -> None:
        self.k = list(ayristir(PDF_METNI, damga="2026-08-24T00:00:00+00:00"))

    def test_kaynak_ve_damga_her_kayitta(self) -> None:
        for x in self.k:
            self.assertTrue(x["source_url"].endswith(".pdf"))
            self.assertEqual(x["collected_at"], "2026-08-24T00:00:00+00:00")

    def test_manuel_toplama_yontemi_KAYITLI(self) -> None:
        """robots.txt engeli ve §5.1 gerekçesi kaydın İÇİNDE durmalı."""
        self.assertEqual({x["method"] for x in self.k}, {"banka-pdf-manuel"})
        self.assertIn("robots.txt", self.k[0]["note"])

    def test_toplam_100_denetimi_var(self) -> None:
        self.assertTrue(all(x["toplam"] == 100.0 for x in self.k))
        self.assertFalse(any(x["toplam_tutarsiz"] for x in self.k))


if __name__ == "__main__":                   # pragma: no cover
    unittest.main()
