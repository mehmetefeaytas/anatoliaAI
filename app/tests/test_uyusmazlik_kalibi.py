"""Uyuşmazlık kalıpları — κ kaybının kaynağı doğru sınıflanıyor mu.

İlgili: ../scripts/uyusmazlik_kalibi.py, ../scripts/report_iaa.py

Bu ayrım kozmetik değil: `etiket-karisikligi` kılavuz revizyonuyla kapanır,
`gercek-fark` hakemlik ister. İkisini karıştıran bir rapor ekibi yanlış işe
yönlendirir — round0'da yalnız `absent`/`ok` karışıklığı düzeltilince Fleiss κ
0,051'den 0,268'e çıkmıştı, kimse fikrini değiştirmeden.
"""

from __future__ import annotations

import csv
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import uyusmazlik_kalibi as U
from scripts.to_review_csv import CSV_DELIMITER, CSV_ENCODING

BASLIK = ["doc_id", "bank", "field", "model_value", "model_conf",
          "confidence_source", "disagreement", "snippet", "gold_value",
          "verdict", "note", "protokol"]


def _satir(doc: str, field: str, verdict: str, gold: str = "",
           model: str = "12") -> dict:
    return {"doc_id": doc, "bank": "test", "field": field,
            "model_value": model, "model_conf": "0.70",
            "confidence_source": "rule", "disagreement": "", "snippet": "…",
            "gold_value": gold, "verdict": verdict, "note": "", "protokol": "v2"}


class TestKaliplar(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.d = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _yaz(self, ad: str, satirlar: list[dict]) -> Path:
        yol = self.d / ad
        with yol.open("w", encoding=CSV_ENCODING, newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=BASLIK, delimiter=CSV_DELIMITER,
                               lineterminator="\r\n")
            w.writeheader()
            w.writerows(satirlar)
        return yol

    def _kalip(self, a: dict, b: dict) -> str:
        sonuc = U.analiz(self._yaz("A.csv", [a]), self._yaz("B.csv", [b]))
        kaliplar = sonuc["kaliplar"]
        self.assertEqual(sum(len(v) for v in kaliplar.values()), 1,
                         f"tek uyuşmazlık bekleniyordu: {kaliplar}")
        return next(iter(kaliplar))

    def test_ayni_deger_farkli_karar_ETIKET_KARISIKLIGI(self) -> None:
        """A `ok` der (model 12 doğru), B `fix` der ama aynı 12'yi yazar."""
        self.assertEqual(
            self._kalip(_satir("d1", "vade_ay", "ok"),
                        _satir("d1", "vade_ay", "fix", gold="12")),
            "etiket-karisikligi")

    def test_ayni_deger_farkli_yazim_BICIM_FARKI(self) -> None:
        """`150000` ile `{"value":150000,...}` kanonikte eşitlenir."""
        self.assertEqual(
            self._kalip(
                _satir("d1", "finansman_tutari", "fix", gold="150000", model=""),
                _satir("d1", "finansman_tutari", "fix",
                       gold='{"currency": "TRY", "value": 150000}', model="")),
            "bicim-farki")

    def test_biri_deger_biri_yok_KAPSAM_FARKI(self) -> None:
        self.assertEqual(
            self._kalip(_satir("d1", "vade_ay", "ok", model="36"),
                        _satir("d1", "vade_ay", "absent", model="36")),
            "kapsam-farki")

    def test_gercekten_farkli_deger_GERCEK_FARK(self) -> None:
        self.assertEqual(
            self._kalip(_satir("d1", "vade_ay", "fix", gold="24", model=""),
                        _satir("d1", "vade_ay", "fix", gold="36", model="")),
            "gercek-fark")

    def test_bir_taraf_unclear_METRIK_DISI_isaretlenir(self) -> None:
        self.assertEqual(
            self._kalip(_satir("d1", "vade_ay", "ok"),
                        _satir("d1", "vade_ay", "unclear")),
            "unclear-tarafi")

    def test_tam_uyum_uyusmazlik_URETMEZ(self) -> None:
        sonuc = U.analiz(self._yaz("A.csv", [_satir("d1", "vade_ay", "ok")]),
                         self._yaz("B.csv", [_satir("d1", "vade_ay", "ok")]))
        self.assertEqual(sonuc["kaliplar"], {})
        self.assertEqual(sonuc["ikisi_dolu"], 1)

    def test_karar_verilmemis_satir_SAYILMAZ(self) -> None:
        """v2'de boş `verdict` 'bakmadım' demektir; uyuşmazlık üretemez."""
        sonuc = U.analiz(self._yaz("A.csv", [_satir("d1", "vade_ay", "")]),
                         self._yaz("B.csv", [_satir("d1", "vade_ay", "absent")]))
        self.assertEqual(sonuc["ikisi_dolu"], 0)
        self.assertEqual(sonuc["kaliplar"], {})


class TestRaporGovdesi(unittest.TestCase):
    def test_rapor_ZARARSIZ_orani_yazar(self) -> None:
        sonuc = {"ikisi_dolu": 10, "a": "A.csv", "b": "B.csv", "kaliplar": {
            "etiket-karisikligi": [{"doc_id": "d1", "field": "vade_ay",
                                    "A_verdict": "ok", "B_verdict": "fix",
                                    "A_deger": "12", "B_deger": "12",
                                    "aciklama": "x"}],
            "gercek-fark": [{"doc_id": "d2", "field": "vade_ay",
                             "A_verdict": "fix", "B_verdict": "fix",
                             "A_deger": "24", "B_deger": "36",
                             "aciklama": "y"}]}}
        metin = U.render(sonuc)
        self.assertIn("1/2", metin)
        self.assertIn("Hangi alan κ'yı yiyor", metin)
        self.assertIn("`vade_ay`", metin)


if __name__ == "__main__":
    unittest.main()
