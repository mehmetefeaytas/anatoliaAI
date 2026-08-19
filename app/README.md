# Anatolia AI — Katılım Bankacılığı Kampanya Bilgi Çıkarımı

[![CI](https://github.com/mehmetefeaytas/anatoliaAI/actions/workflows/ci.yml/badge.svg)](https://github.com/mehmetefeaytas/anatoliaAI/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)
[![Testler](https://img.shields.io/badge/testler-3159%20ye%C5%9Fil-brightgreen.svg)](tests/)
[![Değişmez denetimi](https://img.shields.io/badge/de%C4%9Fi%C5%9Fmez%20denetimi-1782%20belge%20%C2%B7%200%20ihlal-brightgreen.svg)](eval/properties.py)

TEKNOFEST 2026 Türkçe Yapay Zekâ Dil Ajanları Yarışması — 2. Senaryo
(Bilişim Vadisi). Türkiye'deki katılım bankalarının kampanya/ürün metinlerinden
finansal bilgileri otomatik çıkaran, normalize eden, sınıflandıran ve
karşılaştıran; **dashboard + chatbot** ile sunan **tamamen açık kaynak, on-premise,
offline** çalışabilen bir NLP sistemi.

> Mimari kararlar ve gerekçeler için bir üst dizindeki bilgi arşivine bakın:
> `../decisions/`, `../syntheses/teknik-cozum-mimarisi.md`. Operasyon kılavuzu:
> [`CLAUDE.md`](CLAUDE.md).

## Lisans ve Kısıtlar
- Lisans: **Apache-2.0** (`LICENSE`).
- Ücretli API/servis/yazılım **kullanılmaz**; internet olmadan çalışır.
- Yalnızca Apache/MIT/BSD lisanslı model ağırlıkları.

## Mimari (özet)
"Önce Kural, Sonra LLM" hibrit çıkarım — **teslim edilen alan çıkarımı İKİ
katmandır**:
```
scrape → clean → preprocess → extract (kural [birincil] → LLM [yalnız boşluklar])
→ reconcile → normalize → PostgreSQL → compare
→ dashboard + hibrit chatbot (text-to-SQL + RAG)
```

> **Neden "NER" katmanı bu okta YOK.** `CLAUDE.md` §3'teki üç katmanlı tasarım
> PLANDIR; ikinci katman teslim edilmedi. `Extractor.NER` **hiçbir kod yolunda
> üretilmiyor** — şemadaki üç değerden yalnız ikisi atanıyor
> (`src/extraction/rules/extract.py:74` → `RULE`,
> `src/extraction/llm/extractor.py:401` → `LLM`); gerekçe
> `src/extraction/reconcile.py` modül başlığında (GLiNER2 projeye hiç girmedi,
> BERTurk kabul kapısından geçemedi).
> **Ölçüm (2026-08-16, çıkarım düzeltmelerinden SONRA, 1.782 belgelik korpus):**
> çıkarılan **4.704** alanın tamamı `rule` katmanından; `ner` ve `llm`
> katmanlarından **0** alan. Komut:
> ```bash
> .venv/bin/python -c "from src.db.repository import Repository; \
> from src.pipeline import run_pipeline; r=Repository(':memory:'); \
> res=run_pipeline(r,'config/banks.yaml',raw_dir='data/raw',mode='corpus'); \
> print(res.documents_loaded, r.fields_by_extractor())"
> # -> 1782 {'rule': 4704}
> ```
> (Aynı gün erken bir koşum 4.709 vermişti; aradaki 5 alan sahte `%0` kâr payı
> temizliğiyle düştü. `data/demo.db` de bu sayıyı taşıyor — bağımsız doğrulama:
> `sqlite3 data/demo.db "select count(*) from extracted_fields"` → **4704**.)
> (`llm` sayısının 0 olması LLM'in offline Null-fallback'te olmasındandır;
> `ner` sayısının 0 olması ise **kodun kendisindendir** — o katman yok.)

Detay: [`CLAUDE.md`](CLAUDE.md) §3–§6.

## Hızlı Başlangıç (deterministik çekirdek — sıfır bağımlılık)

> **Python 3.11+ gerekir.** Kod `zip(..., strict=)` gibi 3.10+ sözdizimi
> kullanıyor. Stok macOS `/usr/bin/python3` **3.9.6**'dır ve aşağıdaki
> komutlar orada `TypeError: zip() takes no keyword arguments` ile patlar.
> `python3 -V` ile doğrulayın; düşükse `python3.11 -m ...` kullanın.
> "Sıfır bağımlılık" üçüncü taraf **paket** gerekmediği anlamına gelir,
> sürüm bağımsızlığı değil.

Normalizasyon + kural çıkarımı + eval saf stdlib ile çalışır:

```bash
cd app
# birim testler (27 test — ölçüldü 2026-08-16: "Ran 27 tests ... OK")
python3 -m unittest tests.test_normalize tests.test_extract
# eval boru hattının koştuğunu doğrular (DUMAN TESTİ — n=3 örnek gold)
python3 -m eval.run_eval --gold data/gold/gold.sample.json
```

> **Bu iki komut neyi kanıtlar, neyi kanıtlamaz.** `gold.sample.json` **3
> kayıtlıktır** ve bu koşuda her ölçüt **1,000** çıkar, halüsinasyon oranı ise
> "ölçülemedi" yazar (gold'da `absent_fields` kararı yok). Yani komut
> *harness'in bağımlılıksız koştuğunu* kanıtlar — aşağıda yayımlanan **hiçbir
> manşet sayıyı** kanıtlamaz. Ölçüm: `eval/reports/20260816-094841/report.md`
> (2026-08-16, n=3, tüm alt kümelerde P=R=F1=1,000).
>
> Manşet sayılar (0,482 vb.) **gold.v2** (n=48) ile üretilir; o koşum da ek
> paket istemez, yalnız stdlib kullanır:
> ```bash
> python3 -m eval.run_eval --gold data/gold/gold.v2.json --config kural
> ```

## Tam Sistem (Docker, offline)
```bash
docker-compose up        # postgres + vllm/ollama + api + web
pip install -r requirements.txt   # geliştirme ortamı
```

### Geliştirme kurulumu — canlı toplama için tarayıcı

Bankaların **4'ü** (Adil Katılım, Hayat Finans, T.O.M., Türkiye Finans)
sayfalarını JavaScript ile üretiyor; onları toplamak için Playwright'ın
tarayıcı bileşeni gerekir. `pip install` yalnız Python paketini kurar,
tarayıcı ikilisini **indirmez**:

```bash
python -m playwright install chromium   # ~95 MB, internet gerektirir
```

**Bu adım TESLİM EDİLEN SİSTEMİN çalışması için gerekli DEĞİLDİR.** Demo
önceden doldurulmuş veri tabanından okur; kıyas, sohbet ve pano ekranları
tarayıcı olmadan da tam çalışır. Tarayıcı yalnız *yeni veri toplarken*
gerekir ve eksikse sistem o bankayı Türkçe bir açıklamayla atlar, diğerlerini
toplamayı sürdürür.

## Komutlar
```bash
python -m src.scraping.run --config config/banks.yaml   # scraping (demo/fixture)
python -m src.extraction.run --input data/processed/sample.txt
python -m eval.run_eval --gold data/gold/               # değerlendirme + ablasyon
pytest
cd web && npm run dev
```

### Gerçek veri toplama — dört tur

Turlar ayrıdır çünkü her biri farklı bir bilgi türünü taşır ve farklı klasöre
yazılır (`data/raw/<banka>/<küme>/`):

```bash
# 1) Aktif kampanyalar            -> live/
python -m src.scraping.harvest          --config config/banks.yaml
# 2) Ürün sayfaları (oran/vade)   -> products/
python -m src.scraping.harvest_products --config config/banks.yaml
# 3) Süresi dolmuş kampanyalar    -> archive/  (campaign_status: expired)
# 4) PDF ücret tarifesi + formlar -> docs/
python -m src.scraping.harvest_extra    --round all
```

`archive/` turu, `suresi_dolmus_kampanya` kuralı için **elle işaretlenmemiş**
doğrulama verisi üretir. `docs/` turu, kâr payı/tahsis ücreti gibi kesin sayıların
durduğu PDF tarifelerini alır (`pypdf`, BSD-3).

### Turlar arası fark (aylık kampanya yenilenmesi)

Bankalar kampanyaları aylık yeniler; iki tur arasındaki fark sona ermiş / yeni /
güncellenmiş kampanyaları kanıtla ortaya çıkarır.

```bash
# Önceki turun manifesti — metinler çalışma kopyasında EZİLDİĞİ için git'ten okunur
python -m src.scraping.snapshot build --from-git HEAD \
    --out data/snapshots/<eski-tarih>.json --label <eski-tarih>
# Yeni tur (yalnızca bu andan sonra toplananlar; bayat dosyaları dışlar)
python -m src.scraping.snapshot build --since <ISO-an> \
    --out data/snapshots/<yeni-tarih>.json --label <yeni-tarih>
python -m src.scraping.snapshot diff --before ... --after ... --out fark.md
```

Karşılaştırma **temiz metin** hash'i üzerinden yapılır; ham HTML hash'i analitik
ve oturum gürültüsüyle her istekte değişir ve yalancı "değişti" üretir.

### Bayat dosya mutabakatı

Yeniden hasat eski dosyaları silmez, üzerine yazar; sitede olmayan kampanya
`live/` altında kalıp **aktif sanılır**. Mutabakat her kayıp URL'i yeniden çeker
ve karara bağlar (404 → arşive, 200+"süresi dolmuştur" → arşive, 200+normal →
`live/` kalır ve **keşif açığı** olarak raporlanır).

```bash
python -m src.scraping.reconcile_stale --before ... --after ...   # KURU KOŞU
python -m src.scraping.reconcile_stale --before ... --after ... --apply
```

Varsayılan kuru koşudur; hiçbir dosya silinmez, yalnızca `archive/`'a taşınır.

## Mimari katmanlar (tamamı offline çalışır + test edilir)

| Katman | Modül | Durum |
|---|---|---|
| Ön işleme | `src/preprocessing/clean.py` | ✅ |
| Normalizasyon | `src/normalization/normalize.py` | ✅ oran/para/vade/tarih/TR-sayı/aralık/negasyon |
| Kural çıkarımı | `src/extraction/rules/` | ✅ confidence + source_span, halüsinasyon yasağı |
| LLM çıkarımı | `src/extraction/llm/` | ✅ guided_json + vLLM/Ollama + offline Null-fallback |
| Uzlaştırma | `src/extraction/reconcile.py` | ✅ kural birincil + LLM boşluk doldurma (**iki** katman; `Extractor.NER` üretilmiyor) |
| Sınıflandırma (8 tür) | `src/extraction/ner/classifier.py` | ✅ kural-ipucu + BERTurk yolu — **kampanya TÜRÜ sınıflandırması**, alan çıkarımı DEĞİL (klasör adı `ner/` tarihseldir) |
| DB | `src/db/` | ✅ SQLite (offline) + Postgres/pgvector şema |
| Karşılaştırma | `src/comparison/compare.py` | ✅ adil-kıyas garantisi |
| Çelişki tespiti | `src/comparison/contradiction.py` | ✅ yenilikçilik |
| Hibrit chatbot | `src/chatbot/` | ✅ router + yapısal sorgu + RAG |
| Scraping | `src/scraping/` | ✅ config-driven + offline fixtures |
| Pipeline | `src/pipeline.py` | ✅ uçtan uca |
| API | `src/api/main.py` | ✅ FastAPI (import-safe) |
| Web | `web/` | ✅ Next.js dashboard + chatbot |
| Eval | `eval/run_eval.py`, `eval/ablation.py` | ✅ P/R/F1 + zor-vaka + ablasyon |

**Test:** **3.212** birim/entegrasyon testi toplanıyor · **3.159 geçiyor** ·
53 atlanıyor · **0 başarısız**, tamamı offline
(`.venv/bin/python -m unittest discover -s tests`) + 40 arayüz testi
(`cd web && npm run test`).

```bash
python -m scripts.test_ozeti     # -> eval/reports/test-ozeti.json
# 2026-08-16: 3171 toplandı · 3118 geçti · 53 atlandı · 0 başarısız
```

Atlanan 53 test Postgres/pgvector gerektirir; CI'ın `test-with-deps` işinde koşar.

> **İki koşucu, tek sayı.** Depoda testler hem `unittest` hem `pytest` ile
> koşabiliyor. Son ağaçta ikisi de **birebir aynı** sonucu veriyor:
>
> | koşucu | toplanan | geçti | atlandı | başarısız |
> |---|---:|---:|---:|---:|
> | `unittest` (kanonik — `scripts.test_ozeti`) | **3.212** | **3.159** | 53 | **0** |
> | `pytest` (`pytest tests/ -q`) | **3.212** | **3.159** | 53 | **0** (+1.307 subtest) |
>
> Yayımlanan manşet **unittest** sayısıdır, çünkü kanıt-tazeliği kapısı taze
> artefakt varken onu okur; artefakt bayatsa `pytest --collect-only` yedeğine
> düşer. İki koşucu aynı sayıyı verdiği sürece bu yedek sapma üretmez.
>
> **Tarihçe (gizlenmiyor):** 16 Ağustos gün ortasında bir ara ölçümde
> `pytest` 4 testi fazla topluyordu (3.159 / 3.155) ve kapı bunu sapma diye
> raporluyordu. Gün sonunda, o günün test eklemeleri tamamlandıktan sonra
> yapılan ölçümde fark **tekrarlanmıyor** — iki koşucu da 3.212 topluyor.
> Ara ölçüm bir hata değil, bir ara durumdu; kayda geçiriliyor çünkü aynı
> sapma yeniden görülürse ilk bakılacak yer keşif (discovery) farkıdır.
> Doğrulama: `python -m pytest tests/ -q` ve `python -m pytest -q` — ikisi de
> aynı sonucu veriyor.

> ⚠️ **ARTEFAKT HENÜZ KANIT DEĞİL — commit sonrası tekrarlanacak.** Yukarıdaki
> sayı bugünün işinin **tamamı üzerinde** ölçüldü, ama ağaç o an kirliydi
> (günün değişiklikleri henüz commit edilmemişti) ve betik bunu söylüyor:
> `⚠️ kirli ağaç — bu artefakt kanıt sayılmaz, temiz ağaçta tekrarla`.
> **Yapılacak (teslim öncesi, unutulmamalı):** commit'ten sonra
> `python -m scripts.test_ozeti` yeniden koşulacak ve
> `eval/reports/test-ozeti.json` temiz ağaç damgasıyla üretilecek. Sayının
> değişmesi beklenmiyor; beklenen tek fark artefaktın **kanıt sayılabilir**
> hâle gelmesidir. Aynı koşul aşağıdaki "Ölçüm Durumu" tablosunun *Testler*
> satırı ve `docs/SARTNAME-UYUM.md` için de geçerlidir.

## Ölçüm Durumu

Bu bölüm bilinçli olarak **dürüst** tutulur: ölçülmemiş bir sayı buraya yazılmaz.

| Kalem | Durum |
|---|---|
| Korpus | **1.782 gerçek belge**, 10 katılım bankasından canlı toplandı (provenance: `source_url` + `scraped_at` + `content_hash`, 1.772/1.776 tam) |
| Testler | ✅ **3.159 test yeşil** (3.212 toplanan · 53 atlanan · **0 başarısız**), ağ gerektirmeden koşuyor — atlananlar Postgres/pgvector isteyen testlerdir, CI'ın `test-with-deps` işinde koşar. Ölçüm 2026-08-19, temiz ağaçta: `python -m scripts.test_ozeti`. Kanıt tazeliği kapısı (`scripts.kanit_tazeligi`) bu sayıyı her koşumda artefaktla karşılaştırır; sapma CI'ı kırar |
| Değişmez (invariant) denetimi | ✅ **1.782 belgede 0 ihlal** — kapsam **%89,6** (1.597 belgede en az bir alan çıktı; 185 boş belgede denetim hiçbir şey test etmez). Ölçüm 2026-08-16: `python -m eval.properties --raw-dir data/raw --out eval/reports/violations-20260816.jsonl` → çıkış kodu 0. Bir önceki yayımlanan hâl ("1 ihlal `P4_cumle_sirasi`, kapsam %91,3") bu koşumda **tekrarlanmadı**; P4 dahil dört değişmezin dördü de geçti |
| Çelişki tespiti (korpus geneli) | ✅ ölçüldü 2026-08-16, 1.782 belge — **iki yol, iki sayı** (aşağıya bakınız) |
| Kural katmanı kapsamı | ✅ şartnamenin **12/12** alanı |
| Gold set | **66 tekil belge**, iki farklı statüde — aşağıya bakınız |
| Alan bazında P/R/F1 + %95 GA | ✅ ölçüldü — aşağıdaki tablo |
| Ablasyon + McNemar | ✅ ölçüldü — `docs/rapor/ablasyon.md` |
| Anotatörler arası uyum (κ) | ✅ round0: **Fleiss κ 0,302** · α 0,620/0,787 (260 ortak satır, 4 anotatör, hakemlik **sonrası**) · round1: **Cohen κ 0,274** (141 ortak karar, hakemlik **öncesi**). İkisi de eşik altı → ilan edilen sonuç uygulandı. İki sayı simetrik DEĞİLDİR, ayrıntı kök [`README.md`](../README.md) §4 |
| Bağımlılık lisans envanteri | ✅ iki ayrı payda, ikisi de aynı `.venv` kesiti (2026-08-15 21:14 +03): **96 bileşen** = CycloneDX SBOM'un ortam taraması ([`docs/sbom.json`](docs/sbom.json), CI lisans kapısının OKUDUĞU dosya) · **91 paket** = `pip-licenses` insan-okur envanteri ([`docs/LISANSLAR.md`](docs/LISANSLAR.md)). Fark **tam olarak 5 pakettir** ve araç kaynaklıdır — aşağıya bakınız |
| Şartname uyum matrisi | ✅ madde madde, kanıt komutlarıyla ([`docs/SARTNAME-UYUM.md`](docs/SARTNAME-UYUM.md)) |
| Kanıt-tazeliği kapısı | ✅ yayımlanan sayı ile kanıt ayrışırsa CI düşer (`python -m scripts.kanit_tazeligi`) |

#### 96 mı 91 mi — iki payda, iki farklı şey

Bu iki sayı uzun süre adlandırılmadan yan yana durdu ve birbirinin yerine
okunabiliyordu. İkisi de doğrudur, ama **farklı şeyi sayarlar**:

| payda | ne sayıyor | üreten | nerede |
|---:|---|---|---|
| **96** | `.venv`'e kurulu **tüm dağıtımlar** — paketleme araçları (`pip`, `setuptools`) ve envanter aracının kendi zinciri (`pip-licenses`, `prettytable`, `wcwidth`) **dahil** | `make sbom` → `cyclonedx_py environment` | [`docs/sbom.json`](docs/sbom.json) — **CI lisans kapısının okuduğu dosya** (`make lisans-kapisi`) |
| **91** | aynı `.venv`, aynı an — ama `pip-licenses` kendisini, bağımlılıklarını ve `pip`/`setuptools`'u varsayılan olarak **dışarıda bırakır** | `make lisanslar` → `pip-licenses` | [`docs/LISANSLAR.md`](docs/LISANSLAR.md) özet tablosu (85 izinli · 3 listede yok · 3 yasak) |

Fark **ölçüldü** (2026-08-16) ve tam olarak beş pakettir:
`pip`, `pip-licenses`, `prettytable`, `setuptools`, `wcwidth`. Ters yönde fark
yoktur (LISANSLAR'da olup SBOM'da olmayan paket: 0).

```bash
python3 -c "
import json,re
comps={c['name'].lower() for c in json.load(open('docs/sbom.json'))['components']}
rows={m[0].lower() for m in re.findall(r'^\|\s*\`?([A-Za-z0-9_.\-]+)\`?\s*\|\s*\`?([0-9][^|\`]*)\`?\s*\|',
      open('docs/LISANSLAR.md').read(), re.M)}
print(len(comps), len(rows), sorted(comps-rows), sorted(rows-comps))"
# -> 96 91 ['pip', 'pip-licenses', 'prettytable', 'setuptools', 'wcwidth'] []
```

> **İkisi de bir KESİTTİR, sözleşme değil.** `.venv` 2026-08-16'da geçici
> olarak 105 pakete çıkmış, sonra 96'ya döndürülmüştür (aşağıdaki "ÇÖZÜLDÜ"
> bloğu); **şu an ortam ile SBOM birebir örtüşüyor — 96 = 96, sapma 0.**
> Yine de her iki belge de yeniden üretilmeden *gelecekteki* bir ortamın kanıtı
> sayılamaz. Python kilit dosyası
> olmadığı için (`requirements.txt` `>=` pinleri taşıyor) bu kaçınılmazdır —
> ayrıntı `docs/LISANSLAR.md` "Sınır uyarısı".

##### ✅ ÇÖZÜLDÜ — SBOM sapması kapandı (16 Ağustos 2026)

Gün içinde `.venv` ile `docs/sbom.json` **ayrışmıştı**: ortamda SBOM'da olmayan
**9 paket** vardı (96 → 105) — demo videosu seslendirmesinden kalan `edge-tts`,
yedi geçişli bağımlılığı (`aiohttp` ailesi) ve `tabulate`.

**Neden önemliydi:** ölçüldü ki SBOM o hâliyle tazelenirse **CI lisans kapısı
düşüyordu** — `edge-tts` **LGPL-3.0-only** (kapının YASAK/copyleft kovası) ve
`multidict`'in lisans alanı boştu. Sapma üç iddiayı birden tehdit ediyordu:
`docs/sbom.json`'un "96" sayısı, `make lisans-kapisi` adımı ve sunumun 10.
slaytındaki "96 paket · CycloneDX" ifadesi.

**Çözüm — dokuz paket `.venv`'den kaldırıldı.** Gerekçe ölçüyle sabitlenmişti:
`edge_tts`/`tabulate` `src/`, `eval/`, `scripts/`, `web/` altında **hiç
geçmiyor** ve iki `requirements` dosyasında da yok; yalnız
`docs/sunum/video-uretim/ses-*.py` içinde kullanılıyorlar — yani **çalışma
zamanı bağımlılığı değil, tek seferlik üretim aracı**. Videolar zaten üretilmiş
ve dosya olarak duruyor. Aynı ayrımı sunum tarafı `python-pptx` için de
uygulamıştı (ayrı yardımcı ortam, `.venv` kirletilmedi).

**Kaldırma sonrası doğrulama (2026-08-16):**

| kontrol | sonuç |
|---|---|
| `.venv` ↔ `docs/sbom.json` sapması | **0** — her iki yönde de fark yok |
| envanter | **96 = 96** |
| `make lisans-kapisi` | **GEÇTİ ✅** |
| tam test paketi | **3.159 geçti · 0 başarısız** — hiçbir şey kırılmadı |

```bash
.venv/bin/python -m pip list --format=json | .venv/bin/python -c "
import json,sys; d={p['name'].lower() for p in json.load(sys.stdin)}
s={c['name'].lower() for c in json.load(open('docs/sbom.json'))['components']}
print(len(d), len(s), sorted(d-s), sorted(s-d))"
# -> 96 96 [] []
```

Testlerin kaldırma sonrası **sıfır hatayla** geçmesi, "çalışma zamanı
bağımlılığı değiller" ölçümünü bağımsız olarak doğruladı. **"96 paket" iddiası
(SBOM · CI kapısı · slayt 10) yeniden doğrudur.**

> Kalan yapısal kısıt değişmedi: Python kilit dosyası yok (`requirements.txt`
> `>=` pinleri taşıyor), yani bu envanter hâlâ bir **kesit**tir, sözleşme
> değil. Ortama yeni bir paket girdiği anda aynı sapma tekrar oluşabilir; bunu
> yakalayan şey `make lisans-kapisi` ve kanıt-tazeliği kapısıdır.


#### Çelişki tespiti — iki kod yolu, iki sayı (ölçüm 2026-08-16)

Çelişki sayısı **hangi yolun koştuğuna bağlıdır** ve bu ayrım şimdiye kadar
yazılmamıştı. Zaman bağımlı kural (`suresi_dolmus_kampanya`) yalnız `as_of`
verildiğinde koşar; `run_pipeline` bunu geçmez, API/pano geçer.

> **Çıkarım düzeltmelerinden sonra yeniden ölçüldü (2026-08-16) — iki sayı da
> DEĞİŞMEDİ.** Sahte `%0` temizliği kâr payı alanını 5 kayıt azalttı
> (4.709 → 4.704) ama çelişki kümesine dokunmadı; aşağıdaki tablo tazedir.

| yol | `as_of` | çelişki | tür | kırılım |
|---|---|---:|---:|---|
| `run_pipeline(mode="corpus")` — CLI / `scripts.build_demo_db` | ✗ | **5** | **2** | `celisen_tutar_bandi` 4 · `celisen_kampanya_bitisi` 1 |
| API `/contradictions` — `detect(c, as_of=scraped_at)`; **panonun gösterdiği** | ✓ | **15** | **3** | `suresi_dolmus_kampanya` 10 · `celisen_tutar_bandi` 4 · `celisen_kampanya_bitisi` 1 |

Banka kırılımı (15'lik yol): Albaraka 9 · Kuveyt Türk 5 · Dünya Katılım 1.
Her iki koşum da 1.782 belge okudu. Üreten komutlar (ikisi de offline, LLM kapalı):

```bash
# 1) Boru hattı yolu — 5 çelişki / 2 tür
.venv/bin/python -c "
import collections
from src.db.repository import Repository
from src.pipeline import run_pipeline
res = run_pipeline(Repository(':memory:'), 'config/banks.yaml',
                   raw_dir='data/raw', mode='corpus')
print(res.documents_loaded, len(res.contradictions),
      collections.Counter(c['kind'] for c in res.contradictions))"

# 2) API yolu (as_of=scraped_at) — 15 çelişki / 3 tür
.venv/bin/python -c "
import collections
from src.scraping.config import load_banks
from src.pipeline import _collect_for_mode, MODE_CORPUS
from src.preprocessing.clean import normalize_text
from src.extraction.reconcile import build_campaign
from src.comparison.contradiction import detect
found = []
for b in load_banks('config/banks.yaml'):
    for d in _collect_for_mode(b, 'data/raw', MODE_CORPUS, None):
        c = build_campaign(normalize_text(d.clean_text), bank_slug=b.slug,
                           source_url=d.source_url)
        found += [(b.slug, k.kind) for k in detect(c, as_of=d.scraped_at)]
print(len(found), collections.Counter(k for _, k in found))"
```

Kodda tanımlı çelişki türü sayısı **yedidir**
(`grep -o 'kind="[a-z_]*"' src/comparison/contradiction.py | sort -u`); bugünkü
korpusta bunların **üçü** tetikleniyor.

> Teknik raporun §A9'u **849 belgede 1 çelişki** diyor. O sayı silinmedi; 3
> Ağustos korpusuna çapalı ve raporun kendi künye kuralı gereği yerinde duruyor
> — güncel ölçüm oraya **ayrı** bir blok olarak eklendi.

### Ölçüm sonuçları

Kural katmanı, `gold.v2` (n=48, **kör** etiketlenmiş), strict eşleştirici,
belge düzeyi bootstrap 1000 örnek, tohum 42:

| ölçüt | değer |
|---|---|
| **yapılandırılmış alan mikro-F1** (11 alan) | **0,702** |
| 12-alan mikro-F1 | **0,482** [%95 GA 0,410–0,534] |
| makro-F1 | **0,636** |
| halüsinasyon (bilgi metinde YOK, değer uyduruldu) | **0,043** [19/446] · yapısal kesitte 0,030 |
| kalem düzeyi mikro-F1 (12 alan) | 0,381 |

> **Künye.** Bu sayılar 15 Ağustos koşumundan gelir
> (`eval/reports/20260815-195653/`) ve **2026-08-16'da yeniden koşularak
> doğrulandı** — dördü de birebir aynı çıktı
> (`eval/reports/20260816-102045/`). Üreten komut:
> ```bash
> python3 -m eval.run_eval --gold data/gold/gold.v2.json --config kural
> ```
>
> 12 Ağustos koşumu (`eval/reports/20260812-212355/`) **0,452**
> [%95 GA 0,384–0,512] · makro 0,556 · halüsinasyon 0,059 veriyordu; yani
> 0,452 → **0,464**, halüsinasyon 0,059 → **0,047**. Fark iki kural
> düzeltmesinden geliyor: oransal tahsis ücretinde türetme kaldırıldı
> (§4.13/5) ve kabuk bölgesi kapısı eklendi (§4.13/8). İkisi de metinde
> geçmeyen değer üretmeyi bitirdi.
>
> **0,452 artık geçerli manşet DEĞİLDİR** — yalnız 12 Ağustos kesitinin
> tarihsel değeridir. Belgede bu sayıyla karşılaşırsanız tarihine bakın.

**İki mikro-F1 neden veriliyor:** `kampanya_kosullari` serbest cümle listesi
döndürür; span/jeton eşleşmesiyle F1 ölçmek metodolojik olarak yanlıştır (aynı
koşulu farklı sözcüklerle yazan iki anotatör bile birbirini "yanlış" bulurdu).
Alan **gizlenmiyor**, kalem düzeyi ölçütle ayrı raporlanıyor; iki sayı yan yana
duruyor. Ayrıntı: kök [`README.md`](../README.md#-ölçülebilir-durum).

#### Gold setin statüsü — iki set, iki farklı güvenilirlik

Bu ayrım metriklerden önce gelir ve **birleştirilerek sunulmaz**:

| set | n | kim etiketledi | hakemlik |
|---|---|---|---|
| `gold.v1` | 20 | **insan** anotatör | ✅ geçti (2 kayıt düzeltildi) |
| `gold.v2` | 48 | **makine** anotatör (M1–M4), her belge birebir alıntı kanıtıyla | ❌ hakemlik yok (`adjudicated: false`) |
| `gold.round1` | 134 | **makine** anotatör (A–D), protokol v2 | 🟠 **makine kör hakem** — 38 kayıt (`adjudicated: true`); insan hakemliği YOK |

Yukarıdaki 0,464 **gold.v2 üzerinde** ölçüldü, yani **insan hakemliğinden
geçmemiş** bir sette. Bunu gizlemek yerine yazıyoruz çünkü alternatifi
(0,677'yi manşete koymak) daha kötü — o da modele çapalı bir protokolden
geliyor. İkisi de kısıtlıdır ve ikisi de kısıtıyla birlikte sunulur.

**`gold.round1`'deki hakemlik makine hakemliğidir.** 41 uyuşmazlık, yalnız
kendi alanının kılavuz paragrafını gören ve birbirinden habersiz çalışan
kör hakemlerce karara bağlandı; 18 hücre şema onarımından geçti. Bu
protokol, hakemin A ya da B ile **hem karar hem değer** olarak örtüşmesini
şart koşuyor — üçüncü bir cevap hiçbir tarafa dokunmuyor. Yine de **insan
hakemliğinin yerine geçmez** ve öyle sunulmuyor: `adjudicated: true`
bayrağı "hakemlikten geçti" der, "insan onayladı" demez.

**Bu, kapatılması gereken en öncelikli açıktır.** Anotasyon kanıt kapılıydı
(her değer metinde birebir geçen bir alıntıya bağlı, programatik
doğrulandı) ama kanıt kapısı insan hakemliğinin yerine geçmez.

**Bu sayı düşük ve nedenini saklamıyoruz.** İki şey birden doğru:

- `gold.v1` (n=20) üzerinde aynı sistem **0,677** veriyor. Fark protokol
  kaynaklı: v1'de anotatör modelin çıktısını onaylayarak etiketledi
  (`ANNOTATION_GUIDE.md` §3.1, eski kural), v2 ise **kör** etiketlendi.
  0,677 tek başına sunulmaz — ikisi birlikte sunulur.
- Farkın ~%57'si tek bir alandan geliyor: `kampanya_kosullari` F1 = **0,000**
  (TP 0, FP 36, FN 33). **Bu bir ölçüm tasarımı kusurudur, "eşleştirici
  sertliği" değil** — `tolerant` eşleştirici de tam olarak 0,000 veriyor,
  birebir aynı TP/FP/FN ile. Sebep `eval/matchers.py` liste karşılaştırmasının
  **küme eşitliği** araması: beş koşuldan dördü tutsa bile sonuç FP+FN.
  33 belgenin **hiçbirinde** tam küme eşleşmesi yok.
  Yani sistem bu alanda ölçüldüğünden iyi olabilir ama **bugünkü metrik bunu
  gösteremiyor**; kalem düzeyinde kısmi kredi verecek bir puanlama gerekiyor
  (açık iş). Manşet sayının ~%28'i bu tek alanın ölçülemez tasarımından
  geliyor.

> **Senaryonun kalp alanı yeterince ölçülmedi.** `kar_payi_orani` gold.v2'de
> yalnız **3 karar** destekli (TP 2, FN 1). Oradan çıkan F1 = 0,800
> **yorumlanamaz** — üç karar bir F1 taşımaz. Korpusta da alan **60/1.782 belgede (%3,4)** var
> (ölçüm 2026-08-16, sahte `%0` temizliğinden sonra; önceki yayımlanan değer 70/1.782 = %3,9 idi
> ve içinde bağlamsız sıfırlar vardı) — bu bir
> model kısıtı değil, **veri gerçeği**: bankalar oranları kampanya
> sayfalarında büyük ölçüde yayımlamıyor.

**Tekrarlanan tek sayı halüsinasyon oranıdır** (~%10), payda 166'dan 444'e
çıkarken korundu. İki protokolden de bağımsız çıkan tek metrik budur.

### Ölçümle yanlışlanan üç hipotez

Bu projede "daha güçlü model ekleyelim" refleksi **üç kez** denendi ve
üçünde de kural katmanı önde kaldı:

| deneme | sonuç |
|---|---|
| Hibrit kol (LLM boşlukları doldurur) | 0,575 vs kural 0,677; halüsinasyon %70 fazla |
| Orkestrasyon (ajan önerir, hakem reddeder) | 0,377 vs kural 0,387; üç ölçütte de kural önde. McNemar yönü kuralı gösteriyor (ham p=0,039) ama **çoklu karşılaştırma düzeltmesi yapılmadı** — projede ≥18 test koşuldu, bu p tek başına kanıt sayılmamalı |
| BERTurk ince ayarı (8 sınıf) | makro-F1 0,565 vs kural 0,762 — kabul kapısında **kaldı**, projeye alınmadı |

Mekanizma üçünde de aynı: LLM doğru sayısını artırmıyor, yanlış sayısını
artırıyor. Negatif sonuçlar gizlenmedi; `docs/rapor/ablasyon.md` ve
`docs/rapor/berturk-ince-ayar-plani.md` içinde ölçüm künyeleriyle duruyor.

**Yan bulgu (pozitif):** hakem katmanının katkısı izole edildi — orkestra,
hakemsiz kolu anlamlı geçiyor (McNemar p=0,0156, eşleşmiş fark sıfırı
dışlıyor) ve halüsinasyonu 60 → 53 düşürüyor.

### Güvenlik

Prompt-injection seti: **22 saldırının 22'si savuşturuldu, 4 kontrol
sorusunun 4'ü doğru yanıtlandı** — hem kapılar tek başınayken hem RAG sentezi
açıkken. Kısıt: set n=26 ve sentez tarafı tek modelle (`qwen2.5:7b-instruct`)
ölçüldü. Ayrıntı: `docs/rapor/guvenlik-llm-modu.md`.

### κ ÖLÇÜLDÜ ve eşiğin ALTINDA — ilan edilen sonuç uygulandı

> Bu bölüm 2026-08-12'de düzeltildi. Önceki hâli "κ hesaplanmadı, şartname
> §16'nın karşılanmayan tek kalemi" diyordu; **yanlıştı**. Ölçüm yapılmış ve
> raporlanmıştı, README güncellenmemişti. (O rapor sonradan v2 turunun boş
> dosyalarından yeniden üretilip ÜZERİNE YAZILMIŞTI; 15 Ağustos'ta turlar
> ayrı dosyalara bölündü: [`iaa-raporu-round0-kalibrasyon-v1.md`](data/gold/iaa-raporu-round0-kalibrasyon-v1.md).)

Kalibrasyon turu (v1), 4 anotatör, **260 ortak anote edilmiş satır**, karar
bulunmayan hücre 0 — kaynak: `data/gold/review/round0_kalibrasyon_{A,B,C,D}.csv`.

| Ölçüt | Neyi ölçer | Değer |
|---|---|---:|
| **Fleiss κ** (karar) | aynı satırda aynı kararı mı verdiler | **0,302** |
| Krippendorff α (nominal) | gold DEĞERİ birebir aynı mı | 0,620 |
| Krippendorff α (ratio) | sayısal alanlarda değer yakınlığı (37 birim) | 0,787 |

Üretim: `python -m scripts.report_iaa data/gold/review/round0_kalibrasyon_{A,B,C,D}.csv`

**Cohen değil Fleiss:** Cohen κ iki anotatör içindir; burada dört anotatör
var ve Fleiss onun genellemesidir. `eval/iaa.py` üçünü de içeriyor.

**Eşik politikası anotasyon BAŞLAMADAN ilan edilmişti** (ANNOTATION_GUIDE §7):
κ≥0,80 kabul · 0,67≤κ<0,80 notla kabul · κ<0,67 **zorunlu hakemlik + kılavuz
revizyonu**. κ=0,302 üçüncü banda düştü ve ilan edilen sonuç **uygulandı**:
kılavuz v1→v2 revize edildi (`docs/rapor/kilavuz-revizyonu.md`, 2026-08-07),
123 uyuşmazlık tek tek listelendi.

Düşük κ'yı gizlemiyoruz: serbest metin alanları (`kampanya_kosullari`)
uyumu tek başına aşağı çekiyor ve aynı alan mikro-F1'de de ayrı raporlanıyor.
Sayıya bakıp eşik değiştirmek yasaktı, değiştirilmedi.

**Gerçek açık — v2 turu ANOTE EDİLMEDİ.** Revizyondan sonra κ'nın düzelip
düzelmediği ölçülemedi: `round0_kalibrasyon_v2_{A,B,C,D}.csv` dağıtıldı ama
dördünün **sha256'sı birebir aynı** (`66c7db60…`), yani hiçbiri
doldurulmamış. `report_iaa` bu tur için dürüstçe "ölçülemedi / olcusuz"
diyor. Kapanması insan anotasyonu gerektiriyor; kod ve komut hazır.

### Sonraki adımlar

Öncelik sırasıyla, teslime kalan sürede:

- **κ v2 turunu anote et** — revizyon SONRASI κ ölçülemedi çünkü
  `round0_kalibrasyon_v2_{A,B,C,D}.csv` dördü de aynı sha256'yı taşıyor
  (hiç doldurulmamış). Dolunca `python -m scripts.report_iaa <dosyalar>`
  tek komutla Fleiss κ + Krippendorff α üretir ve kılavuz revizyonunun
  uyumu düzeltip düzeltmediği ölçülür. v1 κ'sı ZATEN ölçülmüş (0,302).
- **Gold seti büyütmek** — 66 → 150 bandı; GA'lar daralır ve **0,464** nokta
  tahmini savunulabilir hâle gelir (bugünkü GA 0,398–0,522, yani genişliği
  0,124 — nokta tahminin kendisi kadar büyük).
- **`kampanya_kosullari` ve `vade_ay`** — ikisi mikro-F1'in en büyük tek
  kaldıracı; eşleştirici sertliği mi tanım sorunu mu ayrıştırılmalı.
- ~~**Değişmez denetimini 1.774 belgede tekrarla**~~ — **YAPILDI (2026-08-16):**
  1.782 belge, **0 ihlal**, kapsam %89,6. Komut ve çıktı yukarıdaki "Ölçüm
  Durumu" tablosunda. Kalan iş: kapsamı yükseltmek — 185 belgeden hiç alan
  çıkmıyor ve o belgelerde denetim hiçbir şey test etmiyor.
- **Ablasyon kolları** — izole ortamlarda kalan kollar (Trendyol-8B hibrit,
  GLiNER geri-çağırma ağı). Başarısız kollar **negatif sonuç olarak
  raporlanır**; üç tanesi zaten öyle raporlandı.
