"""Regresyon kapısı: kazanılan F1 sessizce geri gitmemeli.

İlgili: ../eval/run_eval.py (`esik_ihlalleri`), ../eval/esikler.json
        ../../.github/workflows/ci.yml ("Eval regresyon kapisi" adımı)

## Bu kapının varlık sebebi (plan G1.5)

FAZ 1'de üç alan ölçülerek düzeltildi:

    vade_ay          0,133 -> 0,545   (975af3c)
    kar_payi_orani   0,500 -> 0,800   (8003bae)
    indirim_orani    0,000 -> 0,400   (378305c)

Bu kazanımların sessizce geri gitme riski gerçektir: bir regex'i gevşetmek
başka bir alanı bozabilir ve hiçbir birim testi kırılmayabilir — çünkü bu
alanların doğruluğu gold sete karşı ÖLÇÜLÜR, tek tek assert edilmez.

Kapı üç şeyi birden korur:
  1. alan bazında asgari F1,
  2. yapısal mikro-F1 (serbest metin hariç kesit),
  3. halüsinasyon oranının ÜST sınırı — ters yönlü kapı, çünkü bu projede
     uydurmak kaçırmaktan pahalıdır (CLAUDE.md §19).

## Eşik dosyası neden bir "hedef listesi" DEĞİL

`eval/esikler.json` mevcut başarımın hemen altındadır; "daha iyisini yap"
demez, "bugünkünü kaybetme" der. Gold büyüdüğünde (G3.1: 48 -> 70) sayılar
doğal olarak düşebilir; bu gerileme değil genelleme ölçümüdür ve dosya
BİLEREK, gerekçesi commit mesajına yazılarak güncellenir.
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from eval.run_eval import Counts, esik_ihlalleri

_KOK = Path(__file__).resolve().parent.parent
ESIK_DOSYASI = _KOK / "eval" / "esikler.json"


def _c(tp=0, fp=0, fn=0, tn=0, uydurma=0) -> Counts:
    c = Counts()
    c.tp, c.fp, c.fn, c.tn = tp, fp, fn, tn
    c.fp_hallucinated = uydurma
    return c


class TestEsikDosyasi(unittest.TestCase):
    """Dosyanın kendisi tutarlı mı — CI ona güveniyor."""

    @classmethod
    def setUpClass(cls):
        cls.esikler = json.loads(ESIK_DOSYASI.read_text(encoding="utf-8"))

    def test_dosya_okunabilir_ve_alanlari_var(self):
        self.assertIn("alanlar", self.esikler)
        self.assertGreater(len(self.esikler["alanlar"]), 5)

    def test_esikler_makul_bantta(self):
        for alan, v in self.esikler["alanlar"].items():
            with self.subTest(alan=alan):
                self.assertTrue(0.0 <= float(v) <= 1.0, f"{alan}={v}")

    def test_serbest_metin_alanina_esik_KONMAZ(self):
        """`kampanya_kosullari` span-F1'i anlamsız; ona eşik koymak yanlış olur."""
        self.assertNotIn("kampanya_kosullari", self.esikler["alanlar"])

    def test_desteksiz_alana_esik_KONMAZ(self):
        """`tahsis_ucreti` gold.v2'de 0 pozitif örneğe sahip; F1 tanımsız."""
        self.assertNotIn("tahsis_ucreti", self.esikler["alanlar"])

    def test_neden_disarida_kaldiklari_YAZILI(self):
        haric = self.esikler.get("_esigi_olmayan_alanlar", {})
        for alan in ("kampanya_kosullari", "tahsis_ucreti"):
            with self.subTest(alan=alan):
                self.assertIn(alan, haric,
                              "eşiksiz alanın gerekçesi dosyada yazılı değil")


class TestKapiMantigi(unittest.TestCase):

    ESIK = {
        "tolerans": 0.01,
        "alanlar": {"vade_ay": 0.500},
        "mikro_yapisal": 0.600,
        "halusinasyon_ust_sinir": 0.08,
    }

    def test_esik_korunuyorsa_kapi_ACIK(self):
        tablo = {"vade_ay": _c(tp=6, fp=2, fn=2, tn=40)}
        self.assertEqual(esik_ihlalleri(tablo, self.ESIK), [])

    def test_f1_duserse_kapi_KAPANIR(self):
        tablo = {"vade_ay": _c(tp=1, fp=9, fn=4, tn=40)}
        ihlaller = esik_ihlalleri(tablo, self.ESIK)
        self.assertTrue(any("vade_ay" in i for i in ihlaller))

    def test_tolerans_kadar_dusus_AFFEDILIR(self):
        # F1 = 0.4977 — eşiğin 0,002 altı, tolerans 0,01 içinde.
        tablo = {"vade_ay": _c(tp=54, fp=54, fn=55, tn=40)}
        self.assertNotIn(
            "vade_ay", " ".join(esik_ihlalleri(tablo, self.ESIK)))

    def test_alan_kaybolursa_kapi_KAPANIR(self):
        """Alanı silmek, eşiği geçmenin kolay yolu olmamalı."""
        ihlaller = esik_ihlalleri({}, self.ESIK)
        self.assertTrue(any("vade_ay" in i for i in ihlaller))

    def test_halusinasyon_ARTARSA_kapi_KAPANIR(self):
        """Ters yönlü kapı: uydurmak kaçırmaktan pahalıdır."""
        tablo = {"vade_ay": _c(tp=6, fp=20, fn=2, tn=40, uydurma=20)}
        ihlaller = esik_ihlalleri(tablo, self.ESIK)
        self.assertTrue(any("halüsinasyon" in i for i in ihlaller))

    def test_bos_esik_dosyasi_kapiyi_ACIK_birakir(self):
        self.assertEqual(esik_ihlalleri({"vade_ay": _c(tp=1)}, {}), [])


if __name__ == "__main__":                                # pragma: no cover
    unittest.main()
