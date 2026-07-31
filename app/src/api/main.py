"""FastAPI uygulaması — dashboard + chatbot backend.

İlgili: ../../entities/dashboard.md, ../../entities/chatbot.md, CLAUDE.md §7
        ../../decisions/dashboard-ve-chatbot-arayuzu.md
        CLAUDE.md §18 (yenilikçilik: güven skoru + kaynak vurgulama, çelişki tespiti)

Uçlar:
  GET  /health
  GET  /banks
  GET  /campaigns
  GET  /campaigns/{campaign_id}/text     (kaynak metin + alan offset'leri — vurgulama)
  GET  /compare?field=kar_payi_orani&intent=lowest&type=Konut+Finansmanı
  GET  /scoring?field=kar_payi_orani     (şeffaf skorlama: formül + adımlar)
  POST /chat            {"question": "..."}
  POST /extract         {"text": "...", "bank": "..."}   (tek metin canlı çıkarım)
  GET  /contradictions

Veri kaynağı: önceden doldurulmuş DB (demo stratejisi). Uygulama açılışında
fixture'lardan in-memory DB kurulur; DATABASE_PATH verilirse kalıcı SQLite.

## Kaynak-span (offset) neden burada YENİDEN hesaplanıyor

`ExtractedField` hem `source_span` (±40 karakterlik pencere metni) hem
`span_start`/`span_end` (kesin karakter offset'i) taşır (`src/schemas.py:30-36`).
Ancak `extracted_fields` tablosunda offset sütunu YOKTUR
(`src/db/schema.sql:25-34`, `src/db/repository.py:31-35`) — offsetler DB'ye
yazılırken düşüyor. Şema bu ajanın sahiplik alanı dışında olduğu için offsetler
API katmanında, saklanan iki alandan **deterministik** biçimde geri kazanılır:

  `source_span` = `raw_text[a:b].strip()`  → yani raw_text'in bitişik bir alt
  dizesidir, `str.find` ile güvenilir biçimde bulunur. `raw_value` de bu
  pencerenin içinde aranır. Sonuç her zaman `raw_text[start:end] == hedef`
  eşitliğiyle **doğrulanır** (`span_verified`), pencere metni iki kez geçiyorsa
  `span_ambiguous` ile işaretlenir. Bulunamazsa offset `null` döner —
  uydurma yok (CLAUDE.md §21).

Bu yöntem katmandan bağımsızdır (kural/ner/llm hepsi için çalışır) ve yeniden
çıkarım maliyeti yoktur.

`confidence_source` ise saklanan veriden türetilemez (DB'de sütunu yok, kanıt
sinyali de yok). Bu yüzden kampanya başına **bir kez** kural katmanı yeniden
koşturulup (`_rule_conf_sources`) alan adı + ham değer eşleşmesi üzerinden
okunur; eşleşmezse `null` döner. `POST /extract` canlı çıkarım yaptığı için bu
alanı doğrudan gerçek değeriyle verir.
"""

from __future__ import annotations

import json
import os
import sqlite3
import threading
from typing import Any, Optional

from ..chatbot.bot import Chatbot
from ..comparison.compare import _HIGHER_IS_BETTER, _LOWER_IS_BETTER, RankRow, rank
from ..comparison.contradiction import detect as detect_contradictions
from ..db.repository import _SQLITE_SCHEMA, Repository
from ..extraction.llm.extractor import default_extractor
from ..extraction.llm.schema import EXTRACTION_FIELDS
from ..extraction.ner.classifier import default_classifier
from ..extraction.reconcile import build_campaign
from ..pipeline import run_pipeline
from ..preprocessing.clean import normalize_text

CONFIG = os.environ.get("BANKS_CONFIG", "config/banks.yaml")
RAW_DIR = os.environ.get("RAW_DIR", "data/raw")
DB_PATH = os.environ.get("DATABASE_PATH", ":memory:")

# Karşılaştırılabilir alanlar — arayüzdeki alan çipleri bu listeden üretilir.
# Etiketler Türkçedir (CLAUDE.md §19: kullanıcıya dönük tüm metinler Türkçe).
FIELD_LABELS: dict[str, str] = {
    "kar_payi_orani": "Kâr Payı Oranı",
    "finansman_tutari": "Finansman Tutarı",
    "vade_ay": "Vade (ay)",
    "taksit_sayisi": "Taksit Sayısı",
    "tahsis_ucreti": "Tahsis Ücreti",
    "masraf_durumu": "Masraf Durumu",
    "odul_miktari": "Ödül Miktarı",
    "indirim_orani": "İndirim Oranı",
    "alisveris_puani": "Alışveriş Puanı",
    "kampanya_suresi": "Kampanya Süresi",
    "kampanya_kosullari": "Kampanya Koşulları",
    "hedef_kitle": "Hedef Kitle",
}

# `/compare?intent=` için geçerli değerler — `chatbot/router.py:57` Route.intent
# ile BİREBİR aynı sözlük. Ayrışırlarsa dashboard ile chatbot aynı soruya farklı
# sıralama verir.
VALID_INTENTS = ("lowest", "highest", "list", "filter")


# --------------------------------------------------------------------------- #
# İstek gövdesi şemaları — MODÜL SEVİYESİNDE olmak ZORUNDA (hata düzeltmesi)
# --------------------------------------------------------------------------- #
# Bu modül `from __future__ import annotations` kullanır; yani tüm annotation'lar
# string'e dönüşür ve FastAPI bunları `typing.get_type_hints()` ile **modül
# global'lerinden** çözer. Şemalar `build_app()` içinde (yerel kapsamda) tanımlı
# olduğunda `ChatReq` adı global'lerde bulunamıyordu; FastAPI de tipi çözemediği
# `req` parametresini **query parametresi** sanıyordu. Sonuç: `POST /chat` ve
# `POST /extract` gövdeyi hiç okumadan
#     422 {"loc": ["query", "req"], "msg": "Field required"}
# döndürüyordu — iki uç da fiilen çağrılamazdı. Şemalar modül seviyesine
# taşındı; pydantic yoksa `build_app()` yine anlaşılır RuntimeError verir.
try:  # pragma: no cover - pydantic yokluğu build_app()'te raporlanır
    from pydantic import BaseModel

    class ChatReq(BaseModel):
        """`POST /chat` gövdesi."""

        question: str

    class ExtractReq(BaseModel):
        """`POST /extract` gövdesi (canlı çıkarım — CLAUDE.md §11)."""

        text: str
        bank: str = "bilinmeyen"

except ModuleNotFoundError:  # pragma: no cover
    BaseModel = None  # type: ignore[assignment]

# `rank()` girdiye eklenen ek alanları (extractor, confidence, campaign_id...)
# RankRow'a taşımaz. Sıralama mantığını KOPYALAMADAN satırları geri eşlemek için
# `bank` alanına geçici bir satır kimliği gömülür. NUL ayırıcı seçildi: hiçbir
# gerçek banka slug'ında bulunamaz.
_ROW_TOKEN_SEP = "\x00"


class ApiRepository(Repository):
    """`Repository` + thread güvenliği. **Bu bir hata düzeltmesidir.**

    `sqlite3.connect()` varsayılan olarak bağlantıyı **oluşturan thread'e
    kilitler** (`check_same_thread=True`). FastAPI ise `def` (async olmayan)
    uçları bir threadpool worker'ında koşturur. Bağlantı uygulama kurulumunda
    (ana thread) açıldığı için DB'ye dokunan HER uç — `/banks`, `/campaigns`,
    `/compare`, `/chat` — istek anında şu hatayla düşüyordu:

        sqlite3.ProgrammingError: SQLite objects created in a thread can only
        be used in that same thread.

    Dashboard'un boş tablo göstermesinin sebebi buydu; arayüz `catch` ile
    sessizce boş listeye düşüyordu.

    Neden alt sınıf: `src/db/repository.py` bu değişikliğin sahiplik alanı
    dışında. `:memory:` DB'de bağlantıyı sonradan yeniden açmak veriyi
    kaybettireceği için bağlantı burada baştan `check_same_thread=False` ile
    açılır ve tüm erişim `self.lock` ile serileştirilir.
    """

    def __init__(self, path: str = ":memory:"):
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(_SQLITE_SCHEMA)
        self.conn.commit()
        self.lock = threading.RLock()

    def rows(self, sql: str, params: tuple = ()) -> list[dict]:
        """Kilit altında SELECT → dict listesi."""
        with self.lock:
            return [dict(r) for r in self.conn.execute(sql, params).fetchall()]


# --------------------------------------------------------------------------- #
# Kaynak-span geri kazanımı (saf string, yeniden çıkarım yok)
# --------------------------------------------------------------------------- #
def locate_span(text: str, source_span: Optional[str],
                raw_value: Optional[str]) -> dict[str, Any]:
    """`source_span` penceresini ve içindeki `raw_value`'yu metinde konumlandırır.

    Dönüş anahtarları:
      span_start / span_end : karakter offset'leri (bulunamazsa None)
      span_scope            : 'value' (tam ham değer) | 'window' (yalnız pencere)
                              | None
      span_verified         : text[start:end] hedefe birebir eşit mi
      span_ambiguous        : pencere metni metinde birden çok kez geçiyor mu
      window_start/window_end: pencerenin kendi offset'leri (UI bağlam gösterir)

    Hiçbir tahmin yapılmaz: pencere bulunamazsa hepsi None döner.
    """
    out: dict[str, Any] = {
        "span_start": None, "span_end": None, "span_scope": None,
        "span_verified": False, "span_ambiguous": False,
        "window_start": None, "window_end": None,
    }
    if not text or not source_span:
        return out

    w = text.find(source_span)
    if w < 0:
        return out
    out["span_ambiguous"] = text.find(source_span, w + 1) >= 0
    w_end = w + len(source_span)
    out["window_start"], out["window_end"] = w, w_end

    if raw_value:
        v = text.find(raw_value, w, w_end)
        if v < 0:  # pencere dışında da olabilir (normalize farkı) — yine ara
            v = text.find(raw_value)
        if v >= 0 and text[v:v + len(raw_value)] == raw_value:
            out.update(span_start=v, span_end=v + len(raw_value),
                       span_scope="value", span_verified=True)
            return out

    # Ham değer konumlandırılamadı → en azından pencereyi vurgula (dürüst kapsam).
    out.update(span_start=w, span_end=w_end, span_scope="window",
               span_verified=text[w:w_end] == source_span)
    return out


def scoring_direction(field: str) -> tuple[str, str]:
    """Alanın sıralama yönü ve insan-okur açıklaması.

    Kaynak: `src/comparison/compare.py:65-70` (`_LOWER_IS_BETTER` /
    `_HIGHER_IS_BETTER`). Burada ağırlık UYDURULMAZ; yalnız koddaki küme
    üyeliği okunur.
    """
    if field in _LOWER_IS_BETTER:
        return "lower_is_better", "Küçük değer daha avantajlı"
    if field in _HIGHER_IS_BETTER:
        return "higher_is_better", "Büyük değer daha avantajlı"
    return "unranked", "Bu alan için sıralama yönü tanımlı değil (kıyas yapılmaz)"


def build_app():
    """FastAPI uygulamasını kur. fastapi yoksa anlaşılır hata verir."""
    try:
        from fastapi import FastAPI, HTTPException
        from fastapi.middleware.cors import CORSMiddleware
    except ModuleNotFoundError as e:  # pragma: no cover
        raise RuntimeError(
            "fastapi/pydantic kurulu değil. `pip install -r requirements.txt`") from e
    if BaseModel is None:  # pragma: no cover
        raise RuntimeError(
            "pydantic kurulu değil. `pip install -r requirements.txt`")

    app = FastAPI(title="Anatolia AI — Katılım Bankacılığı Kampanya API")
    app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"],
                       allow_headers=["*"])

    repo = ApiRepository(DB_PATH)
    # demo verisini doldur (önceden doldurulmuş DB stratejisi)
    run_pipeline(repo, CONFIG, raw_dir=RAW_DIR, mode="fixture")
    llm = default_extractor()
    bot = Chatbot(repo, llm=llm)
    clf = default_classifier()

    # Tembel önbellekler — her ikisi de kampanya başına BİR kez kural katmanını
    # yeniden koşturur; istek başına değil (aksi halde /compare her satır için
    # tam çıkarım yapardı).
    # kampanya_id → {alan_adı: (raw_value, confidence_source)}
    _conf_src_cache: dict[int, dict[str, tuple[Optional[str], str]]] = {}
    # kampanya_id → çelişki listesi
    _contra_cache: dict[int, list[dict]] = {}

    # ----------------------------------------------------------------- #
    # Dahili yardımcılar
    # ----------------------------------------------------------------- #
    def _campaign_row(campaign_id: int) -> Optional[dict]:
        found = repo.rows(
            "SELECT c.id, b.slug AS bank, b.name AS bank_name, c.campaign_type, "
            "c.raw_text, c.clean_text, c.source_url, c.scraped_at "
            "FROM campaigns c JOIN banks b ON b.id=c.bank_id WHERE c.id=?",
            (campaign_id,))
        return found[0] if found else None

    def _rule_conf_sources(campaign_id: int,
                           text: str) -> dict[str, tuple[Optional[str], str]]:
        """Kural katmanını bir kez koşturup `confidence_source`'ları çıkarır.

        DB'de `confidence_source` sütunu yok (bkz. modül başlığı). Yeniden
        çıkarım kampanya başına ÖNBELLEKLENİR; LLM çağrılmaz (deterministik ve
        offline: `build_campaign(llm=None)` → NullLLMExtractor).
        """
        cached = _conf_src_cache.get(campaign_id)
        if cached is not None:
            return cached
        try:
            c = build_campaign(text, bank_slug="_reindex")
            out = {f.field_name: (f.raw_value, f.confidence_source) for f in c.fields}
        except Exception:  # pragma: no cover - çıkarım hatası UI'yı düşürmesin
            out = {}
        _conf_src_cache[campaign_id] = out
        return out

    def _conf_source_for(campaign_id: int, text: str, field_name: str,
                         raw_value: Optional[str]) -> Optional[str]:
        """Saklanan alanın güven-kaynağı; yeniden çıkarımla eşleşmezse None."""
        idx = _rule_conf_sources(campaign_id, text)
        hit = idx.get(field_name)
        if hit is None:
            return None
        rv, csource = hit
        return csource if rv == raw_value else None

    def _field_rows(field: str) -> list[dict]:
        """Bir alanın tüm banka satırları — kaynak, güven ve katman bilgisiyle.

        `repository.query_fields()` `extractor` ve `raw_value` sütunlarını
        SELECT etmiyor; karşılaştırma tablosunda "hangi katman üretti" sütunu
        için ikisi de gerekli. repository/ bu ajanın sahiplik alanı dışında
        olduğundan sorgu burada açıkça yazılır.
        """
        rows = repo.rows(
            "SELECT b.slug AS bank, b.name AS bank_name, c.id AS campaign_id, "
            "c.campaign_type, c.source_url, c.raw_text, "
            "f.raw_value, f.canonical_value, f.confidence, f.source_span, "
            "f.extractor FROM extracted_fields f "
            "JOIN campaigns c ON c.id=f.campaign_id "
            "JOIN banks b ON b.id=c.bank_id WHERE f.field_name=?", (field,))
        for d in rows:
            try:
                d["canonical_value"] = json.loads(d["canonical_value"])
            except (TypeError, ValueError):
                d["canonical_value"] = None
        return rows

    def _campaign_contradictions(campaign_id: int, text: str,
                                 bank_slug: str) -> list[dict]:
        cached = _contra_cache.get(campaign_id)
        if cached is not None:
            return cached
        try:
            c = build_campaign(text, bank_slug=bank_slug)
            out = [{"kind": k.kind, "detail": k.detail, "fields": k.fields}
                   for k in detect_contradictions(c)]
        except Exception:  # pragma: no cover - çıkarım hatası UI'yı düşürmesin
            out = []
        _contra_cache[campaign_id] = out
        return out

    # ----------------------------------------------------------------- #
    # Uçlar
    # ----------------------------------------------------------------- #
    @app.get("/health")
    def health():
        return {"status": "ok", "llm": llm.available}

    @app.get("/banks")
    def banks():
        return repo.rows("SELECT slug, name, website_url, bddk_active FROM banks")

    @app.get("/campaigns")
    def campaigns():
        return repo.rows(
            "SELECT c.id, b.slug AS bank, b.name AS bank_name, c.campaign_type, "
            "c.raw_text, c.source_url, c.scraped_at FROM campaigns c "
            "JOIN banks b ON b.id=c.bank_id ORDER BY c.id")

    @app.get("/fields")
    def fields():
        """Çıkarılan 12 alan + Türkçe etiket + sıralama yönü (UI çipleri için)."""
        out = []
        for name in EXTRACTION_FIELDS:
            direction, label = scoring_direction(name)
            out.append({
                "field": name,
                "label": FIELD_LABELS.get(name, name),
                "direction": direction,
                "direction_label": label,
                "comparable_field": direction != "unranked",
            })
        return out

    @app.get("/campaigns/{campaign_id}/text")
    def campaign_text(campaign_id: int):
        """Kampanyanın kaynak metni + her alanın karakter offset'i.

        Kaynak-span vurgulaması (CLAUDE.md §18 hedef #1) ve Jüri Audit Paneli
        bu uca dayanır: metin + offsetler + güven + katman + çelişki tek yerde.
        """
        camp = _campaign_row(campaign_id)
        if camp is None:
            raise HTTPException(status_code=404,
                                detail=f"Kampanya bulunamadı: {campaign_id}")
        text = camp.get("raw_text") or ""

        rows = repo.rows(
            "SELECT field_name, raw_value, canonical_value, confidence, "
            "source_span, extractor FROM extracted_fields WHERE campaign_id=? "
            "ORDER BY id", (campaign_id,))

        fields_out = []
        for d in rows:
            try:
                canonical = json.loads(d["canonical_value"])
            except (TypeError, ValueError):
                canonical = None
            loc = locate_span(text, d["source_span"], d["raw_value"])
            fields_out.append({
                "field": d["field_name"],
                "label": FIELD_LABELS.get(d["field_name"], d["field_name"]),
                "raw_value": d["raw_value"],
                "canonical_value": canonical,
                "confidence": d["confidence"],
                "confidence_source": _conf_source_for(
                    campaign_id, text, d["field_name"], d["raw_value"]),
                "extractor": d["extractor"],
                "source_span": d["source_span"],
                **loc,
            })

        return {
            "campaign_id": campaign_id,
            "bank": camp["bank"],
            "bank_name": camp["bank_name"],
            "campaign_type": camp["campaign_type"],
            "source_url": camp["source_url"],
            "scraped_at": camp["scraped_at"],
            "text": text,
            "text_length": len(text),
            "fields": fields_out,
            "contradictions": _campaign_contradictions(campaign_id, text,
                                                       camp["bank"]),
        }

    @app.get("/compare")
    def compare(field: str, intent: Optional[str] = None,
                type: Optional[str] = None):
        """Bir alanı bankalar arası karşılaştırır (adil kıyas — CLAUDE.md §17).

        `intent` KARARI: parametre eskiden imzada duruyor ama gövdede hiç
        kullanılmıyordu (sessiz ölü parametre). KALDIRILMADI, **uygulandı** —
        çünkü chatbot tarafında `chatbot/router.py` zaten aynı niyeti
        ('lowest'/'highest'/'list'/'filter') üretiyor ve dashboard'un "en düşük /
        en yüksek" düğmesi bu sözlüğü paylaşmak zorunda; ayrışırlarsa aynı soru
        iki arayüzde farklı sıralanır. Anlamı:

          lowest  → sıralamayı KÜÇÜK değer önce olacak şekilde zorla
          highest → sıralamayı BÜYÜK değer önce olacak şekilde zorla
          list / filter / None → alanın kendi doğal yönü (compare.rank)

        Yön zorlaması yalnızca `comparable=True` satırlarda uygulanır;
        kıyaslanamayanlar not'larıyla sonda kalır. Geçersiz intent artık
        sessizce yok sayılmaz, 400 döner.

        Dönen alanlar (mevcutlar korunur, yenileri eklendi):
          bank, bank_name, value, comparable, note, source_span  (mevcut)
          campaign_id, campaign_type, source_url, raw_value, confidence,
          confidence_source, extractor, span_start, span_end, span_scope,
          span_verified, span_ambiguous, window_start, window_end, sort_key,
          rank, contradiction_count
        """
        if intent is not None and intent not in VALID_INTENTS:
            raise HTTPException(
                status_code=400,
                detail=f"Geçersiz intent: {intent!r}. "
                       f"Geçerli değerler: {', '.join(VALID_INTENTS)}")

        rows = _field_rows(field)
        if type:
            rows = [r for r in rows if r.get("campaign_type") == type]

        # Satır kimliğini `bank`'a göm (bkz. _ROW_TOKEN_SEP açıklaması).
        by_token: dict[str, dict] = {}
        rank_input: list[dict] = []
        for i, r in enumerate(rows):
            token = f"{i}{_ROW_TOKEN_SEP}{r['bank']}"
            by_token[token] = r
            rank_input.append({
                "bank": token,
                "bank_name": r["bank_name"],
                "canonical_value": r["canonical_value"],
                "source_span": r["source_span"],
            })

        ranked: list[RankRow] = rank(rank_input, field)

        # intent yön zorlaması: rank() comparable'ları alanın doğal yönünde
        # sıralar ve başa koyar; istenen yön tersse yalnız o önek ters çevrilir.
        natural_lower = field in _LOWER_IS_BETTER
        want_lower = {"lowest": True, "highest": False}.get(intent or "")
        if want_lower is not None and want_lower != natural_lower:
            head = [x for x in ranked if x.comparable and x.sort_key is not None]
            tail = [x for x in ranked if not (x.comparable and x.sort_key is not None)]
            ranked = list(reversed(head)) + tail

        out = []
        position = 0
        for x in ranked:
            src = by_token[x.bank]
            text = src.get("raw_text") or ""
            loc = locate_span(text, src["source_span"], src["raw_value"])
            if x.comparable and x.sort_key is not None:
                position += 1
                row_rank: Optional[int] = position
            else:
                row_rank = None
            out.append({
                # --- mevcut sözleşme (kaldırılmadı) ---
                "bank": src["bank"],
                "bank_name": src["bank_name"],
                "value": x.value,
                "comparable": x.comparable,
                "note": x.note,
                "source_span": x.source_span,
                # --- denetim / açıklanabilirlik ---
                "campaign_id": src["campaign_id"],
                "campaign_type": src["campaign_type"],
                "source_url": src["source_url"],
                "raw_value": src["raw_value"],
                "confidence": src["confidence"],
                "confidence_source": _conf_source_for(
                    src["campaign_id"], text, field, src["raw_value"]),
                "extractor": src["extractor"],
                **loc,
                # --- şeffaf skorlama ---
                "sort_key": x.sort_key,
                "rank": row_rank,
                "contradiction_count": len(_campaign_contradictions(
                    src["campaign_id"], text, src["bank"])),
            })
        return out

    @app.get("/scoring")
    def scoring(field: str, type: Optional[str] = None):
        """Şeffaf skorlama: "en avantajlı" iddiasının formülü + ara değerleri.

        ÖNEMLİ — koda dayanır, ağırlık uydurulmaz: `src/comparison/compare.py`
        alanlar arası **ağırlıklı bileşik skor içermez**. Sıralama tek alan
        üzerinden ve iki adımdan oluşur:
          1) `_numeric_key(value)` → (sort_key, comparable, note)
          2) yön = alan `_LOWER_IS_BETTER` mi `_HIGHER_IS_BETTER` mi
        Bu yüzden `composite_weights` bilinçli olarak `null`'dır; birden çok
        alanı tek puana indiren bir formül kodda YOK ve CLAUDE.md §17
        (uydurma sıralama yapma) gereği burada icat edilmez.
        """
        direction, direction_label = scoring_direction(field)
        rows = compare(field=field, type=type)  # aynı sıralama, tek doğruluk kaynağı
        return {
            "field": field,
            "label": FIELD_LABELS.get(field, field),
            "direction": direction,
            "direction_label": direction_label,
            "formula_source": "src/comparison/compare.py",
            "steps": [
                {"no": 1, "name": "Kanonik değer",
                 "detail": "Ham ifade normalize edilir (oran→float, para→"
                           "{value,currency}, vade→ay). CLAUDE.md §10."},
                {"no": 2, "name": "Sıralama anahtarı (sort_key)",
                 "detail": "compare._numeric_key(): sayı→kendisi, para→value, "
                           "masraf→amount (yoksa 0), aralık→min ve "
                           "comparable=False."},
                {"no": 3, "name": "Adil kıyas kapısı",
                 "detail": "Yalnız comparable=True satırlar sıralanır. Aralık, "
                           "farklı para birimi, sayısal olmayan ve boş değerler "
                           "not'uyla sona alınır (CLAUDE.md §17)."},
                {"no": 4, "name": "Yön",
                 "detail": f"{field} → {direction} ({direction_label}). Kaynak: "
                           "compare._LOWER_IS_BETTER / _HIGHER_IS_BETTER."},
            ],
            "composite_weights": None,
            "composite_note": (
                "Kod tabanında alanlar arası ağırlıklı bileşik skor yoktur; "
                "sıralama her zaman TEK alan üzerinden yapılır. Ağırlık "
                "uydurmak CLAUDE.md §17'ye aykırı olurdu."),
            "rows": [
                {"bank": r["bank"], "bank_name": r["bank_name"],
                 "value": r["value"], "sort_key": r["sort_key"],
                 "comparable": r["comparable"], "note": r["note"],
                 "rank": r["rank"], "confidence": r["confidence"],
                 "extractor": r["extractor"]}
                for r in rows
            ],
        }

    @app.post("/chat")
    def chat(req: ChatReq):
        a = bot.ask(req.question)
        return {"answer": a.text, "handler": a.handler, "field": a.field,
                "sources": a.sources}

    @app.post("/extract")
    def extract(req: ExtractReq):
        """Canlı çıkarım (CLAUDE.md §11 "canlı çıkarım butonu").

        Offset'ler burada GERÇEK `ExtractedField` nesnesinden gelir ve
        `verify_span()` ile doğrulanır — DB yolundaki geri kazanıma gerek yok.
        """
        text = normalize_text(req.text)
        ctype, ctype_conf = clf.classify(text)
        c = build_campaign(text, bank_slug=req.bank, llm=llm, campaign_type=ctype)
        by_name = {f.field_name: f for f in c.fields}
        return {
            "bank": c.bank_slug,
            "campaign_type": c.campaign_type,
            "campaign_type_confidence": ctype_conf,
            "text": text,
            "text_length": len(text),
            "llm_available": llm.available,
            "fields": [
                {"field": f.field_name,
                 "label": FIELD_LABELS.get(f.field_name, f.field_name),
                 "value": f.canonical_value,
                 "raw_value": f.raw_value,
                 "confidence": f.confidence,
                 "confidence_source": f.confidence_source,
                 "extractor": f.extractor.value,
                 "source_span": f.source_span,
                 "span_start": f.span_start,
                 "span_end": f.span_end,
                 "span_scope": "value" if f.span_start is not None else None,
                 "span_verified": f.verify_span(text),
                 "span_ambiguous": False}
                for f in c.fields
            ],
            # Hangi alanlar HİÇ bulunamadı — halüsinasyon yasağının görünür hali
            "missing_fields": [
                {"field": name, "label": FIELD_LABELS.get(name, name)}
                for name in EXTRACTION_FIELDS if name not in by_name
            ],
            "contradictions": [
                {"kind": k.kind, "detail": k.detail, "fields": k.fields}
                for k in detect_contradictions(c)
            ],
        }

    @app.get("/contradictions")
    def contradictions():
        """Tüm külliyatta otomatik yakalanan iç çelişkiler (CLAUDE.md §18 #2)."""
        out = []
        for camp in repo.all_campaigns():
            text = camp.get("raw_text", "") or ""
            for k in _campaign_contradictions(camp["id"], text, camp["bank"]):
                out.append({
                    "bank": camp["bank"],
                    "bank_name": camp.get("bank_name"),
                    "campaign_id": camp["id"],
                    "campaign_type": camp.get("campaign_type"),
                    "source_url": camp.get("source_url"),
                    **k,
                })
        return out

    @app.get("/contradictions/summary")
    def contradictions_summary():
        """Çelişki taramasının kapsamı — "kaç belgede kaç bulgu" anlatısı."""
        camps = repo.all_campaigns()
        found = contradictions()
        by_kind: dict[str, int] = {}
        for c in found:
            by_kind[c["kind"]] = by_kind.get(c["kind"], 0) + 1
        return {
            "scanned_campaigns": len(camps),
            "scanned_banks": len({c["bank"] for c in camps}),
            "contradiction_count": len(found),
            "affected_campaigns": len({c["campaign_id"] for c in found}),
            "by_kind": by_kind,
        }

    return app


# uvicorn src.api.main:app
try:  # pragma: no cover
    app = build_app()
except RuntimeError:
    app = None
