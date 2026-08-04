"""Sayfalama (pagination) çiti — keşif katmanı liste sayfasının TÜM sayfalarını gezmeli.

NEDEN BU DOSYA VAR (2026-08-04 tarayıcıyla ölçüldü)
---------------------------------------------------
`https://www.albaraka.com.tr/tr/kampanyalar?slug=gecmis-kampanyalar` sayfasındaki
arşiv listesi bir **slick karuseli** ile sayfalanıyor: `li.slick-active` ve
numaralı `button` öğeleri var. Kritik gerçek şu: **sayfa değişince URL DEĞİŞMİYOR.**

Bunun sonucu:
  * adresi numaralandırmak (`?page=2`, `/sayfa/2`) 2. sayfayı ASLA getirmez,
  * site haritası (sitemap.xml) da getirmez — orada tek bir liste adresi var,
  * tek yol sayfalama denetimine **tıklamaktır** (`BrowserFetcher.fetch_all_pages`).

Ölçüm anında sayfada 55 detay bağlantısı görünüyordu; "2" düğmesine basınca
gelen bağlantılar hasada hiç ULAŞMIYORDU.

SESSİZ KAYIP NEDEN GÜRÜLTÜLÜ HATADAN TEHLİKELİDİR
-------------------------------------------------
Sayfalama gezilmediğinde hasat çökmüyor, hata da vermiyor: "55 belge toplandı"
diyerek BAŞARILI görünüyor. Eksik olanın eksik olduğunu kimse bilmiyor. Oysa
gürültülü bir hata (HTTP 500, bağlantı kopması) rapora düşer, görülür ve
düzeltilir. Bu yüzden bu dosya iki şeyi birlikte çitler:
  1. sayfaların TAMAMINDAN bağlantı toplandığını,
  2. kaç sayfa gezildiğinin `result.notes`'a YAZILDIĞINI — sayfalama denenip
     başarısız olduğu durum dahil. Not düşmeyen bir yol, sessiz kayıp yoludur.

BİLİNEN AÇIK NOKTA (bu testlerin kapsamadığı)
---------------------------------------------
`config/banks.yaml` içinde `albaraka` şu an `scrape_mode: static`. `StaticFetcher`
sınıfında `fetch_all_pages` YOKTUR; dolayısıyla mekanizma bağlı olsa da o banka
için tarayıcı moduna geçilmedikçe devreye GİRMEZ. Buradaki testler mekanizmayı
sahte çekicilerle doğrular, banka yapılandırmasını doğrulamaz.

Tüm testler tamamen OFFLINE — gerçek ağ isteği YOK.
"""

import sys
import unittest
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.scraping import discover as disc
from src.scraping.collector import collect_live
from src.scraping.config import BankConfig
from src.scraping.fetcher import FetcherBundle, FetchResult
from src.scraping.robots import RobotsCache


def ROBOTS_ALLOW_ALL() -> RobotsCache:
    """robots.txt'i 404 döndüren önbellek: "her şeye izin var" + ağa çıkılmaz."""
    return RobotsCache(fetcher=lambda url: (404, None))


def _detail_page(title: str) -> str:
    """MIN_DOC_CHARS eşiğini geçen gerçekçi bir detay sayfası gövdesi."""
    filler = "Kâr payı oranı %2,05, vade 36 ay, tahsis ücreti yoktur. " * 8
    return (f"<html><head><title>{title}</title></head><body><main>"
            f"<h1>{title}</h1><p>{filler}</p></main></body></html>")


class FakePlainFetcher:
    """`fetch_all_pages` OLMAYAN çekici — `StaticFetcher`'ın taklidi.

    Geriye uyumluluk çiti bu sınıfla kurulur: keşif katmanı bu çekiciyle
    eskisiyle bire bir aynı davranmalıdır.
    """

    method = "live"
    available = True
    unavailable_reason: Optional[str] = None

    def __init__(self, pages: dict[str, str]) -> None:
        self.pages = pages
        self.calls: list[str] = []

    def fetch(self, url: str, **kwargs) -> FetchResult:
        self.calls.append(url)
        body = self.pages.get(url)
        if body is None:
            return FetchResult(url, status=404, method=self.method)
        return FetchResult(url, status=200, html=body, method=self.method,
                           final_url=url)

    def close(self) -> None:
        pass


class FakePagingFetcher(FakePlainFetcher):
    """`fetch_all_pages` OLAN çekici — `BrowserFetcher`'ın taklidi.

    `listing_pages`: liste URL'i → o listenin TÜM sayfalarının HTML listesi.
    `fetch()` yalnızca İLK sayfayı verir; gerçek slick karuselinde de tek bir
    HTTP isteği yalnızca 1. sayfayı döndürür (URL değişmiyor).
    """

    method = "browser"

    def __init__(self, pages: dict[str, str],
                 listing_pages: Optional[dict[str, list[str]]] = None,
                 raises: bool = False) -> None:
        super().__init__(pages)
        self.listing_pages = listing_pages or {}
        self.raises = raises
        self.page_calls: list[str] = []

    def fetch(self, url: str, **kwargs) -> FetchResult:
        htmls = self.listing_pages.get(url)
        if htmls:
            self.calls.append(url)
            return FetchResult(url, status=200, html=htmls[0],
                               method=self.method, final_url=url)
        return super().fetch(url, **kwargs)

    def fetch_all_pages(self, url: str, max_pages: int = 12) -> list[str]:
        self.page_calls.append(url)
        if self.raises:
            raise RuntimeError("tarayici sayfalamada patladi")
        return list(self.listing_pages.get(url, []))[:max_pages]


# Üç sayfalık sahte arşiv listesi — her sayfada FARKLI detay bağlantıları.
# Albaraka arşiviyle aynı şekil: aynı URL, farklı içerik.
THREE_PAGES = [
    '<html><body><a href="/tr/kampanyalar/sayfa1-a">A1</a>'
    '<a href="/tr/kampanyalar/sayfa1-b">B1</a></body></html>',
    '<html><body><a href="/tr/kampanyalar/sayfa2-a">A2</a>'
    '<a href="/tr/kampanyalar/sayfa2-b">B2</a></body></html>',
    '<html><body><a href="/tr/kampanyalar/sayfa3-a">A3</a>'
    '<a href="/tr/kampanyalar/sayfa3-b">B3</a></body></html>',
]
LIST_URL = "https://b.test/tr/kampanyalar"
ALL_SIX = [f"https://b.test/tr/kampanyalar/sayfa{p}-{s}"
           for p in (1, 2, 3) for s in ("a", "b")]


def _js_bundle(browser) -> FetcherBundle:
    """Tarayıcı modu demeti — statik yol da SAHTE, testte gerçek ağa çıkılmasın."""
    return FetcherBundle(static=FakePlainFetcher({}), browser=browser)


def _bank(**kwargs) -> BankConfig:
    defaults = dict(slug="b", name="B", website_url="https://b.test",
                    campaign_paths=["/tr/kampanyalar"],
                    detail_patterns=["/tr/kampanyalar/"])
    defaults.update(kwargs)
    return BankConfig(**defaults)  # type: ignore[arg-type]


class TestDiscoveryPagination(unittest.TestCase):
    """`discover` + `_discover` sayfalama davranışı."""

    def test_links_from_all_three_pages_are_collected(self):
        """Sayfalama gezildiğinde ÜÇ sayfanın TAMAMINDAN bağlantı toplanır."""
        fetcher = FakePagingFetcher({}, {LIST_URL: THREE_PAGES})
        res = disc.discover(_bank(), fetcher.fetch,
                            fetch_pages=fetcher.fetch_all_pages)
        for url in ALL_SIX:
            self.assertIn(url, res.urls)
        self.assertEqual(fetcher.page_calls, [LIST_URL])

    def test_page_count_is_noted(self):
        """Kaç sayfa gezildiği `notes`'a yazılır — sessiz kalmaz."""
        fetcher = FakePagingFetcher({}, {LIST_URL: THREE_PAGES})
        res = disc.discover(_bank(), fetcher.fetch,
                            fetch_pages=fetcher.fetch_all_pages)
        notes = " | ".join(res.notes)
        self.assertIn("sayfalama", notes)
        self.assertIn("3 sayfa gezildi", notes)

    def test_single_page_is_also_noted(self):
        """Sayfalama denetimi bulunmayan liste de rapora geçer.

        "1 sayfa topladım" ile "hepsini topladım" ayırt edilebilir olmalı.
        """
        fetcher = FakePagingFetcher({}, {LIST_URL: [THREE_PAGES[0]]})
        res = disc.discover(_bank(), fetcher.fetch,
                            fetch_pages=fetcher.fetch_all_pages)
        notes = " | ".join(res.notes)
        self.assertIn("tek sayfa", notes)
        self.assertIn("https://b.test/tr/kampanyalar/sayfa1-a", res.urls)

    def test_empty_pagination_falls_back_to_single_fetch(self):
        """`fetch_all_pages` boş dönerse (tarayıcı yok) tek sayfaya düşülür + not."""
        fetcher = FakePagingFetcher({LIST_URL: THREE_PAGES[0]}, {})
        res = disc.discover(_bank(), fetcher.fetch,
                            fetch_pages=fetcher.fetch_all_pages)
        notes = " | ".join(res.notes)
        self.assertIn("sayfalama gezilemedi", notes)
        # Eski yol devrede: 1. sayfanın bağlantıları geldi, 2-3 gelmedi.
        self.assertIn("https://b.test/tr/kampanyalar/sayfa1-a", res.urls)
        self.assertNotIn("https://b.test/tr/kampanyalar/sayfa2-a", res.urls)

    def test_pagination_exception_is_noted_and_does_not_crash(self):
        """Tarayıcı sayfalamada patlarsa keşif çökmez; hata NOT olarak görünür."""
        fetcher = FakePagingFetcher({LIST_URL: THREE_PAGES[0]}, {LIST_URL: THREE_PAGES},
                                    raises=True)
        res = disc.discover(_bank(), fetcher.fetch,
                            fetch_pages=fetcher.fetch_all_pages)
        notes = " | ".join(res.notes)
        self.assertIn("sayfalama hatasi", notes)
        self.assertIn("RuntimeError", notes)
        self.assertIn("https://b.test/tr/kampanyalar/sayfa1-a", res.urls)

    def test_archive_round_paginates_too(self):
        """Arşiv turu (Albaraka'nın gerçek vakası) da sayfalanır."""
        archive_url = "https://b.test/tr/kampanyalar?slug=gecmis-kampanyalar"
        pages = [
            '<a href="/tr/kampanyalar/gecmis-kampanya-1">1</a>',
            '<a href="/tr/kampanyalar/gecmis-kampanya-2">2</a>',
        ]
        bank = _bank(archive_paths=["/tr/kampanyalar?slug=gecmis-kampanyalar"],
                     archive_patterns=["gecmis-kampanya"])
        fetcher = FakePagingFetcher({}, {archive_url: pages})
        res = disc.discover_archive(bank, fetcher.fetch,
                                    fetch_pages=fetcher.fetch_all_pages)
        self.assertIn("https://b.test/tr/kampanyalar/gecmis-kampanya-1", res.urls)
        self.assertIn("https://b.test/tr/kampanyalar/gecmis-kampanya-2", res.urls)
        self.assertIn("2 sayfa gezildi", " | ".join(res.notes))

    def test_products_round_accepts_fetch_pages(self):
        """Ürün turu da aynı parametreyi kabul eder (tek gezinme çekirdeği)."""
        list_url = "https://b.test/tr/urunler"
        pages = ['<a href="/tr/bireysel/finansman/konut">K</a>',
                 '<a href="/tr/bireysel/finansman/tasit">T</a>']
        bank = _bank(campaign_paths=[], product_paths=["/tr/urunler"])
        fetcher = FakePagingFetcher({}, {list_url: pages})
        res = disc.discover_products(bank, fetcher.fetch,
                                     fetch_pages=fetcher.fetch_all_pages)
        self.assertIn("https://b.test/tr/bireysel/finansman/konut", res.urls)
        self.assertIn("https://b.test/tr/bireysel/finansman/tasit", res.urls)

    def test_documents_round_accepts_fetch_pages(self):
        """Belge (PDF) turu da aynı parametreyi kabul eder."""
        list_url = "https://b.test/tr/ucretler"
        pages = ['<a href="/dosya/ucret-tarifesi.pdf">Tarife</a>',
                 '<a href="/dosya/bilgi-formu.pdf">Form</a>']
        bank = _bank(campaign_paths=[], document_paths=["/tr/ucretler"])
        fetcher = FakePagingFetcher({}, {list_url: pages})
        res = disc.discover_documents(bank, fetcher.fetch,
                                      fetch_pages=fetcher.fetch_all_pages)
        self.assertIn("https://b.test/dosya/ucret-tarifesi.pdf", res.urls)
        self.assertIn("https://b.test/dosya/bilgi-formu.pdf", res.urls)


class TestBackwardCompatibility(unittest.TestCase):
    """REGRESYON ÇİTİ: `fetch_all_pages` olmayan çekicide davranış DEĞİŞMEZ."""

    def test_plain_fetcher_keeps_old_single_page_behaviour(self):
        fetcher = FakePlainFetcher({LIST_URL: THREE_PAGES[0]})
        res = disc.discover(_bank(), fetcher.fetch)
        self.assertIn("https://b.test/tr/kampanyalar/sayfa1-a", res.urls)
        self.assertIn("https://b.test/tr/kampanyalar/sayfa1-b", res.urls)
        self.assertNotIn("https://b.test/tr/kampanyalar/sayfa2-a", res.urls)
        self.assertFalse(hasattr(fetcher, "fetch_all_pages"))
        # Sayfalama denenmediği için sayfalama notu da olmamalı — mevcut
        # rapor biçimini bozmadan eklendi.
        self.assertNotIn("sayfalama", " | ".join(res.notes))

    def test_failed_listing_still_noted_without_pagination(self):
        """Liste sayfası 404 verdiğinde eski not metni korunur."""
        res = disc.discover(_bank(), FakePlainFetcher({}).fetch)
        self.assertEqual(res.urls, [])
        self.assertIn("liste sayfasi basarisiz", " | ".join(res.notes))

    def test_fetch_pages_none_is_identical_to_omitting_it(self):
        """`fetch_pages=None` açıkça geçilmesi eski çağrıyla aynı sonucu verir."""
        pages = {LIST_URL: THREE_PAGES[0]}
        a = disc.discover(_bank(), FakePlainFetcher(pages).fetch)
        b = disc.discover(_bank(), FakePlainFetcher(pages).fetch, fetch_pages=None)
        self.assertEqual(a.urls, b.urls)
        self.assertEqual(a.notes, b.notes)


class TestCollectorWiring(unittest.TestCase):
    """`collect_live` sayfalamayı `hasattr` ile bağlıyor mu?"""

    def test_browser_fetcher_pagination_reaches_all_pages(self):
        details = {url: _detail_page(url.rsplit("/", 1)[-1]) for url in ALL_SIX}
        fetcher = FakePagingFetcher(details, {LIST_URL: THREE_PAGES})
        docs = collect_live(_bank(scrape_mode="js"), bundle=_js_bundle(fetcher),
                            robots=ROBOTS_ALLOW_ALL())
        collected = {d.source_url for d in docs}
        for url in ALL_SIX:
            self.assertIn(url, collected)
        self.assertEqual(fetcher.page_calls, [LIST_URL])

    def test_static_fetcher_wiring_is_untouched(self):
        """Statik çekicide `fetch_all_pages` yok → sayfalama hiç denenmez."""
        details = {url: _detail_page(url.rsplit("/", 1)[-1]) for url in ALL_SIX[:2]}
        details[LIST_URL] = THREE_PAGES[0]
        fetcher = FakePlainFetcher(details)
        report: dict = {}
        docs = collect_live(_bank(), bundle=FetcherBundle(static=fetcher,
                                                         browser=FakePlainFetcher({})),
                            robots=ROBOTS_ALLOW_ALL(), report=report)
        collected = {d.source_url for d in docs}
        self.assertIn(ALL_SIX[0], collected)
        self.assertNotIn(ALL_SIX[2], collected)   # 2. sayfa gelmedi (beklenen)
        self.assertNotIn("sayfalama", " | ".join(report["notes"]))

    def test_page_count_lands_in_report_notes(self):
        details = {url: _detail_page(url.rsplit("/", 1)[-1]) for url in ALL_SIX}
        fetcher = FakePagingFetcher(details, {LIST_URL: THREE_PAGES})
        report: dict = {}
        collect_live(_bank(scrape_mode="js"), bundle=_js_bundle(fetcher),
                     robots=ROBOTS_ALLOW_ALL(), report=report)
        self.assertIn("3 sayfa gezildi", " | ".join(report["notes"]))

    def test_robots_disallow_blocks_pagination(self):
        """`fetch_all_pages` robots.txt kontrolünü ATLAYAMAZ (CLAUDE.md §14)."""
        fetcher = FakePagingFetcher({}, {LIST_URL: THREE_PAGES})
        robots = RobotsCache(fetcher=lambda url: (200, "User-agent: *\nDisallow: /"))
        report: dict = {}
        docs = collect_live(_bank(scrape_mode="js"), bundle=_js_bundle(fetcher),
                            robots=robots, report=report)
        self.assertEqual(docs, [])
        self.assertEqual(fetcher.page_calls, [])   # tarayıcı hiç çalıştırılmadı
        self.assertTrue(any(b["reason"] == "robots disallow"
                            for b in report["blocked"]))


if __name__ == "__main__":
    unittest.main()
