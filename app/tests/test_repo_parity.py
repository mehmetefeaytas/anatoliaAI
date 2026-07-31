"""Depo paritesi — iki backend AYNI soruya AYNI cevabı vermeli.

İlgili: src/db/base.py (RepositoryProtocol + ThreadSafeRepository)
        src/db/repository.py (SQLite), src/db/postgres.py (Postgres)
        src/db/factory.py (DATABASE_URL ile seçim)
        tests/test_pgvector_repository.py (pgvector/vektör tarafı)
        docs/veri-katmani.md

## Neden bu dosya var (test_pgvector_repository.py'nin üstüne)

`src/api/main.py` 31 Tem 2026'ya kadar depo sözleşmesini DELİYORDU: beş yerde
`repo.rows(<ham SQL>)` çağırıyordu ve o SQL'ler `?` yer tutucusu taşıyordu
(SQLite lehçesi). `psycopg` `%s` bekler — yani API'nin Postgres'te çalışması
mümkün değildi, `DATABASE_URL` verilse bile. Bu dosya o boşluğun geri
gelmesini engelleyen üç şeyi kilitler:

1. **Sözleşme bütünlüğü** (Postgres GEREKMEZ): `RepositoryProtocol`'deki her
   metot ÜÇ uygulamada da var mı, ve `src/api/main.py` içinde ham SQL kaldı mı.
   Bu sınıf her ortamda koşar; regresyonu bağımlılık kurmadan yakalar.
2. **Thread güvenliği** (Postgres GEREKMEZ): `check_same_thread=False` +
   `RLock` düzeltmesinin hâlâ yük taşıdığı, hem düzeltmenin çalıştığını hem
   düzeltilmemiş hâlin çöktüğünü göstererek kanıtlanır.
3. **Gerçek parite** (Postgres GEREKİR, yoksa ATLANIR): aynı korpus iki
   backend'e yazılır, `counts` / `all_banks` / `all_campaigns` /
   `query_fields` / `campaign_text` çıktıları karşılaştırılır.

Ön koşul yoksa 3. grup ATLANIR, başarısız OLMAZ — atlamak ile "geçti" demek
farklı şeylerdir.

## Nasıl koşturulur

    docker run -d --name anatolia-pgtest \\
      -e POSTGRES_USER=anatolia -e POSTGRES_PASSWORD=anatolia \\
      -e POSTGRES_DB=anatolia -p 55432:5432 pgvector/pgvector:pg16

    ANATOLIA_TEST_DATABASE_URL=postgresql://anatolia:anatolia@localhost:55432/anatolia \\
      python3 -m unittest tests.test_repo_parity -v
"""

from __future__ import annotations

import ast
import os
import re
import sqlite3
import sys
import tempfile
import threading
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.db.base import RepositoryProtocol, ThreadSafeRepository
from src.db.factory import create_repository
from src.db.postgres import PostgresRepository, psycopg_available
from src.db.repository import Repository
from src.extraction.reconcile import build_campaign

TEST_DSN_ENV = "ANATOLIA_TEST_DATABASE_URL"
API_MAIN = Path(__file__).resolve().parents[1] / "src" / "api" / "main.py"

# Sabit `scraped_at` damgaları: duvar saati kullanılsa iki backend'in çıktısı
# koşu anına göre değişir ve parite testi kendi kendini yanıltırdı.
CORPUS = [
    ("kuveyt-turk", "Konut finansmanında kâr payı oranı %1,89, 120 ay vade. "
                    "Tahsis ücreti alınmaz.", "Konut Finansmanı",
     "2026-07-31T09:00:00+00:00"),
    ("albaraka", "Taşıt finansmanı kampanyası: 48 ay vade, %2,49 kâr payı, "
                 "masrafsız.", "Taşıt Finansmanı", "2026-07-31T09:00:01+00:00"),
    ("vakif-katilim", "Yeni müşterilere özel alışveriş puanı kampanyası.",
     "Alışveriş Puanı", None),
]

# Sözleşmedeki metotlar. `RepositoryProtocol` üzerinden okunur, elle
# kopyalanmaz: protokole metot eklenip bir backend'de unutulursa test düşer.
CONTRACT_METHODS = tuple(sorted(
    ad for ad in RepositoryProtocol.__dict__
    if not ad.startswith("_") and callable(RepositoryProtocol.__dict__[ad])))


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
    except Exception as e:
        return False, f"bağlantı hatası: {type(e).__name__}: {e}"
    return True, ""


_REACHABLE, _REASON = _postgres_reachable()
requires_pg = unittest.skipUnless(_REACHABLE, f"Postgres yok — {_REASON}")


def reset_pg(conn) -> None:
    """Test şemasını sıfırlar (her test kendi verisiyle başlasın)."""
    with conn.cursor() as cur:
        cur.execute("DROP TABLE IF EXISTS embeddings, extracted_fields, "
                    "campaigns, banks CASCADE")
    conn.commit()


def seed(repo) -> list[int]:
    """Aynı korpusu, aynı sırayla, aynı damgalarla yazar."""
    repo.upsert_bank("Kuveyt Türk", "kuveyt-turk", "https://kuveytturk.test", True)
    repo.upsert_bank("Albaraka Türk", "albaraka", "https://albaraka.test", True)
    repo.upsert_bank("Vakıf Katılım", "vakif-katilim", None, False)
    ids = []
    for slug, text, ctype, ts in CORPUS:
        ids.append(repo.insert_campaign(
            build_campaign(text, bank_slug=slug, campaign_type=ctype,
                           source_url=f"https://ornek.test/{slug}"),
            clean_text=text, scraped_at=ts))
    return ids


# --------------------------------------------------------------------------- #
# 1. Sözleşme bütünlüğü — HER ORTAMDA koşar
# --------------------------------------------------------------------------- #
class TestSozlesmeButunlugu(unittest.TestCase):
    """Protokoldeki her metot üç uygulamada da olmalı."""

    def test_sozlesme_bos_degil(self) -> None:
        """Metot listesi protokolden okunuyor; boşsa test kendini kandırır."""
        self.assertIn("query_fields", CONTRACT_METHODS)
        self.assertIn("all_banks", CONTRACT_METHODS)
        self.assertGreaterEqual(len(CONTRACT_METHODS), 10)

    def test_sqlite_tum_metotlari_uygular(self) -> None:
        for ad in CONTRACT_METHODS:
            with self.subTest(metot=ad):
                self.assertTrue(callable(getattr(Repository, ad, None)),
                                f"Repository.{ad} yok")

    def test_postgres_tum_metotlari_uygular(self) -> None:
        """`psycopg` GEREKMEZ: modül tembel import kalıbı kullanıyor."""
        for ad in CONTRACT_METHODS:
            with self.subTest(metot=ad):
                self.assertTrue(callable(getattr(PostgresRepository, ad, None)),
                                f"PostgresRepository.{ad} yok")

    def test_thread_safe_sarmalayici_tum_metotlari_uygular(self) -> None:
        """Sarmalayıcı `__getattr__` sihriyle değil AÇIKÇA delege eder.

        Sihirle delege edilse yeni bir metot kilitsiz sızabilirdi; açık
        delegasyon eksiği burada görünür kılar.
        """
        for ad in CONTRACT_METHODS:
            with self.subTest(metot=ad):
                self.assertIn(ad, ThreadSafeRepository.__dict__,
                              f"ThreadSafeRepository.{ad} delege edilmiyor")

    def test_runtime_protocol_uyumu(self) -> None:
        repo = Repository(":memory:")
        try:
            self.assertIsInstance(repo, RepositoryProtocol)
            self.assertIsInstance(ThreadSafeRepository(repo), RepositoryProtocol)
        finally:
            repo.close()

    def test_api_icinde_ham_sql_yok(self) -> None:
        """`src/api/main.py` SQL YAZMAZ — asıl regresyon koruması bu.

        Beş `repo.rows(<ham SQL>)` çağrısı `?` yer tutucusu taşıyordu; Postgres
        `%s` bekler. Yani API'nin Postgres'te çalışmasını engelleyen şey buydu.
        Yeni bir sorgu gerekirse doğru yer protokoldür, bu dosya değil.
        """
        agac = ast.parse(API_MAIN.read_text(encoding="utf-8"))
        # Docstring'ler DIŞLANIR: modül başlığı bu hatayı ANLATIYOR ve içinde
        # 'SELECT' kelimesi geçiyor. Ölçtüğümüz şey çalışan koddaki dizeler.
        docstringler = {
            id(d.value) for d in ast.walk(agac)
            if isinstance(d, ast.Expr) and isinstance(d.value, ast.Constant)
            and isinstance(d.value.value, str)}
        sql_kalibi = re.compile(
            r"\b(select\s+\w|insert\s+into|update\s+\w+\s+set|delete\s+from)\b",
            re.IGNORECASE)
        suclular = [
            n.value for n in ast.walk(agac)
            if isinstance(n, ast.Constant) and isinstance(n.value, str)
            and id(n) not in docstringler and sql_kalibi.search(n.value)]
        self.assertEqual(suclular, [],
                         f"src/api/main.py içinde ham SQL var: {suclular[:1]}")

        cagrilar = {n.attr for n in ast.walk(agac) if isinstance(n, ast.Attribute)}
        self.assertNotIn("rows", cagrilar, "rows() kaçış kapısı geri geldi")

        importlar = {alias.name for n in ast.walk(agac)
                     if isinstance(n, ast.Import) for alias in n.names}
        importlar |= {n.module for n in ast.walk(agac)
                      if isinstance(n, ast.ImportFrom) and n.module}
        self.assertNotIn("sqlite3", importlar,
                         "API doğrudan sqlite3'e bağlı — backend'den bağımsız değil")

    def test_api_fabrikayi_kullaniyor(self) -> None:
        kaynak = API_MAIN.read_text(encoding="utf-8")
        self.assertIn("create_repository(", kaynak)
        self.assertIn("thread_safe=True", kaynak,
                      "API deposu thread güvenli kurulmuyor")


# --------------------------------------------------------------------------- #
# 2. Thread güvenliği — HER ORTAMDA koşar (stdlib yeterli)
# --------------------------------------------------------------------------- #
class TestThreadGuvenligi(unittest.TestCase):
    """`check_same_thread=False` + `RLock` düzeltmesi hâlâ yük taşıyor mu."""

    THREADS = 8
    TURLAR = 25

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.path = str(Path(self._tmp.name) / "parity.db")

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_duzeltilmemis_baglanti_baska_threadde_coker(self) -> None:
        """Düzeltmenin GEREKLİ olduğunun kanıtı (yoksa test bir şey ölçmez)."""
        repo = Repository(self.path)          # check_same_thread=True (varsayılan)
        seed(repo)
        hata: list[BaseException] = []

        def isci() -> None:
            try:
                repo.counts()
            except BaseException as e:   # hatayı ölçüyoruz
                hata.append(e)

        t = threading.Thread(target=isci)
        t.start()
        t.join()
        repo.close()
        self.assertTrue(hata, "sqlite3 artık thread kilidi uygulamıyor mu?")
        self.assertIsInstance(hata[0], sqlite3.ProgrammingError)

    def test_thread_safe_depo_paralel_okumada_coksmez(self) -> None:
        repo = create_repository("", self.path, thread_safe=True)
        try:
            seed(repo)
            hatalar: list[BaseException] = []
            sonuclar: list[int] = []

            def isci() -> None:
                try:
                    for _ in range(self.TURLAR):
                        sonuclar.append(repo.counts()["campaigns"])
                        repo.query_fields("kar_payi_orani")
                        repo.all_banks()
                        repo.campaign_text(1)
                except BaseException as e:
                    hatalar.append(e)

            threadler = [threading.Thread(target=isci)
                         for _ in range(self.THREADS)]
            for t in threadler:
                t.start()
            for t in threadler:
                t.join()
            self.assertEqual(hatalar, [], f"paralel okuma çöktü: {hatalar[:1]}")
            self.assertEqual(set(sonuclar), {len(CORPUS)})
        finally:
            repo.close()

    def test_paralel_yazma_kayip_vermez(self) -> None:
        """Serileştirme yazma yolunda da geçerli: N thread, N kampanya."""
        repo = create_repository("", self.path, thread_safe=True)
        try:
            hatalar: list[BaseException] = []

            def isci(i: int) -> None:
                try:
                    repo.insert_campaign(
                        build_campaign(f"%{i},50 kâr payı, 12 ay vade.",
                                       bank_slug=f"banka-{i}"),
                        clean_text=f"%{i},50 kâr payı, 12 ay vade.")
                except BaseException as e:
                    hatalar.append(e)

            threadler = [threading.Thread(target=isci, args=(i,))
                         for i in range(self.THREADS)]
            for t in threadler:
                t.start()
            for t in threadler:
                t.join()
            self.assertEqual(hatalar, [], f"paralel yazma çöktü: {hatalar[:1]}")
            self.assertEqual(repo.counts()["campaigns"], self.THREADS)
        finally:
            repo.close()

    def test_fabrika_bayraksiz_sarmalamaz(self) -> None:
        """Betikler/testler (tek thread) kilit maliyeti ödememeli."""
        repo = create_repository("", ":memory:")
        try:
            self.assertIsInstance(repo, Repository)
            self.assertNotIsInstance(repo, ThreadSafeRepository)
        finally:
            repo.close()

    def test_sarmalayici_backend_ve_conn_acik(self) -> None:
        """`rag.store.open_vector_store()` bu iki alana bakar."""
        repo = create_repository("", ":memory:", thread_safe=True)
        try:
            self.assertEqual(repo.backend, "sqlite")
            self.assertIsNotNone(repo.conn)
            self.assertIsInstance(repo.lock, type(threading.RLock()))
        finally:
            repo.close()


# --------------------------------------------------------------------------- #
# 3. Gerçek parite — Postgres GEREKİR
# --------------------------------------------------------------------------- #
@requires_pg
class TestBackendParitesi(unittest.TestCase):
    """Aynı korpus, iki backend, aynı cevap."""

    def setUp(self) -> None:
        self.pg = PostgresRepository(_dsn())
        reset_pg(self.pg.conn)
        self.pg.ensure_schema()
        self.pg_ids = seed(self.pg)
        self._tmp = tempfile.TemporaryDirectory()
        self.lite = Repository(str(Path(self._tmp.name) / "parity.db"))
        self.lite_ids = seed(self.lite)

    def tearDown(self) -> None:
        reset_pg(self.pg.conn)
        self.pg.close()
        self.lite.close()
        self._tmp.cleanup()

    def test_counts(self) -> None:
        self.assertEqual(self.pg.counts(), self.lite.counts())
        self.assertEqual(self.pg.counts()["campaigns"], len(CORPUS))

    def test_all_banks(self) -> None:
        """`GET /banks` bu metoda dayanır — 31 Tem'de ham SQL'den çevrildi.

        `bddk_active` iki backend'de farklı TİPTE saklanır (SQLite INTEGER,
        Postgres BOOLEAN); metot ikisini de `bool`'a çevirmek zorunda, aksi
        halde aynı uç bir backend'de `1`, diğerinde `true` döndürürdü.
        """
        pg_rows, lite_rows = self.pg.all_banks(), self.lite.all_banks()
        self.assertEqual(pg_rows, lite_rows)
        self.assertEqual([r["slug"] for r in pg_rows],
                         ["albaraka", "kuveyt-turk", "vakif-katilim"])
        for r in pg_rows:
            self.assertIsInstance(r["bddk_active"], bool)
        self.assertFalse(
            next(r for r in pg_rows if r["slug"] == "vakif-katilim")["bddk_active"])
        self.assertEqual(set(pg_rows[0]),
                         {"slug", "name", "website_url", "bddk_active"})

    def test_all_campaigns_sirali_ve_esit(self) -> None:
        """Sıra da parite kapsamında: SQLite'ta `ORDER BY c.id` eksikti."""
        pg_rows = [{k: v for k, v in r.items() if k != "id"}
                   for r in self.pg.all_campaigns()]
        lite_rows = [{k: v for k, v in r.items() if k != "id"}
                     for r in self.lite.all_campaigns()]
        self.assertEqual(pg_rows, lite_rows)
        self.assertEqual([r["bank"] for r in pg_rows],
                         [c[0] for c in CORPUS])
        ids = [r["id"] for r in self.pg.all_campaigns()]
        self.assertEqual(ids, sorted(ids))

    def test_query_fields(self) -> None:
        for alan in ("kar_payi_orani", "vade_ay", "masraf_durumu"):
            pg_rows = [{k: v for k, v in r.items() if k != "campaign_id"}
                       for r in self.pg.query_fields(alan)]
            lite_rows = [{k: v for k, v in r.items() if k != "campaign_id"}
                         for r in self.lite.query_fields(alan)]
            self.assertEqual(pg_rows, lite_rows, alan)

    def test_query_fields_api_alanlarini_tasir(self) -> None:
        """`/compare` bu anahtarların hepsini kullanır (eski ham SQL'in yerine)."""
        rows = self.pg.query_fields("kar_payi_orani")
        self.assertTrue(rows)
        for anahtar in ("bank", "bank_name", "campaign_id", "campaign_type",
                        "source_url", "scraped_at", "canonical_value",
                        "raw_value", "confidence", "source_span", "extractor",
                        "span_start", "span_end", "confidence_source"):
            self.assertIn(anahtar, rows[0], f"query_fields '{anahtar}' vermiyor")

    def test_campaign_text(self) -> None:
        for pg_id, lite_id in zip(self.pg_ids, self.lite_ids, strict=True):
            pg_row = self.pg.campaign_text(pg_id)
            lite_row = self.lite.campaign_text(lite_id)
            self.assertEqual({k: v for k, v in pg_row.items() if k != "id"},
                             {k: v for k, v in lite_row.items() if k != "id"})

    def test_campaign_text_scraped_at_tasir(self) -> None:
        """`scraped_at` 31 Tem'de EKLENDİ: çelişki tespitinin `as_of` girdisi.

        Yoksa "süresi dolmuş ama sayfa yayında" kuralı `/campaigns/{id}/text`
        ucunda sessizce kapalı kalırdı (korpustaki 6 çelişkinin 5'i o kuraldan).
        """
        for pg_id, lite_id, beklenen in zip(
                self.pg_ids, self.lite_ids, [c[3] for c in CORPUS], strict=True):
            self.assertEqual(self.pg.campaign_text(pg_id)["scraped_at"], beklenen)
            self.assertEqual(self.lite.campaign_text(lite_id)["scraped_at"],
                             beklenen)

    def test_saklanan_offsetler_iki_backendde_de_dogrulaniyor(self) -> None:
        """API artık saklanan offset'i BİRİNCİL yol olarak kullanıyor."""
        for depo, cid in ((self.pg, self.pg_ids[0]), (self.lite, self.lite_ids[0])):
            row = depo.campaign_text(cid)
            dogrulanan = [f for f in row["fields"] if f["span_verified"]]
            self.assertTrue(dogrulanan, f"{depo.backend}: hiç doğrulanan span yok")
            for f in dogrulanan:
                self.assertEqual(row["text"][f["span_start"]:f["span_end"]],
                                 f["raw_value"])

    def test_okuma_islemi_acik_birakmaz(self) -> None:
        """Her salt-okunur metot bağlantıyı IDLE bırakmalı, `idle in transaction` DEĞİL.

        psycopg `autocommit=False` ile ilk sorguda örtük bir işlem başlatır.
        Okuma metotları commit/rollback etmediği için bağlantı işlem içinde
        kalıyordu; uzun ömürlü API sunucusunda bu, ACCESS SHARE kilitlerini
        süresiz tutmak demektir.
        """
        from psycopg.pq import TransactionStatus

        cagrilar = {
            "counts": lambda: self.pg.counts(),
            "all_banks": lambda: self.pg.all_banks(),
            "all_campaigns": lambda: self.pg.all_campaigns(),
            "query_fields": lambda: self.pg.query_fields("kar_payi_orani"),
            "campaign_text": lambda: self.pg.campaign_text(self.pg_ids[0]),
            "campaign_text_yok": lambda: self.pg.campaign_text(10_000_000),
            "field_value": lambda: self.pg.field_value(self.pg_ids[0],
                                                       "kar_payi_orani"),
            "field_coverage": lambda: self.pg.field_coverage(),
            "campaigns_per_bank": lambda: self.pg.campaigns_per_bank(),
            "upsert_bank_mevcut": lambda: self.pg.upsert_bank("Kuveyt Türk",
                                                              "kuveyt-turk"),
        }
        for ad, cagri in cagrilar.items():
            with self.subTest(metot=ad):
                cagri()
                self.assertEqual(
                    self.pg.conn.info.transaction_status, TransactionStatus.IDLE,
                    f"{ad}() sonrası bağlantı 'idle in transaction' kaldı")

    def test_okuma_ddl_kilidini_tutmaz(self) -> None:
        """Arızanın GERÇEK belirtisi: okuma sonrası DDL bloklanıyordu.

        31 Tem 2026'da ölçüldü: Postgres'e bağlı bir API kurulup `/banks`
        çağrıldıktan sonra `DROP TABLE` sonsuza kadar bekledi. Burada aynı şey
        `lock_timeout` ile sınırlı süre içinde denenir — bloklanırsa test düşer,
        sonsuza kadar asılı kalmaz.
        """
        import psycopg
        self.pg.query_fields("kar_payi_orani")
        self.pg.all_banks()
        self.pg.campaign_text(self.pg_ids[0])
        # `autocommit=False` (varsayılan): psycopg örtük bir işlem açar, çünkü
        # `LOCK TABLE` yalnızca işlem bloğunda geçerlidir. `lock_timeout` işleme
        # özgüdür ve testin sonsuza kadar asılı kalmasını engeller.
        with psycopg.connect(_dsn(), connect_timeout=5) as conn:
            conn.execute("SET lock_timeout = '3s'")
            try:
                conn.execute("LOCK TABLE banks IN ACCESS EXCLUSIVE MODE")
            except psycopg.errors.LockNotAvailable as e:
                self.fail("okuma sonrası kilit bırakılmadı (idle in "
                          f"transaction): {e}")
            conn.rollback()

    def test_thread_safe_sarmalayici_pariteyi_bozmaz(self) -> None:
        """Kilit sadece serileştirir; döndürülen veriyi DEĞİŞTİRMEZ."""
        sarili = ThreadSafeRepository(self.pg)
        self.assertEqual(sarili.backend, "postgres")
        self.assertEqual(sarili.counts(), self.pg.counts())
        self.assertEqual(sarili.all_banks(), self.lite.all_banks())
        self.assertEqual(sarili.query_fields("vade_ay"),
                         self.pg.query_fields("vade_ay"))

    def test_fabrika_thread_safe_postgres(self) -> None:
        repo = create_repository(_dsn(), thread_safe=True)
        try:
            self.assertIsInstance(repo, ThreadSafeRepository)
            self.assertEqual(repo.backend, "postgres")
            self.assertEqual(repo.counts()["campaigns"], len(CORPUS))
        finally:
            repo.close()

    def test_paralel_okuma_postgres(self) -> None:
        """psycopg bağlantısı da paylaşılıyor — kilit orada da yük taşır."""
        repo = create_repository(_dsn(), thread_safe=True)
        hatalar: list[BaseException] = []
        try:
            def isci() -> None:
                try:
                    for _ in range(10):
                        repo.counts()
                        repo.all_banks()
                        repo.query_fields("kar_payi_orani")
                        repo.campaign_text(self.pg_ids[0])
                except BaseException as e:
                    hatalar.append(e)

            threadler = [threading.Thread(target=isci) for _ in range(8)]
            for t in threadler:
                t.start()
            for t in threadler:
                t.join()
            self.assertEqual(hatalar, [],
                             f"Postgres paralel okuma çöktü: {hatalar[:1]}")
        finally:
            repo.close()


class TestSkipGorunurlugu(unittest.TestCase):
    """Ön koşul yoksa SEBEBİ raporlanabilir olmalı."""

    def test_sebep_bos_degil(self) -> None:
        ok, sebep = _postgres_reachable()
        self.assertTrue(ok or sebep, "Postgres yoksa sebep dizesi boş olmamalı")


if __name__ == "__main__":
    unittest.main()
