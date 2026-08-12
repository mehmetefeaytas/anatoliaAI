---
title: "Offline / On-Prem Kanıt Paketi — `--network none` altında 14/14 adım"
tags: [source, on-premise, offline, ag-izolasyonu, docker, olcum, gecikme, lisans]
source: "raw/docs/OFFLINE-KANIT.md (→ app/docs/OFFLINE-KANIT.md)"
date: 2026-07-31
status: stable
---

# Offline / On-Prem Kanıt Paketi

Koşu tarihi **2026-07-31T10:58:58Z (UTC)**; belgeye 2026-08-08'de bir
**tazelik uyarısı** ve BERTurk ağırlık bütünlüğü bölümü eklendi
(commit `e801642`). Bu sayfa 31 Temmuz koşumunu ve 8 Ağustos güncellemesini
birlikte kaydeder.

## goal

Şartname §5.9'un ([[2026-06-16-teknofest-tyda-sartname-2-senaryo]]) *"dış
servise bağımlı olmadan yerel (on-premise) çalışma"* şartını **iddia değil
ölçüm** düzeyine taşımak. Rubrikte **On-Prem Uygulanabilirlik %20**
([[on-premise-uygulanabilirlik]]).

Belgenin yazılma sebebi açık bir boşluk: bu başlıkta **tek bir ölçüm yoktu**.
`docker-compose.yml` "offline ayağa kalkar" diyordu, `Dockerfile.api` yorumu ise
**var olmayan** bir `docs/OFFLINE-KANIT.md` dosyasına atıf yapıyordu.

**Belgenin sözleşmesi:** yazan her sayı koşturulmuş bir komuttan gelir;
koşturulmayan her kalem `⏳ ölçülmedi — sebep: …` ile işaretlidir. Ara değer,
tahmin, "olması beklenen" sayı yoktur.

## what-was-done

**1. Ölçüm ortamı künyelendi.**

| Kalem | Değer |
|---|---|
| Host | Darwin 25.5.0, arm64 (Apple Silicon, MacBook Air), 10 çekirdek |
| Docker | CLI 29.5.3 · daemon 29.6.1 (linux/aarch64) |
| Konteyner | `linux/arm64`, Python 3.11.15, Linux 6.12.76-linuxkit, glibc 2.41 |
| Taban imaj | `python:3.11-slim@sha256:db3ff2e1…53a93` (digest'e sabit) |
| Teslim imajı | `anatolia-api:offline-proof` · ID `sha256:f234fe8d7733…` · **101 218 586 bayt (≈96,5 MiB)** |
| Git commit | `025c1e5` |
| LLM arka ucu | **kapalı** (`LLM_BACKEND=""` → `NullLLMExtractor`) |

Makinede **GPU yok**; vLLM / Trendyol-LLM-8B-T1 kolu **hiç koşturulmadı**
(→ [[vllm]]). Tüm gecikme sayıları CPU + LLM'siz yoldan gelir.

**2. Kanıtın omurgası: negatif kontrol + onun pozitif kontrolü**
(→ [[negatif-kontrolun-pozitif-kontrolu]]).

Aynı dört prob iki kez koşturuldu:

| Adım | Ortam | Beklenti | Gerçekleşen | Çıkış | Süre |
|---|---|---|---|---|---|
| 2 | ağ **AÇIK** (`docker run`) | proba **ULAŞMALI** | 4/4 ulaştı | 0 | 723 ms |
| 3 | ağ **KAPALI** (`--network none`) | proba **ULAŞAMAMALI** | 4/4 engellendi | 3 | 228 ms |

Adım 3'ün ham hata mesajları işletim sistemi düzeyinde: DNS `huggingface.co` →
`gaierror: [Errno -3] Temporary failure in name resolution`; TCP `1.1.1.1:443` →
`OSError: [Errno 101] Network is unreachable`; iki HTTPS hedefi (`huggingface.co`,
`pypi.org`) → `URLError`. Yani çekirdek seviyesinde ağ yok, uygulama katmanında
zaman aşımı taklidi değil (→ [[ag-izolasyonu-network-none]]).

**3. `--network none` içinde koşan gerçek iş — 14 adım.**

| # | Adım | Çıkış | Süre |
|---|---|---|---|
| 1 | `docker build -f Dockerfile.api` | 0 | 3 471 ms (önbellekli) |
| 2 | Prob doğrulama (ağ açık) | 0 | 723 ms |
| 3 | **NEGATİF KONTROL** (ağ kapalı) | 3 | 228 ms |
| 4 | Test paketi (`unittest discover`) | 0 | 509 ms |
| 5 | `eval.properties --raw-dir data/raw` | 0 | 15 460 ms |
| 6 | `eval.run_eval --gold …` | 0 | 242 ms |
| 7 | `eval.ablation --gold …` | 0 | 198 ms |
| 8 | `scripts.latency_bench --recursive` | 0 | 118 861 ms |
| 9 | Offline ortam değişkenleri | 0 | 201 ms |
| 10 | `pip list` dökümü | 0 | 330 ms |
| 11 | `trafilatura` yok (negatif kontrol) | 1 | 297 ms |
| 12 | `trafilatura` import edilemez | 0 | 168 ms |
| 13 | **API sunucusu ağsız ayağa kalkıyor** | 0 | 2 806 ms |
| 14 | İmaj künyesi | 0 | 51 ms |

**beklenmedik sonuç: 0 / 14.** İlk (soğuk, taban imaj çekilerek) derleme
**192 641 ms** sürdü; tablodaki 3 471 ms önbellekli koşudur.

Ara çıktılar: `Ran 607 tests in 0.240s — OK`; değişmez denetimi
**849 belge** (732'sinde en az bir alan çıktı, 117 boş belge, kapsam **%86,2**),
**0 ihlal**. Offline ortam değişkenleri gerçekten set: `ANATOLIA_OFFLINE=1`,
`HF_HUB_OFFLINE=1`, `HF_HUB_DISABLE_TELEMETRY=1`, `HF_HUB_DISABLE_UPDATE_CHECK=1`,
`TRANSFORMERS_OFFLINE=1`.

Betik test sayısını **sabit yazmaz**; "345 test" gibi sabit bir ifade paket
büyüdükçe sessizce yalan olurdu, gerçek sayı transkriptteki `Ran N tests`
satırındadır.

**4. Adım 13 — servis iddiası ayrı ölçüldü.** *"Testler ağsız geçti"* ile
*"sunucu ağsız ayağa kalktı"* farklı iddialardır; §5.9 çalışan bir **servis**
ister. Konteyner (`6a5b7c26ff37…`) başlatıldı, HTTP istekleri **konteynerin
içinden** `127.0.0.1`'e atıldı:

- hazır olma süresi **~1 sn**
- `/health` → `{"status":"ok","llm":false}` — LLM'in kapalı olduğu dürüstçe
  raporlanıyor, sahte "hazır" yok
- `/banks` → gerçek veri (çıktı transkriptte 300 karakterde kesildi; ilk üç banka
  Kuveyt Türk, Albaraka Türk… görünüyor; `config/banks.yaml` **10 banka**
  tanımlıyor) → [[katilim-bankalari]]
- kaynak kullanımı: **BELLEK 36,36 MiB / 7,75 GiB · CPU %0,81 · PID=2**

**5. Harness'ın lastik damga olmadığı gösterildi.** Ara koşulardan biri
(`transcript-20260731-134646.log`) gerçek bir kırılmayı yakaladı: 13 adımdan 1'i
BEKLENMEDİK, betik *"SONUÇ: 1 ADIM BEKLENMEDİK. Kanıt paketi GEÇERSİZ"* dedi.
Kök neden `tests/test_run_eval.py` içinde eksik `import contextlib`
(`NameError: name 'contextlib' is not defined`); bizim dosyalarımızda değildi ve
sonraki koşudan önce düzeltildi (→ [[offline-kanit-betigi]]).

**6. Digest pin tablosu** (2026-07-31'de `docker buildx imagetools inspect` ile
gerçekten çözüldü) → [[imaj-digest-sabitleme]]:

| Bileşen | Etiket | Digest | Sıkıştırılmış boyut (linux/arm64) |
|---|---|---|---|
| PostgreSQL + pgvector | `pgvector/pgvector:pg16` | `sha256:a36250871de0…` | 154,1 MB (16 katman) |
| vLLM sunucusu | `vllm/vllm-openai:latest` | `sha256:ffb2d59b1c05…` | **10 349,3 MB** (32 katman) |
| Ollama (yedek) | `ollama/ollama:latest` | `sha256:4dea9fb51194…` | 2 774,1 MB (4 katman) |
| API taban imajı | `python:3.11-slim` | `sha256:db3ff2e1800a…` | — (teslim imajına gömülü) |

**7. Lisans kalemleri ölçüldü.** `trafilatura` (GPLv3+, §8 dağıtım şartıyla
uyumsuz) teslim imajında **yok**: adım 10 tam paket dökümünü basıyor (**22 paket**,
tamamı MIT / BSD / Apache-2.0 / PostgreSQL / LGPL(dinamik)), adım 11 `grep` boş
dönüyor (çıkış 1), adım 12 `importlib` ile `find_spec: None` veriyor — üç bağımsız
kanıt. Ayrıca `Trendyol/Trendyol-LLM-8B-T1` kolu **çıkarılmadı**: lisans zinciri
`Qwen3-8B-Base → Qwen3-8B → Trendyol-LLM-8B-T1`, `license: Apache-2.0`, zincirde
Llama/Gemma ve ticari-olmayan kısıt yok → §5.10 uyumlu
([[apache-2-acik-kaynak-lisansi]]).

**8. Gecikme, üç yol ayrı ayrı** (`--network none` konteyneri içinde,
`latency_bench --recursive --iterations 3`, 1696 gerçek banka belgesi, ortalama
4 320 karakter, toplam 7 327 700 karakter):

| Yol | n | p50 | p95 | p99 | max | ortalama |
|---|---|---|---|---|---|---|
| (a) kural-only `extract_all()` | 5 088 | **1,03 ms** | 4,80 ms | 6,30 ms | 37,63 ms | 1,79 ms |
| (b) hibrit boru hattı `build_campaign()` | 5 088 | **1,50 ms** | 6,92 ms | 8,86 ms | 75,32 ms | 2,59 ms |
| (c) chatbot `Chatbot.ask()` | 504 | **12,48 ms** | 325,02 ms | 351,36 ms | 368,53 ms | 155,11 ms |

Host'ta (macOS arm64, Python 3.14.6, konteynersiz) aynı ölçüm: kural p50 1,05 ms ·
hibrit p50 1,67 ms · chatbot p50 6,47 ms → **konteyner cezası kural ve hibrit
yollarında pratikte yok**; on-prem konteynerleştirme çıkarım hızını düşürmüyor.

Bu, "önce kural, sonra LLM" mimarisini ([[ner-fine-tune-yerine-kural-few-shot]])
**ilk kez sayıyla** gerekçelendiriyor: kural yolu belge başına medyan 1,03 ms,
p99 6,30 ms; yerel 8B bir LLM'in tek çağrısı tipik olarak saniyeler
mertebesindedir → **üç mertebe** fark. Chatbot'un p95/p99 yayılımı ayrı bir kalem
olarak kaydedildi (→ [[chatbot-rag-gecikme-yayilimi]]).

**9. Kaynak tüketimi** (hepsi `--network none` koşusundan): teslim imajı
101 218 586 bayt (≈96,5 MiB) · API boşta bellek **36,36 MiB** · hazır olma **~1 s** ·
tepe RSS (1696 belge çıkarımı) **100,4 MB** · demo soğuk başlatma
(`build_demo_repo`) **5,7 ms** · tam korpus alımı **4,83 s** · verim
**21 087 belge/dakika** ([[anatolia-api-teslim-imaji]]).

**10. Ağırlık bütünlüğü (2026-08-08 güncellemesi, `◐ KISMEN KOŞTURULDU`).**
31 Temmuz'da `app/models/` yoktu; 8 Ağustos'ta BERTurk yerelde (Apple Silicon /
MPS) ince ayarlandı. `models/berturk-kampanya-8sinif/model.safetensors`,
**442,5 MB**, SHA-256 `2c9e3af2410d835a479c7e33b033c01535247bef63ad49f1c436548985eb1a5d`
— `KUNYE.json` kaydıyla **eşleşiyor** (2026-08-08'de yeniden hesaplandı). Ağırlık
git'e girmiyor; tekrar üretimi `scripts/train_berturk.py` (tohum 42, katmanlı
%70/%15/%15 bölme). Model **teslim sisteminde kullanılmıyor** (kabul kapısı
"KALDI": gold makro-F1 0,565 vs kural temel çizgisi 0,762); `BERTURK_MODEL_DIR`
bilinçli set edilmiyor, `Dockerfile.api` `models/` dizinini kopyalamıyor. Diğer
ağırlıklar (Trendyol-LLM-8B-T1, `dbmdz/bert-base-turkish-cased`, `BAAI/bge-m3`)
indirilmedi; satırlar boş bırakıldı — **uydurma SHA-256 yazılmadı**.

Ağırlıkları indirmeden doğrulanabilen şey doğrulandı: **konteyner ağırlıkları
indirmeye çalışmıyor.** `HF_HUB_OFFLINE=1` + `TRANSFORMERS_OFFLINE=1` imajda set
ve `--network none` altında boru hattı ağ çağrısı yapmadan tamamlanıyor.

## files-changed / touched

Bu ingest'in kaynağı olan belge ve ürettiği/atıf yaptığı artefaktlar:

- `app/docs/OFFLINE-KANIT.md` — bu kaynağın kendisi
- `app/scripts/offline_proof.sh` — kanıtı üreten harness (→ [[offline-kanit-betigi]])
- `app/docs/offline-proof/transcript-20260731-135858.log` — **yetkili koşu**
  (14/14 yeşil, 1254 satır, kesilmemiş)
- `app/docs/offline-proof/transcript-20260731-134646.log` — harness'ın hata
  yakaladığı koşu (13 adım, 1 beklenmedik)
- `app/docs/offline-proof/transcript-20260731-135051.log` — ara koşu (13 adım)
- `app/docs/offline-proof/transcript-20260731-133540.log` — ilk koşu (bs4 öncesi)
- `app/docs/offline-proof/latency-20260731-135858.json` — yetkili gecikme ölçümü
- `app/docs/offline-proof/latency-20260731-133540.json` (`avg_chars: 6232`) ve
  `latency-20260731-135051.json` (`avg_chars: 4320`) — bs4 sapmasının ham verisi
- `app/docs/offline-proof/latency-host-20260731.json` — konteynersiz karşılaştırma
- `app/scripts/latency_bench.py` — gecikme ölçüm betiği
- `app/docs/kaynak-tuketimi.md` — donanım profili tabloları

Bahsi geçen ama bu belgenin **düzenlemediği** dosyalar:

- `app/docker-compose.yml` — digest pin tablosuyla birlikte güncellenmesi gereken dosya
- `app/Dockerfile.api`, `app/requirements-api.txt` — teslim imajının tanımı
- `app/docs/model-license-audit.md` §2 — `trafilatura` kararının sahibi
- `app/models/berturk-kampanya-8sinif/KUNYE.json`, `app/scripts/train_berturk.py`
- `app/src/scraping/collector.py` — `_extract_main_text` sapması
  (→ [[bs4-eksikligi-teslim-imaji-sapmasi]])

## decisions

- **Ağ izolasyonu negatif kontrolle kanıtlanır, testlerin ağsız geçmesiyle
  değil** → [[negatif-kontrolun-pozitif-kontrolu]],
  [[ag-izolasyonu-network-none]].
- **`curl` yerine bağımlılıksız stdlib probu kullanılır** →
  [[curl-yerine-stdlib-ag-probu]].
- **İmajlar hareketli etiketle değil digest ile sabitlenir** →
  [[imaj-digest-sabitleme]].
- **`trafilatura` (GPLv3+) teslim imajına alınmaz** — kararın sahibi
  `docs/model-license-audit.md` §2; bu belge yalnız ölçülmüş kanıtını sağlar
  ([[apache-2-acik-kaynak-lisansi]]).
- **vLLM / Trendyol-LLM-8B-T1 kolu korunur** (lisans zinciri Apache-2.0 doğrulandı)
  → [[vllm]]; CPU yedeği [[ollama]].
- **Sabit test sayısı belgeye yazılmaz**; sayı her koşuda transkriptten okunur
  → [[offline-kanit-betigi]].

## issues

- **bs4 sessiz sapması** — teslim imajı geliştirme ortamından farklı metin
  üretiyordu (4 317 → 6 232 karakter, +%44 gürültü); düzeltildi (4 320), imaj
  +406 KB (%0,4) büyüdü → [[bs4-eksikligi-teslim-imaji-sapmasi]].
- **Kanıtın kapsam sınırı** — yalnız API konteyneri kanıtlandı; `docker compose
  up` tam yığın (Postgres, web, vLLM, Ollama) ağsız denenmedi ve **imaj derlemesi
  internet gerektiriyor** → [[offline-kanit-kapsam-siniri]].
- **Chatbot p95/p99 yayılımı** — p50 12,48 ms'e karşı p95 325,02 ms (~26×)
  → [[chatbot-rag-gecikme-yayilimi]].
- **Doğruluk sayısı anlamsız** — `gold.sample.json` 3 kayıt, F1 1,000 ve GA
  `[1,000–1,000]` dejenere; buradaki kanıt doğruluk değil **ağsız koşabilirliktir**.
- **Tazelik (2026-08-08)** — koşumdan bu yana depo 136 commit ilerledi:
  607 → **1.610 test**, 849 → **1.774 belge**, gold 3 kayıt → **66 tekil belge**
  (v1 n=20 + v2 n=48, 2 örtüşme), `app/models/` artık **var**. Kanıtın kendisi
  (14/14, `--network none`) geçerli; **sayılar güncellenmeden jüriye sunulmamalı**.
- **Kapanmış çelişki (kayıt için).** Belge yazılırken `docs/model-license-audit.md`
  hâlâ 2026-07-27 sürümündeydi ve Trendyol-LLM-8B-T1'i `⛔ BLOKE` listeliyordu;
  çelişki **aynı gün kapatıldı** (commit `009c89e`) — denetim belgesi güncellendi,
  model `✅` oldu. Bugün açık bir çelişki **yok**.

## open-threads

- `scripts/offline_proof.sh` teslimden önce **temiz ağaçta** yeniden koşturulmalı;
  31 Temmuz koşumunda çalışma ağacı kirliydi (transkript bunu kaydediyor).
- `docker compose up` tam yığının (postgres + api + web) ağsız ayağa kalkması
  `⏳ koşturulmadı`; pgvector/Postgres ağsız başlatma ölçülmedi.
- vLLM + Trendyol-LLM-8B-T1 uçtan uca, gerçek hibrit gecikmesi (LLM dahil),
  Ollama CPU yedeği (Qwen3-4B GGUF Q4), tüketici GPU ve sunucu GPU (A100/H100)
  profilleri: hepsi `⏳ ölçülmedi` — **bu makinede GPU yok**.
- Model ağırlıkları için SHA-256 künye prosedürü **yazıldı ama koşturulmadı**
  (§9.1: `huggingface-cli download --revision <commit-sha>` → `shasum -a 256` →
  `shasum -a 256 -c weights.sha256`).
- **x86_64 (amd64)** mimarisi doğrulanmadı; digest'ler çoklu-mimari indeks olduğu
  için çalışması beklenir ama ölçülmedi.
- Digest tablosu yenilenirse `docker-compose.yml` **birlikte** güncellenmeli;
  aksi halde belge ile dosya çelişir.

## Sources

- `raw/docs/OFFLINE-KANIT.md` → `app/docs/OFFLINE-KANIT.md` (koşu
  2026-07-31T10:58:58Z; tazelik ve §9 güncellemesi 2026-08-08, commit `e801642`)
- `app/docs/offline-proof/transcript-20260731-135858.log` — yetkili koşu, 14/14,
  1254 satır
- `app/docs/offline-proof/transcript-20260731-134646.log` — 1 beklenmedik adım
- `app/docs/offline-proof/latency-*.json` — ham gecikme ölçümleri (konteyner + host)
- [[2026-06-16-teknofest-tyda-sartname-2-senaryo]] — §5.9, §5.10, §8, rubrik s.15
- `app/docs/model-license-audit.md` §2 — `trafilatura` kararı (bu belge onu düzenlemez)

## Related

- [[on-premise-calistirilabilir-mimari]] — bu kanıtın doğruladığı karar
- [[on-premise-uygulanabilirlik]] — %20'lik rubrik kalemi
- [[ag-izolasyonu-network-none]] — ölçüm yöntemi
- [[negatif-kontrolun-pozitif-kontrolu]] — kanıtın omurgası
- [[offline-kanit-betigi]] — kanıtı üreten harness
- [[anatolia-api-teslim-imaji]] — ölçülen konteyner
- [[vllm]], [[ollama]] — yerel model servisi kolları (ikisi de koşturulmadı)
- [[apache-2-acik-kaynak-lisansi]] — §8 dağıtım şartı
- [[2026-08-08-guvenlik-llm-modu]] — aynı chatbot'un güvenlik tarafı; oradaki
  sentez modu bu belgede kapalı olan LLM kolunu açıyor
