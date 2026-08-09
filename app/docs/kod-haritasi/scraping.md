# Kod Haritası — `src/scraping/`

> Salt okur analizle üretildi (2026-08-09). Kaynak: `src/scraping/*.py` (14 dosya,
> 4928 satır) + `config/banks.yaml` (585 satır). Aşağıdaki her ölçüm, kodun
> içindeki docstring/yorumdan **aynen** aktarılmıştır; yorum yoksa "belirsiz"
> yazılmıştır.

---

## 1. Tek cümlelik özet

Bu katman, `config/banks.yaml`'daki banka tariflerinden yola çıkıp robots.txt'e
uyarak ve rate-limit uygulayarak katılım bankası sitelerini **beş ayrı turda**
(aktif kampanya · ürün · arşiv · PDF belge · kâr payı oranı) gezer, her belgeyi
zorunlu provenance sidecar'ıyla `data/raw/` altına yazar ve turlar arası farkı
ölçüp bayat belgeleri kanıta bağlayarak arşive taşır.

---

## 2. Dosya dosya

### `config.py` (175 satır) — banka tarifi yükleyici
`BankConfig` dataclass'ı + `load_banks(path)`. `banks.yaml`'ı **pyyaml varsa
onunla**, yoksa şemaya özel `_mini_parse` ile okur (saf stdlib fallback; liste
öğeleri ':' içerebildiği için liste tespiti aktif liste anahtarına göre yapılır,
':' varlığına göre değil). `BankConfig` beş turun ayarlarını tek yerde toplar:
`campaign_paths`/`detail_patterns`, `product_*`, `archive_*`, `document_*`,
`extra_hosts`, tur başına `max_*_docs`. `_KNOWN_KEYS` dışındaki anahtarlar
sessizce yok sayılır (ileri uyumluluk). Çağıranlar: `harvest*.py`,
`src/pipeline.py`, `src/api/main.py`, `scripts/`.

### `fetcher.py` (347 satır) — HTTP / tarayıcı çekim katmanı
Üç sınıf: `StaticFetcher` (requests, `method="live"`), `BrowserFetcher`
(Playwright, `method="browser"`), `FetcherBundle` (`for_mode()` — `scrape_mode`
alanının **gerçek dispatch noktası**). `RateLimiter` domain başına minimum bekleme
uygular. `StaticFetcher.fetch_bytes` PDF turu içindir. `BrowserFetcher.fetch_all_pages`
sayfalanmış liste sayfalarını tıklayarak gezer. Her yol `FetchResult` döner;
bağımlılık yoksa `available=False` ile zarifçe düşer, çökmez.

### `robots.py` (238 satır) — robots.txt uyumu
`RobotsCache` origin başına robots.txt'i bir kez çeker; `parse_robots` en spesifik
eşleşen user-agent grubunu seçer, `RobotsPolicy.allows` REP'e göre en uzun deseni
uygular (eşit uzunlukta `Allow`, `Disallow`'u yener). robots.txt çekilemezse REP
gereği **izin varsayılır** ve bu gerekçe raporlanır. `--ignore-robots` bayrağı
denetimi kapatabilir ama karar yine raporlanır ("sessizce ihlal yok"). Saf
stdlib; HTTP çekimi enjekte edilebilir (test ağa çıkmaz). Çağıranlar: her
`harvest*` modülü, `collector`, `rates`, `reconcile_stale`.

### `discover.py` (471 satır) — URL keşfi (iki aşamalı gezinme)
Tek çekirdek `_discover()` üzerine dört giriş: `discover` (kampanya),
`discover_products`, `discover_archive`, `discover_documents`. Aşama 1 sitemap
(`<sitemapindex>` özyinelemeli, `max_depth=2`, `max_sitemaps=12`), aşama 2 liste
sayfasından bağlantı hasadı (bs4 varsa bs4, yoksa regex). `same_site()` alt alan
ve varsayılan port farkını tolere eder; ayrı kayıtlı alanlar `extra_hosts` ile
eklenir. `max_docs` kırpması kör değil — `rank` / `rank_products` /
`rank_documents` deterministik önceliklendirme yapar.

### `collector.py` (677 satır) — toplama çekirdeği + diske yazma
Katmanın kalbi. `RawDoc` (zorunlu provenance alanları) ·
`_extract_main_text` (iki geçişli HTML→metin) · `collect_live` (keşif + getirme +
eleme + tekilleştirme) · `collect_documents` (PDF turu) · `collect_from_fixtures`
(offline) · `save_docs` (iki katmanlı çakışma koruması + `.meta.json` sidecar) ·
`collect` (auto/live/fixture dispatch'i). Alt klasör sabitleri burada tanımlı:
`live/`, `manual/`, `products/`, `archive/`, `docs/`. `collect_live`'a
`discover_fn` enjekte edilebilir — kampanya, ürün ve arşiv turları aynı gövdeyi
paylaşır, yalnız URL kümesi değişir.

### `pdf.py` (145 satır) — PDF metin çıkarımı
`looks_like_pdf` (Content-Type'a **güvenilmez**, karar `%PDF-` bayt imzasına
göre), `extract_pdf_text` (pypdf, `max_pages=200`, şifreli PDF'te boş parola
denenir), `_join_pages` (3+ sayfada birebir tekrar eden satır = altbilgi, bir kez
bırakılır). `MIN_PDF_TEXT_CHARS = 200` altı "metin katmanı yok / taranmış olabilir"
notu üretir. Yalnızca `collector.collect_documents` çağırır.

### `rates.py` (1091 satır) — kâr payı oranı adaptörleri
Beşinci turun motoru. `RateQuote` / `RateGrid` şemaları + `RateAdapter` taban
sınıfı + beş banka adaptörü: `EmlakKatilimAdapter` (JSON ucu),
`AlbarakaAdapter` (sayfaya gömülü katalog), `KuveytTurkBrowserAdapter`
(Playwright ile hesaplama aracını sürme, `_PlaywrightDriver` + `_EXTRACT_JS`),
`TurkiyeFinansTableAdapter` (yayımlanmış HTML tablo, 5 para birimi sekmesi),
`VakifKatilimBlockedAdapter` (**kayıt tutucu** — oran toplanamıyor, gerekçesi
raporlanıyor). Kayıt `RATE_ADAPTERS` sözlüğüyle; `adapter_for(slug)` ile çözülür.
Yalnızca `harvest_rates.py` çağırır.

### `harvest.py` (214 satır) — 1. tur CLI (aktif kampanya)
`harvest()` tüm bankaları gezer, `collect_live` + `save_docs(subdir="live")`
çalıştırır, banka bazlı tanılama toplar; `render_report()` markdown rapor üretir
(`data/raw/_collection_report.md`). `--timeout`, `--delay`, `--banks`,
`--max-docs`, `--ignore-robots`, `--json-out` bayrakları. `DEFAULT_USER_AGENT`
buradan `harvest_products`'a da re-export edilir.

### `harvest_products.py` (165 satır) — 2. tur CLI (ürün sayfaları)
`collect_live(discover_fn=discover_products)` + `save_docs(subdir="products")`.
Ayırt edici yanı `field_coverage()`: tur ÖNCE ve SONRA `data/raw`'daki tüm
`.txt`'leri `src.extraction.rules.extract.extract_all` ile tarayıp alan sayımı
yapar — bu turun başarı ölçütü belge sayısı değil, `kar_payi_orani`/`vade_ay`
taşıyan belge sayısıdır. Çıktı `data/raw/_products_report.json`.

### `harvest_extra.py` (227 satır) — 3. ve 4. tur CLI (arşiv + PDF)
`--round all|archive|docs`. Arşiv turu `collect_live(discover_fn=discover_archive,
campaign_status="expired")` → `archive/`; belge turu `collect_documents` →
`docs/`. Rapor: `data/raw/_extra_report.md`.

### `harvest_rates.py` (254 satır) — 5. tur CLI (oran)
Yalnızca `adapter_for(slug)` dönen bankaları hedefler; çıktı
`data/raw/<banka>/rates/quotes.jsonl` + `quotes.jsonl.meta.json` (kayıt sayısı,
istek sayısı, ızgara). `--dry-run` istek atmadan kapsam raporu verir. Rapor
`data/raw/_rates_report.md` "adaptörü olmayan bankalar" bölümünü de yazar.

### `snapshot.py` (496 satır) — manifest + turlar arası fark
`build` alt komutu `.meta.json` sidecar'larından manifest üretir (`--since` ile
bayat kayıtları dışlar, `--from-git <ref>` ile `.txt` içeriklerini git'ten okur —
`_GitTextReader`, `git cat-file --batch` + `git ls-tree`). `diff` alt komutu iki
manifesti **aynı bucket içinde** karşılaştırıp `kayip` / `yeni` / `degisti` /
`ayni` kümelerini ve markdown raporu üretir.

### `reconcile_stale.py` (395 satır) — bayat belge mutabakatı
`snapshot.diff_manifests`'in `kayip` kümesini alır, her URL'i **yeniden çeker** ve
kararı kanıta bağlar (`kaldirilmis` / `suresi_dolmus` / `gecersiz_kilindi` /
`kesif_acigi` / `dogrulanamadi`). `apply_moves` yalnızca `--apply` ile çalışır,
hiçbir dosya silinmez — `live/` → `archive/` taşınır ve `.meta.json` içine
`removal_check` kanıt bloğu yazılır.

### `run.py` (33 satır) — pipeline CLI'ı
Bu dizindeki tek "hasat etmeyen" giriş: `Repository` açar ve
`src.pipeline.run_pipeline`'ı çağırır (`--mode auto|live|fixture`), kaydedilen
kampanya ve tespit edilen çelişki sayısını basar.

---

## 3. Veri akışı — banka sayfasından `campaigns` tablosuna

**A) Hasat (ağdan diske).** `python -m src.scraping.harvest`:

```
main() → harvest()
  load_banks(config/banks.yaml)                       config.py
  ensure_manual_dirs(...)                             collector.py
  FetcherBundle(StaticFetcher, BrowserFetcher) + RateLimiter(delay_s)
  RobotsCache(user_agent, ignore=...)
  banka döngüsü:
    collect_live(bank, bundle, robots, max_docs, report)          collector.py
      bundle.for_mode(bank.scrape_mode)  → static | browser       fetcher.py
      guarded_fetch = robots.allows(url) → fetcher.fetch(url)     robots.py
      fetch_pages   = fetcher.fetch_all_pages (yalnız browser'da) fetcher.py
      discover(bank, guarded_fetch, fetch_pages=...)              discover.py
        ├─ collect_sitemap_urls(...)      → sitemap adayları
        ├─ _listing_pages(...)            → liste sayfası/sayfaları
        ├─ extract_links + normalize_url + same_site + matches
        └─ rank(...)[:max_docs]           → kırpma
      URL döngüsü:
        guarded_fetch(url) → FetchResult
        content_hash(html)               → provenance (ham baytlar)
        _extract_main_text(html)         → agresif geçiş, gerekirse temkinli
        len(text) < MIN_DOC_CHARS        → atla + rapora not
        _is_empty_result_page(text)      → atla + rapora not
        _text_key(text) ∈ seen_texts     → mükerrer, atla + not
        RawDoc(... collection_method=fetcher.method ...)
    save_docs(docs, raw_dir, subdir="live")                       collector.py
      url_to_slug → stem; `used` + `_baska_belgeye_ait` çakışma koruması
      → <stem>.html + <stem>.txt + <stem>.txt.meta.json
  render_report(summary) → data/raw/_collection_report.md
```

Ürün turu aynı gövdeyi `discover_fn=discover_products` + `subdir="products"` ile,
arşiv turu `discover_fn=discover_archive` + `campaign_status="expired"` +
`subdir="archive"` ile koşar. PDF turu ayrı gövdededir:
`collect_documents` → `discover_documents` → `StaticFetcher.fetch_bytes` →
`pdf.looks_like_pdf` → `pdf.extract_pdf_text` → `save_docs(subdir="docs")`
(PDF orijinali de `.pdf` olarak saklanır).

**B) Diskten `campaigns` tablosuna.** `src/pipeline.py::run_pipeline`:

```
load_banks(banks.yaml)                              scraping/config.py
banka döngüsü:
  repo.upsert_bank(name, slug, website_url, bddk_active)          → banks tablosu
  _collect_for_mode(bank, raw_dir, mode, scraped_at)
    mode=corpus  → pipeline.collect_corpus  (data/raw/<slug>/**/*.txt, özyinelemeli)
    mode=fixture → collector.collect_from_fixtures (yalnız <slug>/ KÖKÜ)
    mode=live    → collector.collect_live
    mode=auto    → collect_live, boşsa collect_from_fixtures
belge döngüsü:
  normalize_text(doc.clean_text)                    preprocessing/clean.py
  clf.classify(text)                                extraction/ner/classifier.py
  build_campaign(text, bank_slug, source_url, llm, campaign_type)
                                                    extraction/reconcile.py
  detect_contradictions(campaign)                   comparison/contradiction.py
  repo.insert_campaign(campaign, clean_text, scraped_at)          → campaigns tablosu
```

`clean_text` ve `source_url`/`scraped_at` doğrudan `RawDoc`'tan gelir; yani
provenance sidecar'ı DB'ye kadar taşınır. Oran turu (`rates/quotes.jsonl`) bu
akışa **girmez** — `campaigns` metni değil, yapısal alan olarak kullanılır
(`rates.py` modül başlığı).

**C) Zamansal akış (opsiyonel, iki hasat turu arasında).**

```
snapshot build --from-git HEAD --out önceki.json     (eski turun .txt'leri git'ten)
snapshot build --since <ISO> --out yeni.json
snapshot diff  --before önceki.json --after yeni.json → kayip/yeni/degisti/ayni
reconcile_stale --before ... --after ...              → kuru koşu, kanıtlı karar
reconcile_stale ... --apply                           → live/ → archive/ + removal_check
```

---

## 4. Önemli kararlar ve GEREKÇELERİ

Bu bölüm docstring'lerde gömülü ölçümleri aynen aktarır.

### 4.1 `scrape_mode` gerçekten dispatch edilir
Alan "önceden ayrıştırılıp yok sayılıyordu, bu yüzden js bankaları sessizce boş
dönüyordu" (`collector.py` modül başlığı). Dispatch noktası tek yerde:
`FetcherBundle.for_mode()`.

### 4.2 İki geçişli metin çıkarımı — ve `<form>` oranı
`trafilatura` **kullanılmıyor**: "lisansı doğrulanmadı"
(`docs/model-license-audit.md`). Yerine iki geçiş:

- **Agresif:** script/style + header/footer/nav/**form** atılır, `<main>`/`<article>`
  tercih edilir.
- **Temkinli:** yalnız script/style atılır, tüm gövde alınır.

Temkinli geçiş şart, çünkü ASP.NET WebForms siteleri (ör. Türkiye Finans) tüm
sayfayı `<form runat="server">` içine sarar; agresif geçiş sayfayı komple siler
ve "belge sessizce kaybolurdu".

`FORM_CONTENT_RATIO = 2.0` gerekçesi (**2026-08-04 ölçümü**): Ziraat Bankası ürün
sayfalarında `<main>`/`<article>` yok, içerik `<form>` içinde. Agresif geçiş
**1503 karakter** döndürüyordu — çerez bandı + promo bloğu, yani saf çerçeve.
`1503 > MIN_TEXT_CHARS` olduğu için koruma hiç ateşlenmiyor, belge "başarıyla"
yazılıyordu; üstelik her sayfa aynı 1503 karakteri ürettiğinden metin
tekilleştirmesi **45 sayfayı 2 belgeye** indiriyordu. Temkinli geçiş aynı sayfada
**4277 karakter** ve gerçek ürün bilgisi veriyor → oran **2,8x**. Eşik 2.0
seçildi (ölçülen 2,8'in altında; normal sayfaların agresif/temkinli oranı
**~1,2–1,5** bandında). Koruma yalnızca `<form>` varken çalışır.

### 4.3 `MIN_TEXT_CHARS` ile `MIN_DOC_CHARS` bilinçli olarak ayrı sabit
İkisi de 200 ama "aynı şey değil": ilki hangi **çıkarım geçişinin** kullanılacağına,
ikincisi belgenin **korpusa girip girmeyeceğine** karar verir. "Tek sabite
bağlamak birini değiştirince diğerini sessizce bozar."

### 4.4 Boş sonuç sayfası tespiti: işaretçi VE kısalık birlikte
**2026-08-04 ölçümü:** İş Bankası'nın yanlış giriş noktasından gelen **30 belgesi**
"Kampanya bulunamadı." diyen **202–262 karakterlik** boş kabuklardı —
`MIN_DOC_CHARS`'ın hemen üstünde. Eşiği yükseltmek çözüm değil: geçerli ama kısa
bir VakıfBank ürün listesi **294 karakter** ve korunmalı. Bu yüzden
`_EMPTY_RESULT_MARKERS` + `EMPTY_RESULT_MAX_CHARS = 600` **birlikte** aranıyor;
uzun bir SSS sayfasında "bulunamadı" geçmesi belgeyi düşürmez.

### 4.5 Tekilleştirme TEMİZ METİN üzerinden, ham HTML üzerinden DEĞİL
Ham HTML'de analitik kimlikleri, oturum/CSRF simgeleri ve zaman damgaları her
istekte değişir; aynı sayfa iki kez çekildiğinde hash'ler farklı çıkıyor ve
tekilleştirme kaçırıyordu. **Ölçüm (2026-08-03, 1491 belgelik korpus): 98
mükerrer metin grubu, 215 dosya (~%14).** Tipik sebep iki keşif URL'inin aynı
kanonik sayfaya yönlenmesi. Sonuç: anotasyon bütçesi israfı, metriklerin çifte
sayımı, çelişki şişmesi — **TOGG çelişkisi 2 gerçek bulgu yerine 4
raporlanıyordu**. `content_hash` provenance alanı değişmedi (ham baytların özeti,
yeniden-üretilebilirlik).

### 4.6 `save_docs` iki katmanlı çakışma koruması
1. `used` — aynı çağrı içindeki çakışmalar (zaten vardı).
2. `_baska_belgeye_ait` — **diskteki** çakışmalar. Eskiden yoktu.
   **Ölçülmüş bozulma:** happycard.com.tr'nin liste sayfası Türkiye Finans'ın ana
   kampanya listesini ezdi — **6506 → 2777 karakter**, `source_url` bile değişti.
   Sebep: `url_to_slug` yalnız URL'in YOLUNU kullanır, alan adına bakmaz.

Dosya adı idempotenttir (aynı URL yeniden hasat edilirse ad değişmez): "anotasyonun
`doc_id` eşleşmesi dosya adına dayanıyor ve bir turda dosya adı değişmesi **32
belgenin 10'unu** geçersiz kılmıştı."

### 4.7 Sidecar şeması yalnız dolu alanları yazar
`RawDoc.provenance()` `campaign_status` / `pdf_pages` / `extraction_note`
alanlarını yalnız doluysa ekler — "mevcut **847 sidecar**'ın şeması bozulmasın".

### 4.8 Sayfalama: URL değişmiyor, tıklamak şart
`BrowserFetcher.fetch_all_pages` (yalnız tarayıcı çekicisinde var; `StaticFetcher`'da
yok, `hasattr` ile kontrol edilir). Gerekçe: **Albaraka arşivi, 2026-08-04
tarayıcıyla ölçüldü** — slick karuseliyle sayfalanıyor ve **sayfa değişse de URL
DEĞİŞMİYOR**. Adres numaralandırmak ya da sitemap okumak 2. sayfayı asla getirmez;
hasat sessizce yalnız 1. sayfayı toplar. `_PAGER_JS` site başına özel kod
yazmadan üç yaygın biçimi kapsar (numaralı bağlantı · ileri/sonraki düğmesi ·
slick/swiper noktaları). robots.txt kontrolü `collect_live` içinde bu yol için
**ayrıca** yapılır, çünkü `fetch_all_pages` `guarded_fetch`'i atlar.

### 4.9 Ürün turu neden var: %3,8
İlk tur `/kampanyalar` sayfalarından **292 belge** topladı; **yalnızca 11 belgede
(%3,8) `kar_payi_orani` var** (`harvest_products.py`). Sebep: kampanya sayfaları
"avantajlı oranlarla" deyip ürün sayfasına link verir; oran/vade/tahsis ücreti
ürün sayfalarında yaşar. Aynı ölçüm `discover.DEFAULT_PRODUCT_PATTERNS` yorumunda
tekrarlanıyor.

### 4.10 Ürün keşfinde başlangıç noktası yoksa ana sayfadan gez
"Gerçek veride ölçüldü: Türkiye Finans'ın ne `sitemap_urls`'i ne `product_paths`'i
var (kampanya yolları ASP.NET'e özgü `.aspx` adresleri). Ürün keşfi 0 URL
buluyordu — banka ürün sayfası yayımlamadığı için değil, gezmeye BAŞLAYACAK yer
olmadığı için." Çözüm: `paths = ["/"]`.

### 4.11 Arşiv desenleri çift görevli
`DEFAULT_ARCHIVE_PATTERNS` hem `discover_archive` için **include**, hem `discover`
(aktif tur) için **exclude**'dur. İkincisi olmadan arşiv sayfaları `live/` altına
düşer ve "süresi dolmuş kampanya AKTİF sanılır — karşılaştırma motorunu sessizce
yanıltır (CLAUDE.md §17)". Arşiv turunun boş dönmesi hata değildir:
**2026-08-03 doğrulaması — yalnızca Kuveyt Türk ve Türkiye Finans arşiv
yayımlıyor.**

### 4.12 Ana bilgisayar karşılaştırması `netloc` ile DEĞİL `hostname` ile
`discover._host()`: "Ziraat Bankası'nın site haritası URL'leri varsayılan portu
açıkça yazıyor (`https://www.ziraatbank.com.tr:443/tr/...`); `netloc`
karşılaştırması bunu farklı alan sayıp site haritasındaki **500 URL'nin tamamını**
sessizce atıyordu (2026-08-04'te ölçüldü, **banka 1 belgeyle dönüyordu**)."

### 4.13 `max_docs` kırpması sıralı, kör değil
"max_docs kırpması kör baştan-al olduğunda sitemap'in ilk N kaydı (çoğu kez tek
bir ürün ailesi) geliyordu." Üç ayrı deterministik sıralayıcı var; ürün
sıralamasının önceliği ölçümle belirlendi (2. tur keşif spike'ı): oran/ücret
tarifesi sayfaları oranı METİN olarak yayımlıyor → 0; finansman ürün sayfaları
vade + tahsis ücreti → 1; kart sayfaları en zayıf → 4.

### 4.14 PDF turu: neden PDF, neden pypdf
Ücret/komisyon tarifeleri ve "Ürün Bilgi Formu" belgeleri HTML tablo değil **PDF**
(**2026-08-03 tarayıcı doğrulaması: Emlak Katılım, Dünya Katılım, Türkiye
Finans**). Lisans: **pypdf BSD-3-Clause** uygun; **PyMuPDF (fitz) AGPL olduğu için
KULLANILMAZ** (Apache-2.0 teslimle uyumsuz). PDF'ler her zaman `static`
çekiciyle indirilir — banka `scrape_mode: js` olsa bile: "tarayıcı üzerinden ikili
indirme güvenilmezdir".

### 4.15 Oran turu: HTML'de oran YOK
**Ölçüm (2026-08-03, 1684 belgelik korpus): `kar_payi_orani` yalnızca 73 belgede
var ve finansman ürün sayfalarının HİÇBİRİNDE sayısal değer yok.** Ürün
sayfalarında sadece *etiket* var ("Aylık Kâr Oranı"); değer istemci-taraflı
hesaplama aracının arkasında. Mimari seam: **adaptör KODDA, hangi ürün/tutar/vade
sorulacağı CONFIG'de** (`RateGrid`). Yeni banka = bir sınıf + `RATE_ADAPTERS`'a
bir satır.

### 4.16 `_is_priced` kapısı — uydurma %0 oranı engeller
Emlak Katılım ucu geçersiz (ürün, tutar, vade) üçlüsünde **hata döndürmüyor**:
`Success: true` + `ProfitRate: 0` + `TotalInstallmentAmount == LoanAmount`.
**Doğrulanmış örnekler (2026-08-03):**

| Ürün / tutar / vade | oran | toplam | sonuç |
|---|---|---|---|
| ARACBINEK2EL 1.000.000 TL / 120 ay | 0 | 1.000.000 | geçersiz |
| ARACBINEK2EL 300.000 TL / 36 ay | 4,29 | 701.790 | geçerli |
| IHTIYAC 100.000 TL / 12 ay | 0 | 100.000 | kod yok |

"Bu kapı olmadan geçersiz kombinasyonlar korpusa **%0 kâr payı oranı** olarak
girerdi." Tolerans 1 TL. **Kabul edilen sınır:** gerçek bir %0 kampanyalı
finansman da düşer — "bir oranı YANLIŞ kaydetmek, eksik kaydetmekten daha
kötüdür". Doğrulanmış örnek yanıt (KONUT, 1.000.000 TL, 120 ay):
`ProfitRate 1.99 · TotalCost 27.47 · TotalInstallmentAmount 2635735.62 ·
CommissionAmount 5250 · ExpertiseAmount 11000 · HypothecAmount 3684 ·
TotalExpense 19934`.

### 4.17 Albaraka: katılma hesabı oranı BİLİNÇLİ olarak toplanmıyor
`/plugins/getProfitShareCalculate` robots.txt'te engelli değil, **ama** uç yalnız
`Slug=...&searchUrl=%2Ftr%2Farama` parametreleriyle yanıt veriyor; parametresiz
istekte sunucu bağlantıyı kapatıyor (`RemoteDisconnected`). O parametreli URL ise
robots.txt'in `*search*` / `/*slug` kurallarına takılıyor → **çalışan tek URL
biçimi robots ile engelli**, statik HTML'de de oran yok. Finansman tarafı
etkilenmiyor: **16 ürünün** `profitRate`/vade/tutar sınırı hesaplama sayfasının
HTML'ine JSON olarak gömülü, tek istekle alınıyor. (`_deposit` metodu sınıfta
duruyor ama `quotes()` onu **çağırmıyor** — ölü kod hâline gelmiş.)

### 4.18 Kuveyt Türk: ızgara sürülmüyor, sayfanın kullandığı değer kaydediliyor
**2026-08-03 doğrulaması:** oran JS paketlerinde ve gizli alanlarda yok
(`txtProfilRate` boş); "Ödeme Planı" düğmesine basılınca `id="ProfitRate"`
düğümüne yazılıyor. "Statik hasat bu yüzden oranı **%0** olarak kaydediyordu."

Tutar alanı (`input[name="p1"]`) bir `priceRange`/`moneyformat` eklentisiyle
yönetiliyor ve **programatik değişikliği geri alıyor**. Denenen ve güvenilir
çalışmayan yollar: `fill()`, doğrudan `.value` atama + olay tetikleme, seçim +
`Backspace` + karakter karakter yazma. "Vade alanı oturuyor, tutar oturmuyor; tek
seferlik başarılar yeniden üretilemedi." Bu yüzden adaptör tutarı zorlamaz;
diyalogdaki `Finansman Tutarı` / `Taksit Sayısı` yansıması kaydın tutar/vadesi
olarak alınır — "istenen değer değil, sayfanın gerçekten hesapladığı değer".
Yansıma okunamazsa **kayıt düşürülür**. Bulunmadan önceki hata: "adaptör
500.000/60 istediği hâlde varsayılan 100.000/120 sonucunu kaydediyordu — sessiz
veri bozulması." "Kâr Oranı Belirle" alanı bilinçli boş bırakılır.

### 4.19 Türkiye Finans oran tablosu: para birimi ve sayı biçimi tuzağı
Tek istekle **20 tablo**; tutar dilimi × vade × hesap türü × para birimi.
**5 sekme:** TL · USD · EUR · YAU (altın) · YAG (gümüş). "Sekme tespit edilmezse
**USD %0,61 ile TL %28,03** aynı kümede karışır — karşılaştırma motorunu felaket
biçimde yanıltır (§17)." Panel eşlemesi DOM sırasıyla, **2026-08-03'te 5 sekme /
5 panel olarak doğrulandı**; sayı uyuşmazsa para birimi uydurmak yerine **atlanır**
ve `zip(..., strict=True)` sessiz kırpmayı engeller. Altın/gümüşte dilim GRAM
("50 gr." / "5,000 gr.") → `amount_unit="gram"`. Sayılar **İNGİLİZCE biçimde**
("100,000,000", "28.03"); TR ayrıştırıcı `_num` bunları bozar ("100,000,000" →
virgülü ondalık sanar), bu yüzden ayrı `_num_en` var. "1 Yıldan Uzun Vade" için ay
atanmaz, `note`'a yazılır.

### 4.20 Vakıf Katılım: adaptör var, veri yok — bilinçli kayıt tutucu
**2026-08-03 doğrulaması:** oran sayfasında tablo YOK (tarayıcıda da 0 tablo);
oranlar tek bir PDF'te (`/documents/PerakendeBankacilik/kar-paylasim-oranlari.pdf`)
ve `robots.txt` `/documents/` yolunu **açıkça engelliyor** (yalnız `.jpg/.png/.jpeg`
izinli) → "bu dışlama kazara değil, bankanın bilinçli tercihi". Adaptör kayıtlı ki
rapor "adaptörü yok" demek yerine gerçek gerekçeyi göstersin: "**sessiz eksik,
belgelenmiş eksikten kötüdür**".

### 4.21 Fark raporu: `text_hash` ≠ `content_hash`
`content_hash` ham HTML'in özetidir (tekilleştirme için doğru seçim) ama analitik
/ oturum / zaman damgası gürültüsü yüzünden metin değişmese de değişir. **Ölçüm
(2026-08-03): ham HTML hash'iyle 238 belge "değişmiş" görünüyordu; `git diff` ile
`.txt` içerikleri BİREBİR AYNIYDI.** Bu yüzden `snapshot` ayrıca `text_hash`
tutar ve `diff_manifests` onu tercih eder (`karsilastirma: "metin" | "ham-html"`).
Manifest ham HTML'i kopyalamaz — "**69 MB'lık** korpusu ikiye katlamamak için".

### 4.22 `--since` ve `--from-git` neden şart
Yeniden hasat eski dosyaları **silmez, üzerine yazar**. Sitede artık olmayan bir
Temmuz kampanyası `live/` altında öylece kalır; `--since` süzgeci olmadan yeni
manifest o bayat dosyayı da içerir ve fark raporu onu "hâlâ yayında" sanar —
"yani `kayip` kümesi sessizce boşalır". Simetrik olarak önceki turun `.txt`'leri
yalnız git geçmişinde kalır → `--from-git HEAD`. (`_GitTextReader.list_meta`
komutu depo kökünde koşturur, çünkü `ls-tree` yol belirtimi çalışma dizinine,
`cat-file` ref yolu depo köküne göredir.)

### 4.23 "Hasatta kayıp" ≠ "süresi doldu"
`reconcile_stale` modül başlığındaki karar tablosu:

| Yeniden çekim | Karar |
|---|---|
| 404 / 410 / 451 | gerçekten kaldırılmış → arşive, `expired` |
| 200 + "Süresi Dolmuştur" | yayında ama bitmiş → arşive, `expired` |
| 200 + normal içerik | duruyor → `live/` kalır, **keşif açığı** olarak raporla |
| diğer (5xx, ağ, robots) | karar verilemedi → dokunulmaz, `unverified` |

"Üçüncü satır bedava teşhistir: keşif giriş noktalarımızın neyi kaçırdığını
ölçer." Körlemesine `expired` etiketlemek "veri UYDURMAK olur (§19)". Beşinci
karar `gecersiz_kilindi`: **gerçek vaka (2026-08-03)** — Temmuz turunda Kuveyt
Türk'ün arşiv sayfaları `live/` altına toplanıyordu; arşiv dışlama düzeltmesinden
sonra **aynı 34 URL** `archive/` altına taze hâliyle yazıldı, eski `live/` kopyası
mükerrer oldu. Varsayılan **kuru koşu**; `--apply`'da bile hiçbir dosya silinmez.

### 4.24 `banks.yaml`: `js` bir kez kabul, üç kez reddedildi
- **turkiye-finans → `js` (2026-08-04, kabul).** Zorunlu sebep: happycard.com.tr'ye
  `static` ile **ulaşılamıyor** — sunucu TLS el sıkışmasında yalnız yaprak
  sertifikayı gönderiyor, ara sertifikayı (DigiCert Global G2 TLS RSA SHA256 2020
  CA1) göndermiyor; `openssl` "Verify return code: 21", `requests`+certifi
  `CERTIFICATE_VERIFY_FAILED` ile düşüyor (ölçüldü), `curl` ve Playwright başarılı.
  "StaticFetcher bunu `blocked`a yazıp sessizce geçerdi → **9 kampanya belgesi**
  hiç toplanmazdı." `verify=False` **yapılmadı** (tüm alanlar için güvenlik
  gerilemesi olurdu). Destekleyici ölçüm: `default.aspx` static 11 → js 12 bağlantı;
  `kart-kampanyalari` static 12 → js 14; metin 6506 → 8163 krkt; staticFazla=0.
  **Bedel:** hasat yavaşlıyor, kabul edildi çünkü alternatif sessiz veri kaybı.
- **vakif-katilim → `static` korunuyor.** 41 "kabuk" şüphelisi Playwright ile
  yeniden hasat edildi: metin **33'ünde bayt-aynı**, hiçbirinde içerik artmadı.
  "`js`'e çevirmek hasadı ~10x yavaşlatır, tek karakter kazandırmaz."
- **kuveyt-turk → `static`.** 21 kabuk şüphelisinin **tamamı yanlış pozitif**;
  tarayıcı metni bayt-aynı.
- **turkiye-emlak-katilim → `static`.** 39 şüphelinin **38'inde** tarayıcı metni
  statikle bayt-aynı.

### 4.25 `banks.yaml`: kart markası siteleri — atıf (attribution) kuralı
Eklenenler ölçülmüş kayıp kaynaklarıdır: `milesandsmiles.kuveytturk.com.tr`
(9 kampanya, alt alan → `extra_hosts` gereksiz), `albarakaworldcard.com` →
301'le ana alana düşüyor (`/tr/world-dunyasi/detay/` **37 kampanya**, korpusta 0
belgeydi), `albarakaozel.com` (11 ayrıcalık, **ayrı kayıtlı alan → `extra_hosts`
zorunlu**), `happycard.com.tr` (10 kampanya, 9'u ana ağaçta yok), `hayatpay.com.tr`
(ayrı kayıtlı alan).

Reddedilenler teknik engelden değil **yanlış atıf riskinden** reddedildi:
`bankkart.com.tr` (Ziraat Katılım'ın değil Ziraat **Bankası**'nın kart programı;
ana sayfada "katılım" 0 kez geçiyor) ve `paraf.com.tr` (Emlak Katılım + Dünya
Katılım için — Paraf **ortak** program, Halkbank kampanyalarını da kapsıyor).
"Toplu hasat, Halkbank kampanyalarını Emlak Katılım'a atfederdi." Vakıf
Katılım'ın "VKart" markası için **var olmayan** alan adları tek tek denenip
belgelendi (`vakifkart.com.tr`, `vkart.com.tr`, `vkartdunyasi.com.tr/.com` — DNS
yok; `vkart.com` çözülüyor ama kişisel bir siteye ait).

### 4.26 `banks.yaml`: `max_docs` tavanları ölçüyle yükseltildi
- kuveyt-turk **340** — arşivde 318 aday bulundu (`max_archive_docs: 200`);
  giriş noktası 3 → 6; milesandsmiles 9 + saglamkart 10 = 19 belge ana sitemap'te
  yok, 320'de kalsa kenara itilirlerdi.
- albaraka **180** — 60 → 120 (giriş noktası 1 → 5, gerçekçi beklenti ~2 kat),
  + ölçülen 48 yeni aday (37 + 11) → 168 → yuvarlanarak 180.
- turkiye-finans **100**, hayat-finans **80** (giriş noktası 1 → 2, tavan 2 kat),
  ziraat-katilim **220**, vakif-katilim **110**, emlak **90**, dünya/tom **60**,
  adil **40**.

Genel gerekçe (**2026-08-03**): "max_docs=40 kırpması gerçek kaybettiriyordu
(kuveyt-turk: **475 aday → 39 belge**)". Ayrıca Ziraat'in gerçek kataloğu
`/bireysel/kampanyalar` değil (o sayfa boş: 7 bağlantı, hiçbiri detay değil),
`/kart-kampanyalari` (**191 bağlantı**) + 15 sektör kategorisi — "bu yüzden
yalnızca 5 kampanya toplanabilmişti".

### 4.27 `banks.yaml`: `exclude_patterns` ile liste sayfasını belge saymamak
happycard'ın `.../Sayfalar/default.aspx` yolu `exclude_patterns`'a yazıldı çünkü
`url_to_slug` onu Türkiye Finans'ın ana listesiyle **aynı** `kampanyalar-default`
slug'ına düşürüyordu (bkz. 4.6). Kayıp yok: `_discover` bu yolu `campaign_paths`
girdisi olarak **gezmeye devam ediyor** (`_listing_pages` exclude'a bakmaz),
yalnızca `add()` onu belge listesine koymuyor.

### 4.28 `bddk_active` ≠ `otorite_kaynak` (TKBB vakası)
`bddk_active=False`: gerçek banka, BDDK Liste 77'de aktif değil → **kıyasa girer**.
`otorite_kaynak=True`: banka değil (TKBB) → katalogda ve kıyasta yeri yok.
"İkisini tek alana yıkmak, lisansı düşmüş gerçek bir bankayı da katalogdan
silerdi." Süzme olmadan TKBB `GET /banks` üzerinden "11. banka" olarak dönüyordu.
TKBB'nin `banks:` listesinde durmasının tek nedeni ingest yolunun banka
kayıtlarını `banks.yaml`'dan sürmesi — "burada olmayan bir `data/raw/<slug>/`
klasörü korpusa hiç girmez". Eklenme gerekçesi: korpusta müşarakayı tanımlayan
tek belge yoktu, terim yalnız **6 belgede** ve hepsinde "geçerken anma" biçiminde
geçiyordu.

### 4.29 Zarif bağımlılık düşüşü, her yerde aynı desen
requests / Playwright / bs4 / pypdf / pyyaml yoksa ilgili yol boş sonuç + açık
gerekçe döner, hat çökmez. `harvest*` raporları bu gerekçeleri yazar. Hasat
tamamen offline koşabilir (fixture moduna düşer).

### 4.30 Etik scraping sabitleri
`DEFAULT_USER_AGENT = "AnatoliaAI-Research/1.0 (+TEKNOFEST 2026; arastirma
amacli)"`, `DEFAULT_DELAY_S = 3.0` (CLAUDE.md §14: 2–5 sn, domain başına),
varsayılan timeout 25 sn, PDF indirmede `max_bytes = 40 MB` (aşılırsa içerik
**atılır**, "sessizce kırpılmaz, çünkü yarım PDF ayrıştırıldığında sessiz veri
kaybı olur"), `RateGrid.max_requests = 200` emniyet supabı.

---

## 5. Tuzaklar

**Sessiz başarısızlık noktaları**

1. **`raw_dir` parametresi `verify_stale()`'de kullanılmıyor.** İmzada var
   (`reconcile_stale.py:130`), gövdede hiç okunmuyor; taşıma `apply_moves` içinde
   ayrıca `raw_dir` alıyor. Yanlış `--raw-dir` verilse kuru koşu yine "başarılı"
   görünür.
2. **`AlbarakaAdapter._deposit` ölü kod.** `quotes()` yalnız `_catalog()` çağırıp
   not düşüyor; `_deposit` hiçbir yerden çağrılmıyor. İleride biri robots
   engelinin kalktığını sanıp metodu "zaten var" diye canlı sanabilir.
3. **`KuveytTurkBrowserAdapter._LABELS` / `_FEE_LABELS` sınıf sabitleri
   kullanılmıyor** — gerçek eşleme `_EXTRACT_JS` içindeki JS sözlüklerinde
   **kopyalanmış** durumda. Birini güncelleyip diğerini unutmak sessiz alan kaybı
   üretir.
4. **`max_product_docs` (varsayılan 80) hiçbir kod yolunda okunmuyor.**
   `harvest_products` `max_docs=max_docs or 40` kullanıyor, yani CLI varsayılanı
   **40**. `config/banks.yaml`'da zaten hiçbir bankada `product_*` alanı yok
   (bunlar yalnız `config/banks-classic.yaml`'da tanımlı) → ürün keşfi tümüyle
   `DEFAULT_PRODUCT_PATTERNS` + `paths=["/"]` fallback'ine bağlı.
5. **Fixture modu yalnız `data/raw/<slug>/` KÖKÜNÜ okur.** `collect_from_fixtures`
   varsayılan `recursive=False`; `live/`, `products/`, `archive/`, `docs/`
   görünmez. `pipeline.py` bunu ölçmüş: `fixture` **3 belge**, `corpus` **849
   belge**. Bir zamanlar "eski demo yolu sessizce 3 belge yükleyip 'hazır' diyordu,
   `GET /contradictions` boş dönüyordu".
6. **`collect(mode="auto")` canlı toplama boş dönerse sessizce fixture'a düşer.**
   Ağ kesintisi ile "banka gerçekten kampanya yayımlamıyor" durumu çağıran
   tarafta ayırt edilemez; ayrımı yalnız `report` sözlüğündeki
   `skipped_reason` / `notes` taşır.
7. **`_get_json` başarısızlıkları çift kaydedilmemeli.** Adaptörlerdeki
   `if data is None: continue` yorumları bunu açıkça belirtiyor — "tek başarısızlık
   iki satır görünür" diye ikinci kayıt eklenmiyor. Yeni adaptör yazan biri bunu
   kolayca bozar.
8. **`fetch_all_pages` hata yutar.** İçteki `except Exception: break` ve dıştaki
   `except Exception: return pages` yüzünden yarım gezilmiş sayfalama "başarı"
   gibi döner; tek iz `_listing_pages`'in `result.notes`'a yazdığı satırdır
   (kaç sayfa gezildi / tek sayfa bulundu / gezilemedi ayrımı bilinçli olarak
   raporlanıyor).
9. **robots.txt çekilemezse izin varsayılır** (REP gereği doğru davranış, ama
   "engel yok" ile "engel bilinmiyor" raporda aynı satıra düşmez — `summary()`
   ayırıyor; yine de otomatik bir uyarı yok).
10. **PDF'te metin katmanı yoksa** `extract_pdf_text` boş metin döndürür ve belge
    `blocked`'a düşer; taranmış tarifeler sessizce korpusa girmez (rapor satırı
    dışında iz kalmaz).

**Yeniden üretilemez / kırılgan yerler**

11. **Kuveyt Türk tutar alanı sürülemiyor** (4.18). Docstring'de "tek seferlik
    başarılar yeniden üretilemedi" yazıyor — bu yolu "düzeltmeye" çalışmadan önce
    o notu okuyun.
12. **Site yapısına gömülü regex'ler:** `AlbarakaAdapter._CATALOG_RE`
    (`&quot;ProductCode&quot;` … `XkampMaxAmountManuel`), Türkiye Finans'ın
    `div.tab-wrapper` / `div.tab-item` seçicileri, Kuveyt Türk'ün `#ProfitRate` /
    `input[name="p1"]` / `#maturity` seçicileri, `_EXTRACT_JS`'teki Türkçe etiket
    dizgeleri ("Aylık Kâr Oranı", "Finansman Tutarı"). Sayfa yenilenirse hepsi
    sessizce 0 kayıt üretir — yalnız `notes`'a "bulunamadı, sayfa yapisi degismis
    olabilir" satırı düşer.
13. **`snapshot --from-git` git'e bağlıdır**: `_GitTextReader` `git cat-file
    --batch` alt süreci açar; git yoksa/ref bulunamazsa `list_meta` **boş liste**
    döner ve manifest sessizce 0 kayıtla çıkar.
14. **Mini YAML parser** yalnız `banks.yaml`'ın bilinen yapısını destekler.
    pyyaml kurulu olmayan bir ortamda yeni bir YAML özelliği (çok satırlı dizge,
    iç içe sözlük) kullanılırsa sessizce yanlış ayrıştırılır.

**Bayat kalabilecek durumlar**

15. **`data/raw/` altındaki dosyalar asla silinmez, üzerine yazılır** (4.22). Bu
    katmanın en büyük yapısal riski: sitede artık olmayan bir kampanya `live/`
    altında "aktif" gibi durur. Tek panzehir `snapshot` + `reconcile_stale`
    döngüsünü **düzenli** koşmaktır; koşulmazsa dashboard ve kıyas motoru sessizce
    eski veriyle çalışır.
16. **`banks.yaml`'daki tüm yol/HTTP doğrulamaları 2026-07-30 ve 2026-08-04
    tarihlidir.** "Eski yollar (`/kampanyalar`) 8/10 bankada 404 dönüyordu" —
    aynı çürüme tekrar edebilir. Yeniden doğrulanmadan `max_docs` ve
    `detail_patterns` gerekçeleri geçerli sayılmamalı.
17. **BDDK Liste 77 değişebilir** (CLAUDE.md §13); `bddk_active` alanı elle
    güncelleniyor, otomatik doğrulama yok.
18. **Ölçüm sayıları farklı korpus boyutlarına ait** — 292 / 847 / 849 / 1491 /
    1684 belge gibi. Bir docstring'deki oranı bugünkü korpusa doğrudan uygulamak
    yanıltıcı olur; her sayı kendi tarihiyle birlikte okunmalı.
19. **Rapor dosyaları her koşuda ezilir** (`_collection_report.md`,
    `_extra_report.md`, `_rates_report.md`, `_products_report.json`). Elle not
    eklenirse kaybolur — dosyaların başındaki uyarı bunu söylüyor;
    `data/raw-classic/_collection_report.md` içinde elle korunması gereken bir
    blok olduğuna dair not var.

---

## 6. Dış bağımlılıklar ve nerede kullanıldıkları

| Bağımlılık | Lisans notu (koddan) | Kullanım yeri | Yoksa ne olur |
|---|---|---|---|
| `requests` | — | `fetcher.StaticFetcher` (`fetch`, `fetch_bytes`), `robots._default_fetcher`, `rates.RateAdapter._get_json` (fetcher'ın `_session`'ını ödünç alır) | `available=False`; tur "requests kurulu degil" notuyla atlanır. robots `urllib`'e düşer |
| `beautifulsoup4` (bs4) | — | `collector._extract_main_text` / `_soup_text`, `discover.extract_links`, `rates.TurkiyeFinansTableAdapter.quotes` | metin çıkarımı `normalize_text(html)`'e, bağlantı çıkarımı `_HREF_RE` regex'ine düşer; TF tablo adaptörü boş döner |
| `playwright` | — | `fetcher.BrowserFetcher` (`fetch`, `fetch_all_pages`, `_PAGER_JS`), `rates._PlaywrightDriver` | `unavailable_reason` ile zarif atlama; `js` bankaları toplanmaz, sayfalama devre dışı |
| `pypdf` | **BSD-3-Clause — uygun.** PyMuPDF (fitz) **AGPL olduğu için kullanılmaz** | `pdf.extract_pdf_text` | "pypdf kurulu degil — PDF metni cikarilamadi" |
| `pyyaml` | — | `config._parse` | `_mini_parse` (saf stdlib) devreye girer |
| `trafilatura` | **KULLANILMIYOR — lisansı doğrulanmadı** (`docs/model-license-audit.md`) | — | yerine ev yapımı iki geçişli `_extract_main_text` |
| `git` (CLI) | — | `snapshot._GitTextReader`, `_repo_prefix` (`rev-parse`, `ls-tree`, `cat-file`) | boş liste / boş önek döner |
| stdlib | — | `hashlib`, `json`, `re`, `unicodedata`, `urllib.parse`, `argparse`, `dataclasses`, `subprocess`, `io`, `html`, `time`, `collections` | — |

**Proje içi bağımlılıklar:** `..preprocessing.clean.normalize_text`
(`collector`, `pdf`), `..comparison.contradiction._SELF_EXPIRED`
(`reconcile_stale`, `ImportError` yakalanıp yerel regex'e düşülür),
`src.extraction.rules.extract.extract_all` (`harvest_products.field_coverage`),
`..db.repository` + `..pipeline` (`run.py`).

**Bu katmanı çağıranlar:** `src/pipeline.py` (`collector`, `config`),
`src/api/main.py` (`config.load_banks` — `otorite_kaynak` süzmesi),
`src/chatbot/run_safety_eval.py`, `scripts/reextract_raw.py`,
`scripts/latency_bench.py`, `scripts/sample_gold_v2.py`,
`scripts/crosscheck_rates.py`, ve `tests/test_scraping_*.py`,
`tests/test_rates.py`, `tests/test_snapshot_diff.py`,
`tests/test_reconcile_stale.py`, `tests/test_pipeline_corpus.py`.
