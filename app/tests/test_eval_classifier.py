"""Sınıflandırma ölçümü — çekimserlik muhasebesi ve eşit koşul testleri.

İlgili: ../scripts/eval_classifier.py, ../src/extraction/ner/classifier.py,
        CLAUDE.md §4 (8-sınıf fine-tune), §16 (ablasyon), §19 (uydurma yok)

Buradaki kritik tasarım kararı **çekimserliğin nasıl sayıldığı**. Yanlış
sayılırsa metrik modeli ödüllendirir: zor belgelerde susup kolaylarda konuşan
bir sınıflandırıcı yüksek precision alır ve BERTurk kıyası anlamsızlaşır.
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import eval_classifier as EC
from src.schemas import CAMPAIGN_TYPES

#: (doc_id, metin, gerçek etiket)
GOLD = [
    ("b--1", "konut finansmanı metni", "Konut Finansmanı"),
    ("b--2", "taşıt finansmanı metni", "Taşıt Finansmanı"),
    ("b--3", "kart kampanyası metni", "Kart"),
    ("b--4", "kart kampanyası metni 2", "Kart"),
]


class TestCekimserlikMuhasebesi(unittest.TestCase):
    """Susmak recall'u düşürmeli, precision'ı ŞİŞİRMEMELİ."""

    def test_cekimser_FN_sayilir(self) -> None:
        s = EC.olc(GOLD, {"b--1": None, "b--2": "Taşıt Finansmanı",
                          "b--3": "Kart", "b--4": "Kart"})
        self.assertEqual(s["cekimser"], 1)
        self.assertEqual(s["tablo"]["Konut Finansmanı"].fn, 1)
        self.assertEqual(s["tablo"]["Konut Finansmanı"].recall(), 0.0)

    def test_cekimser_FP_sayilmaz(self) -> None:
        """Çekimser kalan model hiçbir sınıfa yanlış iddia yüklememeli."""
        s = EC.olc(GOLD, dict.fromkeys([g[0] for g in GOLD], None))
        self.assertEqual(sum(c.fp for c in s["tablo"].values()), 0)

    def test_hep_susan_model_yuksek_skor_ALMAZ(self) -> None:
        """Ödüllendirme tuzağı: susmak 'hata yapmamak' sayılmamalı."""
        s = EC.olc(GOLD, dict.fromkeys([g[0] for g in GOLD], None))
        self.assertEqual(s["accuracy"], 0.0)
        self.assertEqual(s["macro_f1"], 0.0)

    def test_secici_susma_precisioni_sismez(self) -> None:
        """Zor olanda susup kolayda konuşan model, hepsini bilenle EŞİT olamaz."""
        secici = EC.olc(GOLD, {"b--1": None, "b--2": None,
                               "b--3": "Kart", "b--4": "Kart"})
        tam = EC.olc(GOLD, {g[0]: g[2] for g in GOLD})
        self.assertLess(secici["macro_f1"], tam["macro_f1"])


class TestSayaclar(unittest.TestCase):
    def test_hepsi_dogru(self) -> None:
        s = EC.olc(GOLD, {g[0]: g[2] for g in GOLD})
        self.assertEqual(s["accuracy"], 1.0)
        self.assertEqual(s["macro_f1"], 1.0)
        self.assertEqual(s["cekimser"], 0)

    def test_yanlis_tahmin_hem_FN_hem_FP(self) -> None:
        s = EC.olc(GOLD, {"b--1": "Kart", "b--2": "Taşıt Finansmanı",
                          "b--3": "Kart", "b--4": "Kart"})
        self.assertEqual(s["tablo"]["Konut Finansmanı"].fn, 1)
        self.assertEqual(s["tablo"]["Kart"].fp, 1)

    def test_karisiklik_kaydedilir(self) -> None:
        s = EC.olc(GOLD, {"b--1": "Kart", "b--2": "Taşıt Finansmanı",
                          "b--3": "Kart", "b--4": "Kart"})
        self.assertEqual(s["karisiklik"][("Konut Finansmanı", "Kart")], 1)

    def test_taksonomi_disi_tahmin_FP_uretmez_ama_FN_uretir(self) -> None:
        """Model uydurma bir sınıf adı verirse tabloya sızmamalı."""
        s = EC.olc(GOLD, {"b--1": "Uydurma Sınıf", "b--2": "Taşıt Finansmanı",
                          "b--3": "Kart", "b--4": "Kart"})
        self.assertEqual(s["tablo"]["Konut Finansmanı"].fn, 1)
        self.assertEqual(sum(c.fp for c in s["tablo"].values()), 0)
        self.assertEqual(s["accuracy"], 0.75)

    def test_tablo_tum_taksonomiyi_kapsar(self) -> None:
        s = EC.olc(GOLD, {g[0]: g[2] for g in GOLD})
        self.assertEqual(set(s["tablo"]), set(CAMPAIGN_TYPES))


class TestEsitKosul(unittest.TestCase):
    """İki model AYNI hattan geçmeli; eksik tahmin kayırma üretmemeli."""

    def test_eksik_tahmin_cekimser_sayilir(self) -> None:
        # b--4 için tahmin hiç yok.
        s = EC.olc(GOLD, {"b--1": "Konut Finansmanı",
                          "b--2": "Taşıt Finansmanı", "b--3": "Kart"})
        self.assertEqual(s["cekimser"], 1)
        self.assertEqual(s["n"], 4, "eksik belge ölçümden düşürüldü")

    def test_eksik_tahmin_paydayi_kucultmez(self) -> None:
        """Kapsam metriğin parçası: tahmin etmemek n'i düşürmemeli."""
        tam = EC.olc(GOLD, {g[0]: g[2] for g in GOLD})
        eksik = EC.olc(GOLD, {"b--1": "Konut Finansmanı"})
        self.assertEqual(tam["n"], eksik["n"])
        self.assertLess(eksik["accuracy"], tam["accuracy"])


class TestTahminYukleme(unittest.TestCase):
    def test_null_etiket_cekimser_olarak_okunur(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "p.jsonl"
            p.write_text(
                json.dumps({"doc_id": "b--1", "label": None}) + "\n"
                + json.dumps({"doc_id": "b--2", "label": "Kart"}) + "\n",
                encoding="utf-8")
            t = EC._tahminleri_yukle(str(p))
        self.assertIsNone(t["b--1"])
        self.assertEqual(t["b--2"], "Kart")


class TestKuralCizgisiKosar(unittest.TestCase):
    """Temel çizgi gerçek gold üzerinde koşabilmeli — BERTurk'ün hedefi bu."""

    def test_gercek_goldda_kosar_ve_makul_sonuc_verir(self) -> None:
        gold = EC._gold_yukle("data/gold/gold.v1.json")
        self.assertGreaterEqual(len(gold), 20, "gold campaign_type kayboldu")
        s = EC.olc(gold, EC._kural_tahminleri(gold))
        # Kural çizgisi ölçüldü: accuracy 0,700 / makro-F1 0,762.
        # Test kırılgan olmasın diye geniş bir bant tutuluyor; amaç "çöktü mü"
        # sorusunu yakalamak, ondalık takip etmek değil.
        self.assertGreater(s["accuracy"], 0.5)
        self.assertGreater(s["macro_f1"], 0.5)


if __name__ == "__main__":
    unittest.main()
