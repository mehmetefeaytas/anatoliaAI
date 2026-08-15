"""Şema onarımı — kayıp anotasyonu kurtarır, sessizce EZMEZ.

İlgili: ../scripts/sema_onarimi_uygula.py

Bu dosyanın koruduğu dört şey:

1. **Satır kayması ölümcüldür.** Öneri `(dosya, satır)` ile geliyor ama hücre
   `(doc_id, field)` ile doğrulanmalı. Satır numarasına körü körüne yazmak,
   araya bir satır eklendiyse BAŞKA bir belgenin kararını ezer — ve bu, gold'da
   asla fark edilmeyecek bir bozulmadır.
2. **Kanonik olmayan öneri reddedilir.** Araç, kapatmak için var olduğu hatanın
   aynısını üretemez.
3. **Ret sessiz değildir.** Reddedilen öneri rapora gerekçesiyle yazılır;
   atlanan hücre "düzeltildi" sanılmamalı.
4. **Damga zorunludur.** `note`'a `#sema-onarimi-round1` düşmezse gold'da
   hangi hücrenin insan kararı hangisinin onarım olduğu ayırt edilemez.
"""

from __future__ import annotations

import csv
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import sema_onarimi_uygula as S
from scripts.to_review_csv import CSV_DELIMITER, CSV_ENCODING

BASLIK = ["doc_id", "bank", "field", "model_value", "model_conf",
          "confidence_source", "disagreement", "snippet", "gold_value",
          "verdict", "note", "protokol"]


def _satir(doc: str = "d1", field: str = "campaign_type", verdict: str = "fix",
           gold: str = "Katılım hesabı", note: str = "") -> dict:
    return {"doc_id": doc, "bank": "test", "field": field,
            "model_value": "Kart", "model_conf": "0.70",
            "confidence_source": "rule", "disagreement": "", "snippet": "…",
            "gold_value": gold, "verdict": verdict, "note": note,
            "protokol": "v2"}


class _Temel(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.d = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _kur(self, satirlar: list[dict], oneriler: list[dict]) -> dict:
        with (self.d / "round1_main_C.csv").open(
                "w", encoding=CSV_ENCODING, newline="") as fh:
            y = csv.DictWriter(fh, fieldnames=BASLIK, delimiter=CSV_DELIMITER,
                               lineterminator="\r\n")
            y.writeheader()
            y.writerows(satirlar)
        (self.d / "o.jsonl").write_text(
            "\n".join(json.dumps(o, ensure_ascii=False) for o in oneriler) + "\n",
            encoding="utf-8")
        return S.uygula(self.d, self.d / "o.jsonl")

    def _oku(self, dizin: int = 0) -> dict:
        with (self.d / "round1_main_C.csv").open(
                encoding=CSV_ENCODING, newline="") as fh:
            return list(csv.DictReader(fh, delimiter=CSV_DELIMITER))[dizin]


class TestOnarim(_Temel):
    def test_taksonomi_disi_deger_kanonige_cevrilir(self) -> None:
        rapor = self._kur([_satir()], [{
            "dosya": "round1_main_C", "satir": 2, "doc_id": "d1",
            "field": "campaign_type", "verdict": "fix",
            "gold_value": "Yatırım Ürünü",
            "note": "katılma hesabı -> Yatırım Ürünü (biçim kartı §3/8)"}])
        self.assertEqual(len(rapor["degisiklik"]), 1)
        self.assertEqual(rapor["reddedilen"], [])
        satir = self._oku()
        self.assertEqual(satir["gold_value"], "Yatırım Ürünü")
        self.assertIn(S.DAMGA, satir["note"])

    def test_mevcut_not_KORUNUR_damga_eklenir(self) -> None:
        """Anotatörün notu silinmez — niyeti kayda geçmiş olmalı."""
        self._kur([_satir(note="katılma hesabı sanırım")], [{
            "dosya": "round1_main_C", "satir": 2, "doc_id": "d1",
            "field": "campaign_type", "verdict": "absent", "gold_value": "",
            "note": "#sema_disi liste sayfası"}])
        satir = self._oku()
        self.assertIn("katılma hesabı sanırım", satir["note"])
        self.assertIn(S.DAMGA, satir["note"])

    def test_bos_fix_absente_cevrilebilir(self) -> None:
        rapor = self._kur([_satir(field="finansman_tutari", gold="")], [{
            "dosya": "round1_main_C", "satir": 2, "doc_id": "d1",
            "field": "finansman_tutari", "verdict": "absent", "gold_value": "",
            "note": "belgede finansman tutarı yok"}])
        self.assertEqual(len(rapor["degisiklik"]), 1)
        self.assertEqual(self._oku()["verdict"], "absent")


class TestSatirKaymasiKapisi(_Temel):
    def test_doc_id_tutmazsa_REDDEDILIR(self) -> None:
        """Satır numarasına körü körüne yazmak başka belgeyi ezerdi."""
        rapor = self._kur([_satir(doc="d1")], [{
            "dosya": "round1_main_C", "satir": 2, "doc_id": "BASKA-BELGE",
            "field": "campaign_type", "verdict": "fix",
            "gold_value": "Kart", "note": "x"}])
        self.assertEqual(rapor["degisiklik"], [])
        self.assertEqual(len(rapor["reddedilen"]), 1)
        self.assertIn("satır kayması", rapor["reddedilen"][0]["gerekce"])
        self.assertEqual(self._oku()["gold_value"], "Katılım hesabı")

    def test_alan_tutmazsa_REDDEDILIR(self) -> None:
        rapor = self._kur([_satir(field="campaign_type")], [{
            "dosya": "round1_main_C", "satir": 2, "doc_id": "d1",
            "field": "vade_ay", "verdict": "fix", "gold_value": "36",
            "note": "x"}])
        self.assertEqual(rapor["degisiklik"], [])
        self.assertIn("alan uyuşmuyor", rapor["reddedilen"][0]["gerekce"])

    def test_dosyada_olmayan_satir_REDDEDILIR(self) -> None:
        rapor = self._kur([_satir()], [{
            "dosya": "round1_main_C", "satir": 999, "doc_id": "d1",
            "field": "campaign_type", "verdict": "fix", "gold_value": "Kart",
            "note": "x"}])
        self.assertEqual(rapor["degisiklik"], [])
        self.assertIn("dosyada yok", rapor["reddedilen"][0]["gerekce"])


class TestKanoniklikKapisi(_Temel):
    def test_kanonik_OLMAYAN_oneri_REDDEDILIR(self) -> None:
        """Araç, kapatmak için var olduğu hatanın aynısını üretemez."""
        rapor = self._kur([_satir()], [{
            "dosya": "round1_main_C", "satir": 2, "doc_id": "d1",
            "field": "campaign_type", "verdict": "fix",
            "gold_value": "Alışveriş finansmanı", "note": "x"}])
        self.assertEqual(rapor["degisiklik"], [])
        self.assertIn("kanonik değil", rapor["reddedilen"][0]["gerekce"])

    def test_fix_ama_gold_value_BOS_reddedilir(self) -> None:
        rapor = self._kur([_satir()], [{
            "dosya": "round1_main_C", "satir": 2, "doc_id": "d1",
            "field": "campaign_type", "verdict": "fix", "gold_value": "",
            "note": "x"}])
        self.assertEqual(rapor["degisiklik"], [])
        self.assertIn("gold_value boş", rapor["reddedilen"][0]["gerekce"])

    def test_absent_ama_gold_value_DOLU_reddedilir(self) -> None:
        rapor = self._kur([_satir()], [{
            "dosya": "round1_main_C", "satir": 2, "doc_id": "d1",
            "field": "campaign_type", "verdict": "absent",
            "gold_value": "Kart", "note": "x"}])
        self.assertEqual(rapor["degisiklik"], [])
        self.assertIn("gold_value dolu", rapor["reddedilen"][0]["gerekce"])

    def test_gerekcesiz_oneri_REDDEDILIR(self) -> None:
        rapor = self._kur([_satir()], [{
            "dosya": "round1_main_C", "satir": 2, "doc_id": "d1",
            "field": "campaign_type", "verdict": "absent", "gold_value": "",
            "note": "  "}])
        self.assertEqual(rapor["degisiklik"], [])
        self.assertIn("gerekçe", rapor["reddedilen"][0]["gerekce"])


class TestRapor(_Temel):
    def test_reddedilen_oneri_RAPORA_yazilir(self) -> None:
        """Sessiz ret, 'düzeltildi' sanılan bir hücre bırakır."""
        rapor = self._kur([_satir()], [{
            "dosya": "round1_main_C", "satir": 2, "doc_id": "d1",
            "field": "campaign_type", "verdict": "fix",
            "gold_value": "Alışveriş finansmanı", "note": "x"}])
        metin = S.render(rapor)
        self.assertIn("Reddedilen öneriler", metin)
        self.assertIn("kanonik değil", metin)

    def test_rapor_hakemlikten_AYRI_oldugunu_yazar(self) -> None:
        rapor = self._kur([_satir()], [{
            "dosya": "round1_main_C", "satir": 2, "doc_id": "d1",
            "field": "campaign_type", "verdict": "absent", "gold_value": "",
            "note": "#sema_disi"}])
        metin = S.render(rapor)
        self.assertIn("hakemlik DEĞİL", metin)


class TestYedek(_Temel):
    def test_degisiklik_varsa_YEDEK_alinir(self) -> None:
        rapor = self._kur([_satir()], [{
            "dosya": "round1_main_C", "satir": 2, "doc_id": "d1",
            "field": "campaign_type", "verdict": "absent", "gold_value": "",
            "note": "#sema_disi"}])
        self.assertEqual(len(rapor["yedek"]), 1)
        self.assertTrue(Path(rapor["yedek"][0]).exists())

    def test_kuru_kosuda_dosya_DEGISMEZ(self) -> None:
        with (self.d / "round1_main_C.csv").open(
                "w", encoding=CSV_ENCODING, newline="") as fh:
            y = csv.DictWriter(fh, fieldnames=BASLIK, delimiter=CSV_DELIMITER,
                               lineterminator="\r\n")
            y.writeheader()
            y.writerow(_satir())
        (self.d / "o.jsonl").write_text(json.dumps({
            "dosya": "round1_main_C", "satir": 2, "doc_id": "d1",
            "field": "campaign_type", "verdict": "absent", "gold_value": "",
            "note": "#sema_disi"}, ensure_ascii=False) + "\n", encoding="utf-8")
        rapor = S.uygula(self.d, self.d / "o.jsonl", kuru=True)
        self.assertEqual(len(rapor["degisiklik"]), 1)
        self.assertEqual(rapor["yedek"], [])
        self.assertEqual(self._oku()["verdict"], "fix")


if __name__ == "__main__":
    unittest.main()
