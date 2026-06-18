-- Anatolia AI — veri şeması (PostgreSQL + pgvector hedef)
-- İlgili: CLAUDE.md §9, ../../concepts/yapilandirilmis-veri-formati.md
-- Not: SQLite fallback (repository.py) bu şemanın uyumlu alt kümesini kurar.

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS banks (
    id          SERIAL PRIMARY KEY,
    name        TEXT NOT NULL,
    slug        TEXT UNIQUE NOT NULL,
    website_url TEXT,
    bddk_active BOOLEAN DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS campaigns (
    id            SERIAL PRIMARY KEY,
    bank_id       INTEGER REFERENCES banks(id),
    raw_text      TEXT NOT NULL,
    clean_text    TEXT,
    source_url    TEXT,
    scraped_at    TIMESTAMP,
    campaign_type TEXT
);

CREATE TABLE IF NOT EXISTS extracted_fields (
    id              SERIAL PRIMARY KEY,
    campaign_id     INTEGER REFERENCES campaigns(id),
    field_name      TEXT NOT NULL,
    raw_value       TEXT,
    canonical_value TEXT,          -- JSON metni (oran=float, para=obj, aralık=obj)
    confidence      REAL,
    source_span     TEXT,
    extractor       TEXT CHECK (extractor IN ('rule','ner','llm'))
);

CREATE TABLE IF NOT EXISTS embeddings (
    id          SERIAL PRIMARY KEY,
    campaign_id INTEGER REFERENCES campaigns(id),
    chunk_text  TEXT,
    vector      vector(1024)       -- bge-m3 boyutu
);

CREATE INDEX IF NOT EXISTS idx_fields_campaign ON extracted_fields(campaign_id);
CREATE INDEX IF NOT EXISTS idx_fields_name ON extracted_fields(field_name);
CREATE INDEX IF NOT EXISTS idx_campaigns_bank ON campaigns(bank_id);
