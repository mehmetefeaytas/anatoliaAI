"""Gümüş etiket doğrulaması — modelin ürettiği veri gold'un süzgecinden geçer.

İlgili: ../scripts/silver_birlestir.py, ../scripts/gold_schema.py

Gümüş veri bir modeli EĞİTECEK. Şema ihlali süzülmezse ihlal doğrudan modele
öğretilir; uydurma alıntı ise kanıt zincirini sahteler. Bu yüzden kapı gold
ile aynı sıkılıktadır ve reddedilen kayıt silinmez, gerekçesiyle saklanır.
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import silver_birlestir as S

METIN = {"d1": S._duzle("Kampanya 36 aya varan vade ile gecerlidir. "
                        "Tahsis ucreti 500 TL'dir.")}


def _kayit(**ek) -> dict:
    temel = {"doc_id": "d1", "field": "vade_ay", "verdict": "ok",
             "gold_value": "", "note": "", "confidence": 0.9,
             "evidence": "", "etiketleyici": "opus-5"}
    temel.update(ek)
    return temel


class TestDogrulama(unittest.TestCase):
    def test_temiz_kayit_gecer(self) -> None:
        self.assertEqual(S.dogrula(_kayit(), METIN), [])

    def test_fix_ise_gold_value_ZORUNLU(self) -> None:
        hatalar = S.dogrula(_kayit(verdict="fix", gold_value=""), METIN)
        self.assertTrue(any("gold_value bos" in h for h in hatalar))

    def test_ok_ise_gold_value_DOLU_OLAMAZ(self) -> None:
        hatalar = S.dogrula(_kayit(verdict="ok", gold_value="36"), METIN)
        self.assertTrue(any("gold_value dolu" in h for h in hatalar))

    def test_kanonik_olmayan_gold_value_REDDEDILIR(self) -> None:
        """`36-24-12` ayrıştırıcıyı sessizce geçemez."""
        hatalar = S.dogrula(_kayit(verdict="fix", gold_value="36-24-12"), METIN)
        self.assertTrue(any("kanonik degil" in h for h in hatalar))

    def test_kanonik_gold_value_gecer(self) -> None:
        self.assertEqual(S.dogrula(_kayit(verdict="fix", gold_value="36"), METIN), [])

    def test_UYDURMA_alinti_reddedilir(self) -> None:
        hatalar = S.dogrula(_kayit(evidence="metinde olmayan bir cumle"), METIN)
        self.assertTrue(any("BIREBIR gecmiyor" in h for h in hatalar))

    def test_gercek_alinti_gecer_BOSLUK_farkina_ragmen(self) -> None:
        self.assertEqual(
            S.dogrula(_kayit(evidence="36  aya\nvaran   vade"), METIN), [])

    def test_taninmayan_verdict_reddedilir(self) -> None:
        hatalar = S.dogrula(_kayit(verdict="belki"), METIN)
        self.assertTrue(any("verdict taninmiyor" in h for h in hatalar))

    def test_bilinmeyen_belgeye_alinti_reddedilir(self) -> None:
        hatalar = S.dogrula(_kayit(doc_id="dyok", evidence="bir sey"), METIN)
        self.assertTrue(any("belge metni bulunamadi" in h for h in hatalar))


class TestBirlestirme(unittest.TestCase):
    """Uçtan uca: iki parça + bir bozuk kayıt -> kabul/red ayrışır."""

    def test_cift_hucre_ve_bozuk_kayit_REDDE_dusr(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            (d / "belgeler").mkdir()
            (d / "belgeler" / "d1.txt").write_text("36 aya varan vade",
                                                   encoding="utf-8")
            p1 = d / "etiket_01.jsonl"
            p2 = d / "etiket_02.jsonl"
            p1.write_text(
                '{"doc_id":"d1","field":"vade_ay","verdict":"ok","gold_value":"",'
                '"evidence":"36 aya varan vade"}\n', encoding="utf-8")
            # aynı hücre TEKRAR + gold_value'lu bir `ok`
            p2.write_text(
                '{"doc_id":"d1","field":"vade_ay","verdict":"ok","gold_value":""}\n'
                '{"doc_id":"d1","field":"kar_payi_orani","verdict":"ok",'
                '"gold_value":"2.05"}\n', encoding="utf-8")

            metinler = {"d1": S._duzle("36 aya varan vade")}
            kabul, red = {}, []
            for yol in (p1, p2):
                for satir in yol.read_text(encoding="utf-8").splitlines():
                    import json
                    k = json.loads(satir)
                    h = S.dogrula(k, metinler)
                    anahtar = (k["doc_id"], k["field"])
                    if h:
                        red.append((anahtar, h))
                    elif anahtar in kabul:
                        red.append((anahtar, ["cift"]))
                    else:
                        kabul[anahtar] = k

            self.assertEqual(len(kabul), 1)
            self.assertEqual(len(red), 2)


if __name__ == "__main__":
    unittest.main()
