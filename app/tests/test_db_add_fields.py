"""`Repository.add_fields` — var olan belgeye alan ekleme, KURAL DEĞERİ EZİLMEZ.

İlgili: ../src/db/repository.py (`add_fields`)
        ../scripts/llm_bosluk_doldur.py (tek çağıranı)
        CLAUDE.md §3 (kural birincil, LLM yalnız boşluk)

## Bu testin varlık sebebi

`add_fields` LLM'in bulduğu değerleri var olan belgelere yazıyor. Eğer aynı
alanda kural katmanının bir değeri VARSA ve LLM onu ezerse, ölçülmüş biçimde
daha zayıf olan kol (F1 0,304 vs kural 0,469) daha güçlü olanı sessizce
bozardı. Varsayılan davranış bu yüzden ATLAMAKTIR ve test onu kilitler.
"""

from __future__ import annotations

import json
import sqlite3
import tempfile
import unittest
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from src.db.repository import Repository
from src.extraction.reconcile import build_campaign


@dataclass
class _Alan:
    field_name: str
    raw_value: Optional[str] = None
    canonical_value: Any = None
    confidence: Optional[float] = None
    source_span: Optional[str] = None
    extractor: Optional[str] = None
    span_start: Optional[int] = None
    span_end: Optional[int] = None
    confidence_source: Optional[str] = None


class TestAddFields(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.db = str(Path(self._tmp.name) / "t.db")
        self.repo = Repository(self.db)
        # Kural hattı `vade_ay` buluyor, `kar_payi_orani` BULMUYOR.
        self.cid = self.repo.insert_campaign(build_campaign(
            "Konut finansmanında 36 ay vade.", bank_slug="albaraka",
            campaign_type="Konut Finansmanı"))

    def tearDown(self):
        self._tmp.cleanup()

    def _alanlar(self, cid: int) -> dict[str, list[tuple]]:
        out: dict[str, list[tuple]] = {}
        with sqlite3.connect(self.db) as c:
            for ad, canon, ex in c.execute(
                    "SELECT field_name, canonical_value, extractor "
                    "FROM extracted_fields WHERE campaign_id=?", (cid,)):
                out.setdefault(ad, []).append((canon, ex))
        return out

    def test_bos_alana_eklenir(self):
        n = self.repo.add_fields(self.cid, [
            _Alan("kar_payi_orani", raw_value="%3,25", canonical_value=3.25,
                  confidence=0.9, extractor="llm")])
        self.assertEqual(n, 1)
        alanlar = self._alanlar(self.cid)
        self.assertIn("kar_payi_orani", alanlar)
        canon, ex = alanlar["kar_payi_orani"][0]
        self.assertEqual(json.loads(canon), 3.25)
        self.assertEqual(ex, "llm")

    def test_MEVCUT_alan_EZILMEZ(self):
        """Kural `vade_ay`ı bulmuş; LLM onu değiştiremez."""
        onceki = self._alanlar(self.cid)["vade_ay"]
        n = self.repo.add_fields(self.cid, [
            _Alan("vade_ay", canonical_value=999, extractor="llm")])
        self.assertEqual(n, 0)
        self.assertEqual(self._alanlar(self.cid)["vade_ay"], onceki)

    def test_ezme_bayragi_ACIKCA_istenir(self):
        n = self.repo.add_fields(self.cid, [
            _Alan("vade_ay", canonical_value=999, extractor="llm")], ezme=True)
        self.assertEqual(n, 1)
        # Eski satır silinmiyor; ikisi de duruyor (denetim izi korunur)
        self.assertEqual(len(self._alanlar(self.cid)["vade_ay"]), 2)

    def test_karisik_kume_yalniz_BOSLARI_yazar(self):
        n = self.repo.add_fields(self.cid, [
            _Alan("vade_ay", canonical_value=999, extractor="llm"),
            _Alan("kar_payi_orani", canonical_value=3.25, extractor="llm"),
            _Alan("finansman_tutari",
                  canonical_value={"value": 500000, "currency": "TRY"},
                  extractor="llm")])
        self.assertEqual(n, 2)
        alanlar = self._alanlar(self.cid)
        self.assertEqual(len(alanlar["vade_ay"]), 1)
        self.assertIn("kar_payi_orani", alanlar)
        self.assertIn("finansman_tutari", alanlar)

    def test_gecersiz_extractor_REDDEDILIR(self):
        """`extractor_dogrula` kapısı; şemadaki CHECK'e güvenilmiyor."""
        with self.assertRaises(ValueError):
            self.repo.add_fields(self.cid, [
                _Alan("kar_payi_orani", canonical_value=3.25,
                      extractor="UYDURMA")])

    def test_bos_kume_sifir_dondurur(self):
        self.assertEqual(self.repo.add_fields(self.cid, []), 0)

    def test_field_name_olmayan_oge_atlanir(self):
        @dataclass
        class _Bozuk:
            canonical_value: Any = 1
        self.assertEqual(self.repo.add_fields(self.cid, [_Bozuk()]), 0)

    def test_sozluk_canonical_JSON_olarak_yazilir(self):
        self.repo.add_fields(self.cid, [
            _Alan("finansman_tutari",
                  canonical_value={"value": 500000, "currency": "TRY"},
                  extractor="llm")])
        canon, _ = self._alanlar(self.cid)["finansman_tutari"][0]
        self.assertEqual(json.loads(canon),
                         {"value": 500000, "currency": "TRY"})

    def test_field_value_uzerinden_okunabilir(self):
        """Yazılan değer normal okuma yolundan görünmeli."""
        self.repo.add_fields(self.cid, [
            _Alan("kar_payi_orani", canonical_value=3.25, extractor="llm")])
        self.assertEqual(Repository(self.db).field_value(
            self.cid, "kar_payi_orani"), 3.25)


if __name__ == "__main__":
    unittest.main()
