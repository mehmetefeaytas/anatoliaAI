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

## Veri kaynağı: HAM SQL DEĞİL, depo sözleşmesi (`src/db/base.py`)

Bu modül `src/db/factory.create_repository()` ile depo açar:

    DATABASE_URL dolu -> PostgresRepository   (üretim / pgvector yolu)
    DATABASE_URL boş  -> Repository(DATABASE_PATH)  (offline demo / test yolu)

**31 Tem 2026'ya kadar API bunu yapmıyordu.** `Repository(DATABASE_PATH)`
doğrudan kuruluyordu, yani `DATABASE_URL` verilse bile okunmuyordu: mimari
diyagramda Postgres vardı, çalışan sistemde yoktu. Bağlamanın önündeki gerçek
engel "tek satır" değildi — bu dosya `repo.rows(<ham SQL>)` kaçış kapısını
**beş yerde** kullanıyordu ve o SQL'ler `?` yer tutucusu taşıyordu (SQLite
lehçesi). `psycopg` `%s` bekler; Postgres'te her uç `ProgrammingError` ile
düşerdi. Beş çağrının hepsi sözleşme metotlarına çevrildi (`campaign_text`,
`query_fields`, `all_banks`, `all_campaigns`) ve `rows()` kaçış kapısı
KALDIRILDI. Kural: bu dosyada SQL yazılmaz; eksik bir sorgu varsa
`RepositoryProtocol`'e metot eklenir ve İKİ backend'de de uygulanır.

## Kaynak-span (offset) — birincil yol DB, yedek yol yeniden hesaplama

`ExtractedField` hem `source_span` (±40 karakterlik pencere metni) hem
`span_start`/`span_end` (kesin karakter offset'i) taşır (`src/schemas.py`) ve
31 Tem 2026 itibarıyla ikisi de veri tabanında SAKLANIYOR
(`extracted_fields.span_start` / `span_end` / `confidence_source`).

Bu modül eskiden saklanan offset'i HİÇ OKUMUYORDU: `span_info()`'nun yedek
yolunu (`locate_span`) her alan için tek yol olarak koşturuyordu. Ölçüm
(`data/demo.db`, 849 belge / 2204 alan): saklanan offsetlerin **2204'ü de
doğrulanıyor**, yeniden hesaplama bunların **73'ünde farklı bir yer**
gösteriyordu — çünkü `str.find` aynı ham değerin ilk geçtiği yeri bulur,
çıkarımın geldiği yeri değil. Yani arayüz alanların ~%3'ünde YANLIŞ yeri
boyuyordu. Artık saklanan offset birincil, yeniden hesaplama yedektir
(`span_info()`); yedek yol eski kayıtlar ve offset üretmeyen katmanlar için
durur:

  `source_span` metnin bitişik bir alt dizesidir, `str.find` ile bulunur;
  `raw_value` pencere içinde aranır. Sonuç her zaman `text[start:end] == hedef`
  eşitliğiyle **doğrulanır** (`span_verified`), pencere metni iki kez geçiyorsa
  `span_ambiguous` ile işaretlenir. Bulunamazsa offset `null` döner —
  uydurma yok (CLAUDE.md §21).

`confidence_source` da artık DB'den okunur. Eskiden "DB'de sütunu yok"
gerekçesiyle kampanya başına kural katmanı YENİDEN KOŞTURULUYOR ve alan adı +
ham değer eşleşmesiyle geri kazanılıyordu; sütun 31 Tem'de eklendi ve
`data/demo.db`'de 2204/2204 alan dolu. Yeniden çıkarım hem gereksiz maliyetti
hem de eşleşmeyen alanlarda sessizce `null` veriyordu. `POST /extract` canlı
çıkarım yaptığı için bu alanı zaten doğrudan gerçek değeriyle verir.
"""

from __future__ import annotations

import os
from typing import Any, Optional

from ..chatbot.bot import Chatbot
from ..comparison.compare import _HIGHER_IS_BETTER, _LOWER_IS_BETTER, RankRow, rank
from ..comparison.contradiction import detect as detect_contradictions
from ..db.factory import create_repository
from ..extraction.llm.extractor import default_extractor
from ..extraction.llm.schema import EXTRACTION_FIELDS
from ..extraction.ner.classifier import default_classifier
from ..extraction.reconcile import build_campaign
from ..pipeline import run_pipeline
from ..preprocessing.clean import normalize_text

CONFIG = os.environ.get("BANKS_CONFIG", "config/banks.yaml")
RAW_DIR = os.environ.get("RAW_DIR", "data/raw")
# SQLite yolu için dosya (yalnızca DATABASE_URL boşken kullanılır — seçimi
# `src/db/factory.create_repository()` yapar).
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


def span_info(text: str, source_span: Optional[str], raw_value: Optional[str],
              span_start: Optional[int] = None,
              span_end: Optional[int] = None) -> dict[str, Any]:
    """Bir alanın metindeki yeri: **saklanan offset birincil**, yeniden hesaplama yedek.

    `span_start`/`span_end` DB'den gelir (`extracted_fields`). Kabul edilmesi
    için `text[span_start:span_end] == raw_value` eşitliğini geçmesi gerekir —
    saklanan offset körü körüne güvenilmez; bozuk bir kayıt arayüzde yanlış yeri
    boyamaktansa yedek yola düşmelidir.

    `window_start` / `window_end` / `span_ambiguous` her durumda `locate_span()`
    üzerinden hesaplanır: bunlar `source_span` PENCERESİNİN metindeki yeriyle
    ilgilidir, DB'de saklanmazlar ve arayüz bağlam göstermek için kullanır.

    Ölçülmüş fark (`data/demo.db`, 2204 alan): saklanan offsetlerin tamamı
    doğrulanıyor, yeniden hesaplama 73'ünde farklı (ve yanlış) yer gösteriyor —
    `str.find` ham değerin İLK geçtiği yeri bulur, çıkarımın geldiği yeri değil.
    """
    out = locate_span(text, source_span, raw_value)
    if (span_start is not None and span_end is not None
            and 0 <= span_start <= span_end <= len(text)
            and text[span_start:span_end] == (raw_value or "")):
        out.update(span_start=span_start, span_end=span_end,
                   span_scope="value", span_verified=True)
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

    # Depo seçimi TEK YERDE: DATABASE_URL varsa Postgres, yoksa SQLite.
    # `thread_safe=True` iki backend için de zorunlu — FastAPI `def` uçlarını
    # threadpool'da koşturur ve ne `sqlite3` ne `psycopg` bağlantısı bu kullanım
    # için güvenlidir (gerekçe: `src/db/base.ThreadSafeRepository`).
    repo = create_repository(database_path=DB_PATH, thread_safe=True)
    # Demo verisini doldur (CLAUDE.md §11 — önceden doldurulmuş DB).
    #
    # KOŞULLU olmak ZORUNDA. Eskiden koşulsuz koşuyordu; in-memory DB'de bu
    # zararsızdı (her açılış sıfırdan başlar) ama `DATABASE_PATH` bir DOSYAYI
    # gösterdiğinde her yeniden başlatma 3 kampanya daha ekliyordu:
    # 849 -> 852 -> 855 -> ... sonsuza dek. Şemada UNIQUE kısıtı yok, yani
    # çift kayıtlar sessizce birikir ve karşılaştırma tablosunda aynı banka
    # birden çok kez görünürdü.
    #
    # `counts()` sözleşme metodudur, bu yüzden koruma Postgres yolunda da
    # AYNEN çalışır — ve orada daha da kritiktir: kalıcı bir hacim (`pgdata`)
    # her `docker compose up`'ta aynı veriyi taşır.
    #
    # `scripts/build_demo_db.py` ile üretilmiş dolu bir DB verildiğinde
    # tohumlama tamamen atlanır ve 849 belgelik gerçek korpus korunur.
    if repo.counts().get("campaigns", 0) == 0:
        run_pipeline(repo, CONFIG, raw_dir=RAW_DIR, mode="fixture")
    llm = default_extractor()
    bot = Chatbot(repo, llm=llm)
    clf = default_classifier()

    # Tembel önbellekler — kampanya başına BİR kez; istek başına değil.
    # kampanya_id → `repo.campaign_text()` sonucu (metin + alanlar + offsetler)
    _view_cache: dict[int, Optional[dict]] = {}
    # kampanya_id → çelişki listesi (kural katmanı kampanya başına bir kez koşar)
    _contra_cache: dict[int, list[dict]] = {}

    # ----------------------------------------------------------------- #
    # Dahili yardımcılar
    # ----------------------------------------------------------------- #
    def _campaign_view(campaign_id: int) -> Optional[dict]:
        """Kampanyanın metni + alanları (offset'leriyle) — önbellekli.

        Tek kaynak `repo.campaign_text()`: `/campaigns/{id}/text` ve `/compare`
        AYNI metni ("span_reference": clean_text varsa o, yoksa raw_text)
        kullanmak zorunda. Ayrışsalardı `/compare`'in verdiği offset'ler
        arayüzün `/campaigns/{id}/text`'ten aldığı metinde başka bir yeri
        gösterirdi.
        """
        if campaign_id in _view_cache:
            return _view_cache[campaign_id]
        view = repo.campaign_text(campaign_id)
        _view_cache[campaign_id] = view
        return view

    def _field_rows(field: str) -> list[dict]:
        """Bir alanın tüm banka satırları — kaynak, güven ve katman bilgisiyle.

        `repo.query_fields()` `raw_value`, `extractor`, `confidence_source` ve
        saklanan span offset'lerini zaten döndürür; `canonical_value` da çözülmüş
        gelir. Eskiden burada ham SQL vardı — `?` yer tutucusuyla, yani Postgres
        yolunda çalışması imkânsızdı.
        """
        return repo.query_fields(field)

    def _campaign_contradictions(campaign_id: int, text: str, bank_slug: str,
                                 scraped_at: Optional[str] = None) -> list[dict]:
        """Bir kampanyanın iç çelişkileri.

        `scraped_at` verilirse zaman bağımlı kural da koşar: *"kampanya
        süresi dolmuş ama sayfa hâlâ yayında ve bunu söylemiyor"*. Korpusta
        doğrulanmış 6 çelişkinin **5'i** bu kuraldan geliyor; `as_of`
        geçilmediği için bu uç noktada tamamen kapalıydı.

        Duvar saati değil `scraped_at` kullanılır: iddia "biz topladığımızda
        süresi çoktan dolmuştu" biçiminde olmalı. Böylece sonuç zamanla
        sessizce değişmez ve demo yeniden-üretilebilir kalır (CLAUDE.md §11).
        """
        cached = _contra_cache.get(campaign_id)
        if cached is not None:
            return cached
        try:
            c = build_campaign(text, bank_slug=bank_slug)
            out = [{"kind": k.kind, "detail": k.detail, "fields": k.fields}
                   for k in detect_contradictions(c, as_of=scraped_at)]
        except Exception:  # pragma: no cover - çıkarım hatası UI'yı düşürmesin
            out = []
        _contra_cache[campaign_id] = out
        return out

    # ----------------------------------------------------------------- #
    # Uçlar
    # ----------------------------------------------------------------- #
    @app.get("/health")
    def health():
        """Sağlık + **hangi veri tabanına bağlıyız**.

        `backend` alanı bilinçli olarak açığa çıkarılır: `DATABASE_URL`
        verildiği hâlde sistemin SQLite'ta koşuyor olması (ya da tersi) tam
        olarak bu projede avlanan hata sınıfıdır ve dışarıdan görünmeden
        anlaşılamaz.
        """
        return {"status": "ok", "llm": llm.available, "backend": repo.backend}

    @app.get("/banks")
    def banks():
        return repo.all_banks()

    @app.get("/campaigns")
    def campaigns():
        return repo.all_campaigns()

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

        `span_reference` alanı offsetlerin HANGİ metinde ölçüldüğünü söyler
        (`clean_text` varsa o, yoksa `raw_text`); `text` de o metindir. İkisini
        karıştırmak offsetleri kaydırır, bu yüzden sözleşmede açıkça durur.
        """
        camp = _campaign_view(campaign_id)
        if camp is None:
            raise HTTPException(status_code=404,
                                detail=f"Kampanya bulunamadı: {campaign_id}")
        text = camp.get("text") or ""

        fields_out = []
        for d in camp.get("fields", []):
            fields_out.append({
                "field": d["field_name"],
                "label": FIELD_LABELS.get(d["field_name"], d["field_name"]),
                "raw_value": d["raw_value"],
                "canonical_value": d["canonical_value"],
                "confidence": d["confidence"],
                "confidence_source": d.get("confidence_source"),
                "extractor": d["extractor"],
                "source_span": d["source_span"],
                **span_info(text, d["source_span"], d["raw_value"],
                            d.get("span_start"), d.get("span_end")),
            })

        return {
            "campaign_id": campaign_id,
            "bank": camp["bank"],
            "bank_name": camp["bank_name"],
            "campaign_type": camp["campaign_type"],
            "source_url": camp["source_url"],
            "scraped_at": camp.get("scraped_at"),
            "text": text,
            "text_length": len(text),
            "span_reference": camp.get("span_reference"),
            "fields": fields_out,
            "contradictions": _campaign_contradictions(
                campaign_id, text, camp["bank"], camp.get("scraped_at")),
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
            # Metin `_campaign_view()`'dan gelir — `/campaigns/{id}/text` ile
            # AYNI metin. `query_fields()` bilerek `raw_text` döndürmez: aynı
            # belgenin tam metnini her alan satırında tekrarlamak, chatbot'un
            # text-to-SQL yolunu da (aynı metodu kullanır) gereksiz şişirirdi.
            view = _campaign_view(src["campaign_id"]) or {}
            text = view.get("text") or ""
            loc = span_info(text, src["source_span"], src["raw_value"],
                            src.get("span_start"), src.get("span_end"))
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
                "confidence_source": src.get("confidence_source"),
                "extractor": src["extractor"],
                **loc,
                # --- şeffaf skorlama ---
                "sort_key": x.sort_key,
                "rank": row_rank,
                # `scraped_at` artık GERÇEKTEN dolu geliyor. Eski ham SQL onu
                # SELECT etmiyordu, yani `as_of` her zaman None kalıyor ve
                # zaman bağımlı çelişki kuralı ("süresi dolmuş ama sayfa
                # yayında") bu uçta TAMAMEN KAPALIYDI: aynı kampanya
                # `/contradictions`'ta çelişkili, `/compare`'de temiz
                # görünüyordu. `query_fields()` alanı döndürdüğü için iki uç
                # artık aynı cevabı veriyor.
                "contradiction_count": len(_campaign_contradictions(
                    src["campaign_id"], text, src["bank"],
                    src.get("scraped_at"))),
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
            for k in _campaign_contradictions(camp["id"], text, camp["bank"],
                                              camp.get("scraped_at")):
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
