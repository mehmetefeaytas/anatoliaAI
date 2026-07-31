"""PostgreSQL + pgvector testleri — ÖN KOŞUL YOKSA ATLANIR, BAŞARISIZ OLMAZ.

İlgili: src/db/postgres.py, src/db/factory.py, src/rag/store.py
        docs/veri-katmani.md

## Neden `skipUnless`

Çekirdek testler ve eval katmanı bilinçli olarak SIFIR üçüncü parti
bağımlılıkla koşuyor (on-prem iddiasının parçası; CI'daki `test` işi hiçbir
şey kurmuyor). Bu dosya `psycopg` VE erişilebilir bir Postgres ister; ikisi
de yoksa testler ATLANIR. Atlamak ile "geçti" demek farklı şeylerdir:
atlanan test raporda atlanmış görünür.

## Nasıl koşturulur

    docker run -d --name anatolia-pgtest \\
      -e POSTGRES_USER=anatolia -e POSTGRES_PASSWORD=anatolia \\
      -e POSTGRES_DB=anatolia -p 55432:5432 pgvector/pgvector:pg16

    pip install 'psycopg[binary]>=3.1'
    ANATOLIA_TEST_DATABASE_URL=postgresql://anatolia:anatolia@localhost:55432/anatolia \\
      python3 -m unittest tests.test_pgvector_repository -v

`DATABASE_URL` değil AYRI bir değişken (`ANATOLIA_TEST_DATABASE_URL`) kullanılır:
test her koşuda şemayı TEMİZLER; üretim `DATABASE_URL`'i yanlışlıkla işaret
ediyorsa gerçek veriyi silerdi.

## Ne test ediliyor

Asıl soru "Postgres çalışıyor mu" değil, **iki backend aynı soruya aynı cevabı
veriyor mu**. Parite testleri aynı korpusu hem SQLite hem Postgres'e yazıp
sekiz sözleşme metodunun çıktısını karşılaştırır.
"""

import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.db.factory import create_repository
from src.db.postgres import psycopg_available
from src.db.repository import Repository
from src.extraction.reconcile import build_campaign
from src.rag.build_embeddings import build_embeddings
from src.rag.store import PgVectorStore, open_vector_store

TEST_DSN_ENV = "ANATOLIA_TEST_DATABASE_URL"

CORPUS = [
    ("kuveyt-turk", "Konut finansmanında kâr payı oranı %1,89, 120 ay vade. "
                    "Tahsis ücreti alınmaz.", "Konut Finansmanı",
     "2026-07-31T09:00:00+00:00"),
    ("albaraka", "Taşıt finansmanı kampanyası: 48 ay vade, %2,49 kâr payı, "
                 "masrafsız.", "Taşıt Finansmanı", "2026-07-31T09:00:01+00:00"),
    ("vakif-katilim", "Yeni müşterilere özel alışveriş puanı kampanyası.",
     "Alışveriş Puanı", None),
]


def _dsn() -> str:
    return os.environ.get(TEST_DSN_ENV, "").strip()


def _postgres_reachable() -> tuple[bool, str]:
    """Postgres gerçekten erişilebilir mi (sebebi ile birlikte)."""
    if not psycopg_available():
        return False, "psycopg kurulu değil"
    dsn = _dsn()
    if not dsn:
        return False, f"{TEST_DSN_ENV} tanımlı değil"
    import psycopg
    try:
        with psycopg.connect(dsn, connect_timeout=5) as conn:
            conn.execute("SELECT 1")
            conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
            conn.commit()
    except Exception as e:
        return False, f"bağlantı/eklenti hatası: {type(e).__name__}: {e}"
    return True, ""


_REACHABLE, _REASON = _postgres_reachable()
requires_pg = unittest.skipUnless(
    _REACHABLE, f"Postgres/pgvector yok — {_REASON}")


def _reset(conn) -> None:
    """Test şemasını sıfırlar (her test kendi verisiyle başlasın)."""
    with conn.cursor() as cur:
        cur.execute("DROP TABLE IF EXISTS embeddings, extracted_fields, "
                    "campaigns, banks CASCADE")
    conn.commit()


def seed(repo) -> list[int]:
    ids = []
    for slug, text, ctype, ts in CORPUS:
        ids.append(repo.insert_campaign(
            build_campaign(text, bank_slug=slug, campaign_type=ctype),
            clean_text=text, scraped_at=ts))
    return ids


@requires_pg
class TestPostgresRepositoryParity(unittest.TestCase):
    """SQLite ile Postgres AYNI cevabı vermeli."""

    def setUp(self):
        from src.db.postgres import PostgresRepository
        self.pg = PostgresRepository(_dsn())
        _reset(self.pg.conn)
        self.pg.ensure_schema()
        self.pg_ids = seed(self.pg)
        self.lite = Repository(":memory:")
        self.lite_ids = seed(self.lite)

    def tearDown(self):
        _reset(self.pg.conn)
        self.pg.close()
        self.lite.close()

    def test_backend_etiketi(self):
        self.assertEqual(self.pg.backend, "postgres")
        self.assertEqual(self.lite.backend, "sqlite")

    def test_counts_esit(self):
        self.assertEqual(self.pg.counts(), self.lite.counts())
        self.assertEqual(self.pg.counts()["campaigns"], len(CORPUS))

    def test_field_coverage_esit(self):
        self.assertEqual(self.pg.field_coverage(), self.lite.field_coverage())
        self.assertTrue(self.pg.field_coverage())   # boş olmamalı

    def test_campaigns_per_bank_esit(self):
        self.assertEqual(self.pg.campaigns_per_bank(),
                         self.lite.campaigns_per_bank())

    def test_all_campaigns_esit(self):
        """`scraped_at` dâhil — ISO-8601 UTC dizesi iki tarafta da aynı olmalı."""
        pg_rows = [{k: v for k, v in r.items() if k != "id"}
                   for r in self.pg.all_campaigns()]
        lite_rows = [{k: v for k, v in r.items() if k != "id"}
                     for r in self.lite.all_campaigns()]
        self.assertEqual(pg_rows, lite_rows)
        self.assertEqual(pg_rows[0]["scraped_at"], CORPUS[0][3])
        self.assertIsNone(pg_rows[2]["scraped_at"])

    def test_query_fields_esit(self):
        for alan in ("kar_payi_orani", "vade_ay", "masraf_durumu"):
            pg_rows = [{k: v for k, v in r.items() if k != "campaign_id"}
                       for r in self.pg.query_fields(alan)]
            lite_rows = [{k: v for k, v in r.items() if k != "campaign_id"}
                         for r in self.lite.query_fields(alan)]
            self.assertEqual(pg_rows, lite_rows, alan)

    def test_field_value_esit(self):
        for pg_id, lite_id in zip(self.pg_ids, self.lite_ids, strict=True):
            self.assertEqual(self.pg.field_value(pg_id, "kar_payi_orani"),
                             self.lite.field_value(lite_id, "kar_payi_orani"))

    def test_campaign_text_ve_span_dogrulamasi_esit(self):
        """31 Tem'de eklenen span_start/span_end/span_verified Postgres'te de çalışmalı."""
        for pg_id, lite_id in zip(self.pg_ids, self.lite_ids, strict=True):
            pg_row = self.pg.campaign_text(pg_id)
            lite_row = self.lite.campaign_text(lite_id)
            self.assertEqual({k: v for k, v in pg_row.items() if k != "id"},
                             {k: v for k, v in lite_row.items() if k != "id"})
            self.assertEqual(pg_row["span_reference"], "clean_text")

    def test_span_gercekten_dogrulaniyor(self):
        row = self.pg.campaign_text(self.pg_ids[0])
        dogrulanan = [f for f in row["fields"] if f["span_verified"]]
        self.assertTrue(dogrulanan, "hiçbir alan span doğrulaması geçmedi")
        for f in dogrulanan:
            self.assertEqual(row["text"][f["span_start"]:f["span_end"]],
                             f["raw_value"])

    def test_bozuk_offset_dogrulanmaz(self):
        """Saklanan offset metni göstermiyorsa span_verified False olmalı."""
        with self.pg.conn.cursor() as cur:
            cur.execute("UPDATE extracted_fields SET span_start=0, span_end=3 "
                        "WHERE campaign_id=%s", (self.pg_ids[0],))
        self.pg.conn.commit()
        row = self.pg.campaign_text(self.pg_ids[0])
        self.assertTrue(all(not f["span_verified"] for f in row["fields"]))

    def test_confidence_source_kalici(self):
        row = self.pg.campaign_text(self.pg_ids[0])
        self.assertTrue(any(f["confidence_source"] for f in row["fields"]))

    def test_olmayan_kampanya_none(self):
        self.assertIsNone(self.pg.campaign_text(10_000_000))

    def test_upsert_bank_idempotent(self):
        a = self.pg.upsert_bank("Kuveyt Türk", "kuveyt-turk")
        b = self.pg.upsert_bank("Kuveyt Türk", "kuveyt-turk")
        self.assertEqual(a, b)

    def test_nul_bayti_acik_hata_verir(self):
        """SQLite'ın yuttuğu NUL baytı Postgres'te ANLAŞILIR hata vermeli.

        31 Tem 2026: 849 belgelik demo korpusunda bir belge (kuveyt-turk)
        352 NUL baytı içeren ikili çöptü. psycopg'nin kriptik `DataError`'ı
        hangi belgenin bozuk olduğunu söylemiyordu.
        """
        from src.db.postgres import NulByteInText
        bozuk = build_campaign("metin\x00çöp", bank_slug="test-bank",
                               campaign_type="Kart")
        with self.assertRaises(NulByteInText) as ctx:
            self.pg.insert_campaign(bozuk)
        self.assertIn("NUL", str(ctx.exception))
        self.assertIn("test-bank", str(ctx.exception))
        # SQLite aynı veriyi SESSİZCE kabul eder — farkın kaynağı bu.
        self.assertIsInstance(self.lite.insert_campaign(bozuk), int)

    def test_nul_strip_modu_uyarir(self):
        """`on_nul='strip'` temizler ama SESSİZ kalmaz (offset kayması riski)."""
        from src.db.postgres import PostgresRepository
        repo = PostgresRepository(_dsn(), on_nul="strip")
        try:
            with self.assertLogs("src.db.postgres", level="WARNING"):
                cid = repo.insert_campaign(
                    build_campaign("metin\x00çöp", bank_slug="strip-bank",
                                   campaign_type="Kart"))
            self.assertNotIn("\x00", repo.campaign_text(cid)["text"])
        finally:
            repo.close()

    def test_gecersiz_on_nul_modu(self):
        from src.db.postgres import PostgresRepository
        with self.assertRaises(ValueError):
            PostgresRepository(_dsn(), on_nul="yoksay")

    def test_migrate_idempotent(self):
        """`ensure_schema()` iki kez koşabilmeli (elle kurulmuş DB senaryosu)."""
        self.pg.ensure_schema()
        self.pg.ensure_schema()
        self.assertEqual(self.pg.counts()["campaigns"], len(CORPUS))


@requires_pg
class TestFactory(unittest.TestCase):
    def test_database_url_varsa_postgres(self):
        repo = create_repository(_dsn())
        try:
            self.assertEqual(repo.backend, "postgres")
        finally:
            _reset(repo.conn)
            repo.close()

    def test_database_url_yoksa_sqlite(self):
        repo = create_repository("", ":memory:")
        try:
            self.assertEqual(repo.backend, "sqlite")
        finally:
            repo.close()


@requires_pg
class TestPgVectorStore(unittest.TestCase):
    """`embeddings` tablosu GERÇEKTEN yazılıyor ve pgvector ile sorgulanıyor."""

    def setUp(self):
        from src.db.postgres import PostgresRepository
        self.pg = PostgresRepository(_dsn())
        _reset(self.pg.conn)
        self.pg.ensure_schema()
        self.ids = seed(self.pg)
        self.store = open_vector_store(self.pg)
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from test_vector_retriever import HashingEmbedder
        self.emb = HashingEmbedder()

    def tearDown(self):
        _reset(self.pg.conn)
        self.pg.close()

    def test_backend_secimi(self):
        self.assertIsInstance(self.store, PgVectorStore)

    def test_yaz_ve_kosinus_ara(self):
        parcalar = ["konut finansmanı kâr payı", "tahsis ücreti alınmaz"]
        self.store.replace_campaign(self.ids[0], parcalar,
                                    self.emb.encode(parcalar), "test")
        self.assertEqual(self.store.count(), 2)
        hits = self.store.search(self.emb.encode(["kâr payı"])[0], k=2)
        self.assertEqual(hits[0].campaign_id, self.ids[0])
        # Kosinüs benzerliği [-1, 1]; birebir eşleşen parça en yüksek olmalı.
        self.assertGreater(hits[0].score, hits[1].score)
        self.assertLessEqual(hits[0].score, 1.0 + 1e-6)

    def test_yeniden_gomme_idempotent(self):
        parcalar = ["a", "b", "c"]
        for _ in range(2):
            self.store.replace_campaign(self.ids[0], parcalar,
                                        self.emb.encode(parcalar), "test")
        self.assertEqual(self.store.count(), 3)

    def test_yanlis_boyut_reddedilir(self):
        with self.assertRaises(ValueError):
            self.store.replace_campaign(self.ids[0], ["x"], [[0.1]], "test")

    def test_build_embeddings_uctan_uca(self):
        rapor = build_embeddings(self.pg, embedder=self.emb)
        self.assertTrue(rapor.ran)
        self.assertEqual(rapor.backend, "postgres")
        self.assertEqual(rapor.campaigns_embedded, len(CORPUS))
        self.assertEqual(self.store.count(), rapor.chunks_written)

    def test_vector_retriever_postgres_uzerinde(self):
        from src.chatbot import rag
        build_embeddings(self.pg, embedder=self.emb)
        r = rag.VectorRetriever(self.pg, embedder=self.emb, min_score=0.05)
        pasajlar = r.retrieve("konut finansmanında tahsis ücreti var mı", k=1)
        self.assertEqual(pasajlar[0]["bank"], "kuveyt-turk")
        self.assertEqual(r.retriever_name, "vector")

    def test_model_kaydediliyor(self):
        """Hangi modelin ürettiği saklanmalı (karışık korpus tespiti)."""
        build_embeddings(self.pg, embedder=self.emb)
        with self.pg.conn.cursor() as cur:
            cur.execute("SELECT DISTINCT model FROM embeddings")
            modeller = {r["model"] for r in cur.fetchall()}
        self.assertEqual(modeller, {self.emb.name})


class TestSkipGorunurlugu(unittest.TestCase):
    """Ön koşul yoksa bunun SEBEBİ raporlanabilir olmalı."""

    def test_sebep_bos_degil(self):
        ok, reason = _postgres_reachable()
        self.assertTrue(ok or reason,
                        "Postgres yoksa sebep dizesi boş olmamalı")


if __name__ == "__main__":
    unittest.main()
