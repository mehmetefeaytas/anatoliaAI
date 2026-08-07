"""Demo DB tazelik kapısı — sessiz bayatlamaya karşı.

İlgili: ../scripts/check_demo_db.py, ../docs/rapor/rag-terim-kapsama.md

Kapının var oluş sebebi gerçekleşmiş bir vakadır: `data/demo.db` 31 Temmuz'da
849 belgeyle kuruldu, korpus 3 Ağustos'ta 1761'e çıktı ve bir hafta boyunca
hiçbir test kırılmadı, hiçbir uyarı çıkmadı. Chatbot, dashboard ve RAG
korpusun %48'ini sessizce görmedi.

Testler kapının ÜÇ davranışını kilitler: güncelde 0, bayatta 1, DB yoksa
seçilebilir davranış. En kritiği ikincisi — kapı bayatı yakalamazsa yok
sayılır.
"""

from __future__ import annotations

import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import check_demo_db as C


def _db_kur(yol: Path, kampanya: int) -> None:
    conn = sqlite3.connect(yol)
    conn.execute("CREATE TABLE campaigns (id INTEGER PRIMARY KEY)")
    conn.executemany("INSERT INTO campaigns (id) VALUES (?)",
                     [(i,) for i in range(1, kampanya + 1)])
    conn.commit()
    conn.close()


def _korpus_kur(kok: Path, belge: int) -> None:
    # Özyinelemeli sayım sınanmalı: gerçek korpus banka/bölüm altında duruyor.
    for i in range(belge):
        d = kok / f"banka{i % 3}" / ("products" if i % 2 else "live")
        d.mkdir(parents=True, exist_ok=True)
        (d / f"belge{i}.txt").write_text("metin", encoding="utf-8")


class TestTazelikKapisi(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.kok = Path(self._tmp.name)
        self.db = self.kok / "demo.db"
        self.raw = self.kok / "raw"
        self.raw.mkdir()

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _kos(self, *ek: str) -> int:
        return C.main(["--db", str(self.db), "--raw-dir", str(self.raw), *ek])

    def test_guncelde_sifir(self) -> None:
        _db_kur(self.db, 10)
        _korpus_kur(self.raw, 10)
        self.assertEqual(self._kos(), 0)

    def test_BAYAT_yakalanir(self) -> None:
        """Yaşanan vaka: DB korpusun gerisinde kaldı."""
        _db_kur(self.db, 849)
        _korpus_kur(self.raw, 1761)
        self.assertEqual(self._kos(), 1, "bayat DB sessizce geçti")

    def test_db_korpustan_FAZLA_ise_de_yakalanir(self) -> None:
        """Ters yön de kusurdur: silinen belgeler DB'de yaşamaya devam eder."""
        _db_kur(self.db, 100)
        _korpus_kur(self.raw, 50)
        self.assertEqual(self._kos(), 1)

    def test_tolerans_kucuk_sapmayi_gecirir(self) -> None:
        _db_kur(self.db, 100)
        _korpus_kur(self.raw, 103)
        self.assertEqual(self._kos("--tolerans", "5"), 0)
        self.assertEqual(self._kos("--tolerans", "2"), 1)

    def test_db_yoksa_varsayilan_HATA(self) -> None:
        _korpus_kur(self.raw, 5)
        self.assertEqual(self._kos(), 2)

    def test_db_yoksa_gec_bayragi_CI_icin_gecirir(self) -> None:
        _korpus_kur(self.raw, 5)
        self.assertEqual(self._kos("--db-yoksa-gec"), 0)

    def test_sayim_ozyinelemeli_ve_yalniz_txt(self) -> None:
        _korpus_kur(self.raw, 4)
        (self.raw / "banka0" / "products" / "sayfa.html").write_text(
            "<html>", encoding="utf-8")
        self.assertEqual(C.korpus_belge_sayisi(str(self.raw)), 4,
                         ".html sayıma girdi — pipeline yalnız .txt okuyor")


if __name__ == "__main__":
    unittest.main()
