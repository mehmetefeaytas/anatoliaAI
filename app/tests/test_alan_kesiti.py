"""Alan kesiti aracı — kesit toplama ve destek-0 kuralı.

İlgili: ../eval/alan_kesiti.py

## Neden bu dosya var

`docs/rapor/capraz-degerlendirme.md` bir alan ALT KÜMESİ üzerinden sayı
yayımlıyor ("ortak 5 alan"). O sayı elle hesaplanırsa kanıtı olmayan bir
iddia olur; araç onu `per_field.csv`'den yeniden üretiyor. Bu testler aracın
iki davranışını kilitler:

  KAPI 1 — toplama doğru: mikro havuz alanlar boyunca toplanır, makro ise
           alan F1'lerinin ortalamasıdır (ikisi farklı sayıdır).
  KAPI 2 — destek 0 olan alan makro ortalamaya GİRMEZ. 0,0 saymak "motor bu
           alanda başarısız" gibi yanlış bir izlenim yaratır; alan yalnızca
           ölçülemez durumdadır (`eval/esikler.json` ile aynı gerekçe).
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from eval.alan_kesiti import KESITLER, kesit_oku

BASLIK = ("config;matcher;scope;field;precision;recall;f1;tp;fp;fn;tn;"
          "fp_hallucinated;fp_wrong;support;absent_decisions;"
          "skipped_undecided;unclear")


def _csv_yaz(dizin: Path, satirlar: list[str]) -> Path:
    (dizin / "per_field.csv").write_text(
        BASLIK + "\n" + "\n".join(satirlar) + "\n", encoding="utf-8")
    return dizin


def _satir(alan: str, tp: int, fp: int, fn: int,
           matcher: str = "strict", scope: str = "all") -> str:
    return (f"kural;{matcher};{scope};{alan};0;0;0;{tp};{fp};{fn};"
            f"0;0;0;{tp + fn};0;0;0")


class TestKesitToplama(unittest.TestCase):
    """KAPI 1 — mikro havuzu toplar, makro alan ortalamasını alır."""

    def test_mikro_ve_makro_ayri_hesaplanir(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            d = _csv_yaz(Path(td), [
                _satir("a", tp=3, fp=1, fn=0),   # F1 = 6/7  = 0,857
                _satir("b", tp=1, fp=0, fn=3),   # F1 = 2/5  = 0,400
            ])
            s = kesit_oku(d, ("a", "b"))
        # mikro: tp=4 fp=1 fn=3 -> P=0,8 R=0,571 -> F1=0,667
        self.assertAlmostEqual(s["mikro_f1"], 2 * 4 / (2 * 4 + 1 + 3), places=6)
        # makro: (0,857 + 0,400) / 2
        self.assertAlmostEqual(s["makro_f1"], (6 / 7 + 2 / 5) / 2, places=6)
        self.assertNotAlmostEqual(s["mikro_f1"], s["makro_f1"], places=3)

    def test_kesit_disindaki_alan_sayilmaz(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            d = _csv_yaz(Path(td), [
                _satir("a", tp=1, fp=0, fn=0),
                _satir("kapsam_disi", tp=99, fp=99, fn=99),
            ])
            s = kesit_oku(d, ("a",))
        self.assertEqual((s["tp"], s["fp"], s["fn"]), (1, 0, 0))

    def test_matcher_ve_scope_suzulur(self) -> None:
        """Aynı alan farklı matcher/scope ile birden çok satırda geçer."""
        with tempfile.TemporaryDirectory() as td:
            d = _csv_yaz(Path(td), [
                _satir("a", tp=1, fp=0, fn=0, matcher="strict", scope="all"),
                _satir("a", tp=9, fp=9, fn=9, matcher="tolerant", scope="all"),
                _satir("a", tp=7, fp=7, fn=7, matcher="strict", scope="hard"),
            ])
            s = kesit_oku(d, ("a",), matcher="strict", scope="all")
        self.assertEqual((s["tp"], s["fp"], s["fn"]), (1, 0, 0))


class TestDestekSifirKurali(unittest.TestCase):
    """KAPI 2 — destek 0 olan alan makro ortalamaya girmez."""

    def test_destek_sifir_makroyu_asagi_cekmez(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            d = _csv_yaz(Path(td), [
                _satir("dolu", tp=4, fp=0, fn=0),     # F1 = 1,0
                _satir("bos", tp=0, fp=0, fn=0),      # destek 0
            ])
            s = kesit_oku(d, ("dolu", "bos"))
        self.assertEqual(s["makro_paydasi"], 1)
        self.assertAlmostEqual(s["makro_f1"], 1.0, places=6)

    def test_eksik_alan_bildirilir(self) -> None:
        """Kesit tanımı ile koşumun alan kümesi ayrışırsa sessiz kalmaz."""
        with tempfile.TemporaryDirectory() as td:
            d = _csv_yaz(Path(td), [_satir("a", tp=1, fp=0, fn=0)])
            s = kesit_oku(d, ("a", "yok_boyle_bir_alan"))
        self.assertIn("yok_boyle_bir_alan", s["eksik"])


class TestKesitTanimlari(unittest.TestCase):
    """Adlandırılmış kesitler rapordaki iddialarla aynı kümeyi göstermeli."""

    def test_ortak5_bes_alan(self) -> None:
        self.assertEqual(len(KESITLER["ortak5"]), 5)
        self.assertIn("kar_payi_orani", KESITLER["ortak5"])

    def test_yapisal_kesitte_serbest_metin_yok(self) -> None:
        self.assertNotIn("kampanya_kosullari", KESITLER["yapisal"])


if __name__ == "__main__":
    unittest.main()
