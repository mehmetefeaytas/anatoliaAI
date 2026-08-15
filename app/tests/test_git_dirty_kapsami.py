"""`git_dirty` ölçümün KENDİ çıktısını kirlilik saymaz.

İlgili: ../eval/report.py (`git_dirty`, `TURETILMIS_YOLLAR`)
        ../scripts/kanit_tazeligi.py (bu bayrağı kanıt kapısı olarak okur)

## Neden bu test var

Bayrak özyinelemeli olarak `True`ya kilitleniyordu: her ölçüm koşusu
`eval/reports/<damga>/` yazıyor, o dizin izlenmeyen olarak görünüyor ve
**bir sonraki koşu** kendini kirli ağaçta sanıyordu. Kusur koşumda değil
bayraktaydı.

Ölçülmüş sonucu: 2026-08-12 tarihli `gold.v2` raporu `git_dirty=true` ile
damgalandı; kanıt-tazeliği kapısı onu haklı olarak reddetti ve yayımlanan
manşet sayılarımız (0,452 · 0,059) bir anda kanıtsız kaldı. Sayılar
yanlış değildi — kanıtları savunulamaz hâldeydi.

Denge kritik ve iki yönlü kırılabilir:
  * Türetilmiş çıktı sayılırsa → hiçbir rapor asla temiz olamaz.
  * Kaynak değişikliği sayılmazsa → bayrak yalan söyler ve tekrar
    üretilemez bir sayı "commit'e karşılık geliyor" diye damgalanır.
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from eval import report as R
from tests._ortam_gereksinimleri import git_gerekir


def _git(kok: Path, *a: str) -> str:
    return subprocess.run(["git", "-C", str(kok), *a], capture_output=True,
                          text=True, check=True).stdout


@git_gerekir
class TestGitDirtyKapsami(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.kok = Path(self._tmp.name)
        _git(self.kok, "init", "-q")
        _git(self.kok, "config", "user.email", "t@t")
        _git(self.kok, "config", "user.name", "t")
        (self.kok / "app" / "src").mkdir(parents=True)
        (self.kok / "app" / "src" / "a.py").write_text("x = 1\n", encoding="utf-8")
        _git(self.kok, "add", "-A")
        _git(self.kok, "commit", "-qm", "ilk")

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _rapor_yaz(self) -> None:
        d = self.kok / "app" / "eval" / "reports" / "20260815-000000"
        d.mkdir(parents=True)
        (d / "report.md").write_text("# rapor\n", encoding="utf-8")

    def test_temiz_agac_False(self) -> None:
        self.assertIs(R.git_dirty(self.kok), False)

    def test_olcumun_KENDI_ciktisi_kirlilik_SAYILMAZ(self) -> None:
        """Bu düzeltilmezse hiçbir rapor hiçbir zaman kanıt olamaz."""
        self._rapor_yaz()
        self.assertIs(R.git_dirty(self.kok), False)

    def test_KAYNAK_degisikligi_kirlilik_SAYILIR(self) -> None:
        """Gevşetme buraya sızarsa bayrak yalan söylemeye başlar."""
        (self.kok / "app" / "src" / "a.py").write_text("x = 2\n", encoding="utf-8")
        self.assertIs(R.git_dirty(self.kok), True)

    def test_izlenmeyen_YENI_kaynak_da_sayilir(self) -> None:
        (self.kok / "app" / "src" / "yeni.py").write_text("y = 1\n", encoding="utf-8")
        self.assertIs(R.git_dirty(self.kok), True)

    def test_rapor_VE_kaynak_birlikte_degistiyse_kirli(self) -> None:
        """Türetilmiş çıktı, yanındaki gerçek kirliliği MASKELEMEMELİ."""
        self._rapor_yaz()
        (self.kok / "app" / "src" / "a.py").write_text("x = 3\n", encoding="utf-8")
        self.assertIs(R.git_dirty(self.kok), True)

    def test_izlenen_rapor_degisirse_de_temiz(self) -> None:
        self._rapor_yaz()
        _git(self.kok, "add", "-A")
        _git(self.kok, "commit", "-qm", "rapor")
        yol = self.kok / "app" / "eval" / "reports" / "20260815-000000" / "report.md"
        yol.write_text("# degisti\n", encoding="utf-8")
        self.assertIs(R.git_dirty(self.kok), False)

    def test_git_yoksa_None_doner(self) -> None:
        """Bilinmiyor ile temiz aynı şey değildir; None gizlenmez."""
        with tempfile.TemporaryDirectory() as d:
            self.assertIsNone(R.git_dirty(Path(d)))


class TestTuretilmisYollar(unittest.TestCase):
    def test_liste_bos_degil_ve_depo_kokune_gore(self) -> None:
        self.assertTrue(R.TURETILMIS_YOLLAR)
        for y in R.TURETILMIS_YOLLAR:
            with self.subTest(yol=y):
                self.assertTrue(y.startswith("app/"),
                                "yol depo köküne göre olmalı")
                self.assertTrue(y.endswith("/"),
                                "dizin öneki olmalı; dosya adı öneki "
                                "beklenmedik yolları da yakalar")


if __name__ == "__main__":
    unittest.main()
