"""İki backend'in göç listesi AYRIŞAMAZ.

İlgili: ../src/db/repository.py (`_SONRADAN_EKLENEN`)
        ../src/db/postgres.py (`_LATER_COLUMNS`)
        ../src/db/base.py (`RepositoryProtocol` — ortak sözleşme)

## Bu testin varlık sebebi

`postgres._LATER_COLUMNS`'un kendi yorumu kuralı zaten yazıyordu:

    "iki liste ayrışırsa bir backend sütunu olan, diğeri olmayan bir şemayla
     koşar"

Kural yazılıydı ama **denetlenmiyordu** ve ayrışmıştı: `embeddings.chunk_index`
ile `embeddings.model` yalnız Postgres tarafında vardı (ölçüldü 2026-08-09).

Kusur GİZLİYDİ, o yüzden kimse fark etmedi: `data/demo.db` o sütunları
taşıyor ama `CREATE TABLE` yolundan (`schema.sql`), göçten değil. Ayrışma
ancak o sütunlar eklenmeden ÖNCE yaratılmış bir `.db` dosyası açıldığında
görünürdü — `SqliteVectorStore.replace_campaign()` INSERT'i
`no such column: chunk_index` ile düşerdi.

Bu, bu depoda İKİNCİ kez görülen bir hata sınıfı: aynı bilgi iki yerde
yaşayınca biri güncelleniyor, öteki unutuluyor. Öncekiler `ihtar.py`
(1774 belgenin 248'inde sızıntı) ve `_ORAN_TABLOSU_BASLIK_RE` (70 kaydın
26'sı kanıtsız). Kural yazmak yetmiyor; kuralın ihlalini yakalayan bir test
gerekiyor.

## Neden tip dizgesi karşılaştırılmıyor

`INTEGER NOT NULL DEFAULT 0` iki motorda da geçerli ama bazı tipler ayrışmak
ZORUNDA (ör. Postgres `JSONB`, SQLite `TEXT`). Bu yüzden test **hangi
sütunların taşındığını** kilitler, tiplerini değil. Tip ayrışması bilinçli bir
karardır; sütun ayrışması her zaman kusurdur.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.db.postgres import _LATER_COLUMNS
from src.db.repository import _SONRADAN_EKLENEN


def _sutunlar(liste) -> set[tuple[str, str]]:
    """(tablo, sütun) kümesi — tip alanı bilerek dışarıda."""
    return {(tablo, sutun) for tablo, sutun, _tip in liste}


class TestGocParitesi(unittest.TestCase):
    def test_ayni_sutun_kumesi(self) -> None:
        sqlite_k = _sutunlar(_SONRADAN_EKLENEN)
        pg_k = _sutunlar(_LATER_COLUMNS)

        yalniz_pg = sorted(pg_k - sqlite_k)
        yalniz_sqlite = sorted(sqlite_k - pg_k)

        self.assertEqual(
            (yalniz_pg, yalniz_sqlite), ([], []),
            "göç listeleri ayrıştı — bir backend sütunu olan, diğeri olmayan "
            f"bir şemayla koşar. Yalnız Postgres'te: {yalniz_pg}; "
            f"yalnız SQLite'ta: {yalniz_sqlite}")

    def test_embeddings_sutunlari_IKISINDE_DE(self) -> None:
        """Ayrışmanın gerçekleştiği somut yer — geri gelmesin."""
        for liste, ad in ((_SONRADAN_EKLENEN, "SQLite"),
                          (_LATER_COLUMNS, "Postgres")):
            k = _sutunlar(liste)
            with self.subTest(backend=ad):
                self.assertIn(("embeddings", "chunk_index"), k)
                self.assertIn(("embeddings", "model"), k)

    def test_liste_bos_degil(self) -> None:
        """Boş liste testi anlamsız kılar; ikisi de dolu olmalı."""
        self.assertGreater(len(_SONRADAN_EKLENEN), 0)
        self.assertGreater(len(_LATER_COLUMNS), 0)

    def test_sutun_adlari_tekil(self) -> None:
        """Aynı (tablo, sütun) iki kez göç ederse ikinci ALTER hata verir."""
        for liste, ad in ((_SONRADAN_EKLENEN, "SQLite"),
                          (_LATER_COLUMNS, "Postgres")):
            with self.subTest(backend=ad):
                ciftler = [(t, s) for t, s, _ in liste]
                self.assertEqual(len(ciftler), len(set(ciftler)),
                                 f"{ad} listesinde yinelenen sütun var")


class TestGocGercektenCalisiyor(unittest.TestCase):
    """Liste doğru olsa bile SQLite ifadeyi kabul etmeli."""

    def test_sqlite_her_sutunu_ekleyebiliyor(self) -> None:
        import sqlite3
        for tablo, sutun, tip in _SONRADAN_EKLENEN:
            with self.subTest(sutun=f"{tablo}.{sutun}"):
                conn = sqlite3.connect(":memory:")
                conn.execute(f"CREATE TABLE {tablo} (id INTEGER PRIMARY KEY)")
                try:
                    conn.execute(
                        f"ALTER TABLE {tablo} ADD COLUMN {sutun} {tip}")
                except sqlite3.OperationalError as e:  # pragma: no cover
                    self.fail(f"SQLite {tablo}.{sutun} ({tip}) eklenemiyor: {e}")
                finally:
                    conn.close()


if __name__ == "__main__":
    unittest.main()
