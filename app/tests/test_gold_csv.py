"""İnceleme CSV'si + gold derleme testleri (gidiş-dönüş dahil).

Çalıştır:  python -m unittest tests.test_gold_csv  (app/ kökünden)

Buradaki testlerin çoğu tek bir soruyu kovalıyor: **anotatörün yazdığı şey
gold'a bozulmadan ulaşıyor mu?** CSV katmanı sessizce veri kaybederse bunu
hiçbir metrik göstermez — sadece skorlar açıklanamaz biçimde düşer.
"""

import csv
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import lint_review_csv, report_iaa
from scripts.build_gold import build, infer_annotator, read_review_csv
from scripts.gold_schema import CAMPAIGN_TYPE_KEY
from scripts.to_review_csv import (
    COLUMNS,
    CSV_DELIMITER,
    CSV_ENCODING,
    balance_main,
    build_snippet,
    generate,
    partition,
    rows_for_doc,
    sort_rows,
    write_csv,
)
from src.extraction.llm.schema import EXTRACTION_FIELDS

TEXT = ("Konut finansmanında kâr payı oranı %1,89, 120 aya kadar vade. "
        "Tahsis ücreti 500 TL. Kampanya 31.12.2026 tarihine kadar geçerlidir.")


def make_doc(doc_id="kuveyt-turk--konut-001", **overrides):
    """Tek belgelik ön-anotasyon kaydı (preannotate.py çıktısıyla aynı biçim)."""
    span_start = TEXT.index("%1,89")
    doc = {
        "id": doc_id,
        "bank_slug": "kuveyt-turk",
        "source_url": "https://example.test/konut",
        "content_hash": "abc123",
        "text": TEXT,
        CAMPAIGN_TYPE_KEY: "Konut Finansmanı",
        "campaign_type_confidence": 0.8,
        "fields": {
            "kar_payi_orani": {
                "value": 1.89, "raw_value": "%1,89", "confidence": 0.95,
                "confidence_source": "rule_heuristic", "extractor": "rule",
                "source_span": "kâr payı oranı %1,89", "span_start": span_start,
                "span_end": span_start + len("%1,89"), "disagreement": False,
                "rule_value": 1.89, "llm_value": None,
            },
            "vade_ay": {
                "value": 120, "raw_value": "120 ay", "confidence": 0.6,
                "confidence_source": "rule_heuristic", "extractor": "rule",
                "source_span": "120 aya kadar", "span_start": TEXT.index("120 ay"),
                "span_end": TEXT.index("120 ay") + len("120 ay"),
                "disagreement": True, "rule_value": 120, "llm_value": 36,
            },
        },
        "missing_fields": [f for f in EXTRACTION_FIELDS
                           if f not in ("kar_payi_orani", "vade_ay")],
    }
    doc.update(overrides)
    return doc


def make_pre(docs):
    return {"schema_version": "1.0", "doc_count": len(docs), "docs": docs}


class TestRowGeneration(unittest.TestCase):
    def test_all_twelve_fields_plus_type_when_absent_included(self):
        """12 alan + campaign_type = 13 satır; eksiksiz kapsama böyle sağlanır."""
        rows = rows_for_doc(make_doc(), include_absent=True)
        self.assertEqual(len(rows), len(EXTRACTION_FIELDS) + 1)
        self.assertEqual({r["field"] for r in rows},
                         set(EXTRACTION_FIELDS) | {CAMPAIGN_TYPE_KEY})

    def test_only_found_fields_when_absent_excluded(self):
        rows = rows_for_doc(make_doc(), include_absent=False)
        self.assertEqual({r["field"] for r in rows},
                         {CAMPAIGN_TYPE_KEY, "kar_payi_orani", "vade_ay"})

    def test_missing_field_rows_have_empty_model_value(self):
        """Boş `model_value` = "model bir şey bulamadı"; boş bırakılırsa absent olur."""
        rows = {r["field"]: r for r in rows_for_doc(make_doc(), include_absent=True)}
        self.assertEqual(rows["taksit_sayisi"]["model_value"], "")
        self.assertEqual(rows["taksit_sayisi"]["model_conf"], "")

    def test_columns_match_contract(self):
        row = rows_for_doc(make_doc(), include_absent=True)[0]
        for column in COLUMNS:
            self.assertIn(column, row)

    def test_disagreement_flag_surfaces(self):
        rows = {r["field"]: r for r in rows_for_doc(make_doc(), include_absent=True)}
        self.assertEqual(rows["vade_ay"]["disagreement"], "EVET")
        self.assertEqual(rows["kar_payi_orani"]["disagreement"], "")

    def test_annotator_columns_start_empty(self):
        for row in rows_for_doc(make_doc(), include_absent=True):
            self.assertEqual(row["gold_value"], "")
            self.assertEqual(row["verdict"], "")
            self.assertEqual(row["note"], "")


class TestSnippet(unittest.TestCase):
    def test_value_is_bracketed(self):
        """Anotatörün gözü değeri aramasın diye değer köşeli parantezle işaretli."""
        payload = make_doc()["fields"]["kar_payi_orani"]
        snippet = build_snippet(TEXT, payload)
        self.assertIn("[%1,89]", snippet)

    def test_snippet_has_surrounding_context(self):
        payload = make_doc()["fields"]["kar_payi_orani"]
        snippet = build_snippet(TEXT, payload)
        self.assertIn("kâr payı oranı", snippet)

    def test_snippet_is_single_line(self):
        """CSV hücresine satır sonu sızarsa dosya Excel'de bozulur."""
        payload = make_doc()["fields"]["kar_payi_orani"]
        multiline = TEXT.replace(". ", ".\n")
        start = multiline.index("%1,89")
        payload = dict(payload, span_start=start, span_end=start + len("%1,89"))
        snippet = build_snippet(multiline, payload)
        self.assertNotIn("\n", snippet)

    def test_missing_payload_gives_document_context(self):
        snippet = build_snippet(TEXT, None)
        self.assertTrue(snippet.startswith("Konut finansmanında"))

    def test_bad_offsets_fall_back_to_search(self):
        """Offset bozuksa yanlış yeri boyamaktansa ham değeri metinde ara."""
        payload = {"value": 1.89, "raw_value": "%1,89",
                   "span_start": 9999, "span_end": 10000}
        self.assertIn("[%1,89]", build_snippet(TEXT, payload))


class TestSorting(unittest.TestCase):
    def test_disagreement_rows_come_first(self):
        rows = sort_rows(rows_for_doc(make_doc(), include_absent=True))
        self.assertEqual(rows[0]["field"], "vade_ay")
        self.assertEqual(rows[0]["disagreement"], "EVET")

    def test_empty_rows_come_last(self):
        """Kova 4 en sonda: zaman biterse en ucuz kayıp orada."""
        rows = sort_rows(rows_for_doc(make_doc(), include_absent=True))
        self.assertEqual(rows[-1]["model_value"], "")

    def test_high_confidence_after_low(self):
        rows = sort_rows(rows_for_doc(make_doc(), include_absent=True))
        fields = [r["field"] for r in rows]
        # vade_ay (anlaşmazlık) < kar_payi_orani (yüksek güven) < boş satırlar
        self.assertLess(fields.index("vade_ay"), fields.index("kar_payi_orani"))


class TestCsvRoundTrip(unittest.TestCase):
    def test_write_then_read_preserves_cells(self):
        rows = sort_rows(rows_for_doc(make_doc(), include_absent=True))
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "round1_A.csv"
            write_csv(rows, path)
            back = read_review_csv(path)
            self.assertEqual(len(back), len(rows))
            for original, restored in zip(rows, back, strict=False):
                for column in COLUMNS:
                    self.assertEqual(restored[column], original[column])

    def test_file_has_utf8_bom_for_turkish_excel(self):
        rows = rows_for_doc(make_doc(), include_absent=True)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "round1_A.csv"
            write_csv(rows, path)
            self.assertTrue(path.read_bytes().startswith(b"\xef\xbb\xbf"))

    def test_semicolon_delimiter(self):
        rows = rows_for_doc(make_doc(), include_absent=True)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "round1_A.csv"
            write_csv(rows, path)
            header = path.read_text(encoding=CSV_ENCODING).splitlines()[0]
            self.assertEqual(header.split(CSV_DELIMITER), COLUMNS)

    def test_turkish_characters_survive(self):
        rows = rows_for_doc(make_doc(), include_absent=True)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "round1_A.csv"
            write_csv(rows, path)
            content = path.read_text(encoding=CSV_ENCODING)
            self.assertIn("kâr payı", content)


def _fill(path, verdicts):
    """CSV'yi anotatör doldurmuş gibi günceller. `verdicts`: alan -> (verdict, değer, not)."""
    with path.open(encoding=CSV_ENCODING, newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter=CSV_DELIMITER))
    for row in rows:
        if row["field"] in verdicts:
            verdict, value, note = verdicts[row["field"]]
            row["verdict"] = verdict
            row["gold_value"] = value
            row["note"] = note
    with path.open("w", encoding=CSV_ENCODING, newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS, delimiter=CSV_DELIMITER,
                                lineterminator="\r\n")
        writer.writeheader()
        writer.writerows(rows)


class TestBuildGold(unittest.TestCase):
    """verdict -> gold eşlemesi (kılavuz §3)."""

    def _run(self, verdicts, second=None):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            pre_path = tmp / "pre.json"
            pre_path.write_text(json.dumps(make_pre([make_doc()]), ensure_ascii=False),
                                encoding="utf-8")

            rows = sort_rows(rows_for_doc(make_doc(), include_absent=True))
            paths = []
            csv_a = tmp / "round1_A.csv"
            write_csv(rows, csv_a)
            _fill(csv_a, verdicts)
            paths.append(str(csv_a))

            if second is not None:
                csv_b = tmp / "round1_B.csv"
                write_csv(rows, csv_b)
                _fill(csv_b, second)
                paths.append(str(csv_b))

            return build(str(pre_path), paths)

    def test_blank_verdict_accepts_model_value(self):
        """Boş hücre = "model doğru" -> değer `fields`'a girer."""
        result = self._run({})
        record = result["records"][0]
        self.assertEqual(record.fields["kar_payi_orani"], 1.89)
        self.assertEqual(record.fields["vade_ay"], 120)

    def test_blank_verdict_on_empty_row_becomes_absent(self):
        """Model bir şey bulamadı + anotatör onayladı = "kontrol ettim, YOK"."""
        record = self._run({})["records"][0]
        self.assertIn("taksit_sayisi", record.absent_fields)
        self.assertNotIn("taksit_sayisi", record.fields)

    def test_full_coverage_reached(self):
        """13 satırın tamamı karara bağlanınca 12/12 kapsama olmalı."""
        record = self._run({})["records"][0]
        self.assertEqual(record.coverage(), len(EXTRACTION_FIELDS))

    def test_absent_on_produced_value_is_recorded(self):
        """EN KRİTİK VAKA: model uydurdu -> onaylanmış halüsinasyon (FP)."""
        record = self._run({"kar_payi_orani": ("absent", "", "")})["records"][0]
        self.assertIn("kar_payi_orani", record.absent_fields)
        self.assertNotIn("kar_payi_orani", record.fields)

    def test_fix_parses_turkish_input(self):
        record = self._run({"vade_ay": ("fix", "36 ay", "")})["records"][0]
        self.assertEqual(record.fields["vade_ay"], 36)

    def test_fix_without_verdict_still_applies(self):
        """Anotatör düzeltmeyi yazıp verdict'i atlarsa veri kaybedilmemeli."""
        record = self._run({"vade_ay": ("", "36 ay", "")})["records"][0]
        self.assertEqual(record.fields["vade_ay"], 36)

    def test_unclear_is_excluded_from_metrics(self):
        record = self._run({"vade_ay": ("unclear", "", "")})["records"][0]
        self.assertIn("vade_ay", record.unclear_fields)
        self.assertNotIn("vade_ay", record.fields)
        self.assertNotIn("vade_ay", record.absent_fields)
        self.assertTrue(record.needs_adjudication)

    def test_hashtags_become_hard_tags(self):
        record = self._run({"vade_ay": ("", "", "aralık var #kosullu_aralik")})["records"][0]
        self.assertIn("kosullu_aralik", record.hard_tags)

    def test_note_is_preserved(self):
        record = self._run({"vade_ay": ("", "", "şüpheli")})["records"][0]
        self.assertIn("şüpheli", record.notes["vade_ay"])

    def test_campaign_type_absent_excludes_document(self):
        """Menü/kurumsal sayfa gold'u kirletmesin diye ucuz bir kaçış yolu."""
        result = self._run({CAMPAIGN_TYPE_KEY: ("absent", "", "")})
        self.assertEqual(result["records"], [])
        self.assertEqual(len(result["excluded"]), 1)
        self.assertEqual(result["excluded"][0]["reason"], "kampanya_degil")

    def test_campaign_type_fix(self):
        record = self._run({CAMPAIGN_TYPE_KEY: ("fix", "Taşıt Finansmanı", "")})["records"][0]
        self.assertEqual(record.campaign_type, "Taşıt Finansmanı")

    def test_provenance_carried_over(self):
        record = self._run({})["records"][0]
        self.assertEqual(record.bank_slug, "kuveyt-turk")
        self.assertEqual(record.source_url, "https://example.test/konut")
        self.assertEqual(record.content_hash, "abc123")
        self.assertEqual(record.text, TEXT)


class TestDoubleAnnotation(unittest.TestCase):
    def _run(self, first, second):
        return TestBuildGold._run(self, first, second)

    def test_agreement_applies_value(self):
        result = self._run({"vade_ay": ("fix", "36 ay", "")},
                           {"vade_ay": ("fix", "36 ay", "")})
        record = result["records"][0]
        self.assertEqual(record.fields["vade_ay"], 36)
        self.assertEqual(result["conflicts"], [])
        self.assertFalse(record.needs_adjudication)

    def test_equivalent_formats_count_as_agreement(self):
        """Biri `36 ay`, diğeri `3 yıl` yazmışsa bu ÇELİŞKİ DEĞİLDİR."""
        result = self._run({"vade_ay": ("fix", "36 ay", "")},
                           {"vade_ay": ("fix", "3 yıl", "")})
        self.assertEqual(result["records"][0].fields["vade_ay"], 36)
        self.assertEqual(result["conflicts"], [])

    def test_value_conflict_becomes_unclear(self):
        """Çelişki gizlenmez, otomatik de çözülmez — insana kalır."""
        result = self._run({"vade_ay": ("fix", "36 ay", "")},
                           {"vade_ay": ("fix", "48 ay", "")})
        record = result["records"][0]
        self.assertIn("vade_ay", record.unclear_fields)
        self.assertTrue(record.needs_adjudication)
        self.assertEqual(len(result["conflicts"]), 1)

    def test_present_versus_absent_conflict(self):
        """Biri "değer var" diyor, diğeri "yok" diyor -> hakemlik."""
        result = self._run({"kar_payi_orani": ("", "", "")},
                           {"kar_payi_orani": ("absent", "", "")})
        self.assertIn("kar_payi_orani", result["records"][0].unclear_fields)
        self.assertEqual(len(result["conflicts"]), 1)

    def test_both_annotators_recorded(self):
        result = self._run({}, {})
        self.assertEqual(result["records"][0].annotators, ["A", "B"])


class TestErrorReporting(unittest.TestCase):
    def test_bad_value_reports_file_line_and_fix(self):
        """Hata mesajı NEREDE ve NASIL düzeltileceğini söylemeli."""
        result = TestBuildGold._run(
            self, {"kampanya_suresi": ("fix", "yakında bir ara", "")})
        self.assertEqual(len(result["errors"]), 1)
        message = str(result["errors"][0])
        self.assertIn("round1_A.csv", message)
        self.assertIn("kampanya_suresi", message)
        self.assertIn("2026-12-31", message)      # doğru biçim örneği

    def test_fix_without_value_is_an_error(self):
        result = TestBuildGold._run(self, {"vade_ay": ("fix", "", "")})
        self.assertTrue(any("gold_value boş" in str(e) for e in result["errors"]))

    def test_unknown_verdict_is_an_error(self):
        result = TestBuildGold._run(self, {"vade_ay": ("belki", "", "")})
        self.assertTrue(any("tanınmıyor" in str(e) for e in result["errors"]))

    def test_wrong_header_raises_actionable_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.csv"
            path.write_text("a;b;c\n1;2;3\n", encoding=CSV_ENCODING)
            with self.assertRaises(ValueError) as ctx:
                read_review_csv(path)
            self.assertIn("to_review_csv", str(ctx.exception))


class TestAnnotatorInference(unittest.TestCase):
    def test_names_from_filenames(self):
        cases = {
            "round1_A.csv": "A",
            "round1_B.csv": "B",
            "round1_main_C.csv": "C",
            "round0_kalibrasyon_efe.csv": "efe",
        }
        for filename, expected in cases.items():
            with self.subTest(filename=filename):
                self.assertEqual(infer_annotator(filename), expected)


class TestPartitionAndBalance(unittest.TestCase):
    def test_partitions_are_disjoint_and_complete(self):
        ids = [f"doc-{i:03d}" for i in range(250)]
        calib, dup, main = partition(ids, 20, 50, seed=42)
        self.assertEqual(len(calib), 20)
        self.assertEqual(len(dup), 50)
        self.assertEqual(len(main), 180)
        self.assertEqual(set(calib) | set(dup) | set(main), set(ids))
        self.assertEqual(set(calib) & set(dup), set())
        self.assertEqual(set(dup) & set(main), set())

    def test_partition_is_deterministic(self):
        ids = [f"doc-{i:03d}" for i in range(250)]
        self.assertEqual(partition(ids, 20, 50, seed=42),
                         partition(ids, 20, 50, seed=42))

    def test_balance_equalises_row_load_not_doc_count(self):
        """A ve B'nin çift anotasyon yükü ana kümeden düşülmeli."""
        main = [f"m{i}" for i in range(100)]
        counts = {doc_id: 5 for doc_id in main}
        # A ve B'de 200'er satırlık sabit yük var, C ve D'de yok.
        assignment = balance_main(main, ["A", "B", "C", "D"], counts,
                                  [200, 200, 0, 0])
        totals = [200 + 5 * len(assignment["A"]), 200 + 5 * len(assignment["B"]),
                  5 * len(assignment["C"]), 5 * len(assignment["D"])]
        self.assertLessEqual(max(totals) - min(totals), 5)
        self.assertLess(len(assignment["A"]), len(assignment["C"]))

    def test_every_main_doc_assigned_exactly_once(self):
        main = [f"m{i}" for i in range(97)]
        counts = {doc_id: (i % 7) + 1 for i, doc_id in enumerate(main)}
        assignment = balance_main(main, ["A", "B", "C", "D"], counts, [0, 0, 0, 0])
        flat = [d for ids in assignment.values() for d in ids]
        self.assertEqual(sorted(flat), sorted(main))


class TestGenerateEndToEnd(unittest.TestCase):
    def test_generates_expected_files(self):
        docs = [make_doc(f"bank--doc-{i:03d}") for i in range(12)]
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            pre_path = tmp / "pre.json"
            pre_path.write_text(json.dumps(make_pre(docs), ensure_ascii=False),
                                encoding="utf-8")
            out = tmp / "review"
            plan = generate(str(pre_path), str(out), ["A", "B"], calibration=2,
                            duplicate=4, absent_docs=-1, seed=42)

            self.assertTrue((out / "round0_kalibrasyon_A.csv").exists())
            self.assertTrue((out / "round0_kalibrasyon_B.csv").exists())
            self.assertTrue((out / "round1_A.csv").exists())
            self.assertTrue((out / "round1_B.csv").exists())
            self.assertTrue((out / "_atama.md").exists())
            self.assertTrue((out / "_plan.json").exists())
            self.assertTrue((out / "belgeler" / "bank--doc-000.txt").exists())
            self.assertEqual(len(plan["calibration"]), 2)
            self.assertEqual(len(plan["duplicate"]), 4)

    def test_duplicate_files_are_identical(self):
        """A ve B AYNI satırları görmeli; yoksa kappa anlamsızdır."""
        docs = [make_doc(f"bank--doc-{i:03d}") for i in range(12)]
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            pre_path = tmp / "pre.json"
            pre_path.write_text(json.dumps(make_pre(docs), ensure_ascii=False),
                                encoding="utf-8")
            out = tmp / "review"
            generate(str(pre_path), str(out), ["A", "B"], calibration=0,
                     duplicate=4, absent_docs=-1, seed=42)
            self.assertEqual((out / "round1_A.csv").read_bytes(),
                             (out / "round1_B.csv").read_bytes())

    def test_stale_csvs_from_previous_run_are_removed(self):
        """Eski turdan kalan CSV, `--csv-dir` ile toplanıp belgeyi iki kez saydırır."""
        docs = [make_doc(f"bank--doc-{i:03d}") for i in range(12)]
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            pre_path = tmp / "pre.json"
            pre_path.write_text(json.dumps(make_pre(docs), ensure_ascii=False),
                                encoding="utf-8")
            out = tmp / "review"
            out.mkdir()
            stale = out / "round1_main_ESKI.csv"
            stale.write_text("bayat", encoding="utf-8")

            generate(str(pre_path), str(out), ["A", "B"], calibration=0,
                     duplicate=4, absent_docs=-1, seed=42)
            self.assertFalse(stale.exists())

    def test_absent_docs_limit_is_respected(self):
        docs = [make_doc(f"bank--doc-{i:03d}") for i in range(12)]
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            pre_path = tmp / "pre.json"
            pre_path.write_text(json.dumps(make_pre(docs), ensure_ascii=False),
                                encoding="utf-8")
            plan = generate(str(pre_path), str(tmp / "review"), ["A", "B"],
                            calibration=0, duplicate=0, absent_docs=3, seed=42)
            self.assertEqual(len(plan["absent_docs"]), 3)

    def test_duplicate_doc_ids_in_preannotation_are_loud(self):
        """Kimlik çakışması sözlüğe çevirirken SESSİZCE kayıt düşürür."""
        docs = [make_doc("bank--ayni"), make_doc("bank--ayni")]
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            pre_path = tmp / "pre.json"
            pre_path.write_text(json.dumps(make_pre(docs), ensure_ascii=False),
                                encoding="utf-8")
            with self.assertRaises(ValueError) as ctx:
                generate(str(pre_path), str(tmp / "review"), ["A"], calibration=0,
                         duplicate=0, absent_docs=-1, seed=42)
            self.assertIn("preannotate", str(ctx.exception))


class TestAnnotatedFilesAreProtected(unittest.TestCase):
    """Anotasyon içeren CSV silinemez ve üzerine yazılamaz.

    `generate` eski turun dosyalarını `round*.csv` kalıbıyla siliyor; kalıp
    TAMAMLANMIŞ dosyayı da kapsıyor. Korpus büyüdükçe ön-anotasyon tazelenmek
    zorunda, yani bu üreteç tekrar tekrar koşuyor — koruma olmadan bir gün
    insan emeği geri alınamaz biçimde gidiyor.
    """

    def _kur(self, tmp: Path):
        docs = [make_doc(f"bank--doc-{i:03d}") for i in range(12)]
        pre_path = tmp / "pre.json"
        pre_path.write_text(json.dumps(make_pre(docs), ensure_ascii=False),
                            encoding="utf-8")
        out = tmp / "review"
        generate(str(pre_path), str(out), ["A", "B"], calibration=2, duplicate=4,
                 absent_docs=-1, seed=42)
        return pre_path, out

    @staticmethod
    def _anote_et(path: Path, verdict: str = "absent") -> bytes:
        """Dosyanın ilk veri satırına karar yazar (insan anotasyonu taklidi)."""
        with path.open(encoding=CSV_ENCODING, newline="") as handle:
            rows = list(csv.DictReader(handle, delimiter=CSV_DELIMITER))
        rows[0]["verdict"] = verdict
        with path.open("w", encoding=CSV_ENCODING, newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=COLUMNS,
                                    delimiter=CSV_DELIMITER, lineterminator="\r\n")
            writer.writeheader()
            writer.writerows(rows)
        return path.read_bytes()

    def test_annotated_file_is_neither_deleted_nor_overwritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            pre_path, out = self._kur(tmp)
            hedef = out / "round0_kalibrasyon_A.csv"
            onceki = self._anote_et(hedef)

            plan = generate(str(pre_path), str(out), ["A", "B"], calibration=2,
                            duplicate=4, absent_docs=-1, seed=42)

            self.assertTrue(hedef.is_file(), "anotasyonlu dosya SİLİNDİ")
            self.assertEqual(hedef.read_bytes(), onceki,
                             "anotasyonlu dosyanın ÜZERİNE YAZILDI")
            self.assertIn("round0_kalibrasyon_A.csv", plan["protected"])
            self.assertNotIn("round0_kalibrasyon_A.csv", plan["files"])
            # Anotasyonsuz kardeş dosya normal şekilde yenilenmeli.
            self.assertIn("round0_kalibrasyon_B.csv", plan["files"])

    def test_stale_model_value_under_silent_approval_is_reported(self):
        """Boş satır = "gördüğüm değeri onaylıyorum". Değer değişmişse onay geçersiz.

        `build_gold` model değerini GÜNCEL ön-anotasyondan okuyor; korunan
        dosyadaki eski değer artık hiçbir yerde görünmez.
        """
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            pre_path, out = self._kur(tmp)
            hedef = out / "round0_kalibrasyon_A.csv"
            self._anote_et(hedef)          # yalnız 1. satırda karar var

            # Ön-anotasyonu tazele: vade 120 -> 36.
            data = json.loads(pre_path.read_text(encoding="utf-8"))
            for doc in data["docs"]:
                doc["fields"]["vade_ay"]["value"] = 36
            pre_path.write_text(json.dumps(data, ensure_ascii=False),
                                encoding="utf-8")

            plan = generate(str(pre_path), str(out), ["A", "B"], calibration=2,
                            duplicate=4, absent_docs=-1, seed=42)

            bayat = plan["protected_stale"]["round0_kalibrasyon_A.csv"]
            self.assertTrue(any("vade_ay" in item for item in bayat["riskli"]),
                            f"örtük onay bayatladı ama raporlanmadı: {bayat}")
            atama = (out / "_atama.md").read_text(encoding="utf-8")
            self.assertIn("YENİDEN bakılacak satırlar", atama)


class TestPinnedCalibration(unittest.TestCase):
    def test_calibration_set_can_be_pinned(self):
        """Kalibrasyon kümesi sabitlenmezse dört anotatör farklı belgelere bakar
        ve Fleiss kappa hesaplanamaz."""
        ids = [f"doc-{i:03d}" for i in range(250)]
        pinned = {"doc-100", "doc-200", "doc-007"}
        calib, dup, main = partition(ids, 20, 50, seed=42,
                                    pinned_calibration=pinned)
        self.assertEqual(calib, sorted(pinned))
        self.assertEqual(len(dup), 50)
        self.assertEqual(set(calib) | set(dup) | set(main), set(ids))
        self.assertEqual(set(calib) & (set(dup) | set(main)), set())

    def test_unknown_pinned_ids_are_ignored_not_invented(self):
        ids = [f"doc-{i:03d}" for i in range(10)]
        calib, dup, main = partition(ids, 2, 2, seed=42,
                                     pinned_calibration={"doc-001", "yok-999"})
        self.assertEqual(calib, ["doc-001"])
        self.assertNotIn("yok-999", calib + dup + main)


class TestInvalidModelValues(unittest.TestCase):
    """Şemaya uymayan çıkarım onaylanabilir bir değer olarak gösterilmez."""

    @staticmethod
    def _doc():
        doc = make_doc()
        doc["fields"].pop("kar_payi_orani")
        doc["invalid_fields"] = {
            "tahsis_ucreti": {
                "value": {"rate": 0.5}, "raw_value": "%1,89", "confidence": 0.9,
                "confidence_source": "rule_heuristic", "extractor": "rule",
                "source_span": "%1,89", "span_start": TEXT.index("%1,89"),
                "span_end": TEXT.index("%1,89") + len("%1,89"),
                "disagreement": False,
                "schema_error": 'tahsis_ucreti: para {"value": 500, ...} olmalı',
            }
        }
        return doc

    def test_row_exists_even_without_absent_coverage(self):
        """Model o alanda BİR ŞEY bulmuş; düzeltilecek yeri bilen tek satır bu."""
        rows = {r["field"]: r for r in rows_for_doc(self._doc(), include_absent=False)}
        self.assertIn("tahsis_ucreti", rows)

    def test_model_value_cell_stays_empty(self):
        """Dolu olsa boş verdict ONAY sayılır ve şema dışı değer gold'a girer."""
        rows = {r["field"]: r for r in rows_for_doc(self._doc(), include_absent=True)}
        row = rows["tahsis_ucreti"]
        self.assertEqual(row["model_value"], "")
        self.assertEqual(row["model_conf"], "")

    def test_snippet_carries_the_warning_and_the_span(self):
        rows = {r["field"]: r for r in rows_for_doc(self._doc(), include_absent=True)}
        snippet = rows["tahsis_ucreti"]["snippet"]
        self.assertIn("ŞEMA DIŞI", snippet)
        self.assertIn("[%1,89]", snippet)       # span işaretli kalmalı


# --------------------------------------------------------------------------- #
# v2 protokolü — boş hücre artık ONAY DEĞİL
# --------------------------------------------------------------------------- #
REVIEW_DIR = Path(__file__).resolve().parents[1] / "data" / "gold" / "review"
V2_CALIBRATION = sorted(REVIEW_DIR.glob("round0_kalibrasyon_v2_*.csv"))


def _row(**overrides):
    """Tek inceleme satırı; `_line` lint için zorunlu."""
    row = {"doc_id": "kuveyt-turk--konut-001", "field": "kar_payi_orani",
           "model_value": "1.89", "gold_value": "", "verdict": "", "note": "",
           "_line": 2}
    row.update(overrides)
    return row


class TestProtocolAwareVerdict(unittest.TestCase):
    """`ANNOTATION_GUIDE.md` §3.1 — boş hücrenin anlamı protokole bağlı.

    v1'de boş = `ok` idi ve gold, modelin çıktısına ÇAPALANDI: anotatörün
    bakmadığı satırda model kendi cevabıyla karşılaştırılıp haklı çıktı
    (mikro-F1 0,677 vs kör protokolde 0,536). v2'de boş = karar verilmedi.
    """

    def test_v1_bos_hucre_ok_sayilir(self):
        """Geriye dönük uyum: `protokol` sütunu yoksa dosya v1'dir."""
        self.assertEqual(report_iaa.row_verdict(_row()), "ok")

    def test_v2_bos_hucre_karar_degildir(self):
        self.assertIsNone(report_iaa.row_verdict(_row(protokol="v2")))

    def test_v2_acik_onay_ok_olarak_okunur(self):
        """Onay AÇIK işaretle verilir; `ok` yazan satır uyuma girer."""
        self.assertEqual(report_iaa.row_verdict(_row(protokol="v2", verdict="ok")),
                         "ok")

    def test_her_iki_protokolde_de_yazilmis_duzeltme_korunur(self):
        """`verdict` atlanmış ama değer yazılmışsa `fix`; o emek çöpe atılmaz."""
        for protocol in ("v1", "v2"):
            with self.subTest(protocol=protocol):
                row = _row(protokol=protocol, gold_value="2.05")
                self.assertEqual(report_iaa.row_verdict(row), "fix")
                self.assertEqual(report_iaa.row_value_token(row), "2.05")

    def test_v2_karar_verilmemis_satirin_degeri_de_yoktur(self):
        """Boş satır Krippendorff'a eksik değer olarak girer, modelin değeri değil."""
        self.assertIsNone(report_iaa.row_value_token(_row(protokol="v2")))
        self.assertEqual(report_iaa.row_value_token(_row()), "1.89")

    def test_bilinmeyen_protokol_degeri_v1_kabul_edilir(self):
        """Tanınmayan değer sessizce v2 sayılmamalı — v1 güvenli varsayılandır."""
        self.assertEqual(report_iaa.row_protocol(_row(protokol="v3")), "v1")
        self.assertEqual(report_iaa.row_protocol(_row(protokol="V2")), "v2")


class TestLintCompleteness(unittest.TestCase):
    """`lint_review_csv` — v2'de karar verilmemiş satır sayılır.

    Varsayılan UYARI (anotasyon sürüyor), `--eksiksiz` ile HATA: `build_gold`
    hâlâ v1 sözleşmesini uyguladığı için boş satırın ona ULAŞMAMASI gerekir.
    """

    def _findings(self, rows, protocol="auto", require_complete=False):
        return list(lint_review_csv.check_completeness(
            rows, "x.csv", protocol, require_complete))

    def test_v1_dosyada_bos_satir_bulgu_uretmez(self):
        self.assertEqual(self._findings([_row()]), [])

    def test_v2_bos_satir_varsayilanda_uyaridir(self):
        findings = self._findings([_row(protokol="v2")])
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].severity, lint_review_csv.SEVERITY_WARN)

    def test_eksiksiz_bayragi_hataya_cevirir(self):
        findings = self._findings([_row(protokol="v2")], require_complete=True)
        self.assertEqual(findings[0].severity, lint_review_csv.SEVERITY_ERROR)

    def test_dosya_basina_tek_bulgu(self):
        """260 özdeş satır 260 bulgu basmamalı; gerçek biçim hataları kaybolur."""
        rows = [_row(protokol="v2", _line=n) for n in range(2, 262)]
        findings = self._findings(rows, require_complete=True)
        self.assertEqual(len(findings), 1)
        self.assertIn("260/260", findings[0].message)

    def test_karar_verilmis_dosya_temiz(self):
        rows = [_row(protokol="v2", verdict="ok"),
                _row(protokol="v2", verdict="absent"),
                _row(protokol="v2", gold_value="2.05")]
        self.assertEqual(self._findings(rows, require_complete=True), [])


@unittest.skipUnless(V2_CALIBRATION, "v2 kalibrasyon paketi yok")
class TestV2CalibrationPackage(unittest.TestCase):
    """Paket bütünlüğü — κ ancak AYNI satırlar paylaşılırsa hesaplanır.

    `data/gold/parca/parca-1..4.json` tamamen ayrıktır (48 belge, sıfır tekrar)
    ve tam bu yüzden κ vermez. Bu paket o hatayı tekrarlamamalı.
    """

    @classmethod
    def setUpClass(cls):
        cls.files = {p.name: read_review_csv(p) for p in V2_CALIBRATION}

    def test_dort_anotator_dosyasi_var(self):
        self.assertEqual(len(self.files), 4)
        self.assertEqual({infer_annotator(name) for name in self.files},
                         {"v2_A", "v2_B", "v2_C", "v2_D"})

    def test_ayni_satir_kumesi_paylasilir(self):
        keys = [ {(r["doc_id"], r["field"]) for r in rows}
                 for rows in self.files.values() ]
        for other in keys[1:]:
            self.assertEqual(keys[0], other)
        self.assertEqual(len({k[0] for k in keys[0]}), 20)   # 20 belge
        self.assertEqual(len(keys[0]), 260)

    def test_protokol_sutunu_v2(self):
        for name, rows in self.files.items():
            with self.subTest(file=name):
                self.assertTrue(all(report_iaa.row_protocol(r) == "v2"
                                    for r in rows))

    def test_karar_sutunlari_bos_baslar(self):
        for name, rows in self.files.items():
            with self.subTest(file=name):
                for column in ("gold_value", "verdict", "note"):
                    self.assertEqual({(r.get(column) or "").strip() for r in rows},
                                     {""})

    def test_bos_paket_sahte_kappa_uretmez(self):
        """Hiç karar yokken κ 'ölçülemedi' (nan) olmalı, 1,0 değil."""
        result = report_iaa.compute([str(p) for p in V2_CALIBRATION])
        self.assertNotEqual(result["verdict_kappa"], result["verdict_kappa"])
        self.assertFalse(result["mixed_protocols"])
        self.assertEqual(result["shared_rows"], 260)

    def test_karisik_protokol_isaretlenir(self):
        """v1 + v2 aynı koşuda birleştirilirse rapor bunu SÖYLEMELİ."""
        v1_file = REVIEW_DIR / "round0_kalibrasyon_A.csv"
        if not v1_file.exists():
            self.skipTest("v1 referans dosyası yok")
        result = report_iaa.compute([str(v1_file), str(V2_CALIBRATION[0])])
        self.assertTrue(result["mixed_protocols"])
        self.assertIn("UYARI", report_iaa.render(result))


if __name__ == "__main__":
    unittest.main()
