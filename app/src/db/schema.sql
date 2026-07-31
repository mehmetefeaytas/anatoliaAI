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
    -- TIMESTAMPTZ (TIMESTAMP değil): provenance damgası `utc_now_iso()` ile
    -- üretilir ve saat dilimi OFSETİ taşır ('...+00:00'). Saat dilimsiz
    -- TIMESTAMP bu ofseti sessizce atardı; SQLite yolu ISO dizesini olduğu
    -- gibi sakladığı için iki backend farklı zaman damgası raporlardı.
    -- Okuma tarafı (`PostgresRepository`) değeri tekrar ISO-8601 UTC metnine
    -- çevirir; parite testi tests/test_pgvector_repository.py'de kilitli.
    scraped_at    TIMESTAMPTZ,
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
    extractor       TEXT CHECK (extractor IN ('rule','ner','llm')),
    -- Kaynak izlenebilirliği: clean_text içindeki karakter aralığı.
    -- Bu iki sütun olmadan arayüz "bu değer metnin neresinden geldi"
    -- sorusunu cevaplayamaz; halüsinasyon yapmadığımızı ispatlayamayız.
    -- ExtractedField.verify_span() bunu clean_text ile karşılaştırıp
    -- kendi kendini denetler (src/schemas.py).
    span_start      INTEGER,
    span_end        INTEGER,
    -- Güvenin NEREDEN geldiği: 'constant' | 'evidence' | 'logprob' | ...
    -- Kalibrasyon (ECE) bu ayrım olmadan yapılamaz: sabit 0.95 ile kanıt
    -- tabanlı skoru aynı kovaya koymak güvenilirlik diyagramını bozar.
    confidence_source TEXT
);

-- RAG vektör deposu. 31 Tem 2026'ya kadar bu tablo ŞEMADA VARDI ama hiçbir
-- Python kodu ona yazmıyor/okumuyordu — mimari slaytta pgvector vardı, kodda
-- yoktu. Yazan taraf: `src/rag/build_embeddings.py`, okuyan taraf:
-- `src/rag/store.PgVectorStore` + `src/chatbot/rag.VectorRetriever`.
CREATE TABLE IF NOT EXISTS embeddings (
    id          SERIAL PRIMARY KEY,
    campaign_id INTEGER REFERENCES campaigns(id),
    -- Kampanya metni parçalara (chunk) bölünür; sıra numarası olmadan
    -- yeniden gömme (re-embed) işlemi eski satırları hedefleyemez ve
    -- tablo her koşuda sessizce şişerdi (§21 "tekrar üretilemeyen repo").
    chunk_index INTEGER NOT NULL DEFAULT 0,
    chunk_text  TEXT,
    vector      vector(1024),      -- bge-m3 boyutu (EMBEDDING_DIM ile aynı)
    model       TEXT,              -- hangi model üretti (karışık korpus tespiti)
    UNIQUE (campaign_id, chunk_index)
);

CREATE INDEX IF NOT EXISTS idx_fields_campaign ON extracted_fields(campaign_id);
CREATE INDEX IF NOT EXISTS idx_fields_name ON extracted_fields(field_name);
CREATE INDEX IF NOT EXISTS idx_campaigns_bank ON campaigns(bank_id);
CREATE INDEX IF NOT EXISTS idx_embeddings_campaign ON embeddings(campaign_id);

-- Kosinüs mesafesi (`<=>`) için IVFFlat dizini.
-- `lists` küçük tutuldu: teslim korpusu ~850 belge / birkaç bin parça
-- mertebesinde; pgvector önerisi satır sayısının karekökü civarıdır.
-- NOT: IVFFlat YAKLAŞIKTIR (approximate). Az satırda tam taramadan yavaş bile
-- olabilir; bu yüzden dizin varlığı sorgu doğruluğunun ön koşulu DEĞİLDİR —
-- `PgVectorStore.search()` dizin olmadan da doğru (tam tarama) çalışır.
CREATE INDEX IF NOT EXISTS idx_embeddings_vector
    ON embeddings USING ivfflat (vector vector_cosine_ops) WITH (lists = 32);
