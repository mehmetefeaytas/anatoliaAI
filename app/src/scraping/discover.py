"""Kampanya URL keşfi — iki aşamalı gezinme (liste sayfası → detay sayfaları).

İlgili: CLAUDE.md §14, ../../decisions/python-tabanli-veri-toplama.md

İki tamamlayıcı kaynak:
1. **sitemap.xml** — hızlı ve eksiksiz; `<sitemapindex>` özyinelemeli çözülür.
2. **liste sayfası** — `banks.yaml`'daki `campaign_paths` başlangıç noktasıdır;
   sayfadaki aynı-alan bağlantıları toplanıp `detail_patterns` ile süzülür.

Bağlantı çıkarımı bs4 varsa onunla, yoksa regex ile yapılır (saf stdlib fallback).

**Sayfalama (pagination):** liste sayfası birden fazla sayfaya bölünmüş olabilir.
Çağıran taraf isteğe bağlı `fetch_pages(url) -> list[str]` geçerse (tarayıcı
çekicisinin `BrowserFetcher.fetch_all_pages` metodu) liste sayfasının TÜM
sayfalarının HTML'i taranır. Geçilmezse tek sayfalık eski davranış korunur.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Callable, Iterable, Optional
from urllib.parse import urljoin, urlsplit, urlunsplit

# Kampanya/ürün sayfası olma ihtimali yüksek yol parçaları (banka özelinde
# banks.yaml `detail_patterns` ile ezilir).
DEFAULT_DETAIL_PATTERNS = ("kampanya", "firsat", "avantaj", "finansman")

# Ürün sayfası olma ihtimali yüksek yol parçaları (2. toplama turu).
# Ölçüm: kampanya sayfalarının yalnızca %3,8'inde kâr payı oranı vardı; vade,
# tahsis ücreti ve oran bilgisi ürün sayfalarında yayımlanıyor.
DEFAULT_PRODUCT_PATTERNS = (
    # finansman ürünleri (kâr payı + vade + tahsis ücreti)
    r"finansman", r"kredi", r"leasing",
    # yatırım / birikim ürünleri (getiri, kâr paylaşım oranı)
    r"hesap", r"katilma", r"yatirim", r"birikim", r"fon", r"sukuk",
    r"kira-sertifikasi", r"altin", r"maden", r"doviz",
    # kart ürünleri
    r"kart",
    # ücret tarifesi / bilgilendirme (tahsis ücreti ve masraf oranları tablosu)
    r"urun-ve-hizmet-ucret", r"urun-hizmet", r"ucretler", r"tarife",
    r"bilgilendirme-form", r"sozlesme",
    # oran sayfaları — en yüksek değerli sınıf
    r"kar-payi", r"kar-paylasim", r"oranlar",
)

# Ürün keşfinde ayrıca elenenler: kampanya belgeleri `live/` altında zaten var
# (çift toplamayı önler), blog/haber/kurumsal içerik ise ürün değildir.
PRODUCT_EXCLUDE_PATTERNS = (
    r"/kampanya", r"kampanyalar", r"kampanyasi", r"/blog/", r"/haberler",
    r"/duyuru", r"/basin", r"/fotograf-galerisi", r"/yatirimci-iliskileri",
    r"/hakkimizda", r"/finansal-kilavuz", r"/bizi-taniyin", r"/insan-kaynaklari",
    r"/kvkk", r"/cerez", r"/site-haritasi", r"/subelerimiz", r"/iletisim",
)

# SÜRESİ DOLMUŞ kampanya yolları (arşiv / "biten kampanyalar").
# ÇİFT GÖREVLİ:
#  1. `discover_archive` için include deseni,
#  2. `discover` (aktif kampanya turu) için EXCLUDE deseni.
# (2) olmadan arşiv sayfaları `live/` altına düşer ve süresi dolmuş kampanya
# AKTİF sanılır — karşılaştırma motorunu sessizce yanıltır (CLAUDE.md §17).
DEFAULT_ARCHIVE_PATTERNS = (
    r"kampanya-arsivi", r"kampanya-arşivi", r"biten-kampanya", r"gecmis-kampanya",
    r"sona-eren", r"arsiv-kampanya",
)

# Belge (PDF) desenleri — ücret tarifeleri + ürün bilgi formları.
DEFAULT_DOCUMENT_PATTERNS = (r"\.pdf(\?|$)",)

# Asla kampanya belgesi olmayan yollar.
DEFAULT_EXCLUDE_PATTERNS = (
    r"/en/", r"/ar/", r"/english", r"\.pdf$", r"\.jpg$", r"\.png$", r"\.svg$",
    r"\.zip$", r"\.doc", r"\.xls", r"/arama", r"/search", r"javascript:", r"^mailto:",
    r"^tel:", r"/gayrimenkuller/", r"/menkuller", r"/teklif-formu/", r"/basvuru",
    r"/sitemap", r"/rss", r"/login", r"/giris",
)

# Liste sayfasının tüm sayfalarını döndüren çağrılabilir (opsiyonel).
# Gerçek uygulaması: `BrowserFetcher.fetch_all_pages`.
FetchPages = Callable[[str], list[str]]

_HREF_RE = re.compile(r"""<a\b[^>]*?href\s*=\s*["']([^"'>]+)["']""", re.I)
_LOC_RE = re.compile(r"<loc>\s*(?:<!\[CDATA\[)?\s*(.*?)\s*(?:\]\]>)?\s*</loc>", re.I | re.S)
_SITEMAPINDEX_RE = re.compile(r"<sitemapindex", re.I)


@dataclass
class DiscoveryResult:
    """Bir banka için keşif çıktısı + hangi kaynaktan geldiği."""

    urls: list[str] = field(default_factory=list)
    from_sitemap: int = 0
    from_listing: int = 0
    notes: list[str] = field(default_factory=list)


def normalize_url(url: str) -> str:
    """Fragment'i atar, sondaki '/' farkını tekilleştirir."""
    parts = urlsplit(url)
    path = parts.path
    if len(path) > 1 and path.endswith("/"):
        path = path[:-1]
    return urlunsplit((parts.scheme, parts.netloc, path, parts.query, ""))


def _host(url: str) -> str:
    """Alan adı — PORTSUZ ve www. eki atılmış.

    `netloc` KULLANILMAZ: portu içerir. Ziraat Bankası'nın site haritası
    URL'leri varsayılan portu açıkça yazıyor
    (`https://www.ziraatbank.com.tr:443/tr/...`); `netloc` karşılaştırması
    bunu farklı alan sayıp site haritasındaki **500 URL'nin tamamını**
    sessizce atıyordu (2026-08-04'te ölçüldü, banka 1 belgeyle dönüyordu).
    `hostname` portu düşürür ve zaten küçük harfe çevirir.
    """
    return (urlsplit(url).hostname or "").removeprefix("www.")


def same_site(url: str, base: str) -> bool:
    """Aynı kayıtlı alan mı? (www. / alt alan / varsayılan port farkını tolere eder)."""
    a = _host(url)
    b = _host(base)
    return bool(a) and (a == b or a.endswith("." + b) or b.endswith("." + a))


def extract_links(html: str, base_url: str) -> list[str]:
    """HTML'den mutlak bağlantılar. bs4 varsa onu, yoksa regex kullanır."""
    hrefs: list[str] = []
    try:
        from bs4 import BeautifulSoup  # type: ignore

        soup = BeautifulSoup(html, "html.parser")
        hrefs = [a.get("href") or "" for a in soup.find_all("a")]
    except ModuleNotFoundError:
        hrefs = _HREF_RE.findall(html)
    out: list[str] = []
    for href in hrefs:
        href = (href or "").strip()
        if not href or href.startswith("#"):
            continue
        out.append(urljoin(base_url, href))
    return out


def parse_sitemap(xml: str) -> tuple[list[str], bool]:
    """<loc> listesini ve bunun bir sitemap *index*'i olup olmadığını döner."""
    return _LOC_RE.findall(xml), bool(_SITEMAPINDEX_RE.search(xml))


def matches(url: str, include: Iterable[str], exclude: Iterable[str]) -> bool:
    """URL include desenlerinden birine uyup exclude'lara uymuyorsa True."""
    for pattern in exclude:
        if re.search(pattern, url, re.I):
            return False
    if not include:
        return True
    return any(re.search(pattern, url, re.I) for pattern in include)


def collect_sitemap_urls(sitemap_urls: Iterable[str], fetch, *, max_depth: int = 2,
                         max_sitemaps: int = 12) -> tuple[list[str], list[str]]:
    """Sitemap(ler)i (index'ler dahil) gezip tüm <loc>'ları toplar.

    `fetch(url) -> FetchResult` benzeri; `.ok` ve `.html` alanları kullanılır.
    Döner: (url listesi, not listesi).
    """
    seen_sitemaps: set[str] = set()
    notes: list[str] = []
    out: list[str] = []
    queue: list[tuple[str, int]] = [(u, 0) for u in sitemap_urls]

    while queue and len(seen_sitemaps) < max_sitemaps:
        current, depth = queue.pop(0)
        if current in seen_sitemaps:
            continue
        seen_sitemaps.add(current)
        res = fetch(current)
        if not getattr(res, "ok", False):
            notes.append(f"sitemap basarisiz: {current} ({res.status or res.error})")
            continue
        locs, is_index = parse_sitemap(res.html or "")
        if not locs:
            notes.append(f"sitemap bos/XML degil: {current}")
            continue
        if is_index and depth < max_depth:
            queue.extend((loc, depth + 1) for loc in locs)
        else:
            out.extend(locs)
    return out, notes


def discover(bank, fetch, *, max_docs: int = 40,
             exclude_patterns: Optional[Iterable[str]] = None,
             fetch_pages: Optional[FetchPages] = None) -> DiscoveryResult:
    """Bir banka için kampanya detay URL'lerini keşfeder.

    Aşama 1: sitemap(ler) — `bank.sitemap_urls`.
    Aşama 2: liste sayfaları — `bank.campaign_paths` üzerinden bağlantı toplama.

    `fetch_pages` verilirse Aşama 2'de liste sayfasının tüm sayfaları gezilir
    (bkz. modül docstring'i).
    """
    include = list(getattr(bank, "detail_patterns", None) or DEFAULT_DETAIL_PATTERNS)
    exclude = list(exclude_patterns if exclude_patterns is not None
                   else DEFAULT_EXCLUDE_PATTERNS)
    exclude += list(getattr(bank, "exclude_patterns", None) or [])
    # Arşiv sayfaları AKTİF kampanya turuna girmez — ayrı turda toplanır
    # (`discover_archive`) ve `archive/` altına, expired etiketiyle yazılır.
    exclude += list(getattr(bank, "archive_patterns", None) or DEFAULT_ARCHIVE_PATTERNS)
    return _discover(bank, fetch, max_docs=max_docs,
                     paths=list(bank.campaign_paths),
                     sitemaps=list(getattr(bank, "sitemap_urls", None) or []),
                     include=include, exclude=exclude, ranker=rank,
                     fetch_pages=fetch_pages)


def discover_archive(bank, fetch, *, max_docs: int = 60,
                     fetch_pages: Optional[FetchPages] = None) -> DiscoveryResult:
    """SÜRESİ DOLMUŞ kampanya URL'lerini keşfeder (3. tur).

    Kaynak: `archive_paths` liste sayfaları + bankanın sitemap'i (arşiv sayfaları
    çoğu bankada sitemap'te de yer alır). Süzgeç `archive_patterns`.

    Bu tur boş dönerse bu bir hata DEĞİLDİR: her banka arşiv yayımlamıyor
    (2026-08-03 doğrulaması: yalnızca Kuveyt Türk ve Türkiye Finans yayımlıyor).

    SAYFALAMA BU TURDA KRİTİKTİR: Albaraka arşivi (`?slug=gecmis-kampanyalar`)
    slick karuseliyle sayfalanıyor ve sayfa değişse de URL DEĞİŞMİYOR
    (2026-08-04 tarayıcıyla ölçüldü). `fetch_pages` verilmezse yalnızca 1. sayfa
    toplanır ve kayıp SESSİZ olur.
    """
    paths = list(getattr(bank, "archive_paths", None) or [])
    if not paths:
        return DiscoveryResult(notes=[f"{bank.slug}: archive_paths tanimli degil — tur atlandi"])
    include = list(getattr(bank, "archive_patterns", None) or DEFAULT_ARCHIVE_PATTERNS)
    exclude = list(DEFAULT_EXCLUDE_PATTERNS)
    exclude += list(getattr(bank, "exclude_patterns", None) or [])
    return _discover(bank, fetch, max_docs=max_docs, paths=paths,
                     sitemaps=list(getattr(bank, "sitemap_urls", None) or []),
                     include=include, exclude=exclude, ranker=rank,
                     fetch_pages=fetch_pages)


def discover_documents(bank, fetch, *, max_docs: int = 40,
                       fetch_pages: Optional[FetchPages] = None) -> DiscoveryResult:
    """PDF belge URL'lerini keşfeder (4. tur — ücret tarifesi / bilgi formu).

    Varsayılan exclude listesi `\\.pdf$` içerir (kampanya turu PDF istemez);
    burada o kural BİLİNÇLİ olarak devre dışıdır — aradığımız şey tam olarak PDF.

    PDF'ler ayrı alan adında olabilir (ör. asset.emlakkatilim.com.tr); bu yüzden
    `document_hosts` izinli taban listesine eklenir.
    """
    paths = list(getattr(bank, "document_paths", None) or [])
    if not paths:
        return DiscoveryResult(notes=[f"{bank.slug}: document_paths tanimli degil — tur atlandi"])
    include = list(getattr(bank, "document_patterns", None) or DEFAULT_DOCUMENT_PATTERNS)
    # PDF dışı ikili/gürültü yolları elenir; `.pdf` KURALI EKLENMEZ.
    exclude = [p for p in DEFAULT_EXCLUDE_PATTERNS if "pdf" not in p]
    exclude += list(getattr(bank, "exclude_patterns", None) or [])
    return _discover(bank, fetch, max_docs=max_docs, paths=paths, sitemaps=[],
                     include=include, exclude=exclude, ranker=rank_documents,
                     extra_allowed_hosts=list(getattr(bank, "document_hosts", None) or []),
                     fetch_pages=fetch_pages)


def discover_products(bank, fetch, *, max_docs: int = 80,
                      exclude_patterns: Optional[Iterable[str]] = None,
                      fetch_pages: Optional[FetchPages] = None) -> DiscoveryResult:
    """Bir banka için ÜRÜN sayfası URL'lerini keşfeder (kampanyadan ayrı).

    Kampanya keşfiyle aynı iki aşamalı mekanizmayı kullanır, yalnızca girdi
    kümesi farklıdır: `product_paths` / `product_sitemap_urls` /
    `product_patterns`. Kampanya URL'leri elenir — onlar `live/` altında zaten
    toplanmıştır, ikinci kez toplanmaları çift kayıt üretirdi.
    """
    include = list(getattr(bank, "product_patterns", None) or DEFAULT_PRODUCT_PATTERNS)
    exclude = list(exclude_patterns if exclude_patterns is not None
                   else DEFAULT_EXCLUDE_PATTERNS + PRODUCT_EXCLUDE_PATTERNS)
    exclude += list(getattr(bank, "product_exclude_patterns", None) or [])
    sitemaps = list(getattr(bank, "product_sitemap_urls", None)
                    or getattr(bank, "sitemap_urls", None) or [])
    paths = list(getattr(bank, "product_paths", None) or [])
    # BAŞLANGIÇ NOKTASI YOKSA ANA SAYFADAN GEZ.
    # Gerçek veride ölçüldü: Türkiye Finans'ın ne `sitemap_urls`'i ne
    # `product_paths`'i var (kampanya yolları ASP.NET'e özgü `.aspx`
    # adresleri). Ürün keşfi 0 URL buluyordu — banka ürün sayfası
    # yayımlamadığı için değil, gezmeye BAŞLAYACAK yer olmadığı için.
    # Ana sayfa her bankada vardır ve ürün menüsünü içerir.
    if not paths and not sitemaps:
        paths = ["/"]
    return _discover(bank, fetch, max_docs=max_docs,
                     paths=paths,
                     sitemaps=sitemaps, include=include, exclude=exclude,
                     ranker=rank_products, fetch_pages=fetch_pages)


def _listing_pages(list_url: str, fetch, fetch_pages: Optional[FetchPages],
                   result: DiscoveryResult) -> list[tuple[str, str]]:
    """Bir liste sayfasının tüm sayfalarını `(html, taban URL)` çiftleri olarak döner.

    `fetch_pages` verilmişse (tarayıcı çekicisi) sayfalama gezilir. Verilmemişse
    ya da boş dönerse tek sayfalık ESKİ davranışa düşülür — `StaticFetcher`'da
    `fetch_all_pages` yoktur ve geriye uyumluluk korunmalıdır.

    Sayfalama sonucu HER DURUMDA `result.notes`'a yazılır: kaç sayfa gezildi,
    tek sayfa mı bulundu, yoksa sayfalama denenip başarısız mı oldu. Sessiz
    kalırsa "1 sayfa topladım" ile "hepsini topladım" birbirinden ayırt edilemez.

    Taban URL olarak `list_url` kullanılır: sayfa değiştiğinde adres değişmediği
    için (slick karusel) zaten tek bir kanonik taban vardır.
    """
    if fetch_pages is not None:
        htmls: list[str] = []
        try:
            htmls = [html for html in (fetch_pages(list_url) or []) if html]
        except Exception as exc:  # sayfalama hatası keşfi durdurmaz
            result.notes.append(
                f"sayfalama hatasi: {list_url} ({type(exc).__name__}: {exc})"[:200])
        if len(htmls) > 1:
            result.notes.append(
                f"sayfalama: {list_url} icin {len(htmls)} sayfa gezildi")
            return [(html, list_url) for html in htmls]
        if len(htmls) == 1:
            result.notes.append(
                f"sayfalama: {list_url} icin tek sayfa bulundu "
                "(sayfalama denetimi yok)")
            return [(htmls[0], list_url)]
        result.notes.append(
            f"sayfalama gezilemedi, tek sayfaya dusuldu: {list_url}")

    res = fetch(list_url)
    if not getattr(res, "ok", False):
        result.notes.append(
            f"liste sayfasi basarisiz: {list_url} ({res.status or res.error})")
        return []
    return [(res.html or "", res.final_url or list_url)]


def _discover(bank, fetch, *, max_docs: int, paths: list[str], sitemaps: list[str],
              include: list[str], exclude: list[str], ranker,
              extra_allowed_hosts: Optional[list[str]] = None,
              fetch_pages: Optional[FetchPages] = None) -> DiscoveryResult:
    """Kampanya, ürün, arşiv ve belge keşfinin ortak çekirdeği (tek gezinme mantığı)."""
    base = bank.website_url.rstrip("/")
    # Banka kampanyalarını ayrı alan adında yayımlıyorsa (ör. TOM Bank →
    # tombankhadi.com) o alan da "aynı site" sayılır. `extra_allowed_hosts`
    # tura özgüdür (ör. yalnızca PDF barındıran asset alanı).
    allowed_bases = [base] + [
        h if h.startswith("http") else f"https://{h}"
        for h in list(getattr(bank, "extra_hosts", None) or [])
        + list(extra_allowed_hosts or [])
    ]
    result = DiscoveryResult()
    seen: set[str] = set()

    def add(url: str, source: str) -> None:
        url = normalize_url(url)
        if url in seen or not any(same_site(url, b) for b in allowed_bases):
            return
        if not matches(url, include, exclude):
            return
        seen.add(url)
        result.urls.append(url)
        if source == "sitemap":
            result.from_sitemap += 1
        else:
            result.from_listing += 1

    # --- Aşama 1: sitemap ---
    if sitemaps:
        locs, notes = collect_sitemap_urls(sitemaps, fetch)
        result.notes.extend(notes)
        for loc in locs:
            add(loc, "sitemap")

    # --- Aşama 2: liste sayfalarından iki aşamalı gezinme ---
    for path in paths:
        list_url = path if path.startswith("http") else base + path
        pages = _listing_pages(list_url, fetch, fetch_pages, result)
        if not pages:
            continue
        add(list_url, "listing")  # liste sayfasının kendisi de içerik taşıyabilir
        for html, page_base in pages:
            for link in extract_links(html, page_base):
                add(link, "listing")

    if max_docs and len(result.urls) > max_docs:
        result.notes.append(
            f"{len(result.urls)} aday bulundu, max_docs={max_docs} ile kirpildi")
        result.urls = ranker(result.urls)[:max_docs]
    return result


# Kırpma sırasında önceliklendirme: kampanya sayfaları ürün/rehber sayfalarını yener.
_PRIORITY = (
    (r"/kampanya", 0),
    (r"kampanyasi|kampanyalari", 1),
    (r"/finansman|finansmani", 2),
    (r"firsat|avantaj|indirim|hediye|puan", 3),
)


def rank(urls: Iterable[str]) -> list[str]:
    """Adayları kampanya olma ihtimaline göre sıralar (kararlı/deterministik).

    max_docs kırpması kör baştan-al olduğunda sitemap'in ilk N kaydı (çoğu kez
    tek bir ürün ailesi) geliyordu; sıralama çeşitliliği ve isabeti artırır.
    """

    def key(url: str) -> tuple[int, int, str]:
        bucket = len(_PRIORITY)
        for pattern, score in _PRIORITY:
            if re.search(pattern, url, re.I):
                bucket = score
                break
        depth = url.count("/")
        return (bucket, depth, url)

    return sorted(urls, key=key)


# Ürün kırpmasında önceliklendirme. Sıra ölçümle belirlendi (2. tur keşif spike'ı):
# oran/ücret tarifesi sayfaları kâr payı oranını METİN olarak yayımlıyor;
# finansman ürün sayfaları vade + tahsis ücreti veriyor; kart sayfaları en zayıf.
_PRODUCT_PRIORITY = (
    (r"kar-payi|kar-paylasim|oranlar|urun-ve-hizmet-ucret|urun-hizmet|ucretler|tarife", 0),
    (r"katilma|finansman|kredi|leasing", 1),
    (r"hesap|yatirim|birikim|fon|sukuk|kira-sertifikasi|altin|maden|doviz", 2),
    (r"bilgilendirme-form|sozlesme", 3),
    (r"kart", 4),
)


def rank_products(urls: Iterable[str]) -> list[str]:
    """Ürün adaylarını bilgi yoğunluğuna göre sıralar (kararlı/deterministik)."""

    def key(url: str) -> tuple[int, int, str]:
        bucket = len(_PRODUCT_PRIORITY)
        for pattern, score in _PRODUCT_PRIORITY:
            if re.search(pattern, url, re.I):
                bucket = score
                break
        # Derin sayfalar gerçek ürün, sığ sayfalar kategori indeksidir; ancak
        # kategori sayfaları da ürün listesi taşır, bu yüzden sığdan derine.
        return (bucket, url.count("/"), url)

    return sorted(urls, key=key)


# Belge (PDF) kırpmasında önceliklendirme: ücret/komisyon tarifesi en değerli —
# kesin tahsis ücreti ve masraf oranları orada. Sözleşme/form ikinci sırada.
_DOCUMENT_PRIORITY = (
    (r"ucret|ücret|komisyon|tarife|masraf", 0),
    (r"bilgi-formu|bilgilendirme|urun-bilgi", 1),
    (r"sozlesme|sözleşme|form", 2),
)


def rank_documents(urls: Iterable[str]) -> list[str]:
    """PDF adaylarını bilgi değerine göre sıralar (kararlı/deterministik)."""

    def key(url: str) -> tuple[int, int, str]:
        bucket = len(_DOCUMENT_PRIORITY)
        for pattern, score in _DOCUMENT_PRIORITY:
            if re.search(pattern, url, re.I):
                bucket = score
                break
        return (bucket, url.count("/"), url)

    return sorted(urls, key=key)
