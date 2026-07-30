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

LIVE_SUBDIR = "live"
MANUAL_SUBDIR = "manual"


def utc_now_iso() -> str:
    """Provenance için ISO-8601 UTC damgası."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def content_hash(content: str | bytes) -> str:
    """İçeriğin sha256 özeti (yeniden-üretilebilirlik + tekilleştirme)."""
    data = content.encode("utf-8") if isinstance(content, str) else content
    return hashlib.sha256(data).hexdigest()


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

    def provenance(self) -> dict[str, Any]:
        """`.meta.json` olarak yazılacak provenance sözlüğü."""
        return {
            "bank_slug": self.bank_slug,
            "source_url": self.source_url,
            "scraped_at": self.scraped_at,
            "content_hash": self.content_hash,
            "collection_method": self.collection_method,
            "title": self.title,
            "http_status": self.http_status,
            "raw_bytes": len(self.raw_html.encode("utf-8")) if self.raw_html else None,
            "text_chars": len(self.clean_text),
        }


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
    """
    try:
        from bs4 import BeautifulSoup  # type: ignore
    except ModuleNotFoundError:
        return normalize_text(html)

    text = _soup_text(BeautifulSoup(html, "html.parser"), aggressive=True)
    if len(text) >= MIN_TEXT_CHARS:
        return text
    return _soup_text(BeautifulSoup(html, "html.parser"), aggressive=False)


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
                 report: Optional[dict[str, Any]] = None) -> list[RawDoc]:
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

    found = discover(bank, guarded_fetch, max_docs=max_docs)
    diag["discovered"] = len(found.urls)
    diag["from_sitemap"] = found.from_sitemap
    diag["from_listing"] = found.from_listing
    diag["notes"].extend(found.notes)

    docs: list[RawDoc] = []
    seen_hashes: set[str] = set()
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
        if digest in seen_hashes:
            continue  # aynı içerik farklı URL (kanonik olmayan yollar)
        text = _extract_main_text(html)
        if len(text) < 200:
            diag["notes"].append(f"cok kisa icerik atlandi: {url} ({len(text)} krkt)")
            continue
        seen_hashes.add(digest)
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
        ))
    if owns_bundle:
        bundle.close()
    return docs


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
    "RawDoc", "collect", "collect_live", "collect_from_fixtures", "save_docs",
    "ensure_manual_dirs", "content_hash", "utc_now_iso", "slugify", "url_to_slug",
    "METHOD_LIVE", "METHOD_BROWSER", "METHOD_MANUAL", "METHOD_FIXTURE",
]
