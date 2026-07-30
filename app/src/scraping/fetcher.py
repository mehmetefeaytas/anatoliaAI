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
    """Tek bir çekim denemesinin sonucu (başarı ya da hata)."""

    url: str
    status: Optional[int] = None
    html: Optional[str] = None
    error: Optional[str] = None
    method: str = "live"
    final_url: Optional[str] = None

    @property
    def ok(self) -> bool:
        return self.status == 200 and bool(self.html)


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
