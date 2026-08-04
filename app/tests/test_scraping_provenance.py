"""Dalga 5 testleri: scrape_mode dispatch + robots.txt + provenance + keşif.

Tamamen OFFLINE — ağ yok. HTTP çekimi sahte (fake) fetcher'larla enjekte edilir.
"""

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.scraping import collector
from src.scraping import discover as disc
from src.scraping.collector import (
    METHOD_BROWSER,
    METHOD_LIVE,
    METHOD_MANUAL,
    RawDoc,
    collect_from_fixtures,
    collect_live,
    content_hash,
    ensure_manual_dirs,
    save_docs,
    url_to_slug,
    utc_now_iso,
)
from src.scraping.config import BankConfig, load_banks
from src.scraping.fetcher import FetcherBundle, FetchResult, RateLimiter
from src.scraping.robots import RobotsCache, RobotsPolicy, parse_robots

CONFIG = str(ROOT / "config" / "banks.yaml")


# --------------------------------------------------------------------------- #
# Test yardımcıları — ağ yerine sözlükten servis eden sahte çekiciler
# --------------------------------------------------------------------------- #

class FakeFetcher:
    """StaticFetcher/BrowserFetcher arayüzünü taklit eder."""

    def __init__(self, pages: dict, method: str = METHOD_LIVE, available: bool = True):
        self.pages = pages
        self.method = method
        self.available = available
        self.unavailable_reason = None if available else "test: kapali"
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


def _page(title: str, body: str = "") -> str:
    filler = "Kâr payı oranı %2,05, vade 36 ay, tahsis ücreti yoktur. " * 8
    return (f"<html><head><title>{title}</title></head><body><main>"
            f"<h1>{title}</h1><p>{body}{filler}</p></main>"
            f"<script>var x=1;</script></body></html>")


ROBOTS_SAMPLE = """
# ornek
User-agent: BadBot
Disallow: /

User-agent: *
Allow: /
Disallow: /gizli/
Disallow: /*.pdf$
Disallow: /arama
Crawl-delay: 2
Sitemap: https://ornek.test/sitemap.xml
"""


# --------------------------------------------------------------------------- #
# robots.txt
# --------------------------------------------------------------------------- #

class TestRobotsParse(unittest.TestCase):
    def test_selects_wildcard_group(self):
        rules, sitemaps, delay, agent = parse_robots(ROBOTS_SAMPLE, "AnatoliaAI-Research/1.0")
        self.assertEqual(agent, "*")
        self.assertEqual(delay, 2.0)
        self.assertEqual(sitemaps, ["https://ornek.test/sitemap.xml"])
        self.assertTrue(any(r.pattern == "/gizli/" and not r.allow for r in rules))

    def test_named_agent_group_wins(self):
        rules, _, _, agent = parse_robots(ROBOTS_SAMPLE, "BadBot/2.0")
        self.assertEqual(agent, "badbot")
        self.assertEqual([r.pattern for r in rules], ["/"])

    def test_empty_disallow_is_not_a_rule(self):
        rules, _, _, _ = parse_robots("User-agent: *\nDisallow:\n", "X/1")
        self.assertEqual(rules, [])

    def test_policy_allow_and_disallow(self):
        rules, sm, delay, agent = parse_robots(ROBOTS_SAMPLE, "AnatoliaAI-Research/1.0")
        p = RobotsPolicy(origin="https://ornek.test", status=200, fetched=True,
                         rules=rules, sitemaps=sm, crawl_delay=delay,
                         matched_agent=agent)
        self.assertTrue(p.allows("https://ornek.test/kampanyalar/konut"))
        self.assertFalse(p.allows("https://ornek.test/gizli/dosya"))
        self.assertFalse(p.allows("https://ornek.test/belge.pdf"))
        self.assertFalse(p.allows("https://ornek.test/arama?q=konut"))
        # $ ile biten desen yalnızca sonda eşleşir
        self.assertTrue(p.allows("https://ornek.test/belge.pdf.html"))

    def test_longest_match_wins_allow_over_disallow(self):
        rules, _, _, _ = parse_robots(
            "User-agent: *\nDisallow: /a/\nAllow: /a/acik/\n", "X/1")
        p = RobotsPolicy(origin="https://o.test", status=200, fetched=True, rules=rules)
        self.assertFalse(p.allows("https://o.test/a/kapali"))
        self.assertTrue(p.allows("https://o.test/a/acik/sayfa"))

    def test_missing_robots_defaults_to_allow(self):
        cache = RobotsCache(fetcher=lambda url: (404, None))
        allowed, reason = cache.allows("https://yok.test/kampanyalar")
        self.assertTrue(allowed)
        self.assertIn("izin", reason)

    def test_cache_fetches_origin_once(self):
        seen: list[str] = []

        def fetcher(url):
            seen.append(url)
            return 200, ROBOTS_SAMPLE

        cache = RobotsCache(fetcher=fetcher)
        cache.allows("https://ornek.test/a")
        cache.allows("https://ornek.test/b")
        self.assertEqual(seen, ["https://ornek.test/robots.txt"])

    def test_default_is_compliant_ignore_flag_overrides(self):
        strict = RobotsCache(fetcher=lambda u: (200, ROBOTS_SAMPLE))
        allowed, reason = strict.allows("https://ornek.test/gizli/x")
        self.assertFalse(allowed)
        self.assertIn("Disallow", reason)

        loose = RobotsCache(fetcher=lambda u: (200, ROBOTS_SAMPLE), ignore=True)
        allowed, reason = loose.allows("https://ornek.test/gizli/x")
        self.assertTrue(allowed)
        self.assertIn("GECILDI", reason)  # sessizce ihlal yok, raporlanır


# --------------------------------------------------------------------------- #
# scrape_mode dispatch
# --------------------------------------------------------------------------- #

class TestScrapeModeDispatch(unittest.TestCase):
    def test_bundle_routes_js_to_browser(self):
        static = FakeFetcher({}, METHOD_LIVE)
        browser = FakeFetcher({}, METHOD_BROWSER)
        bundle = FetcherBundle(static=static, browser=browser)
        self.assertIs(bundle.for_mode("js"), browser)
        self.assertIs(bundle.for_mode("static"), static)
        self.assertIs(bundle.for_mode("manual"), static)

    def test_js_bank_uses_browser_fetcher(self):
        bank = BankConfig(slug="js-bank", name="JS", website_url="https://js.test",
                          scrape_mode="js", campaign_paths=["/kampanyalar"],
                          detail_patterns=["/kampanyalar/"])
        pages = {
            "https://js.test/kampanyalar":
                '<html><body><a href="/kampanyalar/konut">Konut</a></body></html>',
            "https://js.test/kampanyalar/konut": _page("Konut Finansmanı"),
        }
        static = FakeFetcher({}, METHOD_LIVE)
        browser = FakeFetcher(pages, METHOD_BROWSER)
        docs = collect_live(bank, bundle=FetcherBundle(static=static, browser=browser),
                            robots=RobotsCache(fetcher=lambda u: (404, None)))
        self.assertEqual(static.calls, [])       # statik yol HİÇ kullanılmadı
        self.assertTrue(browser.calls)
        self.assertEqual([d.collection_method for d in docs], [METHOD_BROWSER])

    def test_unavailable_browser_is_skipped_gracefully(self):
        bank = BankConfig(slug="js-bank", name="JS", website_url="https://js.test",
                          scrape_mode="js", campaign_paths=["/kampanyalar"])
        bundle = FetcherBundle(static=FakeFetcher({}, METHOD_LIVE),
                               browser=FakeFetcher({}, METHOD_BROWSER, available=False))
        report: dict = {}
        docs = collect_live(bank, bundle=bundle,
                            robots=RobotsCache(fetcher=lambda u: (404, None)),
                            report=report)
        self.assertEqual(docs, [])               # çökmedi
        self.assertIn("test: kapali", report["skipped_reason"])


# --------------------------------------------------------------------------- #
# Keşif (iki aşamalı gezinme)
# --------------------------------------------------------------------------- #

class TestDiscovery(unittest.TestCase):
    def test_two_stage_crawl_from_listing(self):
        bank = BankConfig(slug="b", name="B", website_url="https://b.test",
                          campaign_paths=["/kampanyalar"],
                          detail_patterns=["/kampanyalar/"])
        pages = {"https://b.test/kampanyalar": (
            '<a href="/kampanyalar/konut">K</a>'
            '<a href="/kampanyalar/tasit">T</a>'
            '<a href="/hakkimizda">H</a>'          # desen dışı → elenir
            '<a href="https://baska.test/kampanyalar/x">D</a>'  # dış alan → elenir
        )}
        res = disc.discover(bank, FakeFetcher(pages).fetch)
        self.assertIn("https://b.test/kampanyalar/konut", res.urls)
        self.assertIn("https://b.test/kampanyalar/tasit", res.urls)
        self.assertNotIn("https://b.test/hakkimizda", res.urls)
        self.assertNotIn("https://baska.test/kampanyalar/x", res.urls)

    def test_sitemap_index_is_resolved_recursively(self):
        bank = BankConfig(slug="b", name="B", website_url="https://b.test",
                          campaign_paths=[],
                          sitemap_urls=["https://b.test/sitemap.xml"],
                          detail_patterns=["/kampanyalar/"])
        pages = {
            "https://b.test/sitemap.xml":
                "<sitemapindex><sitemap><loc>https://b.test/sm1.xml</loc>"
                "</sitemap></sitemapindex>",
            "https://b.test/sm1.xml":
                "<urlset><url><loc>https://b.test/kampanyalar/konut</loc></url>"
                "<url><loc>https://b.test/iletisim</loc></url></urlset>",
        }
        res = disc.discover(bank, FakeFetcher(pages).fetch)
        self.assertEqual(res.urls, ["https://b.test/kampanyalar/konut"])
        self.assertEqual(res.from_sitemap, 1)

    def test_default_excludes_drop_pdf_and_english(self):
        self.assertFalse(disc.matches("https://b.test/en/campaigns", [],
                                      disc.DEFAULT_EXCLUDE_PATTERNS))
        self.assertFalse(disc.matches("https://b.test/a.pdf", [],
                                      disc.DEFAULT_EXCLUDE_PATTERNS))
        self.assertTrue(disc.matches("https://b.test/kampanyalar/x", ["kampanya"],
                                     disc.DEFAULT_EXCLUDE_PATTERNS))

    def test_normalize_and_same_site(self):
        self.assertEqual(disc.normalize_url("https://b.test/a/#frag"), "https://b.test/a")
        self.assertTrue(disc.same_site("https://www.b.test/x", "https://b.test"))
        self.assertFalse(disc.same_site("https://c.test/x", "https://b.test"))

    def test_varsayilan_port_ayni_site_sayilir(self):
        """Site haritası varsayılan portu AÇIKÇA yazabilir.

        Ziraat Bankası'nın site haritası `https://www.ziraatbank.com.tr:443/tr/...`
        biçiminde URL veriyor. `netloc` karşılaştırması portu içerdiği için bu
        URL'ler "site dışı" sayılıp **500'ünün tamamı** sessizce atılıyordu;
        banka 1 belgeyle dönüyordu (2026-08-04'te ölçüldü). Sessiz kayıp,
        gürültülü hatadan tehlikelidir: hasat "başarılı" görünüyordu.
        """
        self.assertTrue(disc.same_site("https://www.b.test:443/x", "https://b.test"))
        self.assertTrue(disc.same_site("http://b.test:80/x", "https://www.b.test"))
        # Gerçek başka bir alan hâlâ dışlanmalı — düzeltme kapıyı açmamalı.
        self.assertFalse(disc.same_site("https://c.test:443/x", "https://b.test"))

    def test_rank_prefers_campaign_urls(self):
        ranked = disc.rank(["https://b.test/blog/yazi",
                            "https://b.test/kampanyalar/konut",
                            "https://b.test/urun/hesap"])
        self.assertEqual(ranked[0], "https://b.test/kampanyalar/konut")

    def test_max_docs_crops(self):
        bank = BankConfig(slug="b", name="B", website_url="https://b.test",
                          campaign_paths=["/l"], detail_patterns=["/k/"])
        links = "".join(f'<a href="/k/{i}">x</a>' for i in range(20))
        res = disc.discover(bank, FakeFetcher({"https://b.test/l": links}).fetch,
                            max_docs=5)
        self.assertEqual(len(res.urls), 5)
        self.assertTrue(any("kirpildi" in n for n in res.notes))


# --------------------------------------------------------------------------- #
# Provenance
# --------------------------------------------------------------------------- #

class TestProvenance(unittest.TestCase):
    def test_live_docs_carry_full_provenance(self):
        bank = BankConfig(slug="b", name="B", website_url="https://b.test",
                          campaign_paths=["/kampanyalar"],
                          detail_patterns=["/kampanyalar/"])
        html = _page("Konut Finansmanı Kampanyası")
        pages = {"https://b.test/kampanyalar": '<a href="/kampanyalar/konut">K</a>',
                 "https://b.test/kampanyalar/konut": html}
        docs = collect_live(bank, bundle=FetcherBundle(static=FakeFetcher(pages)),
                            robots=RobotsCache(fetcher=lambda u: (404, None)))
        self.assertEqual(len(docs), 1)
        doc = docs[0]
        self.assertEqual(doc.source_url, "https://b.test/kampanyalar/konut")
        self.assertEqual(doc.content_hash, content_hash(html))
        self.assertEqual(doc.collection_method, METHOD_LIVE)
        self.assertEqual(doc.http_status, 200)
        self.assertEqual(doc.title, "Konut Finansmanı Kampanyası")
        self.assertTrue(doc.scraped_at and doc.scraped_at.endswith("+00:00"))
        self.assertNotIn("<script>", doc.clean_text)   # script ayıklandı

    def test_duplicate_content_is_deduped_by_hash(self):
        bank = BankConfig(slug="b", name="B", website_url="https://b.test",
                          campaign_paths=["/kampanyalar"],
                          detail_patterns=["/kampanyalar/"])
        same = _page("Ayni Icerik")
        pages = {"https://b.test/kampanyalar":
                 '<a href="/kampanyalar/a">a</a><a href="/kampanyalar/b">b</a>',
                 "https://b.test/kampanyalar/a": same,
                 "https://b.test/kampanyalar/b": same}
        docs = collect_live(bank, bundle=FetcherBundle(static=FakeFetcher(pages)),
                            robots=RobotsCache(fetcher=lambda u: (404, None)))
        self.assertEqual(len(docs), 1)

    def test_dedup_html_gurultusune_ragmen_calisir(self):
        """Tekilleştirme TEMİZ METİN üzerinden yapılmalı, ham HTML üzerinden değil.

        Gerçek hata (2026-08-03): sayfadaki analitik kimlikleri / oturum simgeleri
        her istekte değişiyor, bu yüzden AYNI sayfanın iki kopyası farklı
        `content_hash` alıyor ve tekilleştirme kaçırıyordu. 1491 belgelik korpusta
        98 mükerrer metin grubu / 215 dosya (~%14) birikti; TOGG çelişkisi de
        2 gerçek bulgu yerine 4 raporlanıyordu.

        Aşağıdaki iki sayfanın GÖVDE METNİ aynı, yalnızca izleme kimlikleri farklı.
        """
        bank = BankConfig(slug="b", name="B", website_url="https://b.test",
                          campaign_paths=["/kampanyalar"],
                          detail_patterns=["/kampanyalar/"])
        body = ("<main><h1>Konut Finansmanı</h1><p>"
                + "Kâr payı oranı %2,05, vade 120 ay, tahsis ücreti yoktur. " * 8
                + "</p></main>")
        pages = {
            "https://b.test/kampanyalar":
                '<a href="/kampanyalar/a">a</a><a href="/kampanyalar/b">b</a>',
            # Aynı gövde; farklı analitik/oturum artığı → farklı ham HTML hash'i
            "https://b.test/kampanyalar/a":
                f"<html><head><title>T</title></head><body>{body}"
                f"<script>var sid='sess-11111111';</script></body></html>",
            "https://b.test/kampanyalar/b":
                f"<html><head><title>T</title></head><body>{body}"
                f"<script>var sid='sess-99999999';</script></body></html>",
        }
        diag: dict = {}
        docs = collect_live(bank, bundle=FetcherBundle(static=FakeFetcher(pages)),
                            robots=RobotsCache(fetcher=lambda u: (404, None)),
                            report=diag)
        self.assertEqual(len(docs), 1,
                         "HTML gürültüsü tekilleştirmeyi kaçırmamalı")
        self.assertTrue(any("mukerrer" in n for n in diag.get("notes", [])),
                        "atlanan mükerrer belge rapora not edilmeli")

    def test_robots_disallow_is_respected_and_reported(self):
        bank = BankConfig(slug="b", name="B", website_url="https://b.test",
                          campaign_paths=["/kampanyalar"],
                          detail_patterns=["/kampanyalar/"])
        pages = {"https://b.test/kampanyalar":
                 '<a href="/kampanyalar/konut">K</a><a href="/kampanyalar/gizli">G</a>',
                 "https://b.test/kampanyalar/konut": _page("Konut"),
                 "https://b.test/kampanyalar/gizli": _page("Gizli")}
        robots = RobotsCache(fetcher=lambda u: (
            200, "User-agent: *\nAllow: /\nDisallow: /kampanyalar/gizli\n"))
        report: dict = {}
        docs = collect_live(bank, bundle=FetcherBundle(static=FakeFetcher(pages)),
                            robots=robots, report=report)
        self.assertEqual([d.title for d in docs], ["Konut"])
        blocked = [b["url"] for b in report["blocked"]]
        self.assertIn("https://b.test/kampanyalar/gizli", blocked)

    def test_save_docs_writes_sidecar_meta(self):
        doc = RawDoc(bank_slug="b", source_url="https://b.test/kampanyalar/konut-2026",
                     clean_text="Kâr payı %1,99", scraped_at=utc_now_iso(),
                     content_hash="deadbeef", collection_method=METHOD_LIVE,
                     title="Konut", http_status=200, raw_html="<html>x</html>")
        with tempfile.TemporaryDirectory() as tmp:
            written = save_docs([doc], tmp)
            live = Path(tmp) / "b" / "live"
            self.assertTrue((live / "kampanyalar-konut-2026.html").is_file())
            self.assertTrue((live / "kampanyalar-konut-2026.txt").is_file())
            meta = json.loads(
                (live / "kampanyalar-konut-2026.txt.meta.json").read_text("utf-8"))
            self.assertEqual(meta["content_hash"], "deadbeef")
            self.assertEqual(meta["collection_method"], METHOD_LIVE)
            self.assertEqual(meta["source_url"], doc.source_url)
            self.assertEqual(len(written), 2)

    def test_manual_dir_scaffolding_and_method_tagging(self):
        banks = load_banks(CONFIG)
        with tempfile.TemporaryDirectory() as tmp:
            made = ensure_manual_dirs(banks, tmp)
            self.assertEqual(len(made), len(banks))
            manual = Path(tmp) / "albaraka" / "manual"
            self.assertTrue((manual / ".gitkeep").is_file())
            (manual / "elle.txt").write_text(
                "Kâr payı oranı %1,89 ile konut finansmanı. " * 5, encoding="utf-8")
            bank = next(b for b in banks if b.slug == "albaraka")
            docs = collect_from_fixtures(bank, tmp, recursive=True)
            self.assertEqual(len(docs), 1)
            self.assertEqual(docs[0].collection_method, METHOD_MANUAL)
            self.assertTrue(docs[0].content_hash)

    def test_fixture_scan_is_shallow_by_default(self):
        """Varsayılan (recursive=False) demo fixture'larını korur — live/ sızmaz."""
        banks = load_banks(CONFIG)
        bank = next(b for b in banks if b.slug == "albaraka")
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp) / "albaraka"
            (base / "live").mkdir(parents=True)
            (base / "sentetik.txt").write_text("Kâr payı %2,05 konut. " * 20, "utf-8")
            (base / "live" / "canli.txt").write_text("Kâr payı %1,50 taşıt. " * 20, "utf-8")
            self.assertEqual(len(collect_from_fixtures(bank, tmp)), 1)
            self.assertEqual(len(collect_from_fixtures(bank, tmp, recursive=True)), 2)

    def test_url_to_slug_strips_extensions_and_tr_chars(self):
        self.assertEqual(
            url_to_slug("https://b.test/tr-tr/kampanyalar/Sayfalar/konut-2026.aspx"),
            "kampanyalar-konut-2026")
        # kök URL'de yol yok → alan adına düşülür (dosya adı yine de tekil kalır)
        self.assertEqual(url_to_slug("https://b.test/"), "b-test")
        self.assertEqual(url_to_slug("https://b.test/kampanyalar/İş-Yeri"),
                         "kampanyalar-is-yeri")


class TestRateLimiter(unittest.TestCase):
    def test_per_domain_default_is_three_seconds(self):
        self.assertEqual(RateLimiter().delay_s, 3.0)

    def test_first_call_does_not_block(self):
        limiter = RateLimiter(delay_s=99)
        limiter.wait("https://a.test/x")   # ilk çağrı beklemez
        self.assertIn("a.test", limiter._last)


class TestBanksConfigIntegrity(unittest.TestCase):
    def test_every_bank_has_a_discovery_entry_point(self):
        for bank in load_banks(CONFIG):
            with self.subTest(bank=bank.slug):
                self.assertTrue(bank.campaign_paths or bank.sitemap_urls,
                                "keşif için en az bir başlangıç noktası gerekir")
                self.assertIn(bank.scrape_mode, ("static", "js", "manual"))
                self.assertTrue(bank.website_url.startswith("https://"))

    def test_js_banks_are_declared(self):
        js = {b.slug for b in load_banks(CONFIG) if b.scrape_mode == "js"}
        self.assertIn("adil-katilim", js)   # Nuxt SPA — tarayıcı zorunlu
        self.assertIn("hayat-finans", js)


if __name__ == "__main__":
    unittest.main()


class TestFormIcerikliSayfaMetinCikarimi(unittest.TestCase):
    """`<form>` sarmalı sayfalarda içerik atılmamalı.

    ## Neden bu sınıf var

    `_extract_main_text` agresif geçişte `<form>` atıyor (ASP.NET WebForms
    sayfaları tüm gövdeyi form içine sarar). Koruma yalnızca sonuç
    `MIN_TEXT_CHARS`(200) altında kalırsa devreye giriyordu.

    2026-08-04 ölçümü: Ziraat Bankası ürün sayfalarında `<main>`/`<article>`
    YOK ve içerik `<form>` içinde. Agresif geçiş **1503 karakter** döndürüyordu
    — çerez bandı + promo bloğu, yani saf çerçeve. 1503 > 200 olduğu için
    koruma hiç ateşlenmedi; belge "başarıyla" yazıldı. Dahası her sayfa AYNI
    1503 karakteri ürettiğinden metin tekilleştirmesi 45 sayfayı 2 belgeye
    indirdi ve hasat `0 başarısız URL` diyerek başarılı göründü.

    Temkinli geçiş aynı sayfada 4277 karakter ve gerçek ürün bilgisini verdi
    (oran 2,8x) → `FORM_CONTENT_RATIO = 2.0`.
    """

    def _sayfa(self, cerceve: str, form_icerik: str) -> str:
        return (f"<html><body><header>{cerceve}</header>"
                f"<form runat='server'>{form_icerik}</form>"
                f"<footer>alt bilgi</footer></body></html>")

    def test_form_icerigi_cerceveden_buyukse_korunur(self):
        cerceve = "Cerez politikamizi inceleyebilirsiniz. " * 8   # ~300 krk
        icerik = "Tuketici Kredisi 36 aya kadar vade uygun faiz orani. " * 30
        metin = collector._extract_main_text(self._sayfa(cerceve, icerik))
        self.assertIn("36 aya kadar", metin,
                      "form içindeki ÜRÜN bilgisi atıldı — sessiz içerik kaybı")

    def test_mutlak_esik_asilsa_bile_oran_korumasi_calisir(self):
        """EN KRİTİK: çerçeve 200 karakterden UZUN olsa da koruma çalışmalı."""
        cerceve = "x " * 400                                      # 800 krk > 200
        icerik = "y " * 1200                                      # oran ~2.9x
        metin = collector._extract_main_text(self._sayfa(cerceve, icerik))
        self.assertGreater(len(metin), 1000,
                           "1503 karakterlik çerçeve 'başarılı' sayıldı (eski hata)")

    def test_form_sadece_basvuru_kutusuysa_cerceve_bozulmaz(self):
        """Form küçükse (gerçek başvuru kutusu) agresif sonuç korunur."""
        icerik_govde = "<main>" + ("Gercek urun metni burada. " * 60) + "</main>"
        html = (f"<html><body><nav>menu</nav>{icerik_govde}"
                f"<form>Ad Soyad TC Kimlik</form></body></html>")
        metin = collector._extract_main_text(html)
        self.assertIn("Gercek urun metni", metin)
        self.assertNotIn("TC Kimlik", metin, "başvuru formu içeriğe karıştı")

    def test_formsuz_sayfa_ikinci_gecis_denemez(self):
        html = "<html><body><nav>menu</nav><main>" + ("icerik " * 80) + "</main></body></html>"
        metin = collector._extract_main_text(html)
        self.assertIn("icerik", metin)
        self.assertNotIn("menu", metin)


class TestBosSonucSayfasiReddi(unittest.TestCase):
    """"İçerik yok" diyen kabuklar korpusa girmemeli.

    2026-08-04 ölçümü: İş Bankası'nın yanlış giriş noktasından gelen 30 belge
    (257'nin %12'si) "Kampanya bulunamadı." diyen 202-262 karakterlik boş
    kabuklardı. Mevcut 200 karakter eşiğinin hemen ÜSTÜNDE oldukları için
    geçiyorlardı ve hasat `0 başarısız URL` diyerek başarılı görünüyordu.

    Eşiği yükseltmek çözüm DEĞİL: geçerli ama kısa bir VakıfBank ürün listesi
    294 karakter. Bu yüzden işaretçi + kısalık birlikte aranıyor.
    """

    def test_bos_kampanya_kabugu_reddedilir(self):
        metin = ("Ana Sayfa > Kampanyalar > Taşıt Kredisi Kampanyaları > 0 km "
                 "Ticari Taşıt Kredisi Kampanyası. Kampanya bulunamadı. "
                 "Güncel kampanyalara buradan ulaşabilirsiniz.")
        self.assertTrue(collector._is_empty_result_page(metin))

    def test_kisa_ama_gecerli_urun_listesi_korunur(self):
        """294 karakterlik gerçek VakıfBank sayfası — düşürülmemeli."""
        metin = ("Proje ve Yatırım Kredileri Proje Finansmanı Kredileri Proje ve "
                 "yatırımların finansmanına yönelik olarak uygun alternatifler "
                 "VakıfBank'ta. Detaylı Bilgi IPARD Hibe Destekli Yatırım Kredisi "
                 "IPARD kapsamındaki yatırımlarınıza ilişkin IPARD Hibe Destekli "
                 "Yatırım Kredisi VakıfBank'ta. Detaylı Bilgi")
        self.assertFalse(collector._is_empty_result_page(metin))

    def test_uzun_sayfada_gecen_bulunamadi_belgeyi_dusurmez(self):
        """SSS'de 'bulunamadı' geçen UZUN sayfa geçerli içeriktir."""
        metin = ("Tüketici Kredisi 36 aya kadar vade uygun faiz oranı. " * 30 +
                 " Aradığınız kayıt bulunamadı ise şubelerimize başvurun.")
        self.assertGreater(len(metin), collector.EMPTY_RESULT_MAX_CHARS)
        self.assertFalse(collector._is_empty_result_page(metin))

    def test_kabul_esigi_cikarim_esiginden_ayri(self):
        """Tek sabite bağlamak, birini değiştirince diğerini sessizce bozar."""
        self.assertIsNot(collector.MIN_DOC_CHARS, None)
        self.assertIn("MIN_DOC_CHARS", dir(collector))
