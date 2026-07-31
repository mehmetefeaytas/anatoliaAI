"""Veri erişim katmanı — SQLite uygulaması (offline / test yolu).

İlgili: ../../decisions/demo-onceden-doldurulmus-db.md (önceden doldurulmuş DB)
        CLAUDE.md §9, docs/veri-katmani.md (backend seçimi)
        base.py (ortak sözleşme), postgres.py (üretim yolu), factory.py (seçim)

Bu backend BİLİNÇLİ bir tasarım kararıdır, eksiklik değil: stdlib `sqlite3` ile
sıfır kurulum gerektirir, böylece çekirdek testler ve eval katmanı hiçbir üçüncü
parti bağımlılık olmadan koşar (on-prem iddiasının parçası) ve jüri
`docker compose up` dediğinde sistem bir veritabanı sunucusu beklemeden açılır.

Üretim/vektör yolu `postgres.PostgresRepository`'dir; seçim `DATABASE_URL`
ortam değişkeniyle `factory.create_repository()` üzerinden yapılır.

Bu modül canonical_value'yu JSON metni olarak saklar; karşılaştırma/chatbot
bunu çözer.
"""

from __future__ import annotations

import json
import sqlite3
from typing import Any, Optional

from ..schemas import Campaign
from .base import finalize_campaign_text

# SQLite uyumlu şema (Postgres schema.sql'in alt kümesi)
_SQLITE_SCHEMA = """
CREATE TABLE IF NOT EXISTS banks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL, slug TEXT UNIQUE NOT NULL,
    website_url TEXT, bddk_active INTEGER DEFAULT 1
);
CREATE TABLE IF NOT EXISTS campaigns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    bank_id INTEGER, raw_text TEXT NOT NULL, clean_text TEXT,
    source_url TEXT, scraped_at TEXT, campaign_type TEXT
);
CREATE TABLE IF NOT EXISTS extracted_fields (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    campaign_id INTEGER, field_name TEXT NOT NULL, raw_value TEXT,
    canonical_value TEXT, confidence REAL, source_span TEXT, extractor TEXT,
    span_start INTEGER, span_end INTEGER, confidence_source TEXT
);
-- RAG vektör deposu — Postgres'teki `vector(1024)` sütununun SQLite karşılığı.
-- SQLite'ta vektör tipi yoktur; vektör float32 dizisi olarak BLOB'a yazılır ve
-- `rag.store.SqliteVectorStore` kosinüs benzerliğini TAM TARAMA ile hesaplar.
-- Bu, pgvector'ün yerine geçmez (indekssiz, O(n)); demo korpusu ölçeğinde
-- (~850 belge) çalışır ve VectorRetriever'ın mantığını Postgres olmadan
-- test edilebilir kılar. Ölçek yolu pgvector'dür.
CREATE TABLE IF NOT EXISTS embeddings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    campaign_id INTEGER, chunk_index INTEGER NOT NULL DEFAULT 0,
    chunk_text TEXT, vector BLOB, model TEXT,
    UNIQUE (campaign_id, chunk_index)
);
CREATE INDEX IF NOT EXISTS idx_fields_campaign ON extracted_fields(campaign_id);
CREATE INDEX IF NOT EXISTS idx_fields_name ON extracted_fields(field_name);
CREATE INDEX IF NOT EXISTS idx_embeddings_campaign ON embeddings(campaign_id);
"""

# Şemaya sonradan eklenen sütunlar. Diskteki eski bir demo DB'si açıldığında
# CREATE TABLE IF NOT EXISTS hiçbir şey yapmaz ve sütunlar eksik kalır; bu
# liste onları tamamlar. (sqlite ADD COLUMN idempotent değil, bu yüzden
# PRAGMA ile kontrol ediyoruz.)
_SONRADAN_EKLENEN = (
    ("extracted_fields", "span_start", "INTEGER"),
    ("extracted_fields", "span_end", "INTEGER"),
    ("extracted_fields", "confidence_source", "TEXT"),
)


class Repository:
    """SQLite tabanlı depo. path=':memory:' ile testlerde kullanılır.

    `base.RepositoryProtocol` sözleşmesini uygular.
    """

    backend: str = "sqlite"

    def __init__(self, path: str = ":memory:", *,
                 check_same_thread: bool = True):
        """`check_same_thread=False` yalnızca çok thread'li sunucu için.

        `sqlite3` varsayılan olarak bağlantıyı onu OLUŞTURAN thread'e kilitler.
        FastAPI `def` uçlarını bir threadpool'da koşturduğu için API yolunda bu
        kilit her isteği `ProgrammingError` ile düşürüyordu. Bayrak tek başına
        YETMEZ: bağlantı paylaşımı ancak erişim serileştirilirse güvenlidir —
        `base.ThreadSafeRepository` bunu yapar ve `factory.create_repository(
        thread_safe=True)` ikisini birlikte kurar. Bu yüzden varsayılan
        DEĞİŞMEDİ; tek başına açmak sessiz bir yarış koşulu davetidir.
        """
        self.conn = sqlite3.connect(path, check_same_thread=check_same_thread)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(_SQLITE_SCHEMA)
        self._migrate()
        self.conn.commit()

    def _migrate(self) -> None:
        """Eski bir DB dosyasına sonradan eklenen sütunları tamamlar."""
        for tablo, sutun, tip in _SONRADAN_EKLENEN:
            mevcut = {r["name"] for r in
                      self.conn.execute(f"PRAGMA table_info({tablo})")}
            if sutun not in mevcut:
                self.conn.execute(
                    f"ALTER TABLE {tablo} ADD COLUMN {sutun} {tip}")

    # --- bankalar ---
    def upsert_bank(self, name: str, slug: str, website_url: Optional[str] = None,
                    bddk_active: bool = True) -> int:
        cur = self.conn.execute("SELECT id FROM banks WHERE slug=?", (slug,))
        row = cur.fetchone()
        if row:
            return row["id"]
        cur = self.conn.execute(
            "INSERT INTO banks(name, slug, website_url, bddk_active) VALUES (?,?,?,?)",
            (name, slug, website_url, 1 if bddk_active else 0))
        self.conn.commit()
        return cur.lastrowid

    def all_banks(self) -> list[dict]:
        """Banka kataloğu: slug, ad, site, BDDK durumu (`GET /banks`).

        `bddk_active` **bool'a çevrilir**: SQLite bu sütunu INTEGER (0/1),
        PostgreSQL BOOLEAN olarak saklar. Ham değeri döndürmek iki backend'in
        aynı soruya farklı JSON vermesi demek olurdu (`1` vs `true`).
        """
        rows = self.conn.execute(
            "SELECT slug, name, website_url, bddk_active FROM banks "
            "ORDER BY slug").fetchall()
        return [{"slug": r["slug"], "name": r["name"],
                 "website_url": r["website_url"],
                 "bddk_active": bool(r["bddk_active"])} for r in rows]

    # --- kampanya + alanlar ---
    def insert_campaign(self, c: Campaign, clean_text: Optional[str] = None,
                        scraped_at: Optional[str] = None) -> int:
        bank_id = self.upsert_bank(c.bank_slug, c.bank_slug)
        cur = self.conn.execute(
            "INSERT INTO campaigns(bank_id, raw_text, clean_text, source_url, "
            "scraped_at, campaign_type) VALUES (?,?,?,?,?,?)",
            (bank_id, c.raw_text, clean_text, c.source_url, scraped_at, c.campaign_type))
        cid = cur.lastrowid
        for f in c.fields:
            # span_start/end ve confidence_source burada YAZILMAZSA, projenin
            # en özgün iddiası (her değer bir karakter aralığına bağlı) veri
            # tabanı sınırında kaybolur ve arayüz offset'i tahmin etmek
            # zorunda kalır. Bu sütunlar 31 Tem'de tam bu sebeple eklendi.
            self.conn.execute(
                "INSERT INTO extracted_fields(campaign_id, field_name, raw_value, "
                "canonical_value, confidence, source_span, extractor, "
                "span_start, span_end, confidence_source) "
                "VALUES (?,?,?,?,?,?,?,?,?,?)",
                (cid, f.field_name, f.raw_value,
                 json.dumps(f.canonical_value, ensure_ascii=False),
                 f.confidence, f.source_span, f.extractor.value,
                 f.span_start, f.span_end,
                 getattr(f, "confidence_source", None)))
        self.conn.commit()
        return cid

    def field_value(self, campaign_id: int, field_name: str) -> Any:
        row = self.conn.execute(
            "SELECT canonical_value FROM extracted_fields WHERE campaign_id=? "
            "AND field_name=?", (campaign_id, field_name)).fetchone()
        return json.loads(row["canonical_value"]) if row else None

    def query_fields(self, field_name: str) -> list[dict]:
        """Bir alanı tüm bankalar için döndürür (karşılaştırma/text-to-SQL için)."""
        rows = self.conn.execute(
            "SELECT b.slug AS bank, b.name AS bank_name, c.id AS campaign_id, "
            "c.campaign_type, c.source_url, c.scraped_at, f.canonical_value, f.raw_value, "
            "f.confidence, f.source_span, f.extractor, "
            "f.span_start, f.span_end, f.confidence_source "
            "FROM extracted_fields f "
            "JOIN campaigns c ON c.id=f.campaign_id "
            "JOIN banks b ON b.id=c.bank_id "
            # `ORDER BY f.id` parite için ŞART: Postgres yolunda vardı, burada
            # yoktu. Sırasız SELECT'in dönüş sırası garantili değildir ve bu
            # metot `/compare` tablosunu besliyor — eşit değerli satırların
            # sırası backend'e göre değişebilirdi.
            "WHERE f.field_name=? ORDER BY f.id", (field_name,)).fetchall()
        out = []
        for r in rows:
            d = dict(r)
            d["canonical_value"] = json.loads(d["canonical_value"])
            out.append(d)
        return out

    def campaign_text(self, campaign_id: int) -> Optional[dict]:
        """Bir kampanyanın metnini ve alanlarını offset'leriyle döndürür.

        Kaynak-span vurgulaması bunu kullanır: `clean_text` span offset'lerinin
        ölçüldüğü metindir, `raw_text` değil. İkisini karıştırmak offset'leri
        kaydırır — bu yüzden hangisinin kullanıldığı yanıtta açıkça belirtilir.

        Doğrulama/JSON çözme mantığı `base.finalize_campaign_text()`
        içindedir; Postgres yolu birebir aynı fonksiyonu kullanır.

        `scraped_at` de döner: çelişki tespitinin zaman bağımlı kuralı
        ("kampanya süresi dolmuş ama sayfa hâlâ yayında") `as_of` olarak duvar
        saatini DEĞİL toplama anını kullanır; API bu alanı buradan okur.
        """
        row = self.conn.execute(
            "SELECT c.id, c.raw_text, c.clean_text, c.source_url, "
            "c.scraped_at, c.campaign_type, b.slug AS bank, b.name AS bank_name "
            "FROM campaigns c JOIN banks b ON b.id=c.bank_id WHERE c.id=?",
            (campaign_id,)).fetchone()
        if row is None:
            return None
        alanlar = self.conn.execute(
            "SELECT field_name, raw_value, canonical_value, confidence, "
            "source_span, extractor, span_start, span_end, confidence_source "
            "FROM extracted_fields WHERE campaign_id=? ORDER BY field_name",
            (campaign_id,)).fetchall()
        return finalize_campaign_text(dict(row), [dict(a) for a in alanlar])

    # --- özet / kapsam ölçümü ---
    def counts(self) -> dict[str, int]:
        """Banka / kampanya / alan sayıları (doldurma betiğinin özet raporu için)."""
        def one(sql: str) -> int:
            return int(self.conn.execute(sql).fetchone()[0])

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
        """Alan adı → o alanın çıkarıldığı KAMPANYA sayısı.

        Satır değil kampanya sayılır: aynı kampanyada bir alan (şu an olmasa da)
        birden çok kez yazılabilirse "kapsam" yüzdesi 100'ü aşardı.
        """
        rows = self.conn.execute(
            "SELECT field_name, COUNT(DISTINCT campaign_id) AS n "
            # İkincil `field_name` sıralaması Postgres yolundaki ile aynı olmalı;
            # yoksa eşit sayıdaki alanlar iki backend'de farklı sırada raporlanır.
            "FROM extracted_fields GROUP BY field_name "
            "ORDER BY n DESC, field_name").fetchall()
        return {r["field_name"]: int(r["n"]) for r in rows}

    def fields_by_extractor(self) -> dict[str, int]:
        """Katman adı (rule/ner/llm) → o katmanın ürettiği alan SAYISI.

        Ablasyonun ve raporların "hangi katman ne kadar iş yaptı" sorusu.
        Depo dışında ham SQL yazılmaması kuralı gereği burada duruyor
        (bkz. src/api/main.py başlığı: beş ham SQL çağrısı Postgres'te
        `?` yer tutucusu nedeniyle patlıyordu).
        """
        rows = self.conn.execute(
            "SELECT extractor, COUNT(*) AS n FROM extracted_fields "
            "GROUP BY extractor ORDER BY n DESC, extractor").fetchall()
        return {r["extractor"]: int(r["n"]) for r in rows}

    def campaigns_per_bank(self) -> dict[str, int]:
        """Banka slug → kampanya sayısı (belge çıkmayan banka 0 ile görünür)."""
        rows = self.conn.execute(
            "SELECT b.slug AS slug, COUNT(c.id) AS n FROM banks b "
            "LEFT JOIN campaigns c ON c.bank_id=b.id "
            "GROUP BY b.slug ORDER BY n DESC, b.slug").fetchall()
        return {r["slug"]: int(r["n"]) for r in rows}

    def all_campaigns(self) -> list[dict]:
        """Tüm kampanyalar, `id` sırasında.

        `ORDER BY c.id` EKSİKTİ; Postgres yolunda vardı. Sırasız SELECT'in
        dönüş sırası garantili değildir, yani iki backend aynı korpusta farklı
        sıralı liste verebilirdi — `GET /campaigns` de bu metoda dayandığı için
        arayüzdeki kampanya sırası backend'e göre değişirdi.
        """
        rows = self.conn.execute(
            "SELECT c.id, b.slug AS bank, b.name AS bank_name, c.campaign_type, "
            "c.raw_text, c.source_url, c.scraped_at "
            "FROM campaigns c JOIN banks b ON b.id=c.bank_id ORDER BY c.id"
        ).fetchall()
        return [dict(r) for r in rows]

    def close(self):
        self.conn.close()
