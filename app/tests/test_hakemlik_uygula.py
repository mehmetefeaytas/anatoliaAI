"""Hakemlik uygulaması — üçüncü göz uyuşmazlığı çözer, DAYATMAZ.

İlgili: ../scripts/hakemlik_uygula.py

Bu dosyanın koruduğu dört şey:

1. **Hakem yalnız HAKEM SEÇER.** Kararı A ya da B ile örtüşüyorsa diğeri ona
   çekilir; üçüncü bir cevap verdiyse HİÇBİRİNE dokunulmaz. Betiğin kendi
   kararını yazması hakemi anotatör yerine koymak olurdu.
2. **`unclear` uygulanmaz.** Metrik dışı bir etiketi iki tarafa birden yazmak
   uyuşmazlığı çözmez, gizler.
3. **Kazanan tarafa dokunulmaz.** Yalnız kaybeden hücre değişir.
4. **Değişiklik damgalanır.** `note`'a `#hakemlik-round1` düşer, yoksa gold'da
   hangi hücrenin insan kararı hangisinin hakemlik olduğu ayırt edilemez.
"""

from __future__ import annotations

import csv
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import hakemlik_uygula as H
from scripts.to_review_csv import CSV_DELIMITER, CSV_ENCODING

BASLIK = ["doc_id", "bank", "field", "model_value", "model_conf",
          "confidence_source", "disagreement", "snippet", "gold_value",
          "verdict", "note", "protokol"]


def _satir(field: str = "vade_ay", verdict: str = "", gold: str = "",
           model: str = "12", note: str = "") -> dict:
    return {"doc_id": "d1", "bank": "test", "field": field,
            "model_value": model, "model_conf": "0.70",
            "confidence_source": "rule", "disagreement": "", "snippet": "…",
            "gold_value": gold, "verdict": verdict, "note": note,
            "protokol": "v2"}


class _Temel(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.d = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _kur(self, a: dict, b: dict, hakem: dict):
        for ad, satir in (("A.csv", a), ("B.csv", b)):
            with (self.d / ad).open("w", encoding=CSV_ENCODING, newline="") as fh:
                y = csv.DictWriter(fh, fieldnames=BASLIK, delimiter=CSV_DELIMITER,
                                   lineterminator="\r\n")
                y.writeheader()
                y.writerow(satir)
        (self.d / "h.jsonl").write_text(
            json.dumps({"doc_id": "d1", "field": a["field"], **hakem},
                       ensure_ascii=False) + "\n", encoding="utf-8")
        return H.uygula(self.d / "A.csv", self.d / "B.csv", self.d / "h.jsonl")

    def _oku(self, ad: str) -> dict:
        with (self.d / ad).open(encoding=CSV_ENCODING, newline="") as fh:
            return next(iter(csv.DictReader(fh, delimiter=CSV_DELIMITER)))


class TestHakemSecer(_Temel):
    def test_hakem_B_ile_ortusurse_A_duzeltilir(self) -> None:
        rapor = self._kur(_satir(verdict="ok"),
                          _satir(verdict="fix", gold="36"),
                          {"verdict": "fix", "gold_value": "36",
                           "note": "ilan edilen ust sinir 36"})
        self.assertEqual(len(rapor["degisiklik"]), 1)
        self.assertEqual(rapor["degisiklik"][0]["kazanan"], "B")
        a = self._oku("A.csv")
        self.assertEqual(a["verdict"], "fix")
        self.assertEqual(a["gold_value"], "36")
        self.assertIn("#hakemlik-round1", a["note"])
        # kazanan tarafa DOKUNULMAZ
        self.assertNotIn("#hakemlik-round1", self._oku("B.csv")["note"])

    def test_hakem_A_ile_ortusurse_B_duzeltilir(self) -> None:
        rapor = self._kur(_satir(verdict="ok"),
                          _satir(verdict="absent"),
                          {"verdict": "ok", "gold_value": "",
                           "note": "model degeri metinde var"})
        self.assertEqual(rapor["degisiklik"][0]["kazanan"], "A")
        self.assertEqual(self._oku("B.csv")["verdict"], "ok")
        self.assertNotIn("#hakemlik-round1", self._oku("A.csv")["note"])

    def test_hakem_UCUNCU_cevap_verirse_hicbirine_dokunulmaz(self) -> None:
        rapor = self._kur(_satir(verdict="ok"),
                          _satir(verdict="fix", gold="36"),
                          {"verdict": "absent", "gold_value": "",
                           "note": "deger komsu bloktan"})
        self.assertEqual(rapor["degisiklik"], [])
        self.assertEqual(len(rapor["dokunulmayan"]), 1)
        self.assertEqual(self._oku("A.csv")["verdict"], "ok")
        self.assertEqual(self._oku("B.csv")["verdict"], "fix")

    def test_hakem_unclear_derse_atlanir(self) -> None:
        rapor = self._kur(_satir(verdict="ok"),
                          _satir(verdict="absent"),
                          {"verdict": "unclear", "gold_value": "",
                           "note": "metin belirsiz"})
        self.assertEqual(rapor["degisiklik"], [])
        self.assertEqual(len(rapor["unclear_atlanan"]), 1)
        self.assertEqual(self._oku("A.csv")["verdict"], "ok")

    def test_zaten_uyusan_satira_dokunulmaz(self) -> None:
        rapor = self._kur(_satir(verdict="ok"), _satir(verdict="ok"),
                          {"verdict": "fix", "gold_value": "36", "note": "x"})
        self.assertEqual(rapor["degisiklik"], [])
        self.assertEqual(self._oku("A.csv")["verdict"], "ok")


class TestDegerDuyarliligi(_Temel):
    def test_ayni_KARAR_farkli_DEGER_ortusme_saymaz(self) -> None:
        """B `fix 36` dedi, hakem `fix 24` dedi — bu bir örtüşme DEĞİLDİR."""
        rapor = self._kur(_satir(verdict="ok"),
                          _satir(verdict="fix", gold="36"),
                          {"verdict": "fix", "gold_value": "24", "note": "x"})
        self.assertEqual(rapor["degisiklik"], [])
        self.assertEqual(len(rapor["dokunulmayan"]), 1)

    def test_ayni_deger_farkli_YAZIM_ortusme_sayar(self) -> None:
        """`150000` ile `{"value":150000,...}` aynı değerdir."""
        rapor = self._kur(
            _satir(field="finansman_tutari", verdict="absent", model=""),
            _satir(field="finansman_tutari", verdict="fix", gold="150000",
                   model=""),
            {"verdict": "fix",
             "gold_value": '{"value": 150000, "currency": "TRY"}', "note": "x"})
        self.assertEqual(len(rapor["degisiklik"]), 1)
        self.assertEqual(rapor["degisiklik"][0]["kazanan"], "B")


class TestYedek(_Temel):
    def test_degisiklik_varsa_YEDEK_alinir(self) -> None:
        rapor = self._kur(_satir(verdict="ok"), _satir(verdict="absent"),
                          {"verdict": "absent", "gold_value": "", "note": "x"})
        self.assertEqual(len(rapor["yedek"]), 2)
        for y in rapor["yedek"]:
            self.assertTrue(Path(y).exists())
            self.assertIn("yedek-hakemlik-round1", y)


class TestRapor(_Temel):
    def test_rapor_kappa_uyarisini_YAZAR(self) -> None:
        rapor = self._kur(_satir(verdict="ok"), _satir(verdict="absent"),
                          {"verdict": "absent", "gold_value": "", "note": "x"})
        metin = H.render(rapor)
        self.assertIn("0,274", metin)
        self.assertIn("hakemlik ÖNCESİ", metin)


if __name__ == "__main__":
    unittest.main()
