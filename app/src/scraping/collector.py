"""Scraping collector — config-driven, etik, provenance'lı.

İlgili: ../../decisions/python-tabanli-veri-toplama.md
        ../../concepts/web-scraping.md, CLAUDE.md §14

Üç mod:
- fixture (offline): data/raw/<slug>/*.html|*.txt dosyalarından okur. Test/demo.
- static: requests + BeautifulSoup (bağımlılık varsa).
- js: Playwright (bağımlılık varsa).

`scrape_mode` alanı artık GERÇEKTEN dispatch edilir (bkz. `fetcher.FetcherBundle`);
önceden ayrıştırılıp yok sayılıyordu, bu yüzden js bankaları sessizce boş dönüyordu.

Her belge zorunlu provenance taşır: `source_url`, `scraped_at` (ISO-8601),
`content_hash` (sha256), `collection_method` (live | browser | manual | fixture).
Diske yazarken içeriğin yanına `.meta.json` konur.

Bağımlılık yoksa otomatik fixture moduna düşer — pipeline offline koşar.
"""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from ..preprocessing.clean import normalize_text
from .config import BankConfig
from .discover import discover
from .fetcher import FetcherBundle, RateLimiter
from .robots import RobotsCache

# Toplama yöntemleri (provenance)
METHOD_LIVE = "live"        # requests + bs4
METHOD_BROWSER = "browser"  # Playwright
METHOD_MANUAL = "manual"    # elle indirilip data/raw/<slug>/manual/ altına konmuş
METHOD_FIXTURE = "fixture"  # repodaki sentetik örnek
METHOD_PDF = "pdf"          # PDF belge (ücret tarifesi / ürün bilgi formu)

LIVE_SUBDIR = "live"
MANUAL_SUBDIR = "manual"
# 2. toplama turu: ürün sayfaları kampanyalarla karışmasın diye ayrı klasör
PRODUCTS_SUBDIR = "products"
# 3. tur: SÜRESİ DOLMUŞ kampanyalar. Aktif kampanyalarla aynı klasöre KONMAZ —
# karışırsa süresi geçmiş kampanya aktif sanılır (CLAUDE.md §17 adil kıyas).
ARCHIVE_SUBDIR = "archive"
# 4. tur: PDF belgeler (ücret tarifesi, ürün bilgi formu, sözleşme)
DOCS_SUBDIR = "docs"

# Kampanya geçerlilik durumu (provenance) — arşiv turu bunu `expired` yazar.
STATUS_ACTIVE = "active"
STATUS_EXPIRED = "expired"


def utc_now_iso() -> str:
    """Provenance için ISO-8601 UTC damgası."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def content_hash(content: str | bytes) -> str:
    """İçeriğin sha256 özeti (yeniden-üretilebilirlik + provenance)."""
    data = content.encode("utf-8") if isinstance(content, str) else content
    return hashlib.sha256(data).hexdigest()


def _text_key(text: str) -> str:
    """Tekilleştirme anahtarı: temiz metnin boşluk-normalize sha256'sı.

    Ham HTML hash'i tekilleştirme için YETERSİZDİR (bkz. `collect_live` içindeki
    gerekçe): analitik/oturum gürültüsü aynı sayfayı farklı gösterir.
    """
    return hashlib.sha256(re.sub(r"\s+", " ", text).strip().encode("utf-8")).hexdigest()


@dataclass
class RawDoc:
    """Ham belge + zorunlu provenance alanları."""

    bank_slug: str
    source_url: Optional[str]
    clean_text: str
    scraped_at: Optional[str] = None
    content_hash: Optional[str] = None
    collection_method: str = METHOD_FIXTURE
    title: Optional[str] = None
    http_status: Optional[int] = None
    raw_html: Optional[str] = field(default=None, repr=False)
    # Kampanya geçerlilik durumu: arşiv turunda `expired`, aktif turda `active`.
    # Ürün/belge turlarında None (kampanya değil, süre kavramı yok).
    campaign_status: Optional[str] = None
    # PDF belgeler için: ham baytlar + sayfa sayısı (metin çıkarımı tanılaması)
    raw_bytes_blob: Optional[bytes] = field(default=None, repr=False)
    pdf_pages: Optional[int] = None
    extraction_note: Optional[str] = None

    def provenance(self) -> dict[str, Any]:
        """`.meta.json` olarak yazılacak provenance sözlüğü."""
        raw_len = None
        if self.raw_html:
            raw_len = len(self.raw_html.encode("utf-8"))
        elif self.raw_bytes_blob:
            raw_len = len(self.raw_bytes_blob)
        out: dict[str, Any] = {
            "bank_slug": self.bank_slug,
            "source_url": self.source_url,
            "scraped_at": self.scraped_at,
            "content_hash": self.content_hash,
            "collection_method": self.collection_method,
            "title": self.title,
            "http_status": self.http_status,
            "raw_bytes": raw_len,
            "text_chars": len(self.clean_text),
        }
        # Yalnızca dolu alanlar yazılır — mevcut 847 sidecar'ın şeması bozulmaz.
        if self.campaign_status is not None:
            out["campaign_status"] = self.campaign_status
        if self.pdf_pages is not None:
            out["pdf_pages"] = self.pdf_pages
        if self.extraction_note:
            out["extraction_note"] = self.extraction_note
        return out


def _extract_title(html: str) -> Optional[str]:
    m = re.search(r"<title[^>]*>(.*?)</title>", html, re.I | re.S)
    if not m:
        return None
    return re.sub(r"\s+", " ", m.group(1)).strip()[:200] or None


# Her zaman atılan (içerik taşımayan) etiketler
_ALWAYS_DROP = ("script", "style", "noscript", "svg", "iframe", "template")
# Her iki geçişte de atılan sayfa gürültüsü (menü/altbilgi — asla kampanya metni değil)
_CHROME_DROP = ("header", "footer", "nav", "aside")
# YALNIZCA agresif geçişte atılır: ASP.NET WebForms tüm sayfayı <form> ile sarar,
# bu yüzden temkinli geçişte <form> korunur (bkz. _extract_main_text).
_FORM_DROP = ("form",)

# Anlamlı içerik eşiği: bunun altındaysa daha temkinli geçiş denenir
MIN_TEXT_CHARS = 200

# `<form>` atıldığında metnin kaç katı kaybolursa "form içerikti" sayılır.
#
# NEDEN MUTLAK EŞİK YETMİYOR (2026-08-04 ölçümü): Ziraat Bankası ürün
# sayfalarında `<main>`/`<article>` YOK ve içerik `<form>` içine sarılmış.
# Agresif geçiş 1503 karakter döndürüyordu — çerez bandı + promo bloğu, yani
# saf çerçeve. 1503 > MIN_TEXT_CHARS olduğu için koruma HİÇ ateşlenmiyor ve
# belge "başarıyla" yazılıyordu. Üstelik her sayfa için AYNI 1503 karakter
# çıktığından metin tekilleştirmesi 45 sayfayı 2 belgeye indiriyordu.
# Temkinli geçiş aynı sayfada 4277 karakter ve gerçek ürün bilgisini
# ("36 aya kadar", "faiz oranı", hesaplama aracı) veriyor → oran 2,8x.
#
# Eşik 2.0 seçildi (ölçülen 2,8'in altında, normal sayfaların agresif/temkinli
# oranı ~1,2-1,5 bandında kaldığı için güvenli). Koruma yalnızca `<form>`
# varken çalışır: dokümante edilmiş ASP.NET WebForms başarısızlık kipine
# bağlı kalsın, her sayfada çerçeve metnini içeri almasın.
FORM_CONTENT_RATIO = 2.0

# Belgenin KABUL eşiği — `MIN_TEXT_CHARS`'tan ayrı tutulur.
# MIN_TEXT_CHARS hangi ÇIKARIM GEÇİŞİNİN kullanılacağına karar verir;
# bu sabit belgenin korpusa GİRİP GİRMEYECEĞİNE karar verir. İkisi aynı
# sayı olsa bile aynı şey değil; tek sabite bağlamak birini değiştirince
# diğerini sessizce bozar.
MIN_DOC_CHARS = 200

# "İçerik yok" diyen sayfaların işaretçileri.
#
# NEDEN UZUNLUK TEK BAŞINA YETMİYOR (2026-08-04 ölçümü): İş Bankası'nın yanlış
# giriş noktasından gelen 30 belgesi "Kampanya bulunamadı." diyen 202-262
# karakterlik boş kabuklardı — MIN_DOC_CHARS'ın hemen ÜSTÜNDE. Eşiği yükseltmek
# çözüm değil: geçerli ama kısa bir VakıfBank ürün listesi 294 karakter ve
# korunmalı. Bu yüzden işaretçi + kısalık BİRLİKTE aranıyor; uzun bir SSS
# sayfasında "bulunamadı" geçmesi belgeyi düşürmez.
_EMPTY_RESULT_MARKERS = ("bulunamadı", "bulunamadi", "sonuç yok", "kayıt yok")
EMPTY_RESULT_MAX_CHARS = 600


def _is_empty_result_page(text: str) -> bool:
    """Sayfa "içerik yok" mu diyor? (işaretçi VE kısalık birlikte)"""
    if len(text) > EMPTY_RESULT_MAX_CHARS:
        return False
    low = text.casefold()
    return any(m in low for m in _EMPTY_RESULT_MARKERS)


def _extract_main_text(html: str) -> str:
    """Ham HTML'den temiz metin — iki geçişli.

    NOT: trafilatura KULLANILMIYOR — lisansı doğrulanmadı (docs/model-license-audit.md).

    1. geçiş (agresif): script/style + header/footer/nav/form atılır, `<main>`
       veya `<article>` tercih edilir.
    2. geçiş (temkinli): 1. geçiş boş/çok kısa döndüyse yalnızca script/style
       atılıp tüm gövde alınır.

    2. geçiş şart: ASP.NET WebForms siteleri (ör. Türkiye Finans) TÜM sayfayı
       `<form runat="server">` içine sarar; agresif geçiş sayfayı komple siler
       ve belge sessizce kaybolurdu.

    İki tetikleyici var, çünkü tek başına mutlak eşik yetmiyor:
      a) agresif sonuç MIN_TEXT_CHARS altındaysa (sayfa komple silinmiş),
      b) sayfada `<form>` varken temkinli geçiş FORM_CONTENT_RATIO katı fazla
         metin veriyorsa (form İÇERİKTİ, çerçeve değil — bkz. sabitin notu).
    """
    try:
        from bs4 import BeautifulSoup  # type: ignore
    except ModuleNotFoundError:
        return normalize_text(html)

    text = _soup_text(BeautifulSoup(html, "html.parser"), aggressive=True)
    if len(text) < MIN_TEXT_CHARS:
        return _soup_text(BeautifulSoup(html, "html.parser"), aggressive=False)

    # (b) — yalnız `<form>` varsa ikinci geçişi ölçüp karşılaştır.
    if not BeautifulSoup(html, "html.parser").find("form"):
        return text
    lenient = _soup_text(BeautifulSoup(html, "html.parser"), aggressive=False)
    if len(lenient) >= len(text) * FORM_CONTENT_RATIO:
        return lenient
    return text


def _soup_text(soup, *, aggressive: bool) -> str:
    drop = _ALWAYS_DROP + _CHROME_DROP + (_FORM_DROP if aggressive else ())
    for tag in soup(list(drop)):
        tag.decompose()
    root = (soup.find("main") or soup.find("article")) if aggressive else None
    root = root or soup.body or soup
    return normalize_text(root.get_text(separator="\n"))


def slugify(value: str, fallback: str = "belge") -> str:
    """URL/başlıktan dosya adı üretir (TR karakterler sadeleştirilir)."""
    value = value.replace("ı", "i").replace("İ", "i").replace("ş", "s") \
                 .replace("Ş", "s").replace("ğ", "g").replace("Ğ", "g") \
                 .replace("ç", "c").replace("Ç", "c").replace("ö", "o") \
                 .replace("Ö", "o").replace("ü", "u").replace("Ü", "u")
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    value = re.sub(r"[^a-zA-Z0-9]+", "-", value).strip("-").lower()
    return (value or fallback)[:80]


def url_to_slug(url: str) -> str:
    """URL'in son anlamlı yol parçasından dosya adı üretir."""
    from urllib.parse import urlsplit

    parts = [p for p in urlsplit(url).path.split("/") if p and p.lower() != "sayfalar"]
    tail = parts[-1] if parts else urlsplit(url).netloc
    tail = re.sub(r"\.(aspx|html?|php)$", "", tail, flags=re.I)
    if len(parts) > 1:
        tail = f"{parts[-2]}-{tail}"
    return slugify(tail, fallback="anasayfa")


# --------------------------------------------------------------------------- #
# Fixture / manuel toplama
# --------------------------------------------------------------------------- #

def collect_from_fixtures(bank: BankConfig, raw_dir: str | Path,
                          scraped_at: Optional[str] = None,
                          recursive: bool = False) -> list[RawDoc]:
    """data/raw/<slug>/ altındaki .html/.txt dosyalarını okur (offline).

    `recursive=True` ise `live/` ve `manual/` alt klasörleri de taranır; varsayılan
    False, çünkü demo pipeline'ı yalnızca repodaki sentetik örnekleri bekler.
    """
    base = Path(raw_dir) / bank.slug
    docs: list[RawDoc] = []
    if not base.is_dir():
        return docs
    files = sorted(base.rglob("*")) if recursive else sorted(base.iterdir())
    for f in files:
        if not f.is_file() or f.suffix.lower() not in (".html", ".htm", ".txt"):
            continue
        content = f.read_text(encoding="utf-8", errors="ignore")
        text = _extract_main_text(content) if f.suffix.lower() != ".txt" \
            else normalize_text(content)
        if not text:
            continue
        meta = _read_sidecar(f)
        docs.append(RawDoc(
            bank_slug=bank.slug,
            source_url=meta.get("source_url") or f"file://{f}",
            clean_text=text,
            scraped_at=meta.get("scraped_at") or scraped_at,
            content_hash=meta.get("content_hash") or content_hash(content),
            collection_method=meta.get("collection_method") or _method_for_path(f),
            title=meta.get("title"),
        ))
    return docs


def _method_for_path(path: Path) -> str:
    parents = {p.name for p in path.parents}
    if MANUAL_SUBDIR in parents:
        return METHOD_MANUAL
    if LIVE_SUBDIR in parents:
        return METHOD_LIVE
    return METHOD_FIXTURE


def _read_sidecar(path: Path) -> dict[str, Any]:
    meta_path = path.with_suffix(path.suffix + ".meta.json")
    if not meta_path.is_file():
        return {}
    try:
        return json.loads(meta_path.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return {}


# --------------------------------------------------------------------------- #
# Canlı toplama
# --------------------------------------------------------------------------- #

def collect_live(bank: BankConfig, scraped_at: Optional[str] = None,
                 delay_s: float = 3.0, *,
                 bundle: Optional[FetcherBundle] = None,
                 robots: Optional[RobotsCache] = None,
                 max_docs: int = 40,
                 report: Optional[dict[str, Any]] = None,
                 discover_fn: Optional[Any] = None,
                 campaign_status: Optional[str] = None) -> list[RawDoc]:
    """Canlı toplama — `scrape_mode` dispatch'li, robots.txt uyumlu.

    Bağımlılık yoksa boş liste döner (çağıran fixture'a düşer). `report` verilirse
    banka bazlı tanılama (engellenen URL'ler, robots durumu) doldurulur.
    """
    owns_bundle = bundle is None
    bundle = bundle or _default_bundle(delay_s)
    robots = robots if robots is not None else RobotsCache()
    scraped_at = scraped_at or utc_now_iso()
    diag: dict[str, Any] = report if report is not None else {}
    diag.setdefault("blocked", [])
    diag.setdefault("notes", [])

    fetcher = bundle.for_mode(bank.scrape_mode)
    if not fetcher.available:
        reason = getattr(fetcher, "unavailable_reason", None) or \
            f"'{bank.scrape_mode}' modu icin bagimlilik yok"
        diag["notes"].append(f"{bank.slug}: {reason} — atlandi")
        diag["skipped_reason"] = reason
        if owns_bundle:
            bundle.close()
        return []

    def guarded_fetch(url: str):
        allowed, reason = robots.allows(url)
        if not allowed:
            diag["blocked"].append({"url": url, "reason": "robots disallow",
                                    "detail": reason})
            from .fetcher import FetchResult

            return FetchResult(url, error="robots disallow", method=fetcher.method)
        return fetcher.fetch(url)

    # SAYFALAMA: yalnızca tarayıcı çekicisinde `fetch_all_pages` vardır
    # (`StaticFetcher`'da yok — `hasattr` ile kontrol edilir). Liste sayfası
    # slick/swiper karuseliyle sayfalandığında sayfa değişse de URL DEĞİŞMEZ
    # (Albaraka arşivi, 2026-08-04 tarayıcıyla ölçüldü); tek yol tıklamaktır.
    # Metot yoksa keşif eski tek-sayfa davranışını korur.
    #
    # robots.txt kontrolü BURADA da yapılır: `fetch_all_pages` guarded_fetch'i
    # atlar, kontrol atlanırsa yasaklı liste sayfası gezilirdi (CLAUDE.md §14).
    fetch_pages: Optional[Any] = None
    if hasattr(fetcher, "fetch_all_pages"):
        def _fetch_all_pages(url: str) -> list[str]:
            allowed, reason = robots.allows(url)
            if not allowed:
                diag["blocked"].append({"url": url, "reason": "robots disallow",
                                        "detail": reason})
                return []
            return fetcher.fetch_all_pages(url)

        fetch_pages = _fetch_all_pages

    # Keşif fonksiyonu enjekte edilebilir: kampanya turu `discover`,
    # ürün turu `discover_products` kullanır. Getirme/robots/tekilleştirme
    # mantığı ikisinde de aynıdır, yalnızca URL kümesi farklıdır.
    found = (discover_fn or discover)(bank, guarded_fetch, max_docs=max_docs,
                                      fetch_pages=fetch_pages)
    diag["discovered"] = len(found.urls)
    diag["from_sitemap"] = found.from_sitemap
    diag["from_listing"] = found.from_listing
    diag["notes"].extend(found.notes)

    docs: list[RawDoc] = []
    seen_texts: set[str] = set()
    for url in found.urls:
        res = guarded_fetch(url)
        if not res.ok:
            if res.error != "robots disallow":
                diag["blocked"].append({
                    "url": url,
                    "reason": f"HTTP {res.status}" if res.status else "baglanti hatasi",
                    "detail": res.error or "",
                })
            continue
        html = res.html or ""
        digest = content_hash(html)
        text = _extract_main_text(html)
        if len(text) < MIN_DOC_CHARS:
            diag["notes"].append(f"cok kisa icerik atlandi: {url} ({len(text)} krkt)")
            continue
        if _is_empty_result_page(text):
            # "Kampanya bulunamadı." diyen kabuk — korpusa girerse etiketleyiciye
            # ve eğitime gürültü olarak taşınır. Sessizce atlanmaz, rapora yazılır.
            diag["notes"].append(
                f"bos sonuc sayfasi atlandi: {url} ({len(text)} krkt)")
            continue
        # TEKİLLEŞTİRME TEMİZ METİN ÜZERİNDEN yapılır, ham HTML üzerinden DEĞİL.
        #
        # Ham HTML'de analitik kimlikleri, oturum/CSRF simgeleri ve zaman
        # damgaları her istekte değişir; bu yüzden AYNI sayfa iki kez çekildiğinde
        # hash'ler farklı çıkıyor ve tekilleştirme kaçırıyordu.
        #
        # Ölçüm (2026-08-03, 1491 belgelik korpus): 98 mükerrer metin grubu,
        # 215 dosya (~%14). Tipik sebep, iki farklı keşif URL'inin AYNI kanonik
        # sayfaya yönlenmesi (`final_url` aynı, discovery iki kez ekledi).
        # Mükerrer belgeler anotasyon bütçesini boşa harcar, değerlendirme
        # metriklerini çifte sayar ve çelişki sayısını şişirir (TOGG çelişkisi
        # 2 gerçek bulgu yerine 4 raporlanıyordu).
        #
        # `content_hash` provenance alanı DEĞİŞMEDİ: o, ham baytların özetidir
        # (yeniden-üretilebilirlik) ve belgelenmiş anlamı korunur.
        text_key = _text_key(text)
        if text_key in seen_texts:
            diag["notes"].append(f"mukerrer icerik atlandi: {url}")
            continue
        seen_texts.add(text_key)
        docs.append(RawDoc(
            bank_slug=bank.slug,
            source_url=res.final_url or url,
            clean_text=text,
            scraped_at=utc_now_iso(),
            content_hash=digest,
            collection_method=fetcher.method,
            title=_extract_title(html),
            http_status=res.status,
            raw_html=html,
            campaign_status=campaign_status,
        ))
    if owns_bundle:
        bundle.close()
    return docs


def collect_documents(bank: BankConfig, *, bundle: Optional[FetcherBundle] = None,
                      robots: Optional[RobotsCache] = None,
                      max_docs: int = 40,
                      report: Optional[dict[str, Any]] = None,
                      delay_s: float = 3.0) -> list[RawDoc]:
    """PDF belge turu — ücret tarifeleri + ürün bilgi formları (4. tur).

    Keşif HTML sayfalarından yapılır (`document_paths`), indirme ikili modda
    (`StaticFetcher.fetch_bytes`), metin `pdf.extract_pdf_text` ile çıkarılır.

    PDF'ler her zaman `static` çekiciyle indirilir — banka `scrape_mode: js` olsa
    bile PDF indirmek için tarayıcı gerekmez ve tarayıcı üzerinden ikili indirme
    güvenilmezdir.
    """
    from .discover import discover_documents
    from .pdf import extract_pdf_text, looks_like_pdf

    owns_bundle = bundle is None
    bundle = bundle or _default_bundle(delay_s)
    robots = robots if robots is not None else RobotsCache()
    diag: dict[str, Any] = report if report is not None else {}
    diag.setdefault("blocked", [])
    diag.setdefault("notes", [])

    fetcher = bundle.static
    if not fetcher.available:
        diag["notes"].append(f"{bank.slug}: requests yok — belge turu atlandi")
        if owns_bundle:
            bundle.close()
        return []

    def guarded_fetch(url: str):
        allowed, reason = robots.allows(url)
        if not allowed:
            diag["blocked"].append({"url": url, "reason": "robots disallow",
                                    "detail": reason})
            from .fetcher import FetchResult

            return FetchResult(url, error="robots disallow", method=fetcher.method)
        return fetcher.fetch(url)

    found = discover_documents(bank, guarded_fetch, max_docs=max_docs)
    diag["doc_discovered"] = len(found.urls)
    diag["notes"].extend(found.notes)

    docs: list[RawDoc] = []
    seen_hashes: set[str] = set()
    for url in found.urls:
        allowed, reason = robots.allows(url)
        if not allowed:
            diag["blocked"].append({"url": url, "reason": "robots disallow",
                                    "detail": reason})
            continue
        res = fetcher.fetch_bytes(url)
        if not res.ok_bytes:
            diag["blocked"].append({
                "url": url,
                "reason": f"HTTP {res.status}" if res.status else "baglanti hatasi",
                "detail": res.error or "",
            })
            continue
        blob = res.content or b""
        if not looks_like_pdf(blob, res.content_type or ""):
            diag["notes"].append(
                f"PDF degil, atlandi: {url} (content-type={res.content_type})")
            continue
        digest = content_hash(blob)
        if digest in seen_hashes:
            continue  # aynı PDF farklı bağlantıdan (bireysel/ticari tekrarları)
        parsed = extract_pdf_text(blob)
        if not parsed.text:
            diag["blocked"].append({"url": url, "reason": "PDF metni cikarilamadi",
                                    "detail": parsed.error or ""})
            continue
        seen_hashes.add(digest)
        docs.append(RawDoc(
            bank_slug=bank.slug,
            source_url=res.final_url or url,
            clean_text=parsed.text,
            scraped_at=utc_now_iso(),
            content_hash=digest,
            collection_method=METHOD_PDF,
            title=_title_from_pdf_url(url),
            http_status=res.status,
            raw_bytes_blob=blob,
            pdf_pages=parsed.pages,
            extraction_note=parsed.error,
        ))
    if owns_bundle:
        bundle.close()
    return docs


def _title_from_pdf_url(url: str) -> str:
    """PDF'in dosya adından okunabilir başlık üretir (PDF'te <title> yok)."""
    from urllib.parse import unquote, urlsplit

    name = unquote(urlsplit(url).path.rsplit("/", 1)[-1])
    name = re.sub(r"\.pdf$", "", name, flags=re.I)
    return re.sub(r"[-_]+", " ", name).strip()[:200] or "belge"


def _default_bundle(delay_s: float) -> FetcherBundle:
    from .fetcher import BrowserFetcher, StaticFetcher

    limiter = RateLimiter(delay_s)
    return FetcherBundle(static=StaticFetcher(limiter=limiter),
                         browser=BrowserFetcher(limiter=limiter))


# --------------------------------------------------------------------------- #
# Diske yazma (provenance sidecar'ı ile)
# --------------------------------------------------------------------------- #

def save_docs(docs: list[RawDoc], raw_dir: str | Path,
              subdir: str = LIVE_SUBDIR) -> list[Path]:
    """Belgeleri data/raw/<slug>/<subdir>/ altına yazar + `.meta.json` koyar."""
    written: list[Path] = []
    used: set[str] = set()
    for doc in docs:
        target_dir = Path(raw_dir) / doc.bank_slug / subdir
        target_dir.mkdir(parents=True, exist_ok=True)
        stem = url_to_slug(doc.source_url or "") or slugify(doc.title or "belge")
        candidate, n = stem, 2
        while candidate in used:
            candidate, n = f"{stem}-{n}", n + 1
        used.add(candidate)

        if doc.raw_html:
            html_path = target_dir / f"{candidate}.html"
            html_path.write_text(doc.raw_html, encoding="utf-8")
            written.append(html_path)
        elif doc.raw_bytes_blob:
            # PDF orijinali provenance gereği saklanır (CLAUDE.md §14): metin
            # çıkarımı iyileşirse yeniden-çıkarım için kaynak gerekir.
            pdf_path = target_dir / f"{candidate}.pdf"
            pdf_path.write_bytes(doc.raw_bytes_blob)
            written.append(pdf_path)
        txt_path = target_dir / f"{candidate}.txt"
        txt_path.write_text(doc.clean_text, encoding="utf-8")
        written.append(txt_path)
        meta_path = target_dir / f"{candidate}.txt.meta.json"
        meta_path.write_text(
            json.dumps(doc.provenance(), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8")
    return written


def ensure_manual_dirs(banks: list[BankConfig], raw_dir: str | Path) -> list[Path]:
    """Her banka için `data/raw/<slug>/manual/` iskeletini hazırlar.

    Engellenen siteler elle indirilip buraya konur; `.gitkeep` klasörü kalıcı yapar.
    """
    made: list[Path] = []
    for bank in banks:
        d = Path(raw_dir) / bank.slug / MANUAL_SUBDIR
        d.mkdir(parents=True, exist_ok=True)
        keep = d / ".gitkeep"
        if not keep.exists():
            keep.write_text("", encoding="utf-8")
        made.append(d)
    return made


# --------------------------------------------------------------------------- #
# Giriş noktası
# --------------------------------------------------------------------------- #

def collect(bank: BankConfig, raw_dir: str | Path = "data/raw",
            mode: str = "auto", scraped_at: Optional[str] = None,
            **kwargs: Any) -> list[RawDoc]:
    """Toplama girişi. mode='auto' → önce canlı dener, başarısızsa fixture."""
    if mode == "fixture":
        return collect_from_fixtures(bank, raw_dir, scraped_at,
                                     recursive=bool(kwargs.get("recursive")))
    if mode == "live":
        return collect_live(bank, scraped_at, **kwargs)
    docs = collect_live(bank, scraped_at, **kwargs)
    return docs or collect_from_fixtures(bank, raw_dir, scraped_at,
                                         recursive=bool(kwargs.get("recursive")))


__all__ = [
    "RawDoc", "collect", "collect_live", "collect_documents",
    "collect_from_fixtures", "save_docs",
    "ensure_manual_dirs", "content_hash", "utc_now_iso", "slugify", "url_to_slug",
    "METHOD_LIVE", "METHOD_BROWSER", "METHOD_MANUAL", "METHOD_FIXTURE", "METHOD_PDF",
    "LIVE_SUBDIR", "MANUAL_SUBDIR", "PRODUCTS_SUBDIR", "ARCHIVE_SUBDIR", "DOCS_SUBDIR",
    "STATUS_ACTIVE", "STATUS_EXPIRED",
]
