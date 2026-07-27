"""Çelişki tespiti + tahsis_ucreti çıkarımı regresyon testleri.

İlgili: ../../decisions/daraltilmis-yenilikcilik-hedefleri.md (hedef #2)
        ../src/comparison/contradiction.py
        docs/08-problemler-ve-cozumler.md (H2)

Arka plan: `contradiction.detect()` birincil kuralı (`masrafsiz_ama_ucret`) hem
`masraf_durumu` hem `tahsis_ucreti` alanını ister. Kural katmanı `tahsis_ucreti`
alanını hiç üretmediği için bu kural HİÇ tetiklenemiyordu — yani yenilikçilik
hedefi #2 ölüydü.

Ayrıca `extract_masraf` `re.search` (yalnız ilk eşleşme) kullandığı için sonuç
metindeki yazım SIRASINA bağlıydı: "masrafsız ... tahsis 500 TL" çelişkiyi
yakalıyor ama "tahsis 500 TL ... masrafsız" kaçırıyordu.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.comparison.contradiction import detect
from src.extraction.rules.extract import extract_all, extract_tahsis_ucreti
from src.schemas import Campaign


def _campaign(text: str) -> Campaign:
    return Campaign(bank_slug="test", raw_text=text, fields=extract_all(text))


class TestTahsisUcreti(unittest.TestCase):
    """Alan artık üretiliyor mu, doğru üretiliyor mu?"""

    def test_pozitif_tutar(self):
        f = extract_tahsis_ucreti("tahsis ücreti 500 TL")
        self.assertEqual(f.canonical_value, {"value": 500.0, "currency": "TRY"})

    def test_binlik_ayirici_noktasi_cumle_sonu_sanilmaz(self):
        # REGRESYON: '.' hem cümle sonu hem binlik ayırıcı. Naif split
        # "1.500,00" ifadesini "1"de kesip 1500 yerine 1.0 üretiyordu.
        f = extract_tahsis_ucreti("Tahsis ücreti 1.500,00 TL olarak tahsil edilir.")
        self.assertEqual(f.canonical_value["value"], 1500.0)

        f2 = extract_tahsis_ucreti("Dosya masrafı 2.750,50 TL.")
        self.assertEqual(f2.canonical_value["value"], 2750.5)

    def test_negasyon_sifir_demektir_bilgi_yok_degil(self):
        for text in ["TAHSİS ÜCRETİ ALINMAZ", "dosya masrafı yoktur",
                     "tahsis ücreti talep edilmez", "tahsis ücreti alınmıyor"]:
            f = extract_tahsis_ucreti(text)
            self.assertIsNotNone(f, f"alan üretilmedi: {text!r}")
            self.assertEqual(f.canonical_value["value"], 0.0, text)

    def test_hic_gecmiyorsa_uydurmaz(self):
        self.assertIsNone(extract_tahsis_ucreti("hava güzel"))
        self.assertIsNone(extract_tahsis_ucreti("kâr payı oranı %1,89"))

    def test_masraf_durumundan_bagimsiz_uretilir(self):
        # İkisi de aynı metinden, birbirinden bağımsız çıkmalı.
        names = {f.field_name for f in extract_all("Masrafsızdır, tahsis ücreti 500 TL.")}
        self.assertIn("masraf_durumu", names)
        self.assertIn("tahsis_ucreti", names)


class TestCelisikiTespiti(unittest.TestCase):
    """H2: kural artık tetikleniyor ve yazım sırasından bağımsız."""

    def test_celiski_normal_sirada(self):
        c = _campaign("Bu kampanya masrafsızdır. Ancak tahsis ücreti 500 TL "
                      "olarak tahsil edilir.")
        self.assertEqual([x.kind for x in detect(c)], ["masrafsiz_ama_ucret"])

    def test_celiski_ters_sirada(self):
        # REGRESYON: extract_masraf re.search kullandığı için bu kaçıyordu.
        c = _campaign("Tahsis ücreti 500 TL olarak tahsil edilir. "
                      "Bu kampanya masrafsızdır.")
        self.assertEqual([x.kind for x in detect(c)], ["masrafsiz_ama_ucret"])

    def test_celiski_all_caps(self):
        c = _campaign("BU KAMPANYA MASRAFSIZDIR. TAHSİS ÜCRETİ 500 TL ALINIR.")
        self.assertEqual([x.kind for x in detect(c)], ["masrafsiz_ama_ucret"])

    def test_tutarli_metinde_celiski_yok(self):
        # Gerçekten masrafsız — yanlış pozitif üretmemeli.
        c = _campaign("Kampanya masrafsızdır, tahsis ücreti alınmaz.")
        self.assertEqual(detect(c), [])

    def test_sadece_ucret_varsa_celiski_yok(self):
        # Masrafsızlık iddiası yok, sadece ücret var.
        c = _campaign("Tahsis ücreti 500 TL alınır.")
        self.assertEqual(detect(c), [])

    def test_celiski_detayinda_tutar_gecer(self):
        c = _campaign("Masrafsızdır. Tahsis ücreti 500 TL.")
        con = detect(c)[0]
        self.assertIn("500", con.detail)
        self.assertEqual(set(con.fields), {"masraf_durumu", "tahsis_ucreti"})


class TestMasrafIddiasi(unittest.TestCase):
    """masraf_durumu kampanyanın İDDİASINI taşır (sıradan bağımsız)."""

    def test_masrafsiz_iddiasi_sirasi_ne_olursa_olsun_kazanir(self):
        for text in ["Masrafsızdır. Tahsis ücreti 500 TL.",
                     "Tahsis ücreti 500 TL. Masrafsızdır."]:
            d = {f.field_name: f.canonical_value for f in extract_all(text)}
            self.assertIs(d["masraf_durumu"]["has_fee"], False, text)

    def test_iddia_yoksa_gercek_ucret_raporlanir(self):
        d = {f.field_name: f.canonical_value for f in extract_all("Tahsis ücreti 500 TL alınır.")}
        self.assertIs(d["masraf_durumu"]["has_fee"], True)
        self.assertEqual(d["masraf_durumu"]["amount"], 500.0)


if __name__ == "__main__":
    unittest.main()
