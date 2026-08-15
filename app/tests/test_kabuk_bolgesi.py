"""Kabuk bölgesi kapısı — komşu kampanyanın değeri bu belgeye yazılmasın.

İlgili: ../src/extraction/rules/kabuk.py
        ../src/extraction/rules/extract.py (`extract_all` sonundaki süzgeç)
        ../data/gold/ANNOTATION_GUIDE.md §4.13/8

## Neden bu testler

Kural KILAVUZDA vardı, KODDA yoktu. Gümüş turunun kör kalite testinde
ölçüldü: A ve B'nin bağımsız olarak AYNI kararı verdiği 60 hücrenin 9'unda
iki insan da kabuk değerini ONAYLAMIŞTI.

## En kritik test buradaki NEGATİF tuzaktır

Naif tasarım ("işaretten metin sonuna kadar at") gold'da 16+5 gerçek değer
öldürdü: bu işaretler belgede medyan %8–19 konumunda duruyor, yani üst
menüde. `test_menudeki_TEK_baglanti_govdeyi_kesmez` tam o regresyonun kilidi;
düşerse kapı gövdeyi yiyor demektir.

## Ölçülen etki (gold.v2, strict, `--config kural`)

    TP           52 -> 52   (KAYIP YOK)
    FP           66 -> 60
    uydurma      26 -> 21
    mikro-F1  0,452 -> 0,464
    makro-F1  0,556 -> 0,601
    yapısal   0,646 -> 0,671
    halüsinasyon 0,059 -> 0,047

gold.v1'de hiçbir sayı değişmedi. `eval/esikler.json` regresyon kapısı açık
ve korunuyor.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.extraction.rules.extract import extract_all
from src.extraction.rules.kabuk import kabuk_baslangici

GOVDE = ("Taşıt Finansmanı Kampanyası. Kampanya kapsamında 36 aya varan vade "
         "imkânı sunulmaktadır. Kampanya 31.12.2026 tarihine kadar geçerlidir. ")


def _alanlar(metin: str) -> dict:
    return {f.field_name: f.canonical_value for f in extract_all(metin)}


class KuyrukKumesiTespiti(unittest.TestCase):
    def test_ardisik_iki_isaret_kume_olusturur(self) -> None:
        metin = GOVDE + "Diğer Kampanyalar MTV Ödemelerinize 4 Taksit " \
                        "Diğer Kampanyalar Michelin'de 6 Taksit"
        sinir = kabuk_baslangici(metin)
        self.assertIsNotNone(sinir)
        self.assertGreaterEqual(sinir, len(GOVDE) - 1,
                                "kabuk gövdenin içinde başlayamaz")

    def test_UZAK_iki_isaret_kume_DEGILDIR(self) -> None:
        """Yoğunlaşma yoksa kabuk da yoktur — 600 karakterlik boşluk şartı."""
        metin = ("Diğer Kampanyalar " + "x" * 900 + GOVDE
                 + "y" * 900 + " Diğer Kampanyalar")
        self.assertIsNone(kabuk_baslangici(metin))

    def test_tek_gecis_KUYRUKTA_ise_sayilir(self) -> None:
        metin = GOVDE * 6 + " İlginizi Çekebilir: Konut Finansmanı"
        self.assertIsNotNone(kabuk_baslangici(metin))

    def test_tek_gecis_BASTA_ise_sayilmaz(self) -> None:
        """Üst menüdeki tek bağlantı kabuk değildir — 16 TP'lik regresyon."""
        metin = "Diğer Kampanyalar " + GOVDE * 6
        self.assertIsNone(kabuk_baslangici(metin))

    def test_isaret_yoksa_None(self) -> None:
        self.assertIsNone(kabuk_baslangici(GOVDE))

    def test_bos_metin_None(self) -> None:
        self.assertIsNone(kabuk_baslangici(""))


class SuzgecAlanDusurur(unittest.TestCase):
    def test_kabuktaki_deger_ALINMAZ_govdedeki_KALIR(self) -> None:
        """Kılavuz §4.13/8'in birebir vakası."""
        metin = (GOVDE
                 + "Diğer Kampanyalar MTV Ödemelerinize 4 Taksit Son Gün 05.08.2026 "
                 + "Diğer Kampanyalar Michelin'de 4 Taksit Son Gün 06.08.2026")
        alanlar = _alanlar(metin)
        self.assertNotIn("taksit_sayisi", alanlar,
                         "komşu kampanyanın taksiti bu belgeye yazıldı")
        self.assertEqual(alanlar.get("vade_ay"), 36,
                         "gövdedeki vade korunmalı")

    def test_menudeki_TEK_baglanti_govdeyi_KESMEZ(self) -> None:
        """⚠️ KİLİT TEST. Naif tasarım burada 16+5 gerçek değer öldürüyordu.

        İşaret belgenin %10'unda, tekrar yok — sıradan bir kampanya sayfası.
        Hiçbir alan düşmemeli.
        """
        metin = "Anasayfa Kampanyalar Diğer Kampanyalar İletişim " + GOVDE * 6
        alanlar = _alanlar(metin)
        self.assertEqual(alanlar.get("vade_ay"), 36)
        self.assertIn("kampanya_suresi", alanlar)

    def test_kampanyayi_paylas_ISARET_DEGILDIR(self) -> None:
        """Ölçümle elendi: kampanya gövdesinin ortasında geçiyor."""
        metin = (GOVDE + "Kampanyayı Paylaş Facebook'ta paylaş "
                 + "Kampanyayı Paylaş Twitter'da paylaş " + GOVDE)
        self.assertIsNone(kabuk_baslangici(metin))
        self.assertEqual(_alanlar(metin).get("vade_ay"), 36)


class KorpusEtkisi(unittest.TestCase):
    def test_kabuklu_belge_sayisi_makul(self) -> None:
        """Kapı korpusun tamamını kabuk ilan ediyorsa tanım bozuktur."""
        kok = Path(__file__).resolve().parents[1] / "data/gold/review/belgeler"
        if not kok.is_dir():
            self.skipTest("inceleme belgeleri yok")
        metinler = [p.read_text(encoding="utf-8") for p in sorted(kok.glob("*.txt"))]
        kabuklu = sum(1 for t in metinler if kabuk_baslangici(t) is not None)
        self.assertLess(kabuklu, len(metinler) * 0.25,
                        f"belgelerin %{100*kabuklu/len(metinler):.0f}'i kabuk "
                        f"sayıldı — tanım fazla geniş")
        self.assertGreater(kabuklu, 0, "hiçbir belgede kabuk yok — kapı ölü")


if __name__ == "__main__":
    unittest.main()
