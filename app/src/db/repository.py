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
from collections.abc import Mapping
from typing import Any, Optional

from ..schemas import Campaign
from .base import (
    BELGE_TURLERI,
    KAMPANYA_DURUMLARI,
    KAMPANYA_DURUMU_DAMGASIZ,
    arama_sutunlari,
    arama_suz,
    arama_where,
    belge_turu_dogrula,
    extractor_dogrula,
    finalize_campaign_text,
    kampanya_metin_suz,
    kampanya_sutunlari,
    kampanya_where,
    kiyas_where,
    nul_denetle,
    on_nul_dogrula,
)

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
    source_url TEXT, scraped_at TEXT, campaign_type TEXT,
    -- 'kampanya' | 'sozlesme' | NULL (bilinmiyor) — bkz. base.BELGE_TURLERI.
    -- `campaign_type` ile KARIŞTIRMA: o, 8 kampanya TÜRÜ sınıflandırmasıdır
    -- (Konut Finansmanı, Kart, ...); bu ise belgenin kampanya mı yoksa akit
    -- metni mi olduğudur. Akit karşılaştırma tablosuna girmemelidir.
    belge_turu TEXT,
    -- 'expired' | 'active' | NULL (bilinmiyor) — bkz. base.suresi_dolmus_mu().
    -- `.meta.json` sidecar'ındaki `campaign_status` alanının DB karşılığı.
    -- Süresi dolmuş kampanya sıralamaya alınmaz ama GİZLENMEZ: değeri ve
    -- gerekçesi görünür kalır (`compare.rank` içindeki durum kapısı).
    campaign_status TEXT,
    -- LLM üretimi kısa özet. Sütun burada AÇILIR, bu modül DOLDURMAZ.
    ozet TEXT,
    -- Özet NEDEN yok. Gerekçenin tamamı `schema.sql`'deki ikiz sütundadır:
    -- boş `ozet`, "denendi ve içerik çıkmadı" ile "hiç denenmedi"yi ayırt
    -- edemez; sebep sütunu olmadan kapsam sayacı yeni belgeler için yanlış
    -- cümle kurar.
    ozet_sebep TEXT
);
CREATE TABLE IF NOT EXISTS extracted_fields (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    campaign_id INTEGER, field_name TEXT NOT NULL, raw_value TEXT,
    canonical_value TEXT, confidence REAL, source_span TEXT,
    -- CHECK kısıtı `schema.sql` (Postgres) ile AYNI. Ama tek başına YETMEZ ve
    -- sözleşme ona DAYANMAZ: kısıt yalnız `CREATE TABLE` yolundan gelir, yani
    -- ZATEN VAR OLAN bir DB dosyası onu taşımaz — `CREATE TABLE IF NOT EXISTS`
    -- hiçbir şey yapmaz ve `_SONRADAN_EKLENEN` göçü yalnız `ADD COLUMN` bilir;
    -- SQLite `ALTER TABLE` ile CHECK eklemeye zaten izin vermez.
    -- ÖLÇÜLDÜ (2026-08-10): teslim edilen `data/demo.db` bu sütunu KISITSIZ
    -- (`extractor TEXT`) taşıyor ve geçici bir kopyasına `'UYDURMA'` yazılabildi.
    -- Bu yüzden gerçek doğrulama noktası `base.extractor_dogrula()`'dır; iki
    -- backend de `insert_campaign()` içinde oradan geçer. Buradaki CHECK taze
    -- DB'lerde ham SQL yazan çağıranları bedava yakalayan ikinci savunmadır.
    extractor TEXT CHECK (extractor IS NULL OR extractor IN ('rule','ner','llm')),
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
    # `postgres._LATER_COLUMNS` ile AYNI kalmak ZORUNDA — o dosyanın kendi
    # yorumu bunu şart koşuyor: "iki liste ayrışırsa bir backend sütunu olan,
    # diğeri olmayan bir şemayla koşar". Ayrışmıştı: aşağıdaki iki `embeddings`
    # sütunu yalnız Postgres tarafında vardı. Diskteki `data/demo.db` bugün
    # onları TAŞIYOR ama `CREATE TABLE` yolundan (schema.sql), göçten değil —
    # yani kusur gizliydi ve ancak o sütunlar eklenmeden ÖNCE yaratılmış bir
    # `.db` dosyası açıldığında görünürdü: `SqliteVectorStore.replace_campaign()`
    # INSERT'i `no such column: chunk_index` ile düşerdi.
    ("embeddings", "chunk_index", "INTEGER NOT NULL DEFAULT 0"),
    ("embeddings", "model", "TEXT"),
    # 4 Ağu 2026: belge türü + özet. Diskteki 21,6 MB'lık `data/demo.db` bu
    # satırlar olmadan açıldığında `no such column: belge_turu` ile ölürdü.
    ("campaigns", "belge_turu", "TEXT"),
    ("campaigns", "ozet", "TEXT"),
    # 10 Ağu 2026: kampanya geçerlilik durumu. Bu satır olmadan, sütun
    # eklenmeden ÖNCE kurulmuş bir `data/demo.db` açıldığında `query_fields`
    # `no such column: campaign_status` ile ölürdü — yani kıyas tablosunun
    # tamamı, süresi dolmuş kampanyalar yüzünden değil GÖÇ EKSİĞİ yüzünden
    # boşalırdı.
    ("campaigns", "campaign_status", "TEXT"),
    # 11 Ağu 2026: özet yokluğunun sebebi. Bu satır olmadan, sütun eklenmeden
    # ÖNCE kurulmuş bir `data/demo.db` açıldığında `all_campaigns()`
    # `no such column: ozet_sebep` ile ölürdü — yani kampanya listesinin
    # TAMAMI, tek bir açıklama sütunu yüzünden boşalırdı.
    ("campaigns", "ozet_sebep", "TEXT"),
)


class Repository:
    """SQLite tabanlı depo. path=':memory:' ile testlerde kullanılır.

    `base.RepositoryProtocol` sözleşmesini uygular.
    """

    backend: str = "sqlite"

    def __init__(self, path: str = ":memory:", *,
                 check_same_thread: bool = True, on_nul: str = "error"):
        """`check_same_thread=False` yalnızca çok thread'li sunucu için.

        `sqlite3` varsayılan olarak bağlantıyı onu OLUŞTURAN thread'e kilitler.
        FastAPI `def` uçlarını bir threadpool'da koşturduğu için API yolunda bu
        kilit her isteği `ProgrammingError` ile düşürüyordu. Bayrak tek başına
        YETMEZ: bağlantı paylaşımı ancak erişim serileştirilirse güvenlidir —
        `base.ThreadSafeRepository` bunu yapar ve `factory.create_repository(
        thread_safe=True)` ikisini birlikte kurar. Bu yüzden varsayılan
        DEĞİŞMEDİ; tek başına açmak sessiz bir yarış koşulu davetidir.

        `on_nul` **`PostgresRepository` ile aynı ada, aynı kipe ve aynı
        varsayılana** ('error') sahiptir. SQLite NUL baytını saklayabilir ama
        saklamaz: gerekçe `base.nul_denetle()` docstring'inde — offline yolda
        sorunsuz kurulan bir korpusun üretime göç ederken düşmesi, iki
        backend'in aynı veriyi kabul ettiği iddiasının ihlalidir.
        """
        self.on_nul = on_nul_dogrula(on_nul)
        self.conn = sqlite3.connect(path, check_same_thread=check_same_thread)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(_SQLITE_SCHEMA)
        self._migrate()
        self.conn.commit()

    def _text(self, value: Optional[str], alan: str,
              baglam: str) -> Optional[str]:
        """Metni NUL baytına karşı denetler — mantık `base.nul_denetle()`.

        SQLite NUL'u saklayabilir; yine de reddedilir. Gerekçe (ve ölçülen
        sıfır bedel) `base.nul_denetle()` docstring'inde. Denetim Postgres
        yolundan KOPYALANMAZ, aynı fonksiyon çağrılır.
        """
        return nul_denetle(value, alan, baglam, on_nul=self.on_nul)

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
                        scraped_at: Optional[str] = None,
                        campaign_status: Optional[str] = None) -> int:
        bank_id = self.upsert_bank(c.bank_slug, c.bank_slug)
        baglam = f"kampanya (banka={c.bank_slug}, url={c.source_url})"
        raw_text = self._text(c.raw_text, "raw_text", baglam)
        clean_text = self._text(clean_text, "clean_text", baglam)
        # Alanların TAMAMI, TEK satır bile yazılmadan ÖNCE doğrulanır —
        # `set_belge_turu()` docstring'indeki aynı gerekçe: yarım yazılmış bir
        # kampanya (satırı var, alanları yok) sessizce eksik bir korpus
        # bırakırdı. Postgres yolu birebir aynı sırayı izler.
        # span_start/end ve confidence_source burada YAZILMAZSA, projenin en
        # özgün iddiası (her değer bir karakter aralığına bağlı) veri tabanı
        # sınırında kaybolur ve arayüz offset'i tahmin etmek zorunda kalır.
        # Bu sütunlar 31 Tem'de tam bu sebeple eklendi.
        alanlar = [
            (f.field_name,
             self._text(f.raw_value, f"{f.field_name}.raw_value", baglam),
             json.dumps(f.canonical_value, ensure_ascii=False),
             f.confidence,
             self._text(f.source_span, f"{f.field_name}.source_span", baglam),
             # Şemadaki CHECK'e GÜVENİLMEZ: diskteki `data/demo.db` onu
             # taşımıyor (ölçüldü — `base.extractor_dogrula()` docstring'i).
             extractor_dogrula(f.extractor), f.span_start, f.span_end,
             getattr(f, "confidence_source", None))
            for f in c.fields
        ]
        cur = self.conn.execute(
            "INSERT INTO campaigns(bank_id, raw_text, clean_text, source_url, "
            "scraped_at, campaign_type, campaign_status) VALUES (?,?,?,?,?,?,?)",
            (bank_id, raw_text, clean_text, c.source_url, scraped_at,
             c.campaign_type, campaign_status))
        cid = cur.lastrowid
        self.conn.executemany(
            "INSERT INTO extracted_fields(campaign_id, field_name, raw_value, "
            "canonical_value, confidence, source_span, extractor, "
            "span_start, span_end, confidence_source) "
            "VALUES (?,?,?,?,?,?,?,?,?,?)",
            [(cid, *a) for a in alanlar])
        self.conn.commit()
        return cid

    # --- belge türü / özet (toplu yazma) ---
    def set_belge_turu(self, atamalar: Mapping[int, Optional[str]]) -> int:
        """Kampanya id → belge türü ataması. Dönen: güncellenen satır sayısı.

        Toplu (`executemany`) yazılır: 1761 belgelik korpusta satır başına ayrı
        `commit()` kurulum süresini saniyelerce uzatırdı.

        **Tüm sözlük önce doğrulanır, sonra tek satır bile yazılır.** Yarım
        uygulanmış bir atama, kısmen sınıflandırılmış bir korpus bırakırdı ve
        kıyas tablosu belgelerin bir kısmını eler bir kısmını elemezdi —
        sessizce yanlış bir tablo, gürültülü bir hatadan çok daha kötüdür.
        """
        temiz = [(belge_turu_dogrula(v), k) for k, v in atamalar.items()]
        if not temiz:
            return 0
        cur = self.conn.executemany(
            "UPDATE campaigns SET belge_turu=? WHERE id=?", temiz)
        self.conn.commit()
        return cur.rowcount

    def set_ozet(self, atamalar: Mapping[int, Optional[str]]) -> int:
        """Kampanya id → LLM üretimi özet. Dönen: güncellenen satır sayısı.

        Bu modül özet ÜRETMEZ, yalnızca yazma yolunu açar: üreten taraf
        (LLM katmanı) depo dışında ham SQL yazmak zorunda kalmasın diye
        sözleşmede duruyor (bkz. `fields_by_extractor` docstring'indeki aynı
        gerekçe).

        NUL denetimi Postgres yolundaki ile AYNI: özet bir LLM çıktısıdır ve
        bozuk bir kod çözme (decode) NUL üretebilir. Denetim yalnız Postgres'te
        yaşasaydı, offline üretilmiş bir özet kümesi üretime göç ederken
        düşerdi — bkz. `base.nul_denetle()`.

        ## Dolu özet, `ozet_sebep`i AYNI ifadede temizler

        "Özet var" ile "özet şu sebeple yok" aynı satırda birlikte duramaz;
        dursaydı kapsam sayacı aynı belgeyi iki kez sayardı. Daha önce
        `icerik_yok` diye işaretlenmiş bir belge, metni değişip sonraki koşuda
        özetlenebilir — sebebi ayrı bir çağrıya bırakmak, o çağrı atlandığında
        çelişkiyi kalıcı kılardı. Bu yüzden temizlik burada, tek `UPDATE`
        içinde yapılır.

        Ters yön (özet `None`'a çekilir) sebebi ELLEMEZ: özeti silen tarafın
        gerekçesi kendisine aittir ve `set_ozet_sebep()` ile yazılır.
        """
        baglam = "ozet yazımı"
        temiz = [(self._text(v, "ozet", baglam), k)
                 for k, v in atamalar.items()]
        if not temiz:
            return 0
        dolu = [(v, k) for v, k in temiz if (v or "").strip()]
        bos = [(v, k) for v, k in temiz if not (v or "").strip()]
        n = 0
        if dolu:
            n += self.conn.executemany(
                "UPDATE campaigns SET ozet=?, ozet_sebep=NULL WHERE id=?",
                dolu).rowcount
        if bos:
            n += self.conn.executemany(
                "UPDATE campaigns SET ozet=? WHERE id=?", bos).rowcount
        self.conn.commit()
        return n

    def set_ozet_sebep(self, atamalar: Mapping[int, Optional[str]]) -> int:
        """Kampanya id → özetin ÜRETİLEMEME sebebi. Dönen: güncellenen satır.

        Sebep serbest metin değil, `src/summarize/ozet.py`'nin ürettiği sonlu
        bir etikettir (`icerik_yok`, `yabanci_alfabe`, `llm_kapali` …). Burada
        bir beyaz liste ile doğrulanMAZ: liste özet katmanına aittir ve iki
        yerde yaşasaydı yeni bir sebep eklendiğinde depo onu sessizce reddederdi
        — bu projede altı kez tekrarlayan "aynı bilgi iki yerde" kusuru.
        Depo yalnızca metin sağlığını (NUL) denetler.
        """
        baglam = "ozet sebebi yazımı"
        temiz = [(self._text(v, "ozet_sebep", baglam), k)
                 for k, v in atamalar.items()]
        if not temiz:
            return 0
        cur = self.conn.executemany(
            "UPDATE campaigns SET ozet_sebep=? WHERE id=?", temiz)
        self.conn.commit()
        return cur.rowcount

    def field_value(self, campaign_id: int, field_name: str) -> Any:
        row = self.conn.execute(
            "SELECT canonical_value FROM extracted_fields WHERE campaign_id=? "
            "AND field_name=?", (campaign_id, field_name)).fetchone()
        return json.loads(row["canonical_value"]) if row else None

    def query_fields(self, field_name: str, *,
                     sozlesme_dahil: bool = False) -> list[dict]:
        """Bir alanı tüm bankalar için döndürür (karşılaştırma/text-to-SQL için).

        **Varsayılan olarak sözleşme belgeleri ELENİR** (`sozlesme_dahil=False`).
        Bu metot `/compare` tablosunu ve chatbot'un text-to-SQL yolunu besler;
        oradaki soru her zaman "hangi KAMPANYA daha avantajlı"dır. Korpustaki
        113 akit/tarife PDF'inin 41'i oran/vade/tutar taşıyor ve filtre olmadan
        bir genel kredi sözleşmesi bir konut kampanyasıyla aynı kolonda
        sıralanıyordu (CLAUDE.md §17 "adil kıyas garantisi").

        `sozlesme_dahil=True` filtreyi tamamen kaldırır — akit metnindeki bir
        değeri bilerek arayan çağıranlar için. RAG/chatbot'un serbest metin
        yolu zaten `campaign_text()` üzerinden gider ve HİÇ filtrelemez:
        kullanıcı "sözleşmede ne yazıyor" diye sorabilmelidir.

        Türü bilinmeyen (NULL) belgeler ELENMEZ; gerekçe `base.kiyas_where()`.
        """
        rows = self.conn.execute(
            "SELECT b.slug AS bank, b.name AS bank_name, c.id AS campaign_id, "
            "c.campaign_type, c.belge_turu, c.campaign_status, "
            "c.source_url, c.scraped_at, "
            "f.canonical_value, f.raw_value, "
            "f.confidence, f.source_span, f.extractor, "
            "f.span_start, f.span_end, f.confidence_source "
            "FROM extracted_fields f "
            "JOIN campaigns c ON c.id=f.campaign_id "
            "JOIN banks b ON b.id=c.bank_id "
            "WHERE f.field_name=? "
            + ("" if sozlesme_dahil else f"AND {kiyas_where()} ")
            # `ORDER BY f.id` parite için ŞART: Postgres yolunda vardı, burada
            # yoktu. Sırasız SELECT'in dönüş sırası garantili değildir ve bu
            # metot `/compare` tablosunu besliyor — eşit değerli satırların
            # sırası backend'e göre değişebilirdi.
            + "ORDER BY f.id", (field_name,)).fetchall()
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
            "c.scraped_at, c.campaign_type, c.belge_turu, c.campaign_status, "
            "c.ozet, b.slug AS bank, b.name AS bank_name "
            # Bu metot RAG/chatbot'un metin yoludur ve **belge türüne göre
            # SÜZMEZ**: kullanıcı "sözleşmede ne yazıyor" diye sorabilmelidir.
            # Süzülen tek yer kıyas yoludur (`query_fields`).
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

    def belge_turu_counts(self) -> dict[str, int]:
        """Belge türü → kampanya sayısı. Bilinmeyen `'bilinmeyen'` altında.

        Anahtar kümesi SABİTTİR (`kampanya`, `sozlesme`, `bilinmeyen`) ve sıfır
        değerler de yazılır: sütun hiç doldurulmamışsa `{"kampanya": 0,
        "sozlesme": 0, "bilinmeyen": 1761}` döner. Eksik anahtar döndürmek,
        raporu okuyanın `0` ile "ölçülmedi" arasındaki farkı görememesi
        demek olurdu.
        """
        rows = self.conn.execute(
            "SELECT belge_turu, COUNT(*) AS n FROM campaigns "
            "GROUP BY belge_turu").fetchall()
        out = dict.fromkeys((*BELGE_TURLERI, "bilinmeyen"), 0)
        for r in rows:
            out[r["belge_turu"] or "bilinmeyen"] += int(r["n"])
        return out

    def campaign_status_counts(self) -> dict[str, int]:
        """Geçerlilik damgası → kampanya sayısı. Damgasızlar `'damgasiz'` altında.

        Anahtar kümesi `belge_turu_counts()` ile AYNI disiplinde SABİTTİR
        (`active`, `expired`, `damgasiz`) ve sıfırlar da yazılır: damgalama hiç
        koşmamış bir korpusta `{"active": 0, "expired": 0, "damgasiz": 1774}`
        döner. Eksik anahtar döndürmek, raporu okuyanın `0` ile "ölçülmedi"
        arasındaki farkı görememesi demek olurdu.

        `NULL` üçüncü bir kovadır, `active`'e KATILMAZ: gerekçe
        `base.KAMPANYA_DURUMU_DAMGASIZ` yorumunda (korpusun %74'ü damgasız ve
        onları "aktif" saymak doğrulanmamış bir iddia uydurmaktır).

        Sütunda beklenmeyen bir değer varsa (elle yazılmış eski bir DB)
        anahtar olarak OLDUĞU GİBİ eklenir — sessizce bir kovaya atmak, veri
        hatasını gizlerdi.
        """
        rows = self.conn.execute(
            "SELECT campaign_status, COUNT(*) AS n FROM campaigns "
            "GROUP BY campaign_status").fetchall()
        out = dict.fromkeys(KAMPANYA_DURUMLARI, 0)
        for r in rows:
            anahtar = r["campaign_status"] or KAMPANYA_DURUMU_DAMGASIZ
            out[anahtar] = out.get(anahtar, 0) + int(r["n"])
        return out

    def field_coverage(self, *, sozlesme_dahil: bool = True) -> dict[str, int]:
        """Alan adı → o alanın çıkarıldığı KAMPANYA sayısı.

        Satır değil kampanya sayılır: aynı kampanyada bir alan (şu an olmasa da)
        birden çok kez yazılabilirse "kapsam" yüzdesi 100'ü aşardı.

        `sozlesme_dahil` varsayılanı **True** — kıyas yolunun tersine. Bu metot
        bir KAPSAM ÖLÇÜSÜDÜR: "çıkarıcı korpusun ne kadarından alan üretti"
        sorusuna cevap verir ve akitten çıkan alanlar da gerçekten üretilmiş
        alanlardır. Varsayılanı `False` yapmak, mevcut raporların sayılarını
        sessizce küçültürdü. Akitsiz kapsam isteyen açıkça `False` geçer.
        """
        rows = self.conn.execute(
            "SELECT f.field_name AS field_name, "
            "COUNT(DISTINCT f.campaign_id) AS n FROM extracted_fields f "
            + ("" if sozlesme_dahil else
               f"JOIN campaigns c ON c.id=f.campaign_id WHERE {kiyas_where()} ")
            # İkincil `field_name` sıralaması Postgres yolundaki ile aynı olmalı;
            # yoksa eşit sayıdaki alanlar iki backend'de farklı sırada raporlanır.
            + "GROUP BY f.field_name ORDER BY n DESC, field_name").fetchall()
        return {r["field_name"]: int(r["n"]) for r in rows}

    def fields_by_extractor(self, *,
                            sozlesme_dahil: bool = True) -> dict[str, int]:
        """Katman adı (rule/ner/llm) → o katmanın ürettiği alan SAYISI.

        Ablasyonun ve raporların "hangi katman ne kadar iş yaptı" sorusu.
        Depo dışında ham SQL yazılmaması kuralı gereği burada duruyor
        (bkz. src/api/main.py başlığı: beş ham SQL çağrısı Postgres'te
        `?` yer tutucusu nedeniyle patlıyordu).

        `sozlesme_dahil` varsayılanı **True**: `field_coverage` ile aynı
        gerekçe — bu bir üretim ölçüsüdür, bir kıyas tablosu değil.
        """
        rows = self.conn.execute(
            "SELECT f.extractor AS extractor, COUNT(*) AS n "
            "FROM extracted_fields f "
            + ("" if sozlesme_dahil else
               f"JOIN campaigns c ON c.id=f.campaign_id WHERE {kiyas_where()} ")
            + "GROUP BY f.extractor ORDER BY n DESC, extractor").fetchall()
        return {r["extractor"]: int(r["n"]) for r in rows}

    def campaigns_per_bank(self) -> dict[str, int]:
        """Banka slug → kampanya sayısı (belge çıkmayan banka 0 ile görünür)."""
        rows = self.conn.execute(
            "SELECT b.slug AS slug, COUNT(c.id) AS n FROM banks b "
            "LEFT JOIN campaigns c ON c.bank_id=b.id "
            "GROUP BY b.slug ORDER BY n DESC, b.slug").fetchall()
        return {r["slug"]: int(r["n"]) for r in rows}

    def bank_field_coverage(self) -> dict[str, dict[str, int]]:
        """Banka slug → {'belge': kampanya sayısı, 'alan': FARKLI alan sayısı}.

        `field_coverage()` bunu VEREMEZ: orada banka boyutu yoktur, "kâr payı
        oranı 56 belgeden çıktı" der ama hangi bankalardan çıktığını söylemez.
        Arayüzdeki "veri kapsamı: 3 belge / 12 alan" etiketi tam olarak o
        eksik boyutu gösterir — bir bankanın çok belgesi olup az alanı
        çıkmışsa, kıyas tablosundaki zayıflığın sebebi görünür olur.

        `alan` **FARKLI alan adı** sayar (`COUNT(DISTINCT f.field_name)`), satır
        değil: aynı bankanın 500 belgesinde kâr payı oranı 500 kez çıkmış
        olabilir; "12 alan" ise o bankada kaç ÇEŞİT bilgi bulunduğunu söyler ve
        üst sınırı 12'dir (`EXTRACTION_FIELDS`). Satır saymak, kapsamı belge
        sayısıyla karıştıran anlamsız bir sayı üretirdi.

        Anahtar kümesi SABİTTİR: `LEFT JOIN` sayesinde hiç belgesi olmayan banka
        da `{"belge": 0, "alan": 0}` ile görünür (`campaigns_per_bank()` ile
        aynı gerekçe — eksik anahtar "ölçülmedi" ile "sıfır"ı karıştırır).
        """
        rows = self.conn.execute(
            "SELECT b.slug AS slug, COUNT(DISTINCT c.id) AS belge, "
            "COUNT(DISTINCT f.field_name) AS alan FROM banks b "
            "LEFT JOIN campaigns c ON c.bank_id=b.id "
            "LEFT JOIN extracted_fields f ON f.campaign_id=c.id "
            # İkincil `b.slug` sıralaması Postgres yolundaki ile aynı olmalı;
            # yoksa eşit belgeli bankalar iki backend'de farklı sırada gelir.
            "GROUP BY b.slug ORDER BY belge DESC, b.slug").fetchall()
        return {r["slug"]: {"belge": int(r["belge"]), "alan": int(r["alan"])}
                for r in rows}

    def all_campaigns(self, *, belge_turu: Optional[str] = None,
                      bank: Optional[str] = None,
                      campaign_type: Optional[str] = None,
                      status: Optional[str] = None,
                      q: Optional[str] = None,
                      govde: bool = True) -> list[dict]:
        """Kampanyalar, `id` sırasında; isteğe bağlı süzgeçlerle.

        `ORDER BY c.id` EKSİKTİ; Postgres yolunda vardı. Sırasız SELECT'in
        dönüş sırası garantili değildir, yani iki backend aynı korpusta farklı
        sıralı liste verebilirdi — `GET /campaigns` de bu metoda dayandığı için
        arayüzdeki kampanya sırası backend'e göre değişirdi.

        ## `govde=False` — 10,3 MB'lık yükün asıl sebebi

        `raw_text` SELECT listesinden ÇIKAR. Ölçüm (2026-08-11): süzgeçsiz
        `GET /campaigns` 10.339.015 bayttı ve neredeyse tamamı ham gövdeydi;
        arayüz o alanı hiçbir yerde okumuyordu. Varsayılan yine de **True**:
        bu metodun depo içi çağıranları (RAG indeksi, gömme üretimi, toplu
        özetleme) gövdeye MUHTAÇTIR ve varsayılanı `False` yapmak onları
        sessizce boş metinle çalıştırırdı. Kararı veren taraf uçtur.

        ## Süzgeçler

        Hepsi **kesin eşleşmelidir** ve varsayılanları `None` = süzme yok
        (geriye tam uyumlu). Süzgeç metni `base.kampanya_where()` ile ÜRETİLİR,
        burada tekrar yazılmaz; `q` ise SQL'de değil `base.kampanya_metin_suz()`
        ile Python'da uygulanır (gerekçe: `LOWER()` iki backend'de aynı şeyi
        yapmıyor — o fonksiyonun docstring'i).

        `belge_turu='sozlesme'` geçildiğinde YALNIZ akitler döner — chatbot'un
        "hangi sözleşmeler var" sorusunun yolu budur. Burada `kiyas_where()`
        kullanılmaz: bu bir listeleme seçicisidir, kıyas güvenliği değil.
        """
        where, params = kampanya_where(
            yer_tutucu="?", bank=bank, campaign_type=campaign_type,
            belge_turu=belge_turu, status=status)
        sql = ("SELECT " + kampanya_sutunlari(govde=govde)
               + " FROM campaigns c JOIN banks b ON b.id=c.bank_id "
               + where + "ORDER BY c.id")
        rows = self.conn.execute(sql, tuple(params)).fetchall()
        return kampanya_metin_suz([dict(r) for r in rows], q)

    def search_campaigns(self, q: Optional[str], *,
                         bank: Optional[str] = None,
                         campaign_type: Optional[str] = None,
                         belge_turu: Optional[str] = None,
                         status: Optional[str] = None) -> list[dict]:
        """Serbest arama — eşleşen satırlar + **neden eşleştikleri**.

        `all_campaigns(q=...)`ten iki farkı var: sütun listesi kısadır
        (`arama_sutunlari()`, ham gövde hiç seçilmez) ve her satır bir
        `eslesme` alanı taşır. Boş sorgu BOŞ liste döndürür — gerekçe
        `base.arama_suz()` docstring'inde.

        Süzgeç metni ve eşleşme mantığı `base.py`den gelir; burada yalnız
        yer tutucu (`?`) ve bağlantı yolu farklıdır.
        """
        where, params = arama_where(
            yer_tutucu="?", bank=bank, campaign_type=campaign_type,
            belge_turu=belge_turu, status=status)
        sql = ("SELECT " + arama_sutunlari()
               + " FROM campaigns c JOIN banks b ON b.id=c.bank_id "
               + where + "ORDER BY c.id")
        rows = self.conn.execute(sql, tuple(params)).fetchall()
        return arama_suz([dict(r) for r in rows], q)

    def close(self):
        self.conn.close()
