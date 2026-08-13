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


class TestIcerikBayatligi(unittest.TestCase):
    """İçerik kapısı: BİÇİM farkı bayatlık değil, DEĞER farkı bayatlıktır.

    ## Bu sınıfın varlık sebebi — ÖLÇÜLDÜ (2026-08-12)

    `icerik_bayatligi` hiç test edilmemişti ve kapı, TAM `--force` yeniden
    inşadan SONRA bile 1 belgeyi bayat gösteriyordu. Hiçbir yeniden inşa
    bunu düzeltemiyordu çünkü fark veride değildi; tek bir karakterdeydi:

        DB   : ... "Sağlık Kampanyası" kampanyası ...
        disk : ... "Sağlık Kampanyası” kampanyası ...   (U+201D)

    Yazma yolu `preprocessing.clean` üzerinden geçiyor ve o modül kıvrık
    tırnakları düzleştiriyor (`clean.py:127`); denetçi ise yalnız boşluğu
    eşitliyordu. Sonuç: KAPATILAMAYAN bir alarm — ve kapatılamayan alarm,
    kapalı alarmla aynı sonucu verir, kimse bakmaz.
    """

    def _fikstur(self, db_metin: str, disk_metin: str, *, ozet: str = "özet"):
        """Tek belgelik DB + korpus fikstürü kurar, sayıları döndürür."""
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        kok = Path(tmp.name)
        db = kok / "demo.db"
        conn = sqlite3.connect(db)
        conn.execute("CREATE TABLE campaigns (id INTEGER PRIMARY KEY, "
                     "source_url TEXT, raw_text TEXT, ozet TEXT)")
        conn.execute("INSERT INTO campaigns(source_url, raw_text, ozet) "
                     "VALUES (?,?,?)", ("https://x/1", db_metin, ozet))
        conn.commit()
        conn.close()

        ham = kok / "raw" / "banka" / "live"
        ham.mkdir(parents=True)
        (ham / "a.txt").write_text(disk_metin, encoding="utf-8")
        (ham / "a.txt.meta.json").write_text(
            '{"source_url": "https://x/1"}', encoding="utf-8")
        return C.icerik_bayatligi(str(db), str(kok / "raw"))

    def test_TIPOGRAFIK_TIRNAK_bayatlik_SAYILMAZ(self) -> None:
        """Ölçülen kalıcı yalancı bayatlığın tam vakası."""
        degisen, _, karsilastirilan = self._fikstur(
            'Albaraka "Sağlık Kampanyası" kampanyası için katıl.',
            'Albaraka "Sağlık Kampanyası” kampanyası için katıl.')
        self.assertEqual(1, karsilastirilan, "belge hiç karşılaştırılmadı")
        self.assertEqual(
            0, degisen,
            "tipografik tırnak farkı hâlâ 'içerik değişti' sayılıyor — "
            "kapı kapatılamayan alarm çalmaya devam eder")

    def test_KESME_ISARETI_de_bayatlik_SAYILMAZ(self) -> None:
        degisen, _, _ = self._fikstur(
            "Banka'nın kampanyası", "Banka’nın kampanyası")
        self.assertEqual(0, degisen, "kıvrık kesme işareti bayatlık sayıldı")

    def test_BOSLUK_farki_bayatlik_SAYILMAZ(self) -> None:
        """Önceden düzeltilmiş yanlış pozitif gerilemesin."""
        degisen, _, _ = self._fikstur(
            "Mobil Bankacılık Aç", "Mobil\nBankacılık\n  Aç\n")
        self.assertEqual(0, degisen, "boşluk düzeni bayatlık sayıldı")

    def test_GERCEK_deger_degisikligi_YAKALANIR(self) -> None:
        """Kapının dişleri: oran değişince bayatlık bildirilmeli."""
        degisen, ozeti_bayat, _ = self._fikstur(
            "Kâr payı oranı %1,89'dur.", "Kâr payı oranı %2,49'dur.")
        self.assertEqual(
            1, degisen,
            "oran değişmiş ama kapı görmedi — normalizasyon fazla "
            "gevşetilmiş, gerçek bayatlık gizleniyor")
        self.assertEqual(
            1, ozeti_bayat,
            "metni değişen belgenin özeti de bayat sayılmalı: sütun dolu "
            "olduğu için arayüzde normal görünür")

    def test_ozet_YOKSA_ozeti_bayat_SAYILMAZ(self) -> None:
        degisen, ozeti_bayat, _ = self._fikstur(
            "Kâr payı %1,89.", "Kâr payı %2,49.", ozet="")
        self.assertEqual(1, degisen)
        self.assertEqual(0, ozeti_bayat, "özeti olmayan belge 'özeti bayat' sayıldı")
