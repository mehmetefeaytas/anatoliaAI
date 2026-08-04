"""HTTP/tarayıcı çekim katmanı — rate-limit + zarif bağımlılık düşüşü.

İlgili: CLAUDE.md §14 (etik scraping), ../../concepts/web-scraping.md

İki yol:
- `StaticFetcher`  : requests + BeautifulSoup (scrape_mode: static)
- `BrowserFetcher` : Playwright (scrape_mode: js) — kurulu değilse zarifçe atlar

Her ikisi de `FetchResult` döner; `collection_method` alanı provenance'a taşınır
(`live` = requests, `browser` = Playwright).
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Optional
from urllib.parse import urlsplit

DEFAULT_USER_AGENT = "AnatoliaAI-Research/1.0 (+TEKNOFEST 2026; arastirma amacli)"
DEFAULT_DELAY_S = 3.0


@dataclass
class FetchResult:
    """Tek bir çekim denemesinin sonucu (başarı ya da hata).

    `content` / `content_type` yalnızca ikili (binary) çekimde dolar —
    PDF ücret tarifeleri için (`StaticFetcher.fetch_bytes`).
    """

    url: str
    status: Optional[int] = None
    html: Optional[str] = None
    error: Optional[str] = None
    method: str = "live"
    final_url: Optional[str] = None
    content: Optional[bytes] = field(default=None, repr=False)
    content_type: Optional[str] = None

    @property
    def ok(self) -> bool:
        return self.status == 200 and bool(self.html)

    @property
    def ok_bytes(self) -> bool:
        """İkili içerik başarıyla alındı mı? (`ok` metin yolu içindir.)"""
        return self.status == 200 and bool(self.content)


class RateLimiter:
    """Domain başına minimum bekleme (CLAUDE.md §14: 2–5 sn)."""

    def __init__(self, delay_s: float = DEFAULT_DELAY_S) -> None:
        self.delay_s = delay_s
        self._last: dict[str, float] = {}

    def wait(self, url: str) -> None:
        host = urlsplit(url).netloc.lower()
        last = self._last.get(host)
        now = time.monotonic()
        if last is not None:
            remaining = self.delay_s - (now - last)
            if remaining > 0:
                time.sleep(remaining)
        self._last[host] = time.monotonic()


class StaticFetcher:
    """requests tabanlı çekici. requests yoksa her çağrı hata döner (çökmez)."""

    method = "live"

    def __init__(self, user_agent: str = DEFAULT_USER_AGENT, timeout: float = 25.0,
                 limiter: Optional[RateLimiter] = None) -> None:
        self.user_agent = user_agent
        self.timeout = timeout
        self.limiter = limiter or RateLimiter()
        self._session = None
        self._available: Optional[bool] = None

    @property
    def available(self) -> bool:
        if self._available is None:
            try:
                import requests  # type: ignore

                self._session = requests.Session()
                self._session.headers.update({
                    "User-Agent": self.user_agent,
                    "Accept-Language": "tr-TR,tr;q=0.9",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                })
                self._available = True
            except ModuleNotFoundError:
                self._available = False
        return bool(self._available)

    def fetch(self, url: str) -> FetchResult:
        if not self.available:
            return FetchResult(url, error="requests kurulu degil", method=self.method)
        self.limiter.wait(url)
        try:
            resp = self._session.get(url, timeout=self.timeout, allow_redirects=True)  # type: ignore[union-attr]
            # Sunucu charset bildirmediğinde requests latin-1 varsayar; TR için utf-8 daha doğru.
            if resp.encoding is None or resp.encoding.lower() == "iso-8859-1":
                resp.encoding = resp.apparent_encoding or "utf-8"
            return FetchResult(url, status=resp.status_code, html=resp.text,
                               method=self.method, final_url=resp.url)
        except Exception as exc:  # ağ hatası pipeline'ı durdurmaz
            return FetchResult(url, error=f"{type(exc).__name__}: {exc}"[:200],
                               method=self.method)

    def fetch_bytes(self, url: str, *, max_bytes: int = 40 * 1024 * 1024) -> FetchResult:
        """İkili içerik çeker (PDF ücret tarifeleri / ürün bilgi formları).

        `max_bytes` koruması: bir bankanın 100 MB'lık taranmış PDF'i belleği
        şişirmesin. Aşılırsa içerik ATILIR ve hata döner — sessizce kırpılmaz,
        çünkü yarım PDF ayrıştırıldığında sessiz veri kaybı olur.
        """
        if not self.available:
            return FetchResult(url, error="requests kurulu degil", method=self.method)
        self.limiter.wait(url)
        try:
            resp = self._session.get(url, timeout=self.timeout, allow_redirects=True,  # type: ignore[union-attr]
                                     stream=True)
            chunks: list[bytes] = []
            total = 0
            for chunk in resp.iter_content(chunk_size=65536):
                if not chunk:
                    continue
                total += len(chunk)
                if total > max_bytes:
                    resp.close()
                    return FetchResult(
                        url, status=resp.status_code, method=self.method,
                        error=f"belge {max_bytes} bayt sinirini asti ({total}+)")
                chunks.append(chunk)
            resp.close()
            return FetchResult(url, status=resp.status_code, method=self.method,
                               final_url=resp.url, content=b"".join(chunks),
                               content_type=(resp.headers.get("Content-Type") or "").lower())
        except Exception as exc:
            return FetchResult(url, error=f"{type(exc).__name__}: {exc}"[:200],
                               method=self.method)

    def close(self) -> None:
        if self._session is not None:
            self._session.close()


class BrowserFetcher:
    """Playwright tabanlı çekici (scrape_mode: js).

    Playwright ya da tarayıcı ikilisi yoksa `available` False döner; çağıran
    tarafı bunu rapora yazar ve bankayı manuel toplamaya bırakır.
    """

    method = "browser"

    def __init__(self, user_agent: str = DEFAULT_USER_AGENT, timeout_ms: int = 30000,
                 limiter: Optional[RateLimiter] = None) -> None:
        self.user_agent = user_agent
        self.timeout_ms = timeout_ms
        self.limiter = limiter or RateLimiter()
        self.unavailable_reason: Optional[str] = None
        self._pw = None
        self._browser = None
        self._context = None

    @property
    def available(self) -> bool:
        return self._ensure() is None

    def _ensure(self) -> Optional[str]:
        """Tarayıcıyı bir kez başlatır. Hata mesajı döner (None = hazır)."""
        if self._context is not None:
            return None
        if self.unavailable_reason is not None:
            return self.unavailable_reason
        try:
            from playwright.sync_api import sync_playwright  # type: ignore
        except ModuleNotFoundError:
            self.unavailable_reason = "playwright kurulu degil"
            return self.unavailable_reason
        try:
            self._pw = sync_playwright().start()
            self._browser = self._pw.chromium.launch(headless=True)
            self._context = self._browser.new_context(
                user_agent=self.user_agent, locale="tr-TR",
                viewport={"width": 1440, "height": 900},
            )
        except Exception as exc:
            self.unavailable_reason = f"tarayici baslatilamadi: {type(exc).__name__}: {exc}"[:200]
            self._close_quiet()
            return self.unavailable_reason
        return None

    def fetch(self, url: str, wait_selector: Optional[str] = None) -> FetchResult:
        reason = self._ensure()
        if reason:
            return FetchResult(url, error=reason, method=self.method)
        self.limiter.wait(url)
        page = None
        try:
            page = self._context.new_page()  # type: ignore[union-attr]
            resp = page.goto(url, timeout=self.timeout_ms, wait_until="domcontentloaded")
            try:
                page.wait_for_load_state("networkidle", timeout=8000)
            except Exception:
                pass  # networkidle'a hiç ulaşmayan sayfalar (canlı sohbet vb.) normal
            if wait_selector:
                try:
                    page.wait_for_selector(wait_selector, timeout=8000)
                except Exception:
                    pass
            html = page.content()
            status = resp.status if resp is not None else None
            return FetchResult(url, status=status, html=html, method=self.method,
                               final_url=page.url)
        except Exception as exc:
            return FetchResult(url, error=f"{type(exc).__name__}: {exc}"[:200],
                               method=self.method)
        finally:
            if page is not None:
                try:
                    page.close()
                except Exception:
                    pass

    # Sayfalama denetimlerini bulan JS. Site başına özel kod YAZILMAZ; tek
    # genel mekanizma üç yaygın biçimi kapsar:
    #   1. numaralı bağlantı/düğme (1 2 3 ...)
    #   2. "ileri / sonraki / ›" düğmesi
    #   3. slick/swiper karusel noktaları (li.slick-active kardeşleri)
    # Albaraka arşivinde ölçüldü (2026-08-04): slick karuseli, URL DEĞİŞMİYOR.
    # URL değişmediği için adresi numaralandırmak işe yaramaz — tıklamak şart.
    _PAGER_JS = """
    () => {
      const out = [];
      const seen = new Set();
      const push = (el) => {
        if (!el || seen.has(el)) return;
        seen.add(el); out.push(el);
      };
      document.querySelectorAll(
        'a,button,li[role="presentation"],li.slick-slide,.slick-dots li,'
        + '.swiper-pagination-bullet,[class*="pag"] a,[class*="pag"] button'
      ).forEach(el => {
        const t = (el.textContent || '').trim();
        const al = (el.getAttribute('aria-label') || '').trim();
        const cls = (el.className || '').toString();
        if (/^\\d{1,3}$/.test(t)) push(el);
        else if (/^(›|»|>|ileri|sonraki|next|daha fazla|devam)$/i.test(t)) push(el);
        else if (/next|ileri|sonraki|page ?\\d/i.test(al)) push(el);
        else if (/slick-dots|swiper-pagination-bullet/.test(cls)) push(el);
      });
      window.__pagerEls = out;
      return out.length;
    }
    """

    def fetch_all_pages(self, url: str, max_pages: int = 12) -> list[str]:
        """Sayfalanmış bir listeleme sayfasının TÜM sayfalarının HTML'i.

        Neden gerekli: bu sayfalarda sayfa değiştiğinde **URL değişmiyor**
        (Albaraka arşivi slick karuseli, 2026-08-04). Dolayısıyla adres
        numaralandırmak ya da site haritası okumak 2. sayfayı asla getirmez;
        hasat sessizce yalnızca 1. sayfayı toplar.

        Dönen liste her zaman en az bir öğe içerir (ilk sayfa) — sayfalama
        yoksa da çağıran tarafın kodu değişmez.
        """
        reason = self._ensure()
        if reason:
            return []
        self.limiter.wait(url)
        page = None
        pages: list[str] = []
        try:
            page = self._context.new_page()  # type: ignore[union-attr]
            page.goto(url, timeout=self.timeout_ms, wait_until="domcontentloaded")
            try:
                page.wait_for_load_state("networkidle", timeout=8000)
            except Exception:
                pass
            pages.append(page.content())
            try:
                count = int(page.evaluate(self._PAGER_JS) or 0)
            except Exception:
                return pages
            # Aynı düğmeye tekrar basmamak için indeksle ilerlenir; her tıklamadan
            # sonra DOM yenilendiği için eleman referansları JS tarafında tutulur.
            for i in range(1, min(count, max_pages)):
                try:
                    page.evaluate(
                        "(i) => { const e = (window.__pagerEls||[])[i];"
                        " if (e) e.click(); }", i)
                    try:
                        page.wait_for_load_state("networkidle", timeout=5000)
                    except Exception:
                        pass
                    page.wait_for_timeout(400)
                    html = page.content()
                    if html and html not in pages:
                        pages.append(html)
                    # Tıklama DOM'u yenilediyse eleman listesi tazelenir.
                    page.evaluate(self._PAGER_JS)
                except Exception:
                    break  # sayfalama beklenmedik davrandı: elde olanla devam
            return pages
        except Exception:
            return pages
        finally:
            if page is not None:
                try:
                    page.close()
                except Exception:
                    pass

    def _close_quiet(self) -> None:
        for obj in (self._context, self._browser, self._pw):
            try:
                if obj is not None:
                    (obj.stop if hasattr(obj, "stop") else obj.close)()
            except Exception:
                pass
        self._context = self._browser = self._pw = None

    def close(self) -> None:
        self._close_quiet()


@dataclass
class FetcherBundle:
    """scrape_mode → çekici eşlemesi; tek yerden kapatılır."""

    static: StaticFetcher = field(default_factory=StaticFetcher)
    browser: BrowserFetcher = field(default_factory=BrowserFetcher)

    def for_mode(self, scrape_mode: str):
        """`scrape_mode` alanının GERÇEK dispatch noktası (§14, banks.yaml)."""
        return self.browser if scrape_mode == "js" else self.static

    def close(self) -> None:
        self.static.close()
        self.browser.close()
