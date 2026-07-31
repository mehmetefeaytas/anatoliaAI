"""PostgreSQL + pgvector deposu — üretim yolu.

İlgili: CLAUDE.md §7 (teknoloji yığını), §9 (veri modeli)
        base.py (ortak sözleşme), repository.py (SQLite/offline yolu)
        factory.py (DATABASE_URL ile seçim), docs/veri-katmani.md

## Neden bu dosya 31 Tem 2026'da yazıldı

`docker-compose.yml` `pgvector/pgvector:pg16` servisini ayağa kaldırıyor ve
`schema.sql` `vector(1024)` sütunu tanımlıyordu; buna karşılık Python tarafında
`psycopg` import'u bile yoktu ve API servisi `DATABASE_PATH=":memory:"` ile
koşuyordu. Yani mimari diyagramda Postgres vardı, çalışan sistemde yoktu.
Bu modül o boşluğu kapatır.

## Sözleşme paritesi

`Repository` (SQLite) ile AYNI yüzeyi sunar (`base.RepositoryProtocol`) ve
`campaign_text()` doğrulama mantığını `base.finalize_campaign_text()` ile
PAYLAŞIR — kopyalamaz. Parite `tests/test_pgvector_repository.py` içinde
iki backend'e aynı veriyi yazıp çıktıları karşılaştırarak kilitlenir; o test
`psycopg` veya erişilebilir bir Postgres yoksa ATLANIR (başarısız olmaz).

## SQLite'ın yuttuğu, Postgres'in yakaladığı: NUL (0x00) baytı

PostgreSQL `TEXT` sütunları NUL baytı KABUL ETMEZ; SQLite eder. 31 Tem 2026'da
849 belgelik demo korpusu Postgres'e aktarılırken bu fark bir VERİ HATASI
ortaya çıkardı: bir belge (kuveyt-turk, 352 NUL baytı) metin değil ikili
(binary) çöptü ve korpusa `.txt` olarak girmişti. Hiçbir alan çıkmadığı için
SQLite yolunda görünmüyordu.

Varsayılan davranış `on_nul="error"`: psycopg'nin kriptik `DataError`'ı yerine
hangi bankanın hangi belgesinin bozuk olduğunu söyleyen açık bir hata.
`on_nul="strip"` NUL'ları temizler ve UYARI loglar — ama dikkat: temizlik
karakter offset'lerini KAYDIRIR, yani `span_start`/`span_end` doğrulaması
bozulabilir. Bu yüzden varsayılan değildir.

## Okumalar işlemi AÇIK BIRAKMAZ (`_read` bağlam yöneticisi)

Bağlantı `autocommit=False` ile açılır — `insert_campaign()` kampanyayı ve
alanlarını TEK işlemde yazabilmek için buna muhtaç. Bunun bedeli şudur: psycopg
ilk sorguda örtük bir işlem başlatır ve `commit()`/`rollback()` gelene kadar
kapatmaz. Salt-okunur metotlar (`query_fields`, `campaign_text`, `counts`, ...)
commit etmediği için bağlantı her okumadan sonra **`idle in transaction`**
kalıyordu.

Bu, uzun ömürlü bir API sunucusunda gerçek bir arızadır ve 31 Tem 2026'da
ÖLÇÜLDÜ: `tests/test_api_backend.py` Postgres'e bağlı bir uygulama kurup
`/banks` çağırdıktan sonra şema temizliği (`DROP TABLE`) **sonsuza kadar
bloklandı** — `pg_stat_activity` beklenen tabloyu gösterdi:

    pid 255 | idle in transaction | ClientRead | SELECT b.slug AS bank, ...
    pid 256 | active | Lock/relation | DROP TABLE IF EXISTS embeddings, ...

Açık kalan işlem ACCESS SHARE kilitlerini tutar; DDL ve `VACUUM` bloklanır,
tablolar şişer. Çözüm: her salt-okunur sorgu `_read()` ile koşar ve sonunda
`rollback()` yapar (okuma işleminde geri alınacak bir şey yoktur; amaç işlemi
KAPATMAK). `autocommit=True`'ya geçmek yanlış çözüm olurdu: `insert_campaign()`
kampanya + alan yazımının atomikliğini kaybederdi.

## Bilinen ve KASITLI davranış farkı: `scraped_at`

SQLite yolu provenance damgasını (`utc_now_iso()` → '2026-07-31T09:00:00+00:00')
metin olarak olduğu gibi saklar. Postgres yolu `TIMESTAMPTZ` sütununa yazar ve
okurken tekrar ISO-8601 UTC metnine çevirir. Sonuç: UTC anı korunur, ama
girdi başka bir saat diliminde verilmişse ('...+03:00') okunan değer UTC'ye
normalize edilmiş olarak döner. Bu bir kayıp değil normalizasyondur; yine de
sessiz kalmasın diye burada yazılıdır.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Optional

from ..schemas import Campaign
from .base import finalize_campaign_text

logger = logging.getLogger(__name__)

SCHEMA_PATH = Path(__file__).with_name("schema.sql")

# NUL baytı politikası (bkz. modül başlığı).
ON_NUL_MODES = ("error", "strip")

# `utc_now_iso()` çıktısını birebir yeniden üreten okuma biçimi.
# `isoformat(timespec="seconds")` UTC için '...+00:00' üretir; `to_char` saat
# dilimi ofsetini 'OF' ile '+00' olarak basar, bu yüzden dakika kısmı elle
# tamamlanır. Tek yerde tanımlı: her SELECT bunu kullanır.
_SCRAPED_AT_ISO = (
    "to_char(c.scraped_at AT TIME ZONE 'UTC', 'YYYY-MM-DD\"T\"HH24:MI:SS') "
    "|| '+00:00'"
)

# Şemaya sonradan eklenen sütunlar. Postgres `ADD COLUMN IF NOT EXISTS`
# desteklediği için SQLite'taki PRAGMA kontrolüne gerek yok; yine de listenin
# repository._SONRADAN_EKLENEN ile aynı alanları kapsaması gerekir.
_LATER_COLUMNS = (
    ("extracted_fields", "span_start", "INTEGER"),
    ("extracted_fields", "span_end", "INTEGER"),
    ("extracted_fields", "confidence_source", "TEXT"),
    ("embeddings", "chunk_index", "INTEGER NOT NULL DEFAULT 0"),
    ("embeddings", "model", "TEXT"),
)


class PsycopgUnavailable(RuntimeError):
    """`psycopg` kurulu değilken Postgres yolu istendi.

    Sessizce SQLite'a düşmek YANLIŞ olurdu: `DATABASE_URL` veren operatör
    verinin Postgres'e yazıldığını sanır, veri ise geçici bir dosyaya gider.
    """


def psycopg_available() -> bool:
    """`psycopg` import edilebiliyor mu (testlerin skip kararı için)."""
    try:
        import psycopg  # noqa: F401
    except ModuleNotFoundError:
        return False
    return True


def _load_psycopg():
    try:
        import psycopg
        from psycopg.rows import dict_row
    except ModuleNotFoundError as e:  # pragma: no cover - ortama bağlı
        raise PsycopgUnavailable(
            "DATABASE_URL verildi ama `psycopg` kurulu değil. "
            "Kurulum: pip install 'psycopg[binary]>=3.1'  "
            "(offline/test yolu için DATABASE_URL'i boş bırakın; sistem "
            "SQLite ile çalışır — bkz. docs/veri-katmani.md)") from e
    return psycopg, dict_row


class NulByteInText(ValueError):
    """Metinde PostgreSQL'in kabul etmediği NUL (0x00) baytı var."""


class PostgresRepository:
    """PostgreSQL depo. `base.RepositoryProtocol` sözleşmesini uygular."""

    backend: str = "postgres"

    def __init__(self, dsn: str, *, ensure_schema: bool = True,
                 schema_path: Optional[Path] = None,
                 on_nul: str = "error"):
        if on_nul not in ON_NUL_MODES:
            raise ValueError(
                f"on_nul={on_nul!r} geçersiz. Geçerli: {', '.join(ON_NUL_MODES)}")
        psycopg, dict_row = _load_psycopg()
        self.dsn = dsn
        self.on_nul = on_nul
        self.conn = psycopg.connect(dsn, row_factory=dict_row, autocommit=False)
        if ensure_schema:
            self.ensure_schema(schema_path or SCHEMA_PATH)

    @contextmanager
    def _read(self) -> Iterator[Any]:
        """Salt-okunur sorgu için cursor — çıkışta işlemi KAPATIR.

        `rollback()` bir okumada hiçbir şeyi geri almaz; tek işi psycopg'nin
        örtük olarak başlattığı işlemi bitirip kilitleri bırakmaktır. Bkz. modül
        başlığı "Okumalar işlemi AÇIK BIRAKMAZ" (ölçülmüş `DROP TABLE` kilidi).
        """
        try:
            with self.conn.cursor() as cur:
                yield cur
        finally:
            self.conn.rollback()

    def _text(self, value: Optional[str], alan: str,
              baglam: str) -> Optional[str]:
        """Metni NUL baytına karşı denetler (bkz. modül başlığı)."""
        if value is None or "\x00" not in value:
            return value
        adet = value.count("\x00")
        if self.on_nul == "strip":
            logger.warning(
                "%s alanında %d NUL baytı temizlendi (%s). DİKKAT: karakter "
                "offset'leri kaydı, span doğrulaması bozulabilir.",
                alan, adet, baglam)
            return value.replace("\x00", "")
        raise NulByteInText(
            f"{baglam}: '{alan}' alanı {adet} adet NUL (0x00) baytı içeriyor. "
            "PostgreSQL TEXT sütunları NUL kabul etmez (SQLite eder — bu "
            "yüzden hata ancak Postgres yolunda görünür). Genellikle metin "
            "yerine ikili (binary) bir belgenin korpusa .txt olarak girmesi "
            "demektir; kaynağı düzeltmek doğru çözümdür. Geçici olarak "
            "PostgresRepository(dsn, on_nul='strip') ile temizlenebilir, ama "
            "temizlik span offset'lerini kaydırır.")

    # --- şema ---
    def ensure_schema(self, schema_path: Path = SCHEMA_PATH) -> None:
        """`schema.sql`'i uygular ve sonradan eklenen sütunları tamamlar.

        `schema.sql` tamamen idempotenttir (CREATE ... IF NOT EXISTS), bu yüzden
        her açılışta koşturulabilir. Docker Compose bunu ayrıca
        `docker-entrypoint-initdb.d` ile ilk açılışta uygular; kod tarafındaki
        çağrı, elle kurulmuş bir Postgres'e bağlanıldığında şemanın eksik
        kalmamasını garanti eder.
        """
        sql = Path(schema_path).read_text(encoding="utf-8")
        with self.conn.cursor() as cur:
            cur.execute(sql)
        self._migrate()
        self.conn.commit()

    def _migrate(self) -> None:
        """Eski bir veritabanına sonradan eklenen sütunları tamamlar."""
        with self.conn.cursor() as cur:
            for tablo, sutun, tip in _LATER_COLUMNS:
                cur.execute(
                    f"ALTER TABLE {tablo} ADD COLUMN IF NOT EXISTS {sutun} {tip}")

    # --- bankalar ---
    def upsert_bank(self, name: str, slug: str, website_url: Optional[str] = None,
                    bddk_active: bool = True) -> int:
        with self.conn.cursor() as cur:
            cur.execute("SELECT id FROM banks WHERE slug=%s", (slug,))
            row = cur.fetchone()
            if row:
                # Banka zaten var: hiçbir şey yazılmadı ama SELECT bir işlem
                # başlattı. Kapatmadan dönmek bağlantıyı `idle in transaction`
                # bırakırdı (bkz. `_read` ve modül başlığı).
                self.conn.rollback()
                return int(row["id"])
            cur.execute(
                "INSERT INTO banks(name, slug, website_url, bddk_active) "
                "VALUES (%s,%s,%s,%s) RETURNING id",
                (name, slug, website_url, bool(bddk_active)))
            new_id = int(cur.fetchone()["id"])
        self.conn.commit()
        return new_id

    def all_banks(self) -> list[dict]:
        """Banka kataloğu: slug, ad, site, BDDK durumu (`GET /banks`).

        `bddk_active` açıkça `bool()`'a çevrilir — SQLite yolu aynı alanı
        INTEGER (0/1) saklar ve orada da bool'a çevrilir; parite bu iki
        dönüşümle sağlanır (`1` vs `true` farkı JSON'a sızmaz).
        """
        with self._read() as cur:
            cur.execute("SELECT slug, name, website_url, bddk_active FROM banks "
                        "ORDER BY slug")
            rows = cur.fetchall()
        return [{"slug": r["slug"], "name": r["name"],
                 "website_url": r["website_url"],
                 "bddk_active": bool(r["bddk_active"])} for r in rows]

    # --- kampanya + alanlar ---
    def insert_campaign(self, c: Campaign, clean_text: Optional[str] = None,
                        scraped_at: Optional[str] = None) -> int:
        bank_id = self.upsert_bank(c.bank_slug, c.bank_slug)
        baglam = f"kampanya (banka={c.bank_slug}, url={c.source_url})"
        raw_text = self._text(c.raw_text, "raw_text", baglam)
        clean_text = self._text(clean_text, "clean_text", baglam)
        with self.conn.cursor() as cur:
            cur.execute(
                "INSERT INTO campaigns(bank_id, raw_text, clean_text, source_url, "
                "scraped_at, campaign_type) "
                "VALUES (%s,%s,%s,%s,CAST(%s AS TIMESTAMPTZ),%s) RETURNING id",
                (bank_id, raw_text, clean_text, c.source_url, scraped_at,
                 c.campaign_type))
            cid = int(cur.fetchone()["id"])
            # span_start/end ve confidence_source burada YAZILMAZSA, projenin
            # en özgün iddiası (her değer bir karakter aralığına bağlı) veri
            # tabanı sınırında kaybolur. SQLite yolundaki aynı gerekçe.
            rows = [
                (cid, f.field_name,
                 self._text(f.raw_value, f"{f.field_name}.raw_value", baglam),
                 json.dumps(f.canonical_value, ensure_ascii=False),
                 f.confidence,
                 self._text(f.source_span, f"{f.field_name}.source_span", baglam),
                 f.extractor.value, f.span_start, f.span_end,
                 getattr(f, "confidence_source", None))
                for f in c.fields
            ]
            if rows:
                cur.executemany(
                    "INSERT INTO extracted_fields(campaign_id, field_name, "
                    "raw_value, canonical_value, confidence, source_span, "
                    "extractor, span_start, span_end, confidence_source) "
                    "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)", rows)
        self.conn.commit()
        return cid

    def field_value(self, campaign_id: int, field_name: str) -> Any:
        with self._read() as cur:
            cur.execute(
                "SELECT canonical_value FROM extracted_fields "
                "WHERE campaign_id=%s AND field_name=%s LIMIT 1",
                (campaign_id, field_name))
            row = cur.fetchone()
        return json.loads(row["canonical_value"]) if row else None

    def query_fields(self, field_name: str) -> list[dict]:
        """Bir alanı tüm bankalar için döndürür (karşılaştırma/text-to-SQL için)."""
        with self._read() as cur:
            cur.execute(
                "SELECT b.slug AS bank, b.name AS bank_name, c.id AS campaign_id, "
                "c.campaign_type, c.source_url, "
                f"{_SCRAPED_AT_ISO} AS scraped_at, "
                "f.canonical_value, f.raw_value, f.confidence, f.source_span, "
                "f.extractor, f.span_start, f.span_end, f.confidence_source "
                "FROM extracted_fields f "
                "JOIN campaigns c ON c.id=f.campaign_id "
                "JOIN banks b ON b.id=c.bank_id "
                "WHERE f.field_name=%s ORDER BY f.id", (field_name,))
            rows = cur.fetchall()
        out = []
        for r in rows:
            d = dict(r)
            d["canonical_value"] = json.loads(d["canonical_value"])
            out.append(d)
        return out

    def campaign_text(self, campaign_id: int) -> Optional[dict]:
        """Bir kampanyanın metnini ve alanlarını offset'leriyle döndürür.

        SQLite yoluyla birebir aynı sözlüğü üretir; ortak mantık
        `base.finalize_campaign_text()`. `scraped_at` burada da ISO-8601 UTC
        metnine çevrilir (`_SCRAPED_AT_ISO`) — çelişki tespitinin `as_of`
        girdisi iki backend'de aynı biçimde gelmek zorunda.
        """
        with self._read() as cur:
            cur.execute(
                "SELECT c.id, c.raw_text, c.clean_text, c.source_url, "
                f"{_SCRAPED_AT_ISO} AS scraped_at, "
                "c.campaign_type, b.slug AS bank, b.name AS bank_name "
                "FROM campaigns c JOIN banks b ON b.id=c.bank_id WHERE c.id=%s",
                (campaign_id,))
            row = cur.fetchone()
            if row is None:
                return None
            cur.execute(
                "SELECT field_name, raw_value, canonical_value, confidence, "
                "source_span, extractor, span_start, span_end, confidence_source "
                "FROM extracted_fields WHERE campaign_id=%s ORDER BY field_name",
                (campaign_id,))
            alanlar = cur.fetchall()
        return finalize_campaign_text(dict(row), [dict(a) for a in alanlar])

    # --- özet / kapsam ölçümü ---
    def counts(self) -> dict[str, int]:
        """Banka / kampanya / alan sayıları."""
        def one(sql: str) -> int:
            with self._read() as cur:
                cur.execute(sql)
                return int(next(iter(cur.fetchone().values())))

        return {
            "banks": one("SELECT COUNT(*) FROM banks"),
            "banks_with_campaigns":
                one("SELECT COUNT(DISTINCT bank_id) FROM campaigns"),
            "campaigns": one("SELECT COUNT(*) FROM campaigns"),
            "fields": one("SELECT COUNT(*) FROM extracted_fields"),
            "campaigns_with_fields":
                one("SELECT COUNT(DISTINCT campaign_id) FROM extracted_fields"),
        }

    def field_coverage(self) -> dict[str, int]:
        """Alan adı → o alanın çıkarıldığı KAMPANYA sayısı (satır değil)."""
        with self._read() as cur:
            cur.execute(
                "SELECT field_name, COUNT(DISTINCT campaign_id) AS n "
                "FROM extracted_fields GROUP BY field_name "
                "ORDER BY n DESC, field_name")
            rows = cur.fetchall()
        return {r["field_name"]: int(r["n"]) for r in rows}

    def campaigns_per_bank(self) -> dict[str, int]:
        """Banka slug → kampanya sayısı (belge çıkmayan banka 0 ile görünür)."""
        with self._read() as cur:
            cur.execute(
                "SELECT b.slug AS slug, COUNT(c.id) AS n FROM banks b "
                "LEFT JOIN campaigns c ON c.bank_id=b.id "
                "GROUP BY b.slug ORDER BY n DESC, b.slug")
            rows = cur.fetchall()
        return {r["slug"]: int(r["n"]) for r in rows}

    def all_campaigns(self) -> list[dict]:
        with self._read() as cur:
            cur.execute(
                "SELECT c.id, b.slug AS bank, b.name AS bank_name, "
                "c.campaign_type, c.raw_text, c.source_url, "
                f"{_SCRAPED_AT_ISO} AS scraped_at "
                "FROM campaigns c JOIN banks b ON b.id=c.bank_id ORDER BY c.id")
            return [dict(r) for r in cur.fetchall()]

    def close(self) -> None:
        self.conn.close()
