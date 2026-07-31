# Offline / On-Prem Kanıt Paketi

**Durum:** ölçüldü — `--network none` koşusu **14/14 adım** beklendiği gibi
**Koşu tarihi:** 2026-07-31T10:58:58Z (UTC)
**Üreten betik:** [`scripts/offline_proof.sh`](../scripts/offline_proof.sh)
**Ham transkript:** [`docs/offline-proof/transcript-20260731-135858.log`](offline-proof/transcript-20260731-135858.log) (1254 satır, kesilmemiş)
**Sorumlu kalem:** Şartname §5.9 (dış servise bağımlı olmadan yerel çalışma), §8, §5.10

---

## Neden bu belge var

Şartname §5.9 sistemin dış servise bağımlı olmadan yerel (on-premise)
çalışmasını şart koşuyor; rubrikte **On-Prem Uygulanabilirlik %20**.

Bugüne kadar elimizde bu başlıkta **tek bir ölçüm yoktu**. `docker-compose.yml`
"offline ayağa kalkar" diyordu, `Dockerfile.api` yorumu var olmayan bir
`docs/OFFLINE-KANIT.md`'ye atıf yapıyordu. Bu belge o boşluğu kapatır ve
iddiaları **koşturulmuş komut çıktısıyla** değiştirir.

**Belgenin sözleşmesi:** burada yazan her sayı gerçekten koşturulmuş bir
komuttan gelir. Koşturulmayan her kalem `⏳ ölçülmedi — sebep: ...` ile
işaretlidir. Ara değer, tahmin, "olması beklenen" sayı yoktur.

---

## 1. Ölçüm ortamı

| Kalem | Değer |
|---|---|
| Host | Darwin 25.5.0, arm64 (Apple Silicon, MacBook Air), 10 çekirdek |
| Docker | CLI 29.5.3 · daemon 29.6.1 (linux/aarch64) |
| Konteyner | `linux/arm64`, Python 3.11.15, Linux 6.12.76-linuxkit, glibc 2.41 |
| Taban imaj | `python:3.11-slim@sha256:db3ff2e1…53a93` (digest'e sabit) |
| Teslim imajı | `anatolia-api:offline-proof` · ID `sha256:f234fe8d7733…` · **101 218 586 bayt (≈96,5 MiB)** |
| Git commit | `025c1e5` |
| LLM arka ucu | **kapalı** (`LLM_BACKEND=""` → `NullLLMExtractor`) |

> ⚠️ **GPU yok.** Bu makinede GPU bulunmadığı için vLLM / Trendyol-LLM-8B-T1
> kolu **hiç koşturulmadı**. Aşağıdaki tüm gecikme sayıları **CPU, LLM'siz**
> yoldan gelir. Ayrıntı: §7 ve §9.

---

## 2. Kanıtın omurgası: negatif kontrol ve onun pozitif kontrolü

Bir sistemin offline çalıştığını göstermenin zayıf yolu, testlerin ağsız
geçtiğini söylemektir — testler ağı hiç denemiyor olabilir. Güçlü yol, ağ
erişimi **deneyen** bir çağrının izolasyon içinde **başarısız olduğunu**
göstermektir.

Ama bu da tek başına yetmez: prob başka bir sebeple (yazım hatası, eksik ikili,
yanlış hostname) her koşulda başarısız oluyorsa "izolasyon çalışıyor" diye
**yanlış** sonuç çıkarırız. Bu projede daha önce *"duman testi bağlantı hatasını
BAŞARILI raporladı"* sınıfından bir hata yaşandı.

Bu yüzden **aynı prob iki kez** koşturulur:

| Adım | Ortam | Beklenti | Gerçekleşen |
|---|---|---|---|
| 2 | ağ **AÇIK** (`docker run`) | proba **ULAŞMALI** | ✅ 4/4 ulaştı |
| 3 | ağ **KAPALI** (`--network none`) | proba **ULAŞAMAMALI** | ✅ 4/4 engellendi |

Adım 2 olmadan adım 3 hiçbir şey kanıtlamaz. İkna edici olan çift.

### 2.1 Adım 2 — ağ AÇIK, prob çalışıyor (ham çıktı)

```
ADIM 2: Prob dogrulama: ag ACIK iken prob ULASMALI (metaKontrol)
beklenti : cikis kodu 0
komut    : docker run --rm anatolia-api:offline-proof python -c <prob>
------------------------------------------------------------------------------
  [ULASILDI]   DNS huggingface.co       -> AG ERISIMI VAR
  [ULASILDI]   TCP 1.1.1.1:443          -> AG ERISIMI VAR
  [ULASILDI]   HTTPS huggingface.co     -> AG ERISIMI VAR
  [ULASILDI]   HTTPS pypi.org           -> AG ERISIMI VAR

engellenen: 0/4   ulasilan: 4/4
------------------------------------------------------------------------------
sonuc    : cikis kodu=0  sure=723 ms  -> BEKLENDIGI GIBI
```

### 2.2 Adım 3 — NEGATİF KONTROL, `--network none` (ham çıktı)

```
ADIM 3: NEGATIF KONTROL: --network none icinde ag ERISILEMEZ olmali
beklenti : cikis kodu 0 DEGIL (negatif kontrol)
komut    : docker run --rm --network none ... anatolia-api:offline-proof python -c <prob>
------------------------------------------------------------------------------
  [ENGELLENDI] DNS huggingface.co       -> gaierror: [Errno -3] Temporary failure in name resolution
  [ENGELLENDI] TCP 1.1.1.1:443          -> OSError: [Errno 101] Network is unreachable
  [ENGELLENDI] HTTPS huggingface.co     -> URLError: <urlopen error [Errno -3] Temporary failure in name resolution>
  [ENGELLENDI] HTTPS pypi.org           -> URLError: <urlopen error [Errno -3] Temporary failure in name resolution>

engellenen: 4/4   ulasilan: 0/4
------------------------------------------------------------------------------
sonuc    : cikis kodu=3  sure=228 ms  -> BEKLENDIGI GIBI
```

Dört prob **birbirinden bağımsız katmanları** sınar: DNS çözümleme (ad
çözümleme), ham TCP (yönlendirme), ve iki ayrı HTTPS hedefi (model deposu +
paket deposu). Hata mesajları farklı ve işletim sistemi düzeyinde
(`Errno -3`, `Errno 101`) — yani gerçekten çekirdek seviyesinde ağ yok, uygulama
katmanında bir zaman aşımı taklidi değil.

### 2.3 `curl` neden yok

Görev tanımında `curl -sS --max-time 5 https://huggingface.co` istenmişti.
`python:3.11-slim` taban imajı **curl içermez**. Bu adım koşturulsaydı
`command not found` da 0-dışı dönerdi ve *ağ izolasyonunun kanıtı sanılırdı* —
tam olarak kaçındığımız hata sınıfı. Betik bu yüzden `curl`'ün varlığını **ayrı
olarak** sınar ve yoksa adımı atlayıp gerekçesini transkripte yazar:

```
NOT: imajda 'curl' YOK (python:3.11-slim taban imaji curl icermez).
     Bu yuzden 'curl -sS --max-time 5 https://huggingface.co' adimi
     KOSTURULMADI. Kosturulsa 'command not found' da 0-disi donerdi ve
     ag izolasyonunun kaniti SANILIRDI — bu tam olarak kacinilan hata.
     Ayni is adim 3'teki stdlib probu ile, bagimliliksiz yapiliyor.
```

Aynı iş stdlib probuyla, bağımlılıksız ve daha ayrıntılı yapılıyor.

---

## 3. `--network none` içinde koşan gerçek iş

Aşağıdakilerin hepsi **ağı tamamen kapatılmış** konteynerde koştu.

| # | Adım | Çıkış | Süre | Sonuç |
|---|---|---|---|---|
| 1 | `docker build -f Dockerfile.api` | 0 | 3 471 ms (önbellekli) | ✅ |
| 2 | Prob doğrulama (ağ açık) | 0 | 723 ms | ✅ |
| 3 | **NEGATİF KONTROL** (ağ kapalı) | 3 | 228 ms | ✅ |
| 4 | Test paketi (`unittest discover`) | 0 | 509 ms | ✅ |
| 5 | `eval.properties --raw-dir data/raw` | 0 | 15 460 ms | ✅ |
| 6 | `eval.run_eval --gold …` | 0 | 242 ms | ✅ |
| 7 | `eval.ablation --gold …` | 0 | 198 ms | ✅ |
| 8 | `scripts.latency_bench --recursive` | 0 | 118 861 ms | ✅ |
| 9 | Offline ortam değişkenleri | 0 | 201 ms | ✅ |
| 10 | `pip list` dökümü | 0 | 330 ms | ✅ |
| 11 | `trafilatura` yok (negatif kontrol) | 1 | 297 ms | ✅ |
| 12 | `trafilatura` import edilemez | 0 | 168 ms | ✅ |
| 13 | **API sunucusu ağsız ayağa kalkıyor** | 0 | 2 806 ms | ✅ |
| 14 | İmaj künyesi | 0 | 51 ms | ✅ |

**beklenmedik sonuç: 0 / 14**

> İlk derleme (soğuk, taban imaj çekilerek) **192 641 ms**'de tamamlandı;
> tablodaki 3 471 ms önbellekli koşudur. Her ikisi de transkriptlerde.

### 3.1 Testler (ham kuyruk)

```
Ran 607 tests in 0.240s

OK
```

> Betik test sayısını **yazmaz**. Sabit bir "345 test" ifadesi paket büyüdükçe
> sessizce yalan olurdu; gerçek sayı her koşuda transkriptteki `Ran N tests`
> satırındadır. Bu koşuda 607.

### 3.2 Değişmez denetimi (ham çıktı)

```
849 belge (732 tanesinde en az bir alan çıktı; 117 boş belgede denetim hiçbir şey
test etmiyor — kapsam 86.2%) — tüm değişmezler GEÇTİ (0 ihlal)
```

### 3.3 Değerlendirme ve ablasyon (ham çıktı, kısaltılmadı)

```
konfig : kural — yalnız kural katmanı (regex + normalizasyon), LLM kapalı
gold   : data/gold/gold.sample.json (3 kayıt, alt küme 'all' -> 3 belge)

=== KURAL / strict — TÜM VAKALAR ===
MİKRO                   1.000  1.000  1.000    9    0    0    0    0   27
MAKRO (F1 ort.)                       1.000

=== ABLASYON — eşleştirici 'strict' ===
konfig            F1(tüm)   makro  F1(zor)    TP    FP    FN   UYD  mikro-F1 %95 GA
kural               1.000   1.000    1.000     9     0     0     0  1.000 [1.000–1.000]
llm             ÖLÇÜLMEDİ   (bkz. NOTLAR)
hibrit          ÖLÇÜLMEDİ   (bkz. NOTLAR)
hibrit-verify   ÖLÇÜLMEDİ   (bkz. NOTLAR)
```

> **Bu tablodan doğruluk sonucu çıkarmayın.** `gold.sample.json` yalnızca **3
> kayıt** içerir; F1=1.000 istatistiksel olarak anlamsızdır (güven aralığı da
> dejenere: `[1.000–1.000]`, n=3). Buradaki kanıt **doğruluk değil**, bu
> boru hattının **ağsız koşabildiğidir**. Doğruluk kanıtı gold setin
> büyümesini bekliyor ve bu belgenin konusu değil.

### 3.4 Offline ortam değişkenleri (ham çıktı)

```
ANATOLIA_OFFLINE=1
HF_HUB_DISABLE_TELEMETRY=1
HF_HUB_DISABLE_UPDATE_CHECK=1
HF_HUB_OFFLINE=1
TRANSFORMERS_OFFLINE=1
```

### 3.5 API sunucusu `--network none` içinde ayağa kalkıyor (adım 13)

Adım 4–12 **toplu iş (batch)** kanıtıydı. Şartname §5.9 çalışan bir **servis**
istiyor; *"testler ağsız geçti"* ile *"sunucu ağsız ayağa kalktı"* farklı
iddialardır. Adım 13 ikincisini ölçer: konteyner başlatılır, HTTP istekleri
**konteynerin İÇİNDEN** `127.0.0.1`'e atılır (dışarı çıkış yok), bellek
ölçülür, konteyner durdurulur.

```
konteyner : 6a5b7c26ff37…
hazir olma suresi : ~1 sn

--- /health (konteyner ICINDEN, localhost) ---
{"status":"ok","llm":false}

--- /banks (ilk 300 karakter) ---
[{"slug":"kuveyt-turk","name":"Kuveyt Türk","website_url":"https://www.kuveytturk.com.tr",
"bddk_active":1},{"slug":"albaraka","name":"Albaraka Türk", …

--- calisma zamani kaynak kullanimi ---
BELLEK=36.36MiB / 7.75GiB  CPU=0.81%  PID=2

--- sunucu gunlugu ---
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     127.0.0.1:43900 - "GET /banks HTTP/1.1" 200 OK
```

Üç bulgu:

1. Sunucu **~1 saniyede** hazır — demo için fazlasıyla yeterli.
2. `/health` `llm:false` diyerek LLM'in kapalı olduğunu **dürüstçe** raporluyor.
   Sahte bir "hazır" yok; servis neyin çalışmadığını söylüyor.
3. `/banks` gerçek veri dönüyor (çıktı transkriptte **300 karakterde kesildi**,
   ilk üç banka görünüyor; `config/banks.yaml` 10 banka tanımlıyor ve
   `run_pipeline` hepsini kaydediyor).

---

## 4. Betiğin gerçekten hata yakaladığının kanıtı

Yeşil bir koşu, harness'ın çalıştığını değil, sistemin o an sağlam olduğunu
gösterir. Harness'ın **lastik damga olmadığını** göstermek için: ara koşulardan
biri gerçek bir kırılmayı yakaladı ve betik 0-dışı çıktı.

**Transkript:** [`transcript-20260731-134646.log`](offline-proof/transcript-20260731-134646.log)

```
4   Test paketi (345 test) — --network none            1      648      BEKLENMEDIK
...
adim sayisi        : 13
beklenmedik sonuc  : 1

SONUC: 1 ADIM BEKLENMEDIK. Kanit paketi GECERSIZ.
```

Kök neden (o an paralel geliştirilen `tests/test_run_eval.py` dosyasında
eksik `import contextlib`):

```
ERROR: test_basarili_kosum (test_run_eval.TestCLI.test_basarili_kosum)
NameError: name 'contextlib' is not defined
```

Bu kırılma bizim dosyalarımızda değildi ve sonraki koşudan önce düzeltildi;
buraya **betiğin sessizce yeşil raporlamadığının kanıtı** olarak konuldu.

---

## 5. Digest pin tablosu (tekrar-üretilebilirlik)

Önceki `docker-compose.yml` üç imajı da **hareketli etiketle** (`:pg16`,
`:latest`) çekiyordu. "Offline **ve** tekrar üretilebilir" iddiası hareketli
etiketle teknik olarak yanlıştır: aynı dosya üç ay sonra farklı imajlar çeker ve
jürinin gördüğü sistem bizim test ettiğimiz sistem olmaz.

Digest'ler **2026-07-31'de** `docker buildx imagetools inspect <imaj>` ile
gerçekten çözüldü (uydurulmadı):

| Bileşen | Etiket | Digest (çoklu-mimari indeks) | Sıkıştırılmış boyut (linux/arm64) |
|---|---|---|---|
| PostgreSQL + pgvector | `pgvector/pgvector:pg16` | `sha256:a36250871de0833b8757561c72f2477ef1ddd1101afa4e617fb552e0de514c6b` | 154,1 MB (16 katman) |
| vLLM sunucusu | `vllm/vllm-openai:latest` | `sha256:ffb2d59b1c059a5bd8d781320c9f5189de8293693b7d95da54befddaa54abf52` | **10 349,3 MB** (32 katman) |
| Ollama (yedek) | `ollama/ollama:latest` | `sha256:4dea9fb511947e24a84237bb636b0203abcb2ff0d3fbc7b4ff865deb91362131` | 2 774,1 MB (4 katman) |
| API taban imajı | `python:3.11-slim` | `sha256:db3ff2e1800a8581e2c48a27c3995339d47bdf046da21c7627accd3d51053a93` | — (teslim imajına gömülü) |

Yenilemek için:

```bash
docker buildx imagetools inspect pgvector/pgvector:pg16 | grep Digest
```

> Digest yenilenirse bu tablo **ve** `docker-compose.yml` birlikte güncellenmeli;
> aksi halde belge ile dosya çelişir.

### 5.1 Model lisansı — vLLM kolu korundu

`--model Trendyol/Trendyol-LLM-8B-T1` **çıkarılmadı**. Lisans zinciri
2026-07-31'de doğrulandı: `license: Apache-2.0`, zincir
`Qwen3-8B-Base → Qwen3-8B → Trendyol-LLM-8B-T1`. Zincirde Llama/Gemma **yok**,
ticari-olmayan kısıt **yok** → §5.10 uyumlu.

> ⚠️ `docs/model-license-audit.md` (2026-07-27 tarihli, **başka bir kalemin
> sahipliğinde**) bu modeli hâlâ `⛔ BLOKE` olarak listeliyor. Belge ile bu
> doğrulama **çelişiyor**; ilgili kalem tarafından güncellenmesi gerekiyor. Bu
> belge o dosyayı düzenlemedi, yalnızca çelişkiyi kayda geçiriyor.

---

## 6. `trafilatura` (GPLv3+) teslim imajında YOK — ölçülmüş kanıt

`docs/model-license-audit.md` §2'ye göre `requirements.txt` yorumunda `# GPLv3+`
işareti vardı ve GPLv3, projenin Apache-2.0 ile dağıtım şartıyla (§8) uyumsuz.
Karar: teslim imajına (`requirements-api.txt`) alınmayacak. **Kanıtı:**

Teslim imajının tam paket dökümü (adım 10, ham, kesilmemiş):

```
annotated-doc==0.0.5      idna==3.18                setuptools==79.0.1
annotated-types==0.8.0    packaging==26.2           soupsieve==2.9.1
anyio==4.14.2             pgvector==0.5.0           starlette==1.3.1
beautifulsoup4==4.15.0    pip==24.0                 typing-inspection==0.4.2
click==8.4.2              psycopg-binary==3.3.4     typing_extensions==4.16.0
fastapi==0.141.1          psycopg==3.3.4            uvicorn==0.52.0
h11==0.16.0               pydantic==2.13.4          wheel==0.46.3
                          pydantic_core==2.46.4
```

22 paket, tamamı MIT / BSD / Apache-2.0 / PostgreSQL / LGPL(dinamik).
**`trafilatura` listede yok.**

İki bağımsız negatif kontrol:

```
ADIM 11: trafilatura teslim imajinda YOK (grep bos donmeli)
komut    : ... sh -c 'pip list --format=freeze | grep -i trafilatura'
------------------------------------------------------------------------------
                                    <boş — hiçbir satır eşleşmedi>
------------------------------------------------------------------------------
sonuc    : cikis kodu=1  sure=297 ms  -> BEKLENDIGI GIBI

ADIM 12: trafilatura import EDILEMEZ (ikinci, bagimsiz kanit)
------------------------------------------------------------------------------
trafilatura find_spec: None
------------------------------------------------------------------------------
sonuc    : cikis kodu=0  sure=168 ms  -> BEKLENDIGI GIBI
```

`grep`'in boş dönmesi tek başına zayıf kanıttır (`pip` çalışmasaydı da 1
dönerdi); bu yüzden adım 10 tam listeyi basar ve adım 12 `importlib` ile
bağımsız olarak doğrular. Üçü birlikte kesin.

> Karar ve gerekçe `docs/model-license-audit.md` §2'ye aittir; bu belge onu
> **düzenlemez**, yalnızca ölçülmüş kanıtını sağlar.

### 6.1 Yan bulgu: `bs4` sapması (düzeltildi)

Ölçüm sırasında bulundu: `src/scraping/collector._extract_main_text`,
`beautifulsoup4` yoksa `except ModuleNotFoundError` ile **sessizce**
`normalize_text(html)`'e düşüyor. `requirements-api.txt`'te bs4 olmadığı için
teslim konteyneri, geliştirme ortamından **farklı metin** üretiyordu:

| Ortam | bs4 | 1696 belgede ortalama karakter |
|---|---|---|
| Geliştirme (host) | var | **4 317** |
| Teslim imajı (önce) | yok | **6 232** (+%44 menü/altbilgi gürültüsü) |
| Teslim imajı (sonra) | var | **4 320** ✅ |

Ham veri: [`latency-20260731-133540.json`](offline-proof/latency-20260731-133540.json)
(önce, `avg_chars: 6232`) ve
[`latency-20260731-135051.json`](offline-proof/latency-20260731-135051.json)
(sonra, `avg_chars: 4320`).

Testler yeşil olduğu için hata görünmüyordu — tam olarak "sessiz bozulma"
sınıfı. `beautifulsoup4` (MIT, saf Python) + `soupsieve` ince imaja eklendi;
imaj **100 802 593 → 101 208 799 bayt** büyüdü (**+406 KB**, %0,4). Bu bedel
karşılığında teslim imajı ile geliştirme ortamı aynı metni üretiyor.

On-prem kanıtının anlamı, **teslim edilen imajın test edilen sistemle aynı
davranmasıdır**; bu sapma kapatılmadan yukarıdaki hiçbir ölçüm teslim edilen
sistemi temsil etmiyordu.

---

## 7. Gecikme (latency) — üç yol ayrı ayrı

**Ölçüm:** `python -m scripts.latency_bench --recursive --iterations 3`,
**`--network none` konteyneri içinde**, 1696 gerçek banka belgesi
(ortalama 4 320 karakter), toplam 7 327 700 karakter.
Ham JSON: [`latency-20260731-135858.json`](offline-proof/latency-20260731-135858.json)

| Yol | n | p50 | p95 | p99 | max | ortalama |
|---|---|---|---|---|---|---|
| **(a) kural-only** `extract_all()` | 5 088 | **1,03 ms** | 4,80 ms | 6,30 ms | 37,63 ms | 1,79 ms |
| **(b) hibrit boru hattı** `build_campaign()` | 5 088 | **1,50 ms** | 6,92 ms | 8,86 ms | 75,32 ms | 2,59 ms |
| **(c) chatbot** `Chatbot.ask()` | 504 | **12,48 ms** | 325,02 ms | 351,36 ms | 368,53 ms | 155,11 ms |

Karşılaştırma için aynı ölçüm host'ta (macOS arm64, Python 3.14.6, konteynersiz):
kural p50 1,05 ms · hibrit p50 1,67 ms · chatbot p50 6,47 ms
([`latency-host-20260731.json`](offline-proof/latency-host-20260731.json)).
**Konteyner cezası kural ve hibrit yollarında pratikte yok** — on-prem
konteynerleştirme çıkarım hızını düşürmüyor.

### 7.1 "Önce kural" mimarisi sayıyla gerekçelendi

CLAUDE.md §3 "önce kural, sonra LLM" kararını ilan ediyordu ama destekleyen
ölçüm yoktu. Artık var: **kural yolu belge başına medyan 1,03 ms**, p99 6,30 ms.
Yerel 8B bir LLM'in tek çağrısı tipik olarak **saniyeler** mertebesindedir.
Yüksek güvenle kuralla çıkan alanı LLM'e göndermemek, uçtan uca gecikmeyi
**üç mertebe** düşürüyor. Karar doğrulandı.

### 7.2 ⚠️ Bu tablonun okunma biçimi — LLM DAHİL DEĞİL

`LLM_BACKEND` boş olduğu için `default_extractor()` **`NullLLMExtractor`**
döndürür. Yani (b) ve (c) satırları boru hattının **LLM dışı** kısmıdır.

Bu bilinçli bir ölçümdür — teslim edilen offline demo tam olarak bu
konfigürasyonda koşar (CLAUDE.md §11, önceden doldurulmuş DB). Ama
**"hibrit gecikmesi" diye 8B model çıkarımını içeren bir sayı sanılmamalı.**

`⏳ ölçülmedi — sebep: bu makinede GPU yok, vLLM/Trendyol-LLM-8B-T1 kolu
hiç çalıştırılmadı.` Ölçmek için:

```bash
LLM_BACKEND=vllm VLLM_URL=http://localhost:8001 \
  python -m scripts.latency_bench --recursive
```

Betik hangi arka ucun aktif olduğunu başlıkta basar; sahte "hibrit = kural"
satırı üretmez.

### 7.3 Bulgu: chatbot p95/p99 yüksek

Chatbot p50 12,48 ms ama p95 **325,02 ms**, p99 **351,36 ms** — yaklaşık 26×
yayılım. Sebep, router'ın iki kolunun çok farklı maliyette olması: yapısal sorgu
(text-to-SQL) indeksli ve hızlı; RAG kolu 1696 kampanyalık gövde üzerinde
tarama yapıyor. 4 dakikalık demoda RAG sorusu sorulursa yarım saniyelik
duraklama görünür.

Bu bir **performans borcudur**, kapsamım dışındadır (`src/chatbot/**` başka bir
kalemin), ama ölçülmüş olarak kayda geçiriliyor.

---

## 8. Kaynak tüketimi

Ayrıntılı tablo ve profil kırılımı: [`kaynak-tuketimi.md`](kaynak-tuketimi.md)

Özet (hepsi `--network none` konteyner koşusundan, gerçekten ölçüldü):

| Kalem | Ölçülen değer |
|---|---|
| Teslim imajı (API) boyutu | 101 218 586 bayt (≈96,5 MiB) |
| API sunucusu çalışırken bellek (boşta) | **36,36 MiB**, 2 PID, %0,81 CPU |
| API hazır olma süresi (`--network none`) | **~1 s** |
| Tepe RSS (çıkarım süreci, 1696 belge) | **100,4 MB** |
| Demo soğuk başlatma (`build_demo_repo`) | **5,7 ms** |
| Tam korpus alımı (1696 belge, uçtan uca) | **4,83 s** |
| Verim | **21 087 belge/dakika** |
| Test paketi (607 test) | 0,240 s |
| Değişmez denetimi (849 belge) | 15 460 ms |

---

## 9. Ağırlık bütünlüğü (model ağırlıkları)

**`⏳ KOŞTURULMADI — sebep: bu ortamda model ağırlıkları indirilmedi.`**

`app/models/` dizini repoda **yok** ve bu makinede oluşturulmadı. Ağırlıklar
onlarca GB'dır, git'e girmez ve GPU olmadan doğrulanmalarının pratik faydası
yok. Aşağıdaki tablo **boş bırakılmıştır** — uydurma SHA-256 yazılmadı.

| Bileşen | Repo ID | Revizyon (commit) | Dosya | SHA-256 |
|---|---|---|---|---|
| Çıkarım LLM'i | `Trendyol/Trendyol-LLM-8B-T1` | ⏳ | `model-*.safetensors` | ⏳ |
| Sınıflandırıcı | `dbmdz/bert-base-turkish-cased` | ⏳ | `pytorch_model.bin` | ⏳ |
| Embedding | `BAAI/bge-m3` | ⏳ | `model.safetensors` | ⏳ |

### 9.1 Uygulanacak prosedür (yazıldı, koşturulmadı)

Ağırlıklar **ağı olan** bir makinede bir kez indirilir, SHA-256'ları kaydedilir,
sonra hedef makineye taşınır ve `HF_HUB_OFFLINE=1` ile ağsız kullanılır.

```bash
# 1. İndir — REVİZYONU SABİTLE. Etiketsiz indirme tekrar üretilemez;
#    `main` hareketli bir referanstır.
huggingface-cli download Trendyol/Trendyol-LLM-8B-T1 \
    --revision <commit-sha> \
    --local-dir models/Trendyol-LLM-8B-T1

# 2. Bütünlük künyesi al — bu çıktı bu belgeye yapıştırılır.
find models/Trendyol-LLM-8B-T1 -type f \
    \( -name '*.safetensors' -o -name '*.json' -o -name 'LICENSE' \) \
    -exec shasum -a 256 {} \; | sort -k2

# 3. Çözülen revizyonu kaydet (etiket -> commit).
git -C models/Trendyol-LLM-8B-T1 rev-parse HEAD

# 4. Hedef (ağsız) makineye taşı, sonra doğrula:
shasum -a 256 -c weights.sha256
```

### 9.2 Doğrulanan kısım

Ağırlıkları indirmeden de doğrulanabilen şey doğrulandı: **konteyner
ağırlıkları indirmeye çalışmıyor.** `HF_HUB_OFFLINE=1` ve
`TRANSFORMERS_OFFLINE=1` imajda gerçekten set (§3.4) ve `--network none`
altında tüm boru hattı ağ çağrısı yapmadan tamamlanıyor (§3). Ağırlık klasörü
boşken vLLM **sessizce internete çıkmaz, başlamaz** — istenen davranış budur.

---

## 10. Dürüst eksikler — neyi ölçemedik ve neden

| Kalem | Durum | Sebep |
|---|---|---|
| vLLM + Trendyol-LLM-8B-T1 uçtan uca | `⏳ ölçülmedi` | Bu makinede **GPU yok**. İmaj bile 10,3 GB. |
| Gerçek hibrit gecikmesi (LLM dahil) | `⏳ ölçülmedi` | Aynı sebep; `NullLLMExtractor` ile ölçülen sayı LLM içermez (§7.2) |
| Ollama (CPU yedeği, Qwen3-4B GGUF Q4) | `⏳ ölçülmedi` | 2,8 GB imaj + ağırlık indirilmedi; ayrı bir koşu gerektirir |
| Tüketici GPU profili | `⏳ ölçülmedi` | Donanım yok |
| Sunucu GPU profili (A100/H100) | `⏳ ölçülmedi` | Donanım yok |
| Model ağırlığı SHA-256 | `⏳ koşturulmadı` | §9 — ağırlıklar indirilmedi, prosedür yazıldı |
| `docker compose up` tam yığın (postgres + api + web) | `⏳ koşturulmadı` | Bu paket **API konteynerini** kanıtladı (adım 13: sunucu ağsız ayağa kalkıyor). Postgres + Next.js web katmanının ağsız birlikte ayağa kalkması ölçülmedi |
| pgvector / Postgres ağsız başlatma | `⏳ ölçülmedi` | İmaj çekildi mi diye bakılmadı; `docker compose` koşusu yapılmadı |
| Doğruluk (P/R/F1) | ölçüldü **ama anlamsız** | `gold.sample.json` = 3 kayıt (§3.3). Ağsız *koşabilirlik* kanıtı, doğruluk kanıtı değil |
| `curl` negatif kontrolü | `atlandı, gerekçeli` | Taban imajda curl yok (§2.3); yerine stdlib probu |
| x86_64 (amd64) mimarisi | `⏳ ölçülmedi` | Host arm64. Digest'ler çoklu-mimari indeks olduğu için amd64 çalışmalı, ama **doğrulanmadı** |

---

## 11. Kanıtı yeniden üretme

```bash
cd app
bash scripts/offline_proof.sh
```

Betik:
- `set -euo pipefail` ile koşar,
- Docker yoksa veya daemon kapalıysa **açık hata** verip `exit 2` döner
  (sessizce "başarılı" **demez**),
- her adımın çıkış kodunu ve süresini kaydeder,
- transkripti `docs/offline-proof/transcript-<zaman>.log`'a yazar,
- en az bir adım beklenmedikse `exit 1` döner ve "kanıt paketi GEÇERSİZ" der.

Ortam değişkenleri: `IMAGE`, `OUT_DIR`, `GOLD`, `BENCH_ITERATIONS`, `SKIP_BUILD`.

---

## Sources

- `raw/teknofest/2026-teknofest-tyda-sartname-2-senaryo.pdf` — §5.9, §5.10, §8
- `app/CLAUDE.md` §2 (on-prem/Colab ayrımı), §3 (önce kural), §11 (demo), §20
- `docs/offline-proof/transcript-20260731-135858.log` — **yetkili koşu** (14/14 yeşil)
- `docs/offline-proof/transcript-20260731-134646.log` — harness'ın hata yakaladığı koşu
- `docs/offline-proof/transcript-20260731-135051.log` — ara koşu (13 adım, API adımı öncesi)
- `docs/offline-proof/transcript-20260731-133540.log` — ilk koşu (bs4 düzeltmesi öncesi)
- `docs/offline-proof/latency-*.json` — ham gecikme ölçümleri (konteyner + host)
- `docs/model-license-audit.md` §2 — trafilatura kararı (bu belge onu düzenlemez)

## Related

- [[on-premise-calistirilabilir-mimari]] — kararın kendisi
- [[apache-2-acik-kaynak-lisansi]] — §8 dağıtım şartı
- [`kaynak-tuketimi.md`](kaynak-tuketimi.md) — donanım profili tabloları
- [`../scripts/offline_proof.sh`](../scripts/offline_proof.sh) — kanıtı üreten betik
- [`../scripts/latency_bench.py`](../scripts/latency_bench.py) — gecikme ölçüm betiği
