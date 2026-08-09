"""Toplu özet üretimi ARADA yazar — koşu kesilirse iş kaybolmaz.

İlgili: ../scripts/build_summaries.py, ../src/summarize/ozet.py
        ../src/db/repository.py (`set_ozet` sözleşmesi)

## Bu testin varlık sebebi

`calistir()` eskiden bütün özetleri bellekte biriktirip **yalnız en sonda**
tek `set_ozet()` çağrısıyla yazıyordu. Tam korpus koşusu ~1400 belge ve belge
başına ~6 sn, yani ~2,5 saat: o sürenin TAMAMI tek bir kesintiye bağlıydı.
Ctrl-C, uyku, OOM ya da Ollama'nın düşmesi hâlinde DB'de hiçbir iz kalmıyor
ve `--devam` sıfırdan başlıyordu — çünkü `--devam`'ın "zaten özeti var mı"
sorusunun cevabını yazan tek yer o son çağrıydı.

Buradaki iki test bunun karşıtını kilitler:

  TestParcaliYazma      — koşu bitmeden önce DB'de satır OLMALI.
  TestKesintiDayaniklilik — ortada patlayan koşu, patlamadan önceki parçaları
                            KORUMALI ve `--devam` onları atlamalı.

İkincisi asıl iddiadır: "dayanıklı" demek, kesintiyi gerçekten simüle edip
verinin durduğunu görmektir.
"""

from __future__ import annotations

import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import build_summaries as BS


class _Istemci:
    """Her belge için o belgeye özgü kısa bir özet döndürür.

    Kesinti `KeyboardInterrupt` ile benzetilir, `RuntimeError` ile DEĞİL:
    `ozet.ozetle()` LLM hatalarını bilerek yutup `sebep` alanına yazıyor
    (bkz. tests/test_ozet.py::test_llm_hatasi_yutulmaz_sebebe_yazilir), yani
    tek bir model hatası koşuyu durdurmaz — durdurmamalı da. Koşuyu gerçekten
    yarıda kesen şey sinyaldir: Ctrl-C, `kill`, uyku sonrası ölüm.
    `KeyboardInterrupt` bir `BaseException`'dır ve o yakalayıcıya takılmaz.
    """

    def __init__(self, kes_at: int | None = None):
        self.kes_at = kes_at
        self.cagri = 0

    def generate_json(self, system: str, user: str, schema: dict) -> dict:
        self.cagri += 1
        if self.kes_at is not None and self.cagri > self.kes_at:
            raise KeyboardInterrupt("koşu kesildi (benzetim)")
        return {"ozet": f"Özet {self.cagri}."}


class _LLM:
    def __init__(self, kes_at: int | None = None):
        self.available = True
        self.client = _Istemci(kes_at)


def _db_kur(yol: Path, belge: int) -> None:
    """Yalnız bu testin ihtiyacı kadar şema.

    `all_campaigns()` `banks` ile JOIN yapıyor ve `belge_turu` sütununu
    seçiyor; ikisi de olmazsa sorgu satır döndürmez ve test sessizce
    "0 belge işlendi" ile geçmiş gibi görünürdü.
    """
    conn = sqlite3.connect(yol)
    conn.executescript("""
        CREATE TABLE banks (
            id INTEGER PRIMARY KEY,
            slug TEXT,
            name TEXT
        );
        CREATE TABLE campaigns (
            id INTEGER PRIMARY KEY,
            bank_id INTEGER,
            raw_text TEXT,
            clean_text TEXT,
            source_url TEXT,
            scraped_at TEXT,
            campaign_type TEXT,
            belge_turu TEXT,
            ozet TEXT
        );
        INSERT INTO banks (id, slug, name) VALUES (1, 'test-katilim', 'Test Katılım');
    """)
    conn.executemany(
        "INSERT INTO campaigns (id, bank_id, raw_text, belge_turu) "
        "VALUES (?, 1, ?, 'kampanya')",
        [(i, f"Konut finansmanı kampanyası {i}. Kâr payı oranı %2,05.")
         for i in range(1, belge + 1)])
    conn.commit()
    conn.close()


def _ozetli(yol: Path) -> int:
    conn = sqlite3.connect(yol)
    try:
        return conn.execute(
            "SELECT COUNT(*) FROM campaigns "
            "WHERE ozet IS NOT NULL AND TRIM(ozet) <> ''").fetchone()[0]
    finally:
        conn.close()


class _Temel(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.db = Path(self._tmp.name) / "t.db"
        _db_kur(self.db, belge=20)

    def tearDown(self) -> None:
        self._tmp.cleanup()


class TestParcaliYazma(_Temel):
    """Koşu BİTMEDEN önce DB'de satır olmalı."""

    def test_parca_dolunca_yazilir(self) -> None:
        gorulen: list[int] = []

        def ilerleme(islenen: int, hedef: int, yazilan: int) -> None:
            # Geri çağrı, `bosalt()`tan SONRA çalışır: o an DB'de gerçekten
            # satır olmalı. Rapordaki sayıya değil, diskteki duruma bakıyoruz.
            gorulen.append(_ozetli(self.db))

        rapor = BS.calistir(str(self.db), kapsam="hepsi", llm=_LLM(),
                            parca=5, ilerleme=ilerleme)

        self.assertEqual(rapor["yazilan"], 20)
        self.assertEqual(gorulen, [5, 10, 15, 20],
                         "her parçadan sonra DB'de o kadar satır olmalıydı")

    def test_parca_sifir_yalniz_sonda_yazar(self) -> None:
        """Eski davranış `--parca 0` ile hâlâ erişilebilir (geri uyum)."""
        gorulen: list[int] = []
        BS.calistir(str(self.db), kapsam="hepsi", llm=_LLM(), parca=0,
                    ilerleme=lambda *a: gorulen.append(_ozetli(self.db)))
        self.assertEqual(gorulen, [], "parca=0 iken ara yazma OLMAMALI")
        self.assertEqual(_ozetli(self.db), 20)

    def test_kuru_kosu_YAZMAZ(self) -> None:
        rapor = BS.calistir(str(self.db), kapsam="hepsi", llm=_LLM(),
                            parca=5, kuru=True)
        self.assertEqual(_ozetli(self.db), 0)
        self.assertEqual(rapor["yazilan"], 0)
        self.assertEqual(rapor["ozetlenen"], 20,
                         "kuru koşu üretimi yine de RAPORLAMALI")


class TestKesintiDayaniklilik(_Temel):
    """Asıl iddia: ortada patlayan koşu, önceki parçaları korur."""

    def test_kesinti_oncesi_parcalar_KALIR(self) -> None:
        # 12. belgeden sonra patlar: 5'lik iki parça (10 satır) yazılmış olmalı.
        with self.assertRaises(KeyboardInterrupt):
            BS.calistir(str(self.db), kapsam="hepsi", llm=_LLM(kes_at=12),
                        parca=5)
        self.assertEqual(
            _ozetli(self.db), 10,
            "kesintiden önce yazılan parçalar korunmalıydı — eski davranışta "
            "0 olurdu ve 12 belgelik iş çöpe giderdi")

    def test_devam_yazilanlari_ATLAR(self) -> None:
        """Kesinti + `--devam` = gerçekten kaldığı yerden."""
        with self.assertRaises(KeyboardInterrupt):
            BS.calistir(str(self.db), kapsam="hepsi", llm=_LLM(kes_at=12),
                        parca=5)

        rapor = BS.calistir(str(self.db), kapsam="hepsi", devam=True,
                            llm=_LLM(), parca=5)
        self.assertEqual(rapor["hedef_belge"], 10,
                         "`--devam` yalnız özeti olmayan 10 belgeyi almalı")
        self.assertEqual(_ozetli(self.db), 20)

    def test_tek_seferde_yazan_eski_davranisda_HERSEY_KAYBOLUR(self) -> None:
        """Karşıt kanıt: `parca=0` iken kesinti her şeyi götürür.

        Bu test düzeltmenin gerçekten bir şeyi değiştirdiğini gösterir; onsuz
        yukarıdaki testler "zaten çalışıyordu" ile ayırt edilemez.
        """
        with self.assertRaises(KeyboardInterrupt):
            BS.calistir(str(self.db), kapsam="hepsi", llm=_LLM(kes_at=12),
                        parca=0)
        self.assertEqual(_ozetli(self.db), 0)


if __name__ == "__main__":
    unittest.main()
