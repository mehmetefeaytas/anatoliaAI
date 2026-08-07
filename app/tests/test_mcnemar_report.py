"""`scripts/mcnemar_report.py` — eşleştirme doğru kuruluyor mu?

İlgili: ../scripts/mcnemar_report.py, ../eval/stats.py, ../eval/report.py

İstatistiğin kendisi `eval/stats.py`de ve `tests/test_stats.py`de sınanıyor;
burada sınanan şey **hizalama** ve **raporlama sözleşmesi**:

- `(matcher, doc_id, field)` anahtarı kesişimde mi alınıyor,
- hizalanamayan anahtar SESSİZCE atılıyor mu (atılmamalı — sayılmalı),
- eşleştiriciler karışıyor mu (strict kararı tolerant'la eşleşmemeli),
- bootstrap birimi BELGE mi (alan düzeyinde örneklemek GA'yı yapay daraltır),
- bilinen cevaplı küçük vakada b/c sayımı doğru mu.
"""

from __future__ import annotations

import contextlib
import csv
import io
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from eval.report import CSV_DELIMITER, DECISION_COLUMNS
from scripts.mcnemar_report import (
    align,
    compare,
    doc_units,
    load_decisions,
    main,
    markdown_report,
    matchers_in,
    resolve_decisions_path,
)


def write_decisions(path: Path, rows: list[tuple[str, str, str, int]]) -> Path:
    """Test yardımcısı — `decisions.csv` üretir (üretimdeki ayırıcıyla)."""
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh, delimiter=CSV_DELIMITER)
        writer.writerow(DECISION_COLUMNS)
        writer.writerows(rows)
    return path


class TestOkuma(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_dosya_yolu_okunur(self):
        p = write_decisions(self.root / "decisions.csv",
                            [("strict", "d1", "vade_ay", 1)])
        self.assertEqual(load_decisions(p), {("strict", "d1", "vade_ay"): True})

    def test_dizin_verilirse_decisions_csv_aranir(self):
        write_decisions(self.root / "decisions.csv",
                        [("strict", "d1", "vade_ay", 0)])
        self.assertEqual(resolve_decisions_path(self.root).name, "decisions.csv")
        self.assertEqual(load_decisions(self.root),
                         {("strict", "d1", "vade_ay"): False})

    def test_eksik_dosya_hata(self):
        with self.assertRaises(FileNotFoundError):
            load_decisions(self.root / "yok.csv")

    def test_eksik_sutun_hata(self):
        p = self.root / "bozuk.csv"
        p.write_text("matcher;doc_id\nstrict;d1\n", encoding="utf-8")
        with self.assertRaises(ValueError):
            load_decisions(p)

    def test_mukerrer_anahtar_HATA(self):
        """Sessizce üzerine yazmak eşleştirmeyi bozar."""
        p = write_decisions(self.root / "d.csv", [
            ("strict", "d1", "vade_ay", 1),
            ("strict", "d1", "vade_ay", 0),
        ])
        with self.assertRaises(ValueError):
            load_decisions(p)

    def test_cozumlenemeyen_correct_HATA(self):
        p = self.root / "d.csv"
        p.write_text("matcher;doc_id;field;correct\nstrict;d1;vade_ay;belki\n",
                     encoding="utf-8")
        with self.assertRaises(ValueError):
            load_decisions(p)

    def test_bos_dosya_HATA(self):
        p = write_decisions(self.root / "d.csv", [])
        with self.assertRaises(ValueError):
            load_decisions(p)

    def test_matchers_in(self):
        p = write_decisions(self.root / "d.csv", [
            ("strict", "d1", "vade_ay", 1),
            ("tolerant", "d1", "vade_ay", 1),
        ])
        self.assertEqual(matchers_in(load_decisions(p)), ["strict", "tolerant"])


class TestHizalama(unittest.TestCase):

    A = {("strict", "d1", "f1"): True,
         ("strict", "d1", "f2"): False,
         ("strict", "d2", "f1"): True,
         ("tolerant", "d1", "f1"): False}
    B = {("strict", "d1", "f1"): False,
         ("strict", "d1", "f2"): False,
         ("strict", "d3", "f1"): True,
         ("tolerant", "d1", "f1"): True}

    def test_kesisim_alinir(self):
        al = align(self.A, self.B, "strict")
        self.assertEqual(al.keys, [("strict", "d1", "f1"), ("strict", "d1", "f2")])
        self.assertEqual(al.a_correct, [True, False])
        self.assertEqual(al.b_correct, [False, False])

    def test_hizalanamayanlar_SAYILIR_atilmaz(self):
        al = align(self.A, self.B, "strict")
        self.assertEqual(al.only_a, [("strict", "d2", "f1")])
        self.assertEqual(al.only_b, [("strict", "d3", "f1")])
        self.assertEqual(al.n_unaligned, 2)
        self.assertEqual(al.as_dict()["n_only_a"], 1)

    def test_esleştiriciler_KARISMAZ(self):
        """strict kararı tolerant kararıyla eşleşirse test anlamsızlaşır."""
        al = align(self.A, self.B, "tolerant")
        self.assertEqual(al.keys, [("tolerant", "d1", "f1")])
        self.assertEqual(al.a_correct, [False])

    def test_ortak_karar_yoksa_HATA(self):
        with self.assertRaises(ValueError):
            compare({("strict", "d1", "f1"): True},
                    {("strict", "d9", "f1"): True}, "strict", n_resamples=10)

    def test_bootstrap_birimi_BELGE(self):
        al = align(self.A, self.B, "strict")
        units = doc_units(al)
        # d1'in iki alanı TEK birimde toplanır; alan düzeyinde olsaydı 2 birim.
        self.assertEqual(len(units), 1)
        self.assertEqual(len(units[0]), 2)


class TestKarsilastirma(unittest.TestCase):
    """Bilinen cevaplı küçük vaka — b/c sayımı ve GA davranışı."""

    def _arms(self, a_flags: list[bool], b_flags: list[bool]
              ) -> tuple[dict, dict]:
        a, b = {}, {}
        for i, (x, y) in enumerate(zip(a_flags, b_flags, strict=True)):
            key = ("strict", f"d{i}", "f1")
            a[key], b[key] = x, y
        return a, b

    def test_b_c_sayimi(self):
        # A doğru & B yanlış: 3 kez; A yanlış & B doğru: 1 kez.
        a, b = self._arms([True, True, True, False, True],
                          [False, False, False, True, True])
        cmp_ = compare(a, b, "strict", a_name="A", b_name="B", n_resamples=50)
        self.assertEqual((cmp_.mcnemar.b, cmp_.mcnemar.c), (3, 1))
        self.assertEqual(cmp_.mcnemar.n_agree_correct, 1)
        self.assertEqual(cmp_.mcnemar.method, "exact_binomial")

    def test_dogruluk_noktalari(self):
        a, b = self._arms([True, True, False, False],
                          [True, False, False, False])
        cmp_ = compare(a, b, "strict", n_resamples=50)
        self.assertAlmostEqual(cmp_.acc_a, 0.5)
        self.assertAlmostEqual(cmp_.acc_b, 0.25)

    def test_ayni_kol_fark_sifir(self):
        a, _ = self._arms([True, False, True], [True, False, True])
        cmp_ = compare(a, dict(a), "strict", n_resamples=50)
        self.assertEqual((cmp_.mcnemar.b, cmp_.mcnemar.c), (0, 0))
        self.assertAlmostEqual(cmp_.diff_ci.point, 0.0)
        self.assertFalse(cmp_.diff_significant)

    def test_ayni_seed_ayni_ga(self):
        a, b = self._arms([True, True, False, True, False, True],
                          [False, True, False, False, False, True])
        one = compare(a, b, "strict", n_resamples=200, seed=42)
        two = compare(a, b, "strict", n_resamples=200, seed=42)
        self.assertEqual((one.diff_ci.low, one.diff_ci.high),
                         (two.diff_ci.low, two.diff_ci.high))

    def test_sozluk_ciktisi_alanlari(self):
        a, b = self._arms([True, False], [False, False])
        data = compare(a, b, "strict", n_resamples=50).as_dict()
        for key in ("mcnemar", "accuracy_diff_ci", "alignment",
                    "independent_ci_overlap", "paired_diff_significant"):
            with self.subTest(key=key):
                self.assertIn(key, data)

    def test_markdown_n_uyarisi_ve_hizalama_notu(self):
        a, b = self._arms([True, False, True], [False, False, True])
        a[("strict", "yalniz-a", "f1")] = True
        cmp_ = compare(a, b, "strict", a_name="temel", b_name="n-gram",
                       n_resamples=50)
        md = markdown_report([cmp_], n_docs=cmp_.n_docs, alpha=0.05)
        self.assertIn(f"n = **{cmp_.n_docs} belge**", md)
        self.assertIn("hizalanamadı", md)
        self.assertIn("temel", md)


class TestCLI(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.a = self.root / "a"
        self.b = self.root / "b"
        self.a.mkdir()
        self.b.mkdir()
        write_decisions(self.a / "decisions.csv", [
            ("strict", "d1", "f1", 1), ("strict", "d1", "f2", 1),
            ("strict", "d2", "f1", 1), ("strict", "d2", "f2", 0),
        ])
        write_decisions(self.b / "decisions.csv", [
            ("strict", "d1", "f1", 0), ("strict", "d1", "f2", 1),
            ("strict", "d2", "f1", 0), ("strict", "d3", "f1", 1),
        ])

    def tearDown(self):
        self.tmp.cleanup()

    def _run(self, *extra: str) -> tuple[int, str]:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            code = main(["--a", str(self.a), "--b", str(self.b),
                         "--resamples", "50", *extra])
        return code, buf.getvalue()

    def test_basarili_kosum(self):
        code, out = self._run("--ad-a", "temel", "--ad-b", "n-gram")
        self.assertEqual(code, 0)
        self.assertIn("temel ↔ n-gram", out)

    def test_hizalanamayanlar_KONSOLA_yazilir(self):
        _, out = self._run()
        # A'da d2/f2 var B'de yok; B'de d3/f1 var A'da yok.
        self.assertIn("hizalanamayan   : 2", out)

    def test_json_ve_markdown_yazilir(self):
        js, md = self.root / "o.json", self.root / "o.md"
        code, _ = self._run("--json", str(js), "--markdown", str(md))
        self.assertEqual(code, 0)
        self.assertTrue(js.is_file())
        self.assertTrue(md.is_file())
        self.assertIn("belge", md.read_text(encoding="utf-8"))

    def test_eksik_dosya_cikis_2(self):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            code = main(["--a", str(self.root / "yok"), "--b", str(self.b)])
        self.assertEqual(code, 2)

    def test_ortak_esleştirici_yoksa_cikis_2(self):
        write_decisions(self.b / "decisions.csv",
                        [("tolerant", "d1", "f1", 1)])
        code, out = self._run()
        self.assertEqual(code, 2)
        self.assertIn("ortak eşleştirici yok", out)


if __name__ == "__main__":
    unittest.main()
