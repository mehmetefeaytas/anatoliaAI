"""`decisions.csv` — belge×alan karar dökümü diske gerçekten yazılıyor mu?

İlgili: ../eval/run_eval.py (`decision_rows`), ../eval/report.py (`write_report`),
        ../scripts/mcnemar_report.py (tüketici)

## Bu testler neden var

`DocScore.decisions` McNemar'ın eşleştirme birimidir ve uzun süre yalnız
BELLEKTE üretildi: `MatcherResult.as_dict()` onu serileştirmiyordu,
`per_field_rows()` alan×kapsam düzeyinde topluyordu (`doc_id` sütunu yok),
`write_report` da yalnız dört dosya yazıyordu. Sonuç: süreç bitince veri çöpe
gidiyor, iki ayrı koşum SONRADAN eşleştirilemiyordu.

Buradaki üç şart, o boşluğun kapandığını mekanik olarak sabitler:

1. dosya yazılıyor mu,
2. satır sayısı `DocScore.decisions` toplamına EŞİT mi (sessiz kayıp yok),
3. `doc_id` kümesi gold ile BİREBİR eşleşiyor mu (uydurma/eksik belge yok).

Üçüncüsü özellikle önemli: bu projede bir kez kimlik kuralı bozulduğu için
ölçüm hata vermeden "fark yok" üretti (docs/rapor/gold-genisletme.md).
"""

from __future__ import annotations

import contextlib
import csv
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from typing import ClassVar

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from eval.predictors import CONFIG_KURAL, build_predictor
from eval.report import DECISION_COLUMNS
from eval.run_eval import decision_rows, evaluate, main
from scripts.gold_schema import load_gold

GOLD: list[dict] = [
    {"id": "g1",
     "text": "Konut finansmanında kâr payı oranı %1,89, 120 aya kadar vade.",
     "fields": {"kar_payi_orani": 1.89, "vade_ay": 120},
     "absent_fields": ["odul_miktari", "indirim_orani"],
     "hard_tags": []},
    {"id": "g2",
     "text": "İhtiyaç finansmanında ilk 6 ay masrafsız, 36 ay vade imkânı.",
     "fields": {"vade_ay": 36},
     "absent_fields": ["odul_miktari"],
     "hard_tags": ["eksik_bilgi"]},
    {"id": "g3",
     "text": "Kampanya kapsamında 500 TL hediye çeki kazanın.",
     "fields": {"odul_miktari": {"value": 500, "currency": "TRY"}},
     "absent_fields": ["kar_payi_orani"],
     "hard_tags": []},
]


class TestDecisionsCsv(unittest.TestCase):
    """`main()` uçtan uca — gerçek dosya yazma dahil."""

    GOLD: ClassVar[list] = GOLD

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.gold_path = self.root / "gold.json"
        self.gold_path.write_text(json.dumps(self.GOLD, ensure_ascii=False),
                                  encoding="utf-8")
        self.out_dir = self.root / "reports"

    def tearDown(self):
        self.tmp.cleanup()

    def _run(self, *extra: str) -> int:
        # Konsol çıktısı bastırılır; test edilen şey YAZILAN DOSYA.
        with contextlib.redirect_stdout(io.StringIO()):
            return main(["--gold", str(self.gold_path), "--config", CONFIG_KURAL,
                         "--out-dir", str(self.out_dir), "--no-bootstrap",
                         *extra])

    def _run_dir(self) -> Path:
        dirs = list(self.out_dir.iterdir())
        self.assertEqual(len(dirs), 1)
        return dirs[0]

    def _rows(self) -> list[dict]:
        path = self._run_dir() / "decisions.csv"
        with path.open(encoding="utf-8", newline="") as fh:
            return list(csv.DictReader(fh, delimiter=";"))

    # -- 1. dosya yazılıyor mu ------------------------------------------- #
    def test_dosya_yazilir(self):
        self._run("--matcher", "strict")
        self.assertTrue((self._run_dir() / "decisions.csv").is_file())

    def test_sutunlar_sozlesmeye_uyar(self):
        self._run("--matcher", "strict")
        rows = self._rows()
        self.assertTrue(rows)
        self.assertEqual(list(rows[0]), DECISION_COLUMNS)

    def test_correct_sutunu_0_1(self):
        """`True/False` metni YASAK: `bool("False") == True` tuzağı var."""
        self._run("--matcher", "strict")
        self.assertEqual({r["correct"] for r in self._rows()} - {"0", "1"}, set())

    # -- 2. satır sayısı = DocScore.decisions toplamı --------------------- #
    def test_satir_sayisi_karar_toplamina_esit(self):
        self._run("--matcher", "strict")
        predictor = build_predictor(CONFIG_KURAL)
        records = load_gold(self.gold_path)
        result = evaluate(records, predictor, "strict", bootstrap=False)
        beklenen = sum(len(d.decisions) for d in result.docs)
        self.assertGreater(beklenen, 0, "sentetik gold hiç karar üretmedi")
        self.assertEqual(len(self._rows()), beklenen)

    def test_iki_esleştirici_iki_gecis_yazar(self):
        """strict + tolerant AYRI geçiştir; ikisi de dosyada olmalı."""
        self._run("--matcher", "both")
        rows = self._rows()
        self.assertEqual({r["matcher"] for r in rows}, {"strict", "tolerant"})
        strict = [r for r in rows if r["matcher"] == "strict"]
        tolerant = [r for r in rows if r["matcher"] == "tolerant"]
        self.assertEqual(len(strict), len(tolerant))

    def test_anahtar_esleştirici_icinde_TEKIL(self):
        """`(matcher, doc_id, field)` iki kez geçerse eşleştirme bozulur."""
        self._run("--matcher", "both")
        keys = [(r["matcher"], r["doc_id"], r["field"]) for r in self._rows()]
        self.assertEqual(len(keys), len(set(keys)))

    # -- 3. doc_id'ler gold ile birebir ----------------------------------- #
    def test_doc_id_kumesi_gold_ile_BIREBIR(self):
        self._run("--matcher", "strict")
        self.assertEqual({r["doc_id"] for r in self._rows()},
                         {g["id"] for g in self.GOLD})

    def test_split_alt_kumesi_doc_id_kisitlar(self):
        """`--split hard` verildiyse yalnız zor belgeler dökülmeli."""
        self._run("--matcher", "strict", "--split", "hard")
        self.assertEqual({r["doc_id"] for r in self._rows()}, {"g2"})

    def test_alanlar_metrik_disi_kararlari_TASIMAZ(self):
        """Gold karar vermediği alan `decisions`a girmez — payda şişmesin."""
        self._run("--matcher", "strict")
        by_doc: dict[str, set[str]] = {}
        for row in self._rows():
            by_doc.setdefault(row["doc_id"], set()).add(row["field"])
        for record in self.GOLD:
            beklenen = set(record["fields"]) | set(record["absent_fields"])
            with self.subTest(doc=record["id"]):
                self.assertEqual(by_doc[record["id"]], beklenen)

    # -- yardımcı fonksiyonun kendisi ------------------------------------- #
    def test_decision_rows_sirasi_deterministik(self):
        predictor = build_predictor(CONFIG_KURAL)
        records = load_gold(self.gold_path)
        a = evaluate(records, predictor, "strict", bootstrap=False)
        b = evaluate(records, predictor, "strict", bootstrap=False)
        self.assertEqual(decision_rows([a]), decision_rows([b]))

    def test_no_write_decisions_uretmez(self):
        self.assertEqual(self._run("--no-write"), 0)
        self.assertFalse(self.out_dir.exists())


if __name__ == "__main__":
    unittest.main()
