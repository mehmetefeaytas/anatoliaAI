"""Veri erişim katmanı — SQLite fallback (offline test) + Postgres hedefi.

İlgili: ../../decisions/demo-onceden-doldurulmus-db.md (önceden doldurulmuş DB)
        CLAUDE.md §9

Varsayılan: SQLite (stdlib, sıfır kurulum) — pipeline ve chatbot offline koşar.
Üretim: PostgreSQL+pgvector (DATABASE_URL ile, psycopg). Bu modül canonical_value'yu
JSON metni olarak saklar; karşılaştırma/chatbot bunu çözer.
"""

from __future__ import annotations

import json
import sqlite3
from typing import Any, Optional

from ..schemas import Campaign

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
    canonical_value TEXT, confidence REAL, source_span TEXT, extractor TEXT
);
CREATE INDEX IF NOT EXISTS idx_fields_campaign ON extracted_fields(campaign_id);
CREATE INDEX IF NOT EXISTS idx_fields_name ON extracted_fields(field_name);
"""


class Repository:
    """SQLite tabanlı depo. path=':memory:' ile testlerde kullanılır."""

    def __init__(self, path: str = ":memory:"):
        self.conn = sqlite3.connect(path)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(_SQLITE_SCHEMA)
        self.conn.commit()

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
            self.conn.execute(
                "INSERT INTO extracted_fields(campaign_id, field_name, raw_value, "
                "canonical_value, confidence, source_span, extractor) "
                "VALUES (?,?,?,?,?,?,?)",
                (cid, f.field_name, f.raw_value,
                 json.dumps(f.canonical_value, ensure_ascii=False),
                 f.confidence, f.source_span, f.extractor.value))
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
            "c.campaign_type, f.canonical_value, f.confidence, f.source_span "
            "FROM extracted_fields f "
            "JOIN campaigns c ON c.id=f.campaign_id "
            "JOIN banks b ON b.id=c.bank_id "
            "WHERE f.field_name=?", (field_name,)).fetchall()
        out = []
        for r in rows:
            d = dict(r)
            d["canonical_value"] = json.loads(d["canonical_value"])
            out.append(d)
        return out

    def all_campaigns(self) -> list[dict]:
        rows = self.conn.execute(
            "SELECT c.id, b.slug AS bank, b.name AS bank_name, c.campaign_type, "
            "c.raw_text, c.source_url FROM campaigns c JOIN banks b ON b.id=c.bank_id"
        ).fetchall()
        return [dict(r) for r in rows]

    def close(self):
        self.conn.close()
