"""Gümüş etiket partisi — hangi hücreler alınır, hangileri ALINMAZ.

İlgili: ../scripts/silver_parti_hazirla.py, ../scripts/silver_parti_bol.py

Bu dosyanın koruduğu üç şey:

1. **İnsan kararı olan hücre partiye GİRMEZ.** Tek bir anotatörün kararı bile
   varsa o hücre insanındır; modele yeniden sordurmak gold'u modele çapalama
   riskidir (ANNOTATION_GUIDE §3.1).
2. **Bölme metin hacmine göre yapılır.** Belge sayısına göre bölmek 1 KB'lik
   kampanya sayfası ile 50 KB'lik ücret tarifesini eşit sayar; kümeler on kat
   farklı iş yükü alır.
3. **Metni olmayan belge partiye alınmaz** — etiketlenemez.
"""

from __future__ import annotations

import csv
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import silver_parti_bol as B
from scripts import silver_parti_hazirla as S
from scripts.to_review_csv import CSV_DELIMITER, CSV_ENCODING

BASLIK = ["doc_id", "bank", "field", "model_value", "model_conf",
          "confidence_source", "disagreement", "snippet", "gold_value",
          "verdict", "note", "protokol"]


def _satir(doc: str, field: str, verdict: str = "", **ek) -> dict:
    temel = {"doc_id": doc, "bank": "test", "field": field,
             "model_value": "12", "model_conf": "0.70",
             "confidence_source": "rule", "disagreement": "",
             "snippet": "…", "gold_value": "", "verdict": verdict,
             "note": "", "protokol": "v2"}
    temel.update(ek)
    return temel


class _Temel(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.kok = Path(self._tmp.name)
        self.review = self.kok / "data/gold/review"
        self.belgeler = self.review / "belgeler"
        self.belgeler.mkdir(parents=True)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _csv(self, ad: str, satirlar: list[dict]) -> None:
        with (self.review / ad).open("w", encoding=CSV_ENCODING, newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=BASLIK, delimiter=CSV_DELIMITER,
                               lineterminator="\r\n")
            w.writeheader()
            w.writerows(satirlar)

    def _belge(self, doc: str, metin: str = "metin") -> None:
        (self.belgeler / f"{doc}.txt").write_text(metin, encoding="utf-8")


class TestKararliHucreAlinmaz(_Temel):
    def test_tek_anotator_karar_verdiyse_hucre_partiye_GIRMEZ(self) -> None:
        self._belge("d1")
        self._csv("round1_A.csv", [_satir("d1", "vade_ay", "ok"),
                                   _satir("d1", "kar_payi_orani")])
        self._csv("round1_B.csv", [_satir("d1", "vade_ay"),
                                   _satir("d1", "kar_payi_orani")])

        kayitlar = S.parti_uret(self.kok, dosyalar=("round1_A.csv", "round1_B.csv"))
        alanlar = {a["field"] for k in kayitlar for a in k["alanlar"]}
        self.assertEqual(alanlar, {"kar_payi_orani"})

    def test_hicbir_dosyada_karar_yoksa_ALINIR(self) -> None:
        self._belge("d1")
        self._csv("round1_A.csv", [_satir("d1", "vade_ay")])
        kayitlar = S.parti_uret(self.kok, dosyalar=("round1_A.csv",))
        self.assertEqual(len(kayitlar), 1)
        self.assertEqual(kayitlar[0]["alanlar"][0]["field"], "vade_ay")

    def test_metni_olmayan_belge_partiye_alinmaz(self) -> None:
        # belge dosyası YAZILMADI
        self._csv("round1_A.csv", [_satir("d_yok", "vade_ay")])
        self.assertEqual(S.parti_uret(self.kok, dosyalar=("round1_A.csv",)), [])


class TestBolmeDengesi(unittest.TestCase):
    def test_bolme_METIN_HACMINE_gore_dengelenir(self) -> None:
        """Bir dev + çok küçük belge: dev tek başına bir kümede kalmalı."""
        kayitlar = [{"doc_id": "dev", "metin_karakter": 100_000, "alanlar": [1]}]
        kayitlar += [{"doc_id": f"k{i}", "metin_karakter": 1_000, "alanlar": [1]}
                     for i in range(20)]
        kutular = B.bol(kayitlar, 2)
        agirliklar = sorted(sum(k["metin_karakter"] for k in kutu) for kutu in kutular)
        # Belge sayısına göre bölseydi ağırlıklar ~100k / ~20k olurdu.
        self.assertEqual(agirliklar, [20_000, 100_000])
        dev_kutu = next(k for k in kutular if any(r["doc_id"] == "dev" for r in k))
        self.assertEqual(len(dev_kutu), 1)

    def test_hicbir_belge_kaybolmaz_ve_TEKRARLANMAZ(self) -> None:
        kayitlar = [{"doc_id": f"d{i}", "metin_karakter": (i * 37) % 900 + 100,
                     "alanlar": [1]} for i in range(50)]
        kutular = B.bol(kayitlar, 7)
        hepsi = [r["doc_id"] for kutu in kutular for r in kutu]
        self.assertEqual(len(hepsi), 50)
        self.assertEqual(len(set(hepsi)), 50)


if __name__ == "__main__":
    unittest.main()
