# Anatolia AI — Katılım Bankacılığı Kampanya Bilgi Çıkarımı

[![CI](https://github.com/mehmetefeaytas/anatoliaAI/actions/workflows/ci.yml/badge.svg)](https://github.com/mehmetefeaytas/anatoliaAI/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)
[![Testler](https://img.shields.io/badge/testler-3456%20ye%C5%9Fil-brightgreen.svg)](tests/)
[![Değişmez denetimi](https://img.shields.io/badge/de%C4%9Fi%C5%9Fmez%20denetimi-2708%20belge%20%C2%B7%200%20ihlal-brightgreen.svg)](eval/properties.py)

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

**Üretim yolu kural tabanlıdır.** LLM katmanı kodda vardır, koşar ve
ölçülmüştür — ama ölçüm onu üretime almamayı söyledi. Bu bir eksiklik değil,
kanıta bağlı bir karardır; kanıtı `docs/rapor/ablasyon.md` taşıyor ve aşağıda
özetleniyor.

```
scrape → clean → preprocess → extract (KURAL — üretimde tek etkin katman)
→ reconcile → normalize → PostgreSQL → compare
→ dashboard + chatbot (yapısal sorgu ↔ RAG yönlendirmesi)
```

> **"Hibrit" bu depoda iki ayrı şeye kullanılıyordu ve karıştırılması fazla
> iddia üretiyordu.** Bundan sonra ayrı yazılıyor:
>
> | anlam | durum |
> |---|---|
> | **mimari olarak mevcut** | `src/extraction/llm/` + `reconcile.py`'nin boşluk-doldurma kolu vardır, test edilir, ablasyonda koşar |
> | **üretimde devre dışı** | resmî metrik ve teslim kolu `kural`'dır (K-2); teslim edilen korpusta LLM katmanı **hiç alan üretmedi** (ölçüm aşağıda) |
>
> Ablasyon tablolarında `hibrit` kelimesi geçmeye **devam ediyor**; orada bir
> **ölçüm konfigürasyonunun adıdır**, sistem hakkında bir iddia değil.
> Chatbot'un iki yollu (yapısal sorgu ↔ RAG) yönlendirmesi ayrı bir
> mekanizmadır ve alan çıkarımıyla ilgisi yoktur.

### LLM katmanı neden üretimde değil — ölçüm

20 Ağustos 2026, `gold.v2` (48 kayıt, 40'ı zor), Ollama +
`qwen2.5:7b-instruct` (Apache-2.0), CPU, `LLM_STRICT=1`. **LLM sağlığı temiz:
384 çağrının 384'ü başarılı** — parse hatası 0, HTTP hatası 0, şema ihlali 0,
onarım 0. Yani düşük başarım teknik bir arızadan **gelmiyor**; model çağrıldı,
geçerli JSON döndürdü ve yine kaybetti.

| kol | mikro-F1 (`strict`) | halüsinasyon | McNemar vs `kural` (`tolerant`) |
|---|---|---|---|
| **kural** | **0,4771** | **0,0425** | — |
| llm | 0,2545 | 0,0582 | p = 0,00105 · kural üstün |
| hibrit | 0,4402 | **0,1029** | p = 0,00050 · kural üstün |
| hibrit-verify | 0,3672 | 0,0984 | p = 0,0000123 · kural üstün |

İki cümlelik okuma: LLM katmanı kural katmanını **hiçbir konfigde** geçmiyor
(üç karşılaştırmada da p < 0,05), ve hibrit halüsinasyonu **2,4 katına**
çıkarıyor (0,0425 → 0,1029). Bankacılıkta uydurulmuş bir değer doğrudan "En
Avantajlı" sıralamasına girdiği için bunun bedeli F1 değil, **kullanıcıya
yanlış bilgi verme oranıdır**.

Bu tablo "LLM işe yaramaz" demiyor: ölçülen şey tek bir 7B modelin, bu
korpusta, bu şemayla verdiği sonuçtur. Kuralın kendi F1'i de yüksek değildir —
tablo kuralın iyi olduğunu değil, LLM'in onu geçemediğini gösteriyor. Künye,
kırılım ve karşı-okumalar: [`docs/rapor/ablasyon.md`](docs/rapor/ablasyon.md).

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
> **Tazelenmiş ölçüm (2026-08-21, PDF hasadından sonra):** korpus 2.708 belge,
> çıkarılan **7.032** alanın tamamı `rule`; `ner` ve `llm` yine **0**. Katman
> dağılımı hasatla DEĞİŞMEDİ — iddia büyüyen korpusta da geçerli.
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
> Manşet sayılar (0,5702 vb.) **gold.v2** (n=48) ile üretilir; o koşum da ek
> paket istemez, yalnız stdlib kullanır:
> ```bash
> python3 -m eval.run_eval --gold data/gold/gold.v2.json --config kural
> ```

## Arayüz + sohbet — Docker'sız, yerel (en hızlı demo yolu)

> **`DATABASE_PATH` verilmezse sistem sessizce 3 fixture'a düşer.** Varsayılan
> `:memory:`'dir (`src/api/main.py:231`). Docker yolu bunu imaja gömülü
> `data/demo.db` ile çözer; **yerel** koşumda değişkeni elle vermek
> zorunludur. Verilmezse `/stats` `campaigns: 3` döner ve dashboard 2.708
> belge yerine 3 kampanya gösterir — sessiz düşüş, hata vermez.

```bash
cd app
python3 -m scripts.build_demo_db --out data/demo.db   # bir kez, ~282 s
# Özetleri geri yükle — ATLAMAYIN.
# `build_demo_db` `campaigns.ozet` sütununu BİLMEZ ve boş bırakır. Bu adım
# atlanırsa panel ve sohbet her belgede "AI Özeti üretilmedi" der ve kullanıcıya
# ham metnin başı (bazı sayfalarda site gezinme şeridi) gösterilir.
# Özetler yerel modelle üretildi (~4 saat) ve yedekte duruyor; geri yükleme
# saniyeler sürer ve LLM İSTEMEZ. Kural tabanlı sahte özet basmak YASAK
# (src/summarize/ozet.py) — bu yüzden yedek tek meşru yol.
# Kaynak `data/ozet-yedegi.json` — GIT'TE İZLENEN dosya (1,3 MB, 2.634 özet).
# ÖNEMLİ: bu adım bir `.db` yedeğine bağlanMAZ. `*.db` gitignore'dadır, yani
# temiz bir klonda hiçbir `demo.db.yedek-*` dosyası YOKTUR ve o dosyayı kaynak
# gösteren bir komut sessizce başarısız olur. İzlenen JSON yedeği tek doğru yol.
# Ölçüldü (2026-08-20): 2.708 belgenin 2.634'ü özetlendi (%97,3); kalan 74'ün
# sebebi `metin_bos` (içerik yok) ya da `terminoloji_ihlali` (kapı reddetti).
python3 -m scripts.ozet_geri_yukle --db data/demo.db


DATABASE_PATH=data/demo.db .venv/bin/python -c "
import uvicorn, sys; sys.path.insert(0,'.')
from src.api.main import build_app
uvicorn.run(build_app(), host='127.0.0.1', port=8000)"
```

Doğrulama (ölçüldü 2026-08-20, bu komutlarla):

```bash
curl -s localhost:8000/health   # {"status":"ok","llm":false,"backend":"sqlite"}
curl -s localhost:8000/stats    # campaigns: 2708, banks_with_campaigns: 11, fields: 7032
```

Şartnamenin s.12 referans senaryoları, aynı koşumda canlı doğrulandı:

```bash
# Senaryo 1 — tek banka, İKİ alan birlikte
curl -s -X POST localhost:8000/chat -H 'Content-Type: application/json' \
  -d '{"question":"Kuveyt Türk konut finansmanı oranı ve vadesi ne?"}'
# -> "kâr payı oranı: %1,89" + "vade: 120 ay" (iki alan da döner; koşullu oran
#    uyarısı ve katılma hesabı ihtarı eklenir)

# Senaryo 2 — gerekçeli karşılaştırma
curl -s -X POST localhost:8000/chat -H 'Content-Type: application/json' \
  -d '{"question":"Kuveyt Türk mü avantajlı Ziraat Katılım mı?"}'
# -> kâr payı / vade / masraf / ek ödül boyutlarında "çünkü ..." gerekçeli
#    madde madde cevap, 7 kaynak

# Tanınmayan banka — çekimser kalma (uydurma YOK, ilgisiz banka YOK)
curl -s -X POST localhost:8000/chat -H 'Content-Type: application/json' \
  -d '{"question":"XYZ Bankası konut finansmanı oranı ne?"}'
# -> "Sorduğunuz bankayı veri setimde bulamadım" + tanınan 10 bankanın listesi
```

## Tam Sistem (Docker, offline)

> **Önce veri tabanını kur, SONRA `docker-compose up`.** `Dockerfile.api`
> `data/demo.db` dosyasını `COPY data/ ./data/` ile **derleme anında** imaja
> gömer. Dosya `.gitignore`'dadır (`*.db` kuralı) — temiz bir `git clone`
> sonrası **yoktur**. Bu adım atlanırsa API açılışta `repo.counts()["campaigns"]
> == 0` koşuluyla sessizce fixture'lara düşer ve dashboard **2.708 belge
> yerine yalnızca 3 fixture kampanyası** gösterir; korpus ölçeği (projenin en
> güçlü fonksiyonellik kanıtı) jüriye hiç görünmez.

```bash
cd app
python3 -m scripts.build_demo_db --out data/demo.db

# Özetleri geri yükle — ATLAMAYIN.
# `build_demo_db` `campaigns.ozet` sütununu BİLMEZ ve boş bırakır. Bu adım
# atlanırsa panel ve sohbet her belgede "AI Özeti üretilmedi" der ve kullanıcıya
# ham metnin başı (bazı sayfalarda site gezinme şeridi) gösterilir.
# Özetler yerel modelle üretildi (~4 saat) ve yedekte duruyor; geri yükleme
# saniyeler sürer ve LLM İSTEMEZ. Kural tabanlı sahte özet basmak YASAK
# (src/summarize/ozet.py) — bu yüzden yedek tek meşru yol.
# Kaynak `data/ozet-yedegi.json` — GIT'TE İZLENEN dosya (1,3 MB, 2.634 özet).
# ÖNEMLİ: bu adım bir `.db` yedeğine bağlanMAZ. `*.db` gitignore'dadır, yani
# temiz bir klonda hiçbir `demo.db.yedek-*` dosyası YOKTUR ve o dosyayı kaynak
# gösteren bir komut sessizce başarısız olur. İzlenen JSON yedeği tek doğru yol.
# Ölçüldü (2026-08-20): 2.708 belgenin 2.634'ü özetlendi (%97,3); kalan 74'ün
# sebebi `metin_bos` (içerik yok) ya da `terminoloji_ihlali` (kapı reddetti).
python3 -m scripts.ozet_geri_yukle --db data/demo.db
# Gerçekten ölçüldü (temiz klon simülasyonu — izlenen dosyalardan taze
# checkout, 2026-08-20): süre 282 s (~4 dk 42 sn), 1.782 belge -> 1.782
# kampanya kaydı, 11/11 banka, çıktı data/demo.db ~22,2 MB.
# Çıkış kodları: 0 başarılı · 1 hedef dosya zaten var (--force gerekir)
# · 2 korpus BOŞ (sessizce "kuruldu" demez).

docker-compose up        # postgres + vllm/ollama + api + web
pip install -r requirements.txt   # geliştirme ortamı
```

> **Neden otomatik değil (compose'a init servisi olarak eklenmedi).**
> `scripts/build_demo_db` ~4-5 dakika sürüyor; bunu her `docker-compose up`'ta
> koşturmak CLAUDE.md §11'in doğrudan ihlali olurdu ("4 dakikalık sunumda
> beklenecek tek bir servis bile fazladır") — jüri `up` dedikten dakikalarca
> sonra ekran görürdü. Ayrıca `Dockerfile.api` `data/`yi **derleme anında**
> kopyaladığı için bir çalışma-zamanı init konteyneri zaten geç kalırdı
> (imaj o ana kadar demo.db'siz derlenmiş olurdu). Doğru sıralama **derleme
> ÖNCESİ, elle, bir kez** çalıştırmaktır — tam olarak yukarıdaki adım.

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
| LLM çıkarımı | `src/extraction/llm/` | ✅ guided_json + vLLM/Ollama + offline Null-fallback — **üretimde devre dışı** (ölçülmüş karar, yukarı bkz.) |
| Uzlaştırma | `src/extraction/reconcile.py` | ✅ kural birincil; LLM boşluk-doldurma kolu **mevcut ama üretimde kapalı** (`Extractor.NER` hiç üretilmiyor) |
| Sınıflandırma (8 tür) | `src/extraction/ner/classifier.py` | ✅ kural-ipucu + BERTurk yolu — **kampanya TÜRÜ sınıflandırması**, alan çıkarımı DEĞİL (klasör adı `ner/` tarihseldir) |
| DB | `src/db/` | ✅ SQLite (offline) + Postgres/pgvector şema |
| Karşılaştırma | `src/comparison/compare.py` | ✅ adil-kıyas garantisi |
| Çelişki tespiti | `src/comparison/contradiction.py` | ✅ yenilikçilik |
| Chatbot — iki yollu yönlendirme | `src/chatbot/` | ✅ router + yapısal sorgu ↔ RAG (alan çıkarımından bağımsız mekanizma) |
| Scraping | `src/scraping/` | ✅ config-driven + offline fixtures |
| Pipeline | `src/pipeline.py` | ✅ uçtan uca |
| API | `src/api/main.py` | ✅ FastAPI (import-safe) |
| Web | `web/` | ✅ Next.js dashboard + chatbot |
| Eval | `eval/run_eval.py`, `eval/ablation.py` | ✅ P/R/F1 + zor-vaka + ablasyon |

**Test:** **3.509** birim/entegrasyon testi toplanıyor · **3.456 geçiyor** ·
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
> | `unittest` (kanonik — `scripts.test_ozeti`) | **3.509** | **3.456** | 53 | **0** |
> | `pytest` (`pytest tests/ -q`) | **3.509** | **3.456** | 53 | **0** (+1.623 subtest) |
>
> Yayımlanan manşet **unittest** sayısıdır, çünkü kanıt-tazeliği kapısı taze
> artefakt varken onu okur; artefakt bayatsa `pytest --collect-only` yedeğine
> düşer. İki koşucu aynı sayıyı verdiği sürece bu yedek sapma üretmez.
>
> **Tarihçe (gizlenmiyor):** 16 Ağustos gün ortasında bir ara ölçümde
> `pytest` 4 testi fazla topluyordu (3.162 / 3.155) ve kapı bunu sapma diye
> raporluyordu. Gün sonunda, o günün test eklemeleri tamamlandıktan sonra
> yapılan ölçümde fark **tekrarlanmıyor** — iki koşucu da aynı sayıyı topluyor.
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
| Korpus | **2.708 gerçek belge** (758 PDF dâhil), 10 katılım bankasından canlı toplandı (provenance: `source_url` + `scraped_at` + `content_hash`, 1.772/1.776 tam) |
| Testler | ✅ **3.456 test yeşil** (3.509 toplanan · 53 atlanan · **0 başarısız**), ağ gerektirmeden koşuyor — atlananlar Postgres/pgvector isteyen testlerdir, CI'ın `test-with-deps` işinde koşar. Ölçüm 2026-08-21: `python -m pytest tests -q` → `3456 passed, 53 skipped, 1623 subtests passed`. İki koşucu birebir aynı. Kanıt tazeliği kapısı (`scripts.kanit_tazeligi`) bu sayıyı her koşumda artefaktla karşılaştırır; sapma CI'ı kırar |
| Değişmez (invariant) denetimi | ✅ **2.708 belgede 0 ihlal** — kapsam **%92,3** (2.499 belgede en az bir alan çıktı; 209 boş belgede denetim hiçbir şey test etmez). Ölçüm 2026-08-21: `python -m eval.properties --raw-dir data/raw` → çıkış kodu 0. **21 Ağustos'ta bu denetim 2 GERÇEK ihlal verdi ve CI'ı kırdı**: son PDF hasadındaki okunamaz bir Albaraka sözleşmesi (ToUnicode tablosu olmayan gömülü yazı tipi) çöp metni `kampanya_kosullari` kalemi olarak sunuyordu. Kök neden kodda değil veride olduğu için çözüm bir KAPI oldu (`_ortak.bozuk_metin`); ihlal gizlenmedi, sebebi burada yazılı |
| Çelişki tespiti (korpus geneli) | ✅ ölçüldü 2026-08-21, 2.708 belge — **28 çelişki: 8'i belgeler-arası** (6 çapraz bitiş tarihi + **2 çapraz kâr payı uyuşmazlığı**), 20'si belge-içi. Kâr payı örneği manşetliktir: Albaraka aynı ürün için iki ayrı formda **%7,0 ve %1,0** yayımlamış — kesişmeyen iki oran. Komut: `python -m src.comparison.scan --raw-dir data/raw`. **İki yol, iki sayı** (aşağıya bakınız) |
| Kural katmanı kapsamı | ✅ şartnamenin **12/12** alanı |
| Gold set | **66 tekil belge**, iki farklı statüde — aşağıya bakınız |
| Alan bazında P/R/F1 + %95 GA | ✅ ölçüldü — aşağıdaki tablo |
| Ablasyon + McNemar | ✅ ölçüldü — `docs/rapor/ablasyon.md` |
| Anotatörler arası uyum (κ) | ✅ **v2 turu: Cohen κ 0,714** (16 kayıt, 192 çift, ikinci etiketleyici LLM — "notla kabul" bandı; `masraf_durumu` negatif κ'sı hakemlenip gold+kılavuz+motor düzeltildi) · round0: **Fleiss κ 0,302** · α 0,620/0,787 (260 ortak satır, 4 anotatör, hakemlik **sonrası**) · round1: **Cohen κ 0,274** (141 ortak karar, hakemlik **öncesi**). İkisi de eşik altı → ilan edilen sonuç uygulandı. İki sayı simetrik DEĞİLDİR, ayrıntı kök [`README.md`](../README.md) §4 |
| Bağımlılık lisans envanteri | ✅ iki ayrı payda, ikisi de aynı `.venv` kesiti (2026-08-15 21:14 +03): **96 bileşen** = CycloneDX SBOM'un ortam taraması ([`docs/sbom.json`](docs/sbom.json), CI lisans kapısının OKUDUĞU dosya) · **91 paket** = `pip-licenses` insan-okur envanteri ([`docs/LISANSLAR.md`](docs/LISANSLAR.md)). Fark **tam olarak 5 pakettir** ve araç kaynaklıdır — aşağıya bakınız |
| Şartname uyum matrisi | ✅ madde madde, kanıt komutlarıyla ([`docs/SARTNAME-UYUM.md`](docs/SARTNAME-UYUM.md)) |
| Kanıt-tazeliği kapısı | ✅ yayımlanan sayı ile kanıt ayrışırsa CI düşer (`python -m scripts.kanit_tazeligi`) — **14 iddia · 0 sapma** (2026-08-20) |
| Eşik düşürme disiplini | ✅ ADR'ye bağlı: bir regresyon eşiği yalnız **ölçüt kusuru** kanıtlanırsa düşürülebilir, dört kapı + iki imza ([`docs/adr/0001`](docs/adr/0001-esik-dusurme-disiplini.md)) — üç düşürme kayıtlı: `kampanya_kosullari`, `odul_miktari`, **`masraf_durumu` (0,714 → 0,65, 2026-08-19, gold düzeltmesi)** |

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
| tam test paketi | **3.162 geçti · 0 başarısız** (o günün ağacı) — hiçbir şey kırılmadı |

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
Her iki koşum da (2026-08-16 ölçümünde) 1.782 belge okudu; 2026-08-21 koşumu 2.708 belge okudu. Üreten komutlar (ikisi de offline, LLM kapalı):

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

#### Çelişki tespiti — canlı yeni örnek: 28 çelişki, dahil kâr payı uyuşmazlığı (ölçüm 2026-08-21)

Üçüncü bir kod yolu (`src.comparison.scan`, tek anlık görüntü + `product_key`
gruplaması) tam korpusta tarandı ve **28 çelişki** üretti:

| tür | adet | kırılım |
|---|---:|---|
| belgeler-arası (`detect_across`) | **8** | 6 çapraz bitiş tarihi + **2 çapraz kâr payı uyuşmazlığı** |
| belge-içi (`detect`) | **20** | 17 süresi dolmuş kampanya + 2 çelişen tutar bandı + 1 çelişen bitiş |

**Manşet örnek:** Albaraka Türk aynı ürün için iki ayrı formda **%7,0** ve
**%1,0** kâr payı oranı yayımlamış — kesişmeyen iki oran, `detect_across()`
tarafından üretim koduyla fiilen tespit edildi. Bu, kâr payı alanında canlı
ateşlenen ilk dokümante edilmiş belgeler-arası çelişki örneğidir.

```bash
cd app && .venv/bin/python -m src.comparison.scan --raw-dir data/raw
```

Ayrıntı, önceki (2026-08-20) dual-snapshot ölçümüyle ilişkisi ve tam kırılım:
[`docs/rapor/celiski-canli-atesleme-2026-08-21.md`](docs/rapor/celiski-canli-atesleme-2026-08-21.md).

### Ölçüm sonuçları

Kural katmanı, `gold.v2` (n=48, **kör** etiketlenmiş), strict eşleştirici,
belge düzeyi bootstrap 1000 örnek, tohum 42:

| ölçüt | değer |
|---|---|
| **yapılandırılmış alan mikro-F1** (11 alan, ikili) | **0,8228** |
| kalem düzeyi mikro-F1 (12 alan) | **0,6291** |
| 12-alan mikro-F1 | **0,5702** *(ikili ölçüt)* |
| makro-F1 | **0,7646** |
| halüsinasyon (bilgi metinde YOK, değer uyduruldu) | **0,0336** · yapısal kesitte 0,0254 |

**Hedef tutulmadı ve bu yazılıyor:** ikili 12-alan mikro-F1 **0,5702 < 0,60**
hedefinin altında kaldı. Sayı bugün iki turda iyileştirildi (0,4771 → 0,5702)
ama ilan edilmiş hedefe ulaşmadı; hedefi sonradan indirmek yerine tutulmadığını
yazıyoruz.

#### Alan bazında (aynı koşum, `strict`, tümü)

| alan | ikili F1 | not |
|---|---:|---|
| `vade_ay` | **1,000** | |
| `kar_payi_orani` | **1,000** | destek 3 — F1 yorumlanamaz |
| `finansman_tutari` | **1,000** | destek 4 |
| `kampanya_suresi` | 0,936 | |
| `alisveris_puani` | 0,933 | |
| `taksit_sayisi` | 0,909 | |
| `odul_miktari` | 0,727 | |
| `masraf_durumu` | 0,667 | |
| `indirim_orani` | 0,667 | destek 2 |
| `hedef_kitle` | 0,571 | kalem düzeyinde 0,632 |
| `kampanya_kosullari` | **0,000** | **kalem düzeyinde 0,520** — aşağıya bakınız |
| `tahsis_ucreti` | — | destek 0, F1 tanımsız |

> **`kampanya_kosullari` ikili 0,000 gizlenmiyor — ama tek başına okunması
> yanlıştır.** İkili ölçüt **tam küme eşitliği** arar: bir belgenin koşul
> listesi birebir eşleşmezse, kaç koşulun doğru çıkarıldığına bakılmaksızın
> sonuç TP=0 / FP=1 / FN=1 olur. Bu koşumda **137 kalemin 78'i doğru
> çıkarıldı** (kalem P 0,479 · R 0,569 · F1 **0,520**) ama **hiçbir kayıt**
> birebir küme eşleşmesi vermedi — dolayısıyla ikili sayı 0,000.
>
> Serbest metin listesi döndüren bir alanda anlamlı ölçüt **kalem
> düzeyidir**; ikili sayı yine de yayımlanıyor, çünkü onu saklamak ölçütün
> zayıflığını değil sonucu saklamak olurdu. **Üç görünüm de (ikili · kalem ·
> yapısal) yayımlanmaya devam ediyor** ve hiçbiri diğerinin yerine
> geçmez — yapısal kesit (11 alan) bu alanı dışlar, o yüzden 0,8228'dir.

> **Künye.** Bu sayılar **20 Ağustos 2026** koşumundan gelir
> (`eval/reports/20260820-130322/`, kod sha `7e19f2d0`, gold sha `e38a5276…`).
> Üreten komut:
> ```bash
> .venv/bin/python -m eval.run_eval --gold data/gold/gold.v2.json --config kural
> ```
>
> **Bugün iki tur iyileştirme koştu ve sayılar bu yüzden değişti:**
>
> | ölçüt | 19 Ağu (`20260820-053530`) | **20 Ağu (bugün)** |
> |---|---|---|
> | 12-alan mikro-F1, ikili | 0,4771 | **0,5702** |
> | kalem mikro-F1 | 0,3866 | **0,6291** |
> | yapısal mikro-F1 (11 alan) | 0,6980 | **0,8228** |
> | makro-F1 | 0,6317 | **0,7646** |
> | halüsinasyon oranı | 0,0425 | **0,0336** |
>
> Önceki manşetler (0,452 · 0,464 · 0,477) **artık geçerli DEĞİLDİR** — her
> biri kendi kesitinin tarihsel değeridir. Belgede bu sayılarla
> karşılaşırsanız tarihine bakın; kanıt-tazeliği kapısı
> (`python -m scripts.kanit_tazeligi`) bu kalıntıları arar.
>
> ⚠️ **Bu koşumun künyesi `git_dirty: true`.** Ölçüm bugünün işinin tamamı
> üzerinde koştu ama ağaç o an kirliydi (değişiklikler henüz commit
> edilmemişti). Kanıt-tazeliği kapısı bunu **doğru biçimde reddediyor** ve
> `KANIT YOK` diyor — kirli ağaçta üretilmiş rapor tekrar üretilemez, o yüzden
> kanıt sayılmaz. **Yapılacak (teslim öncesi):** commit'ten sonra `run_eval`
> yeniden koşulacak ve temiz damgalı rapor üretilecek. Sayının değişmesi
> beklenmiyor; beklenen tek fark artefaktın **kanıt sayılabilir** hâle
> gelmesidir.

**Neden üç mikro-F1 birden veriliyor:** `kampanya_kosullari` serbest cümle
listesi döndürür; küme eşitliği arayan ikili ölçüt bu alanda metodolojik
olarak yanlıştır (aynı koşulu farklı sözcüklerle yazan iki anotatör bile
birbirini "yanlış" bulurdu). Alan **gizlenmiyor**: ikili sayısı (0,000), kalem
sayısı (0,520) ve alanı dışlayan yapısal kesit (0,8228) **üçü birden**
yayımlanıyor. Ayrıntı: kök [`README.md`](../README.md#-ölçülebilir-durum).

#### Gold setin statüsü — iki set, iki farklı güvenilirlik

Bu ayrım metriklerden önce gelir ve **birleştirilerek sunulmaz**:

| set | n | kim etiketledi | hakemlik |
|---|---|---|---|
| `gold.v1` | 20 | **insan** anotatör | ✅ geçti (2 kayıt düzeltildi) |
| `gold.v2` | 48 | **makine** anotatör (M1–M4), her belge birebir alıntı kanıtıyla | ❌ hakemlik yok (`adjudicated: false`) |
| `gold.round1` | 134 | **makine** anotatör (A–D), protokol v2 | 🟠 **makine kör hakem** — 38 kayıt (`adjudicated: true`); insan hakemliği YOK |

Yukarıdaki **0,5702** `gold.v2` üzerinde ölçüldü, yani **insan
hakemliğinden geçmemiş** bir sette. Bunu gizlemek yerine yazıyoruz çünkü
alternatifi (`gold.v1`'in 0,677'sini manşete koymak) daha kötü — o da modele
çapalı bir protokolden geliyor. İkisi de kısıtlıdır ve ikisi de kısıtıyla
birlikte sunulur.

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
> **yorumlanamaz** — üç karar bir F1 taşımaz. Korpusta alan **146/2.708 belgede (%5,4)** var
> (ölçüm 2026-08-21; PDF hasadı payı 60'tan 146'ya çıkardı). Önceki ölçüm: **60/1.782 (%3,4)**
> (ölçüm 2026-08-16, sahte `%0` temizliğinden sonra; önceki yayımlanan değer 70/1.782 = %3,9 idi
> ve içinde bağlamsız sıfırlar vardı) — bu bir
> model kısıtı değil, **veri gerçeği**: bankalar oranları kampanya
> sayfalarında büyük ölçüde yayımlamıyor.

**Tekrarlanan tek sayı halüsinasyon oranıdır** (~%10), payda 166'dan 444'e
çıkarken korundu. İki protokolden de bağımsız çıkan tek metrik budur.

#### Halüsinasyon oranı: `gold.v2` ile `gold.round1` DOĞRUDAN KARŞILAŞTIRILAMAZ

İki gold setin halüsinasyon oranı çok farklı görünüyor: `gold.v2` **0,034**,
`gold.round1` **0,344**. Bu bir model kötüleşmesi **değildir** — paydanın
farklı tanımlı olmasıdır. Aşağıdaki sayılar iddiaya güvenilmeden, en yeni iki
rapordan (`per_field.csv`, `kural;strict;all` satırları, 12 alan) elle
toplanarak doğrulandı:

```bash
.venv/bin/python -m eval.run_eval --gold data/gold/gold.v2.json --config kural
.venv/bin/python -m eval.run_eval --gold data/gold/gold.round1.json --config kural
```
Kanıt: `eval/reports/20260820-224033/` (`gold.v2`) ve
`eval/reports/20260820-224058/` (`gold.round1`).

| | `gold.v2` (n=48) | `gold.round1` (n=134) |
|---|---:|---:|
| halüsinasyon oranı | **0,034** (15/447) | **0,344** (21/61) |
| payda (`absent_decisions` toplamı — gold'un "YOK" dediği karar sayısı, 12 alan) | **447** | **61** |
| `skipped_undecided` toplamı (gold hiç karar vermemiş, metriğe hiç girmeyen alan-kararı) | 0 | **1.389** |

`gold.round1`'in paydası küçük çünkü anotatörler **1.389 alan-kararında hiç
karar vermemiş**; bunlar metrik dışı kalıyor ve `absent_decisions`'a hiç
girmiyor. `gold.v2`'de "YOK" kararı 447 kez verilmiş, `gold.round1`'de yalnız
61 kez — küçük paydada tek kayıt oranın çok daha büyük bir dilimini taşır:
61'lik paydadaki 21 halüsinasyonun **10'u tek başına `vade_ay`** alanından
geliyor (`per_field.csv`: `vade_ay` satırı `fp_hallucinated=10`), yani
round1'in yüksek oranının ~%48'i tek bir alanın kararlarına yığılı.

**Sonuç:** iki oran ayrı ayrı doğru ölçülmüş ama yan yana konup "model
round1'de kötüleşti" denemez. Payda 447'den 61'e küçülmesi bir **gold
kapsama yoğunluğu artefaktıdır**, gerçek bir model kusuru değil.

### Ölçümle yanlışlanan hipotezler

Bu projede "daha güçlü model ekleyelim" refleksi **beş ayrı kolda** denendi ve
beşinde de kural katmanı önde kaldı. LLM'li dört kolun künyesi ortak:
20 Ağustos 2026, `gold.v2` (48 kayıt, 40 zor), `qwen2.5:7b-instruct`, CPU,
`LLM_STRICT=1`, mikro-F1 `strict`:

| deneme | sonuç |
|---|---|
| Hibrit kol (LLM boşlukları doldurur) | **20 Ağu, 40 zor belge:** 0,4402 vs kural 0,4771; McNemar p=0,00050; halüsinasyon **2,4 katı** (0,0425 → 0,1029). *(5 Ağu, n=20: 0,575 vs 0,677 — aynı yön)* |
| LLM-only kol | 0,2545 vs kural 0,4771; McNemar p=0,00105. LLM sağlığı temiz (384/384 çağrı, 0 hata) — düşük başarım arıza değil |
| Doğrulama kolu (`hibrit-verify`) | 0,3672 — hibritten de **kötü**; güven skoru kalibre olmadığı için doğru değerleri de eliyor |
| Orkestrasyon (ajan önerir, hakem reddeder) | 0,377 vs kural 0,387; üç ölçütte de kural önde. McNemar yönü kuralı gösteriyor (ham p=0,039) ama **çoklu karşılaştırma düzeltmesi yapılmadı** — projede ≥18 test koşuldu, bu p tek başına kanıt sayılmamalı |
| BERTurk ince ayarı (8 sınıf) | makro-F1 0,565 vs kural 0,762 — kabul kapısında **kaldı**, projeye alınmadı |

Mekanizma hepsinde aynı: LLM doğru sayısını artırmıyor, yanlış sayısını
artırıyor. Sebep yapısaldır — `reconcile.py` sözleşmesi gereği LLM kuralın
FP'lerini **düzeltemez**, yalnız kuralın boş bıraktığı alanlara FP
**ekleyebilir**; kazanç tavanı dar, kayıp tabanı geniştir. Negatif sonuçlar
gizlenmedi; `docs/rapor/ablasyon.md` ve
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

**Bu açık 19 Ağustos'ta KAPANDI — ama insan turuyla değil.** Aşağıdaki
paragraf önceki hâlini belgeliyor ve silinmiyor, çünkü kapanmanın NASIL
olduğu sayının kendisi kadar önemli.

> *(19 Ağustos öncesi)* Revizyondan sonra κ'nın düzelip düzelmediği
> ölçülemedi: `round0_kalibrasyon_v2_{A,B,C,D}.csv` dağıtıldı ama dördünün
> **sha256'sı birebir aynı** (`66c7db60…`), yani hiçbiri doldurulmamış.

### κ v2 — ÖLÇÜLDÜ: **0,714** (ikinci etiketleyici bir LLM)

`gold.v2`'nin 48 kaydında **hiç etiketleyici örtüşmesi yoktu**
(`annotators` dağılımı M1:12, M2:12, M3:12, M4:10, M4+HAKEM-02:2) ve κ
örtüşme olmadan tanımı gereği hesaplanamaz. 16 kayıt (her etiketleyici
bloğundan 4, blok içinde eşit aralıkla) bağımsız bir LLM turuyla ikinci kez
etiketlendi:

| Ölçüt | Değer | Karar |
|---|---|---|
| **κ — varlık kararı** (192 çift) | **0,714** | **notla kabul** — §7'nin 0,67 ≤ κ < 0,80 bandı |
| Değer uyumu — birebir | 0,423 (11/26) | κ değil; şans düzeltmesi yok |
| Krippendorff α (`ratio`) | 1,000 ama **3 birim** | **yetersiz birim** — iddia kurulmuyor |

Eşik tablosu anotasyon başlamadan sabitlenmişti; ölçülen κ onun ilan edilmiş
bandına düştü ve o bandın gereği olan not bu bölümdür. Örtüşme artık gold'un
KENDİSİNDE görünür (`annotators` içinde `LLM-01`; 18 kayıt ≥ 2 etiketleyici).

### κ İNSAN turu — ÖLÇÜLDÜ: κ (İNSAN) = **0,716**

Yukarıdaki turun tek zayıf noktası ikinci etiketleyicinin bir LLM olmasıydı:
model-model uyumu, gold'un **insan** yargısıyla tutarlılığını kanıtlamaz.
Bu yüzden **aynı 16 kayıt** (aynı seçim mantığı, yeni rastgelelik yok) bir
İNSAN tarafından ikinci kez etiketlendi (`INSAN-01`, 287 dk).

Körleme yapısaldır: alan sorma fonksiyonu gold/LLM parametresi **bile
almıyor**, kayıt alanlarına ve LLM turunun dosyasına hiç erişmiyor
(`tests/test_insan_etiketleyici.py` bunu sahte bir gold değerinin hiçbir
çıktı satırında görünmediğini göstererek kilitliyor).

| Ölçüt | LLM turu | **İNSAN turu** |
|---|---|---|
| κ — varlık kararı (192 çift) | 0,714 | **0,716** |
| Değer uyumu — birebir | 0,423 (11/26) | **0,750 (18/24)** |
| Uyuşmazlık | 31 | **21** |
| Krippendorff α (`ratio`) | 1,000 / 3 birim | 0,760 / 9 birim — ikisi de **yetersiz birim** |

**İki bulgu, ikisi de ölçülmüş:**

1. **Varlık kararında LLM geçerli bir vekildi.** İki κ arasındaki fark
   **0,002**. Yani gold'un κ'sının 0,80 eşiğinin altında kalmasının sebebi
   "ikinci etiketleyici LLM'di" değil; gold setin kendi tutarlılık
   seviyesidir. Bu, LLM turunun sonucunu güçlendirir — çürütmez.
2. **Değer uyumunda LLM zayıf bir vekildi.** 0,423 ↔ 0,750. Alanın *var
   olduğunu* saptamak ile *doğru değeri* yazmak farklı zorluklardır ve LLM
   ikincisinde belirgin biçimde geride kaldı. "İkinci etiketleyici LLM
   olabilir" sonucu bu yüzden yalnız varlık kararı için geçerlidir.

κ hâlâ 0,80'in altında ve **§7'nin ilan ettiği "notla kabul" bandındadır**;
insan turu bu bandı değiştirmedi, yalnız sebebini netleştirdi.

Bir düzeltme kayıtta duruyor: `INSAN-01` bir kayıtta `kampanya_suresi`'ni
`2926-09-01` girdi (hane hatası), sonradan `2026-09-01` olarak bildirdi.
Düzeltme uygulandı ve **eski değer `duzeltmeler` alanında saklandı** — IAA
verisinde sonradan yapılan değişiklik κ'yı etkilediği için izi bırakılır.

**İkinci etiketleyicinin LLM olduğu saklanmıyor** ve tek başına insan
çift-anotasyonun yerine geçmez. Turun kendisi bunun nedenini gösterdi: bir
vakada LLM, belgede `masraf|ücret|komisyon` geçen **sıfır** cümle olmasına
rağmen `has_fee:false` üretti — yani bağımsız görüş değil **uydurma**.

**Hakemlik koştu ve gold'u düzeltti.** `masraf_durumu` κ'sı hakemlik
ÖNCESİNDE **−0,103** (gözlenen uyum 12/16), hakemlik SONRASINDA **−0,091**
(13/16) — hâlâ negatif, yani anlaşmazlık sistematik ve alan **kapanmadı**.
Dört uyuşmazlık hakemlendi → 3 onay, 1 düzeltme. Düzeltilen vakada kusur
anotatörde değil **kılavuzun kapsamında**ydı: kural "ücretsiz" gördüğü her
yerde sıfır masraf diyordu ve *"GastroClub üyeliği … ücretsiz"* cümlesi
belgeyi kıyas tablosunda **"masrafsız" rozetiyle** gösteriyordu. Düzeltme üç
katmanda birden yapıldı (gold + kılavuz §4 kapsam kuralı + motorda
`_ALAN_DISI_OZNE_RE` kolu) ve **ölçülen bedeli raporlanıyor**: mikro-F1
0,482 → 0,477, çünkü gold ile motorun aynı yanlışı yaptığı bir hücre TP
sayılıyordu; ikisi de düzeltilince hücre TN oldu ve TN F1'e girmez.

> **Bu düzeltme κ'yı da değiştirdi ve yayımlanan κ 0,700'de KALDI.** Hakemlik
> `hayat-finans … gastroclub` kaydındaki uyuşmazlığı çözünce toplam uyuşmazlık
> 32 → 31'e, `masraf_durumu` gözlenen uyumu 12/16 → 13/16'ya ve **κ 0,700 →
> 0,714**'e taşındı. Sayı bizim lehimize değişti ama README günlerce eski
> değeri yayımladı; **yanlış sayı lehimize de olsa yanlıştır**. Kanıt-tazeliği
> kapısı bunu yakalamamıştı çünkü κ hiç denetlenmiyordu — kapı onarıldı
> (`kappa_ikinci_tur` iddiası) ve artık bu sapma CI'ı kırar.

Ayrıntı: [`data/gold/review/_kappa-ikinci-tur.md`](data/gold/review/_kappa-ikinci-tur.md)
· [`data/gold/review/_hakem-turu-03-masraf-durumu.md`](data/gold/review/_hakem-turu-03-masraf-durumu.md)

**Hâlâ açık:** insan hakemliği. Bir sonraki tur `colab/03_kappa.py` ile daha
güçlü bir modelle (`qwen3` ailesi) tekrar ölçüp "düşük değer uyumunun sebebi
gold mu, yargıç mı" ayrımını yapacak.

### Sonraki adımlar

Öncelik sırasıyla, teslime kalan sürede:

- ~~**κ v2 turunu anote et**~~ — **YAPILDI (19 Ağu)**, ama LLM ikinci
  etiketleyiciyle: κ = **0,714**, "notla kabul" bandı (yukarıdaki bölüm).
  Kalan iş **insan** hakemliği ve ikinci turun daha güçlü bir modelle
  tekrarı (`colab/03_kappa.py`).
- **Gold seti büyütmek** — 66 → 150 bandı; GA'lar daralır ve **0,5702**
  nokta tahmini savunulabilir hâle gelir (bugünkü %95 GA **0,492–0,632**, yani
  genişliği **0,140** — nokta tahminin dörtte biri kadar. Bu genişlikte
  "0,5702 < 0,60 hedefi" ifadesi bile GA içinde kalıyor; hedefin
  tutulmadığını nokta tahmine dayanarak yazıyoruz, GA'ya dayanarak
  *kesinleştirmiyoruz*).
- **`kampanya_kosullari` ve `vade_ay`** — ikisi mikro-F1'in en büyük tek
  kaldıracı; eşleştirici sertliği mi tanım sorunu mu ayrıştırılmalı.
- ~~**Değişmez denetimini 1.774 belgede tekrarla**~~ — **YAPILDI, en son 2026-08-21:**
  2.708 belge, **0 ihlal**, kapsam **%92,3**. Komut ve çıktı yukarıdaki "Ölçüm
  Durumu" tablosunda. Kalan iş: kapsamı yükseltmek — 209 belgeden hiç alan
  çıkmıyor ve o belgelerde denetim hiçbir şey test etmiyor.
- **Ablasyon kolları** — izole ortamlarda kalan kollar (Trendyol-8B hibrit,
  GLiNER geri-çağırma ağı). Başarısız kollar **negatif sonuç olarak
  raporlanır**; üç tanesi zaten öyle raporlandı.
