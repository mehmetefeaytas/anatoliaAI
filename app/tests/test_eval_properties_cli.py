"""`eval/properties.py` korpus yükleme + CLI kapısı testleri.

İlgili: ../eval/properties.py

Buradaki iki değişmez, CI kapısının SESSİZCE yeşil vermesini engeller:

  1. **Çift sayım.** `data/raw/` her belgeyi hem `.html` hem `.txt` olarak
     tutar. İkisini birden saymak 849 belgeyi 1696 gösteriyordu.
  2. **Boş korpus.** Yanlış `--raw-dir` verildiğinde eski kod `UYARI` basıp
     **0** döndürüyordu; hiçbir şey denetlenmeden "geçti" raporlanıyordu.

`tests/test_properties.py` değişmezlerin KENDİSİNİ test eder; bu dosya
denetleyiciyi ÇALIŞTIRAN katmanı test eder.
"""

from __future__ import annotations

import contextlib
import io
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from eval.properties import (
    HTML_SUFFIXES,
    TEXT_SUFFIXES,
    PropertyReport,
    _main,
    load_corpus,
    run,
)

METIN = "Konut finansmanında kâr payı oranı %1,89, 120 aya kadar vade."


class TestKorpusYukleme(unittest.TestCase):
    """`load_corpus` — çift sayım hatası."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        # Aynı belgenin İKİ biçimi — data/raw'daki gerçek düzenin aynısı.
        for i in range(3):
            (self.root / f"kampanya-{i}.txt").write_text(METIN, encoding="utf-8")
            (self.root / f"kampanya-{i}.html").write_text(
                f"<html><body>{METIN}</body></html>", encoding="utf-8")
        (self.root / "kampanya-0.meta.json").write_text("{}", encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def test_varsayilan_yalniz_txt(self):
        """3 benzersiz belge -> 3, 6 DEĞİL."""
        self.assertEqual(len(load_corpus(str(self.root))), 3)

    def test_varsayilan_html_okumaz(self):
        corpus = load_corpus(str(self.root))
        self.assertTrue(all(k.endswith(".txt") for k in corpus))

    def test_include_html_ikisini_de_alir(self):
        self.assertEqual(len(load_corpus(str(self.root), include_html=True)), 6)

    def test_meta_json_hicbir_zaman_okunmaz(self):
        corpus = load_corpus(str(self.root), include_html=True)
        self.assertFalse(any(".meta.json" in k for k in corpus))

    def test_bos_dizin_bos_sozluk(self):
        with tempfile.TemporaryDirectory() as empty:
            self.assertEqual(load_corpus(empty), {})

    def test_olmayan_dizin_bos_sozluk(self):
        self.assertEqual(load_corpus(str(self.root / "yok")), {})

    def test_uzanti_sabitleri(self):
        self.assertEqual(TEXT_SUFFIXES, (".txt",))
        self.assertEqual(set(HTML_SUFFIXES), {".html", ".htm"})


class TestKapsamSayaci(unittest.TestCase):
    """`documents_with_fields` — "0 ihlal"in GERÇEK kapsamı.

    Alan çıkmayan belgede değişmez denetimi hiçbir şey test etmez ve otomatik
    geçer. Bu sayaç olmadan "N belgede 0 ihlal" bedava geçişlerle şişirilebilir.
    """

    def test_alan_cikan_belge_sayilir(self):
        rep = run({"a": METIN, "b": METIN})
        self.assertEqual(rep.documents, 2)
        self.assertEqual(rep.documents_with_fields, 2)

    def test_alansiz_belge_ayri_sayilir(self):
        rep = run({"dolu": METIN, "bos": "Merhaba dünya. Nasılsınız?"})
        self.assertEqual(rep.documents, 2)
        self.assertEqual(rep.documents_with_fields, 1)
        self.assertEqual(rep.documents_without_fields, 1)
        self.assertAlmostEqual(rep.coverage, 0.5)

    def test_ozet_kapsami_gosterir(self):
        summary = run({"dolu": METIN, "bos": "Merhaba."}).summary()
        self.assertIn("2 belge", summary)
        self.assertIn("1 tanesinde en az bir alan çıktı", summary)
        self.assertIn("kapsam", summary)

    def test_bos_rapor_kapsami_sifir(self):
        self.assertAlmostEqual(PropertyReport().coverage, 0.0)

    def test_ihlal_yoksa_gecti(self):
        self.assertTrue(run({"a": METIN}).passed)


class TestCLIKapisi(unittest.TestCase):
    """`_main` çıkış kodları — CI kapısı sessizce yeşil VERMEMELİ."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "a.txt").write_text(METIN, encoding="utf-8")
        self._argv = sys.argv

    def tearDown(self):
        sys.argv = self._argv
        self.tmp.cleanup()

    def _main_with(self, *args: str) -> int:
        sys.argv = ["properties", *args]
        with contextlib.redirect_stdout(io.StringIO()), \
                contextlib.redirect_stderr(io.StringIO()):
            return _main()

    def test_temiz_korpus_cikis_0(self):
        self.assertEqual(self._main_with("--raw-dir", str(self.root)), 0)

    def test_OLMAYAN_DIZIN_CIKIS_2(self):
        """En kritik test: eski kod burada 0 döndürüyordu (sessiz yeşil CI)."""
        self.assertEqual(self._main_with("--raw-dir", str(self.root / "yok")), 2)

    def test_bos_dizin_cikis_2(self):
        with tempfile.TemporaryDirectory() as empty:
            self.assertEqual(self._main_with("--raw-dir", empty), 2)

    def test_yalniz_html_iceren_dizin_varsayilanda_cikis_2(self):
        """`.txt` yoksa varsayılan süzgeç boş döner -> sessiz geçiş DEĞİL, hata."""
        with tempfile.TemporaryDirectory() as only_html:
            Path(only_html, "a.html").write_text(f"<p>{METIN}</p>",
                                                 encoding="utf-8")
            self.assertEqual(self._main_with("--raw-dir", only_html), 2)
            self.assertEqual(
                self._main_with("--raw-dir", only_html, "--include-html"), 0)

    def test_hata_mesaji_yol_gosterici(self):
        sys.argv = ["properties", "--raw-dir", str(self.root / "yok")]
        err = io.StringIO()
        with contextlib.redirect_stdout(io.StringIO()), \
                contextlib.redirect_stderr(err):
            _main()
        message = err.getvalue()
        self.assertIn("HATA", message)
        self.assertIn("--raw-dir", message)

    def test_jsonl_yazilir(self):
        out = self.root / "violations.jsonl"
        self.assertEqual(
            self._main_with("--raw-dir", str(self.root), "--out", str(out)), 0)
        self.assertTrue(out.is_file())


if __name__ == "__main__":
    unittest.main()
