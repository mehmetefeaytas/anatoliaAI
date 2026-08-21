# Kaynak Tüketimi — Donanım Profilleri

**Durum:** dört profilden ikisi ölçüldü (A tam, B ikame modelle gerçek Ollama
çağrısıyla); GPU profilleri (C, D) bu makinede **ölçülemez** — sebep donanım
yokluğu, aşağıda §4/§5'te.
**Ölçüm tarihi:** 2026-07-31 (Profil A, izole Docker) + **2026-08-21** (Profil
B, API servisi RSS/gecikme — bu turun eklentisi, paylaşımlı geliştirme
makinesinde, `.venv/bin/python -m scripts.olc_kaynak` ile)
**Kaynak koşu:** [`offline-proof/transcript-20260731-135858.log`](offline-proof/transcript-20260731-135858.log)
(Profil A) — Profil B ve API servisi ölçümlerinin ham komut+çıktısı bu
belgenin ilgili bölümlerine **doğrudan gömülüdür** (ayrı transkript dosyası
yok; bu turun kapsamı yalnızca bu iki dosyayla sınırlıydı, bkz. görev notu).
**Ana belge:** [`OFFLINE-KANIT.md`](OFFLINE-KANIT.md)

---

## Neden bu belge var

On-prem uygulanabilirlik (rubrik %20) "çalışıyor mu" sorusundan ibaret değil;
**hangi donanımda, ne kadar kaynakla** sorusunun da cevaplanması gerekiyor. Bir
katılım bankasının BT birimi bu tabloya bakıp "bu bizim sunucumuzda döner mi"
diyebilmeli.

**Bu belgenin sözleşmesi:** ölçülmeyen hiçbir hücreye sayı yazılmaz.
`⏳ ölçülmedi` bir eksiklik itirafıdır, doldurulacak bir yer tutucu değildir.

---

## 1. Üç dağıtım profili

| Profil | LLM | Donanım | Durum |
|---|---|---|---|
| **A — CPU-only, LLM'siz** | yok (`NullLLMExtractor`) | herhangi bir x86_64/arm64, 2 çekirdek, 2 GB RAM | ✅ **ölçüldü** |
| **B — CPU/Metal + GGUF Q4** | Qwen2.5-7B-Instruct Q4_K_M + Qwen3.5-9B Q4_K_M (Ollama) | Apple Silicon, unified memory (bu makine) | ✅ **ölçüldü — ikame modellerle** (bkz. §3, not) |
| **C — Tüketici GPU** | Trendyol-LLM-8B-T1 AWQ (vLLM) | RTX 4090 / 24 GB VRAM | `⏳ ölçülmedi` |
| **D — Sunucu GPU** | Trendyol-LLM-8B-T1 AWQ (vLLM) | A100 / H100 | `⏳ ölçülmedi` |

> Görev tanımı üç profil istiyordu (CPU-only / tüketici GPU / sunucu GPU).
> Profil A ile B ayrıldı çünkü **ölçülebilirlikleri farklı**: A bu makinede
> gerçekten koştu, B ağırlık indirmeyi gerektirir ve koşmadı. İkisini tek satırda
> "CPU-only" diye birleştirmek, ölçülmemiş bir kolu ölçülmüş göstermek olurdu.

---

## 2. Profil A — CPU-only, LLM'siz (ÖLÇÜLDÜ)

Bu, **teslim edilen demo konfigürasyonudur** (CLAUDE.md §11: önceden
doldurulmuş DB, LLM kritik yolda değil). Aşağıdaki her satır
`docker run --network none` içinde gerçekten ölçüldü.

### 2.1 Ölçüm ortamı

| Kalem | Değer |
|---|---|
| Host | Apple MacBook Air, arm64, 10 çekirdek, 7,75 GiB konteyner belleği |
| Konteyner | `linux/arm64`, Python 3.11.15, Linux 6.12.76-linuxkit, glibc 2.41 |
| Ağ | **kapalı** (`--network none`) |
| LLM | kapalı (`LLM_BACKEND=""` → `NullLLMExtractor`) |

### 2.2 Bellek (RAM)

| Ölçüm | Değer | Nasıl ölçüldü |
|---|---|---|
| API sunucusu, boşta | **36,36 MiB** | `docker stats --no-stream` (adım 13) |
| API sunucusu, CPU (boşta) | %0,81 | aynı |
| Süreç sayısı | 2 PID | aynı |
| Çıkarım süreci tepe RSS (1696 belge) | **100,4 MB** | `resource.getrusage(RUSAGE_SELF).ru_maxrss` |

**RAM tavanı önerisi (profil A): 512 MB.** Ölçülen tepe 100,4 MB; 5× emniyet
payı bırakıldı. Bu, mütevazı bir sanal makinede rahatlıkla döner.

> Not: `ru_maxrss` birimi macOS'ta **bayt**, Linux'ta **kilobayt**. Ölçüm betiği
> bu farkı platforma göre ayırıyor (`scripts/latency_bench.py:_peak_rss_mb`);
> ayrılmasaydı tablo sessizce 1024× yanlış olurdu.

### 2.3 Disk

| Bileşen | Boyut | Nasıl ölçüldü |
|---|---|---|
| Teslim imajı (`anatolia-api`) | **101 218 586 bayt (≈96,5 MiB)** | `docker image inspect --format {{.Size}}` |
| ├─ taban `python:3.11-slim` | (imaja gömülü) | digest'e sabit |
| ├─ Python bağımlılıkları (22 paket) | ~15 MB | `pip list` (adım 10) |
| └─ `data/raw` korpusu | **205 MB kaynak → sıkıştırılmış katman** | `du -sh data/raw` |
| Derleme bağlamı (`.dockerignore` sonrası) | **215,71 MB** | `docker build` çıktısı `transferring context` |
| Derleme bağlamı (`.dockerignore` öncesi) | ~657 MB | `du -sh .` (`.venv` 193 MB + `web/` 250 MB dahil) |

`.dockerignore` eklenmeden önce her derleme 657 MB'lık bir bağlamı daemon'a
kopyalıyordu. Şimdi 215,71 MB; fark tamamen geliştirme artıklarından
(`.venv`, `web/node_modules`, `notebooks/`).

**Diskte olması gereken (profil A): ~1 GB** (imaj + Docker katman deposu payı).

### 2.4 Soğuk başlatma

| Ölçüm | Değer |
|---|---|
| API `/health` yanıt verene kadar (`--network none`) | **~1 s** |
| `build_demo_repo()` (demo DB kurulumu, kök korpus) | **5,7 ms** |
| Tam korpus alımı (1696 belge → DB, uçtan uca) | **4,83 s** |
| Test paketi (607 test) | 0,240 s |
| Değişmez denetimi (849 belge) | 15,46 s |

### 2.5 Verim (belge/dakika)

| Ölçüm | Değer |
|---|---|
| Uçtan uca alım (normalize → sınıflandır → uzlaştır → çelişki → DB) | **21 087 belge/dakika** |
| Kural katmanı tek başına (belge başına medyan 1,03 ms) | ~58 000 belge/dakika (teorik üst sınır) |

10 katılım bankasının tüm kampanya korpusu (1696 belge) **5 saniyenin altında**
işleniyor. Günlük tazeleme pratikte anlık.

### 2.6 Gecikme özeti

Tam tablo: [`OFFLINE-KANIT.md` §7](OFFLINE-KANIT.md#7-gecikme-latency--üç-yol-ayrı-ayrı)

| Yol | p50 | p95 | p99 |
|---|---|---|---|
| kural-only | 1,03 ms | 4,80 ms | 6,30 ms |
| hibrit boru hattı (LLM'siz) | 1,50 ms | 6,92 ms | 8,86 ms |
| chatbot | 12,48 ms | 325,02 ms | 351,36 ms |

### 2.7 API servisi tek başına — bekleyen süreç RSS + uç gecikmesi (2026-08-21)

Yukarıdaki §2.6 gecikmeleri `Chatbot.ask()` / `build_campaign()` **Python
fonksiyon çağrısı** olarak ölçülüyordu — FastAPI/uvicorn/HTTP/JSON katmanı
dahil değildi. Bu bölüm gerçek bir `uvicorn` sürecine gerçek HTTP isteği
atarak o farkı kapatıyor. `data/demo.db` **salt-okunur** kopyalandı (`cp`),
sunucu kopya üzerinde çalıştı; orijinal dosyaya hiç yazma açılmadı.

Komut (tekrarlanabilir; betik bu görevde eklendi: `scripts/olc_kaynak.py`):

```bash
cp data/demo.db /tmp/demo_ro.db          # salt-okunur kopya — orijinal dokunulmaz
.venv/bin/python -m scripts.olc_kaynak api \
  --db /tmp/demo_ro.db --port 8042 --n 25 --json /tmp/api_bench.json
```

Bellek `ps -o rss= -p <pid>` ile okunur — bu KB birimi macOS'ta da Linux'ta
da **kilobayt**tır (§2.2'deki `ru_maxrss` byte/kilobyte platform farkı burada
YOK, çünkü `ps` farklı bir arayüz).

| Ölçüm | Değer | Nasıl ölçüldü |
|---|---|---|
| DB (salt-okunur kopya) | 75 309 056 bayt (≈71,8 MiB) | `Path.stat().st_size` |
| RSS, boşta (health-check sonrası, istek atılmadan önce) | **21 568 KB (≈21,1 MiB)** | `ps -o rss=` |
| RSS, 50 istekten sonra (25× `/stats` + 25× `/chat`) | **73 952 KB (≈72,2 MiB)** | `ps -o rss=` |
| `/stats` gecikmesi (n=25, 1 ısınma turu hariç) | medyan **268,22 ms**, p95 **1 216,87 ms**, min 162,19 ms, max 2 778,88 ms | `time.perf_counter()` etrafında `urllib` isteği |
| `/chat` gecikmesi (n=25, soru: "kâr payı oranı nedir") | medyan **26,93 ms**, p95 **62,66 ms**, min 18,63 ms, max 363,52 ms | aynı |

**Dürüstlük notu:** bu ölçüm sırasında host'ta EŞ ZAMANLI olarak bu turun
Ollama ölçümü (§3, 9B model çağrısı) ve başka ajanların Docker/Colab
süreçleri çalışıyordu; `sysctl vm.swapusage` o aralıkta 16,8/18,4 GB swap
kullanımı gösteriyordu (bkz. §3 dürüstlük notu). `/stats`'ın p95'i (1,2 sn),
`banka_kapsami`/`alan_kapsami` gibi ağır agregasyon sorgularının bu yükle
çakıştığı turlardan şişmiş olabilir; medyan (268 ms) daha temsilcidir ama o
da izole bir sunucudan YAVAŞTIR. Tek kiracılı, boşta bir banka sunucusunda
her iki uç için de p95'in medyana yakınsaması beklenir; bunu doğrulamak
sessiz bir hostta yeniden ölçüm gerektirir (bu turda yapılamadı — makine
paylaşımlıydı).

**RAM tavanı önerisi (API servisi, LLM'siz, tek kullanıcı): 512 MB** — ölçülen
tepe 72,2 MiB'nin altı zaten §2.2'deki 512 MB öneriyle örtüşüyor; bu ölçüm
o öneriyi HTTP katmanı dahil olacak şekilde doğruluyor.

---

## 3. Profil B — CPU/Metal + Q4 GGUF (Ollama) — ✅ ölçüldü, ikame modelle

**Model ikamesi — neden ve ne anlama geldiği:** Görev tanımı Qwen3-4B GGUF
Q4 öngörüyordu; bu ağırlık hiç indirilmedi. Bu makinede kurulu olan
(`ollama list`) iki model **ile gerçek çağrı yapıldı**: `qwen2.5:7b-instruct`
ve `qwen3.5:9b-q4_K_M`. İkisi de aynı sınıf (7-9B, Q4 nicemleme) olduğu için
sayılar mertebe olarak temsilcidir, ama **Qwen3-4B'nin kendisi ölçülmedi** —
4B daha küçük olduğundan bu sayılardan DAHA HIZLI ve DAHA AZ bellek
kullanması beklenir; tersini iddia etmiyoruz.

### 3.1 Model dosyası — gerçek boyut + SHA-256 (Ollama içerik deposundan)

| Model | Dosya boyutu | SHA-256 (ağırlık katmanı) | Nicemleme |
|---|---|---|---|
| `qwen2.5:7b-instruct` | **4 683 087 332 bayt** (≈4,36 GiB / 4,68 GB) — ağırlık katmanı tek başına 4 683 073 952 bayt | `2bada8a7450677000f678be90653b85d364de7db25eb5ea54136ada5f3933730` | Q4_K_M |
| `qwen3.5:9b-q4_K_M` | **6 594 474 711 bayt** (≈6,14 GiB / 6,59 GB) — ağırlık katmanı tek başına 6 594 462 816 bayt | `dec52a44569a2a25341c4e4d3fee25846eed4f6f0b936278e3a3c900bb99d37c` | Q4_K_M |
| **İkisi birden** | **11 277 562 043 bayt (≈10,50 GiB)** | — | — |

Nasıl ölçüldü: `curl -s http://localhost:11434/api/tags` (toplam boyut) +
`~/.ollama/models/manifests/.../<tag>` manifest dosyası (katman SHA-256'ları,
`application/vnd.ollama.image.model` medya tipi — Ollama'nın içerik-adresli
deposunda dosya adı zaten kendi SHA-256'sıdır, ayrıca hesaplamaya gerek
kalmadı).

### 3.2 Soğuk/sıcak çağrı — gerçek ölçüm (2026-08-21)

Komut:

```bash
.venv/bin/python -m scripts.olc_kaynak ollama \
  --model qwen2.5:7b-instruct --json /tmp/ollama_qwen25.json
.venv/bin/python -m scripts.olc_kaynak ollama \
  --model qwen3.5:9b-q4_K_M --json /tmp/ollama_qwen35.json
```

(İstem her ikisinde de aynı: *"Katılım bankacılığında kâr payı oranı nedir?
Tek cümleyle özetle."* — `/api/generate`, `stream:false`.)

| Model | Çağrı | önceden yüklüydü mü | toplam süre | yükleme süresi | üretilen token | üretim süresi | token/sn (üretim) |
|---|---|---|---|---|---|---|---|
| qwen2.5:7b-instruct | soğuk | evet* | 40,16 s | 35,83 s | 20 | 1,90 s | ~10,5 |
| qwen2.5:7b-instruct | sıcak | evet | 74,21 s | 70,65 s | 31 | 2,94 s | ~10,5 |
| qwen2.5:7b-instruct | bağımsız prob (curl) | evet | 12,90 s | 11,87 s | 12 | 0,80 s | ~14,9 |
| qwen3.5:9b-q4_K_M | soğuk | **hayır (gerçek soğuk)** | 231,39 s | 33,02 s | 1923 | 197,78 s | ~9,7 |
| qwen3.5:9b-q4_K_M | sıcak | evet | 297,86 s | 46,81 s | 2553 | 250,66 s | ~10,2 |

\* `ollama ps` çağrı öncesi modeli "yüklü" gösteriyordu (60 dk `keep_alive`
ile), ama yine de tam yükleme süresi ölçüldü — bkz. dürüstlük notu.

**Dürüstlük notu — bu sayılar "modelin hızı" değil, "o an bu paylaşımlı
makinenin durumu"nu da ölçüyor:** `sysctl vm.swapusage` ölçüm penceresinde
sürekli **swap'ın %90'ından fazlasının dolu** olduğunu gösterdi (ör. 16,83 /
18,43 GB kullanılan, 1,60 GB boş; bir noktada 20,72 / 21,50 GB). Bu yüzden
`qwen2.5:7b-instruct` "sıcak" çağrısı (70,65 s yükleme) "soğuk"tan (35,83 s)
**daha yavaş** çıktı — normalde Ollama modeli bellekte tutar ve ikinci çağrı
yükleme içermemesi beklenir. Burada tersinin gözlenmesi, host'un işletim
sistemi seviyesinde model ağırlıklarını swap'a atıp geri getirdiğinin
kanıtıdır (bu makinede o anda başka ajanlar/Docker/Colab eş zamanlı
çalışıyordu). **Sonuç: `yükleme süresi` sütunu bu ortamda güvenilir bir
"soğuk başlatma" göstergesi değildir; tek kiracılı, yeterli boş RAM'i olan
bir banka sunucusunda çok daha düşük olması beklenir ama bu iddia
ÖLÇÜLMEDİ.** `token/sn (üretim)` sütunu göreli olarak daha güvenilirdir
(hesaplama zaten belleğe yüklenmiş ağırlık üzerinden yapılıyor) ve iki model
için de aynı mertebede (~10-15 tok/sn), Apple Silicon/Metal + bellek baskısı
altında.

`qwen3.5:9b` çağrısının 1923 token üretmesi de bir bulgu: istem "tek
cümleyle özetle" dedi ama model (muhakeme eğilimli bir sürüm olduğu için)
uzun bir yanıt üretti — `max_tokens`/`num_predict` sınırlanmadığı için. Bu,
modelin YAVAŞLIĞI değil, isteğin eksik kısıtlanmasıdır; üretimde bir banka
`num_predict` ile sınırlar.

### 3.3 Ölçülmeyenler (Profil B içinde)

| Kalem | Durum | Sebep |
|---|---|---|
| RAM/VRAM tavanı (bellek profili) | ⏳ ölçülmedi | `ollama ps` "SIZE" sütunu GPU+RAM toplamını gösteriyor (5,0-5,6 GB) ama bu host'un swap baskısı altındaki değeri; izole/temiz host ölçümü yapılmadı |
| Qwen3-4B GGUF Q4 (görevde istenen asıl model) | ⏳ ölçülmedi | indirilmedi; `ollama pull qwen3:4b-q4_K_M` ile ölçülebilir |
| Belge/dakika (Ollama arka ucuyla hibrit boru hattı) | ⏳ ölçülmedi | `LLM_BACKEND=ollama` ile `scripts/latency_bench.py --recursive` koşulmadı — bu turun kapsamı yalnızca `docs/kaynak-tuketimi.md` + `scripts/olc_kaynak.py` idi |
| Temiz (eş zamanlı yük olmayan) host'ta soğuk/sıcak farkı | ⏳ ölçülmedi | bu host paylaşımlıydı (§ dürüstlük notu); sessiz makinede yeniden ölçüm gerekir |
| Disk (Ollama Docker imajı) | **2 774,1 MB sıkıştırılmış** (registry manifest'inden, gerçekten sorgulandı) | — |

Belge/dakika + temiz-host ölçümü için:

```bash
docker compose --profile ollama up -d
docker exec -it <ollama> ollama pull qwen3:4b-q4_K_M
LLM_BACKEND=ollama OLLAMA_URL=http://localhost:11434 \
  python -m scripts.latency_bench --recursive
```

---

## 4. Profil C — Tüketici GPU (RTX 4090 sınıfı)

**`⏳ ölçülmedi — sebep: bu makinede GPU yok.`**

| Kalem | Durum |
|---|---|
| VRAM tavanı | ⏳ ölçülmedi |
| RAM tavanı | ⏳ ölçülmedi |
| Disk (vLLM imajı) | **10 349,3 MB sıkıştırılmış** (registry manifest'inden, gerçekten sorgulandı) |
| Disk (Trendyol-LLM-8B-T1 AWQ ağırlığı) | ⏳ ölçülmedi — indirilmedi |
| Soğuk başlatma (model yükleme) | ⏳ ölçülmedi |
| Hibrit gecikme p50/p95/p99 | ⏳ ölçülmedi |
| Token/saniye | ⏳ ölçülmedi |

---

## 5. Profil D — Sunucu GPU (A100 / H100)

**`⏳ ölçülmedi — sebep: donanım yok.`**

Tüm hücreler ⏳. Geliştirme/eğitim tarafı Colab Pro+ üzerinde yürüyor
(CLAUDE.md §2) ama **teslim edilen sistem Colab'a bağlı değil** ve bu profilin
ölçümü teslim iddiası için gerekli değil — yalnızca kapasite planlaması için
faydalı olurdu.

---

## 6. Offline paket toplam boyutu

İnternetsiz bir makineye taşınması gereken toplam veri. Bu, on-prem kurulumun
**gerçek maliyetidir** ve genelde küçümsenir.

| Bileşen | Sıkıştırılmış boyut | Kaynak |
|---|---|---|
| `anatolia-api` (teslim imajı) | ~96,5 MiB (yerel, sıkıştırılmamış 101 218 586 bayt) | ölçüldü |
| `pgvector/pgvector:pg16` | **154,1 MB** | registry manifest (16 katman) |
| `ollama/ollama` (profil B) | **2 774,1 MB** | registry manifest (4 katman) |
| `vllm/vllm-openai` (profil C/D) | **10 349,3 MB** | registry manifest (32 katman) |
| Model ağırlığı — `qwen2.5:7b-instruct` Q4_K_M (profil B, ikame) | **4 683 087 332 bayt (≈4,68 GB)** | `ollama` içerik deposu, gerçekten ölçüldü (§3.1) |
| Model ağırlığı — `qwen3.5:9b-q4_K_M` (profil B, ikame) | **6 594 474 711 bayt (≈6,59 GB)** | aynı |
| Model ağırlığı — Qwen3-4B GGUF Q4 (görevde istenen asıl model) | ⏳ ölçülmedi | indirilmedi |
| Model ağırlığı — Trendyol-LLM-8B-T1 AWQ (profil C/D) | ⏳ ölçülmedi | indirilmedi, GPU yok |
| **Minimum (profil A: api + postgres)** | **≈ 255 MB** | ölçülen değerlerin toplamı |
| **Profil B (api + postgres + ollama + 2 ikame model)** | **≈ 14,3 GB** | ölçülen değerlerin toplamı (255 MB + 2 774,1 MB + 11 277,6 MB ağırlık) |
| **Tam GPU yığını (api + postgres + vllm)** | **≈ 10,6 GB** + ağırlıklar | ölçülen değerlerin toplamı |

**Bulgu:** vLLM imajı tek başına 10,3 GB. Ağırlıklar (8B AWQ ≈ 5–6 GB)
eklendiğinde offline paket **16 GB'ı aşar**. Buna karşılık **profil A yalnızca
≈255 MB** ve tüm işlevselliği (çıkarım, karşılaştırma, chatbot, dashboard API)
LLM olmadan sunuyor. "Önce kural" mimarisinin (CLAUDE.md §3) on-prem
dağıtımdaki ikinci faydası budur: **paket boyutunda 40× fark**.

Sıkıştırılmış boyutlar şöyle ölçüldü:

```bash
docker buildx imagetools inspect --raw <imaj>@<arm64-manifest-digest> \
  | python3 -c "import json,sys; d=json.load(sys.stdin); \
      print(sum(l['size'] for l in d['layers']))"
```

---

## 7. Ölçülemeyenlerin özeti

| Kalem | Sebep |
|---|---|
| Tüm GPU profilleri (C, D) — VRAM, AWQ soğuk başlatma, vLLM hibrit gecikme | Bu makinede NVIDIA GPU yok; vLLM kurulu değil. Ölçmek için: `docker compose --profile vllm up -d` + `LLM_BACKEND=vllm VLLM_URL=http://localhost:8001 python -m scripts.latency_bench --recursive` (bir GPU makinesinde) |
| Qwen3-4B GGUF Q4 (görevde istenen asıl profil B modeli) | Hiç indirilmedi; ölçülen `qwen2.5:7b-instruct`/`qwen3.5:9b-q4_K_M` bu makinede zaten kuruluydu, İKAME olarak kullanıldı (§3) |
| Trendyol-LLM-8B-T1 AWQ ağırlığı — disk boyutu, SHA-256 | İndirilmedi (GPU/vLLM gerektirir) |
| Profil B'de temiz (eş zamanlı yük yok) host'ta soğuk/sıcak farkı | Bu host ölçüm sırasında paylaşımlıydı (swap %90+ dolu, başka ajanlar eş zamanlı Docker/Colab koşturuyordu) — §3.2 dürüstlük notu |
| `data/raw` korpusuyla (şimdi 2708 belge, 815 566 848 bayt) **tam kural-only yeniden alım** | Bu turda denendi, TAMAMLANMADI: `python -m scripts.build_demo_db` 300/2708 belgede `sqlite3.OperationalError: unable to open database file` ile durdu — host disk boşluğu o anda 3,4 GiB'a düşmüştü (başka ajanların eş zamanlı yazma yükü, kanıt: `df -h /` art arda 4,4→3,4→5,8 GiB salındı). §2'deki 4,83 s / 100,4 MB sayıları DAHA KÜÇÜK bir korpusla (1696 belge, izole Docker, `--network none`) ölçülmüştür ve hâlâ geçerlidir, ama BÜYÜMÜŞ (2708 belge) korpusla yeniden doğrulanmadı. |
| Token/saniye — Qwen3-4B / Trendyol-LLM-8B-T1 (asıl planlanan modeller) | Hiçbiri koşmadı; §3.2'deki tok/sn rakamları ikame modellere aittir |
| x86_64 (amd64) profili | Host arm64; digest'ler çoklu-mimari ama amd64 **doğrulanmadı** |
| Eşzamanlı kullanıcı yükü / dayanıklılık testi | Kapsam dışı; tek kullanıcı ölçümü yapıldı |
| Postgres kalıcı disk büyümesi | `docker compose` koşulmadı; demo `:memory:` SQLite kullanıyor |

---

## 8. Sonuç — bir banka bunu koşturmak için en az ne ister

**Kural-only asgari (profil A, tam ölçüldü):** 2 çekirdek, 512 MB RAM, ~1 GB
disk (imaj + katman deposu), ağ yok. Bu, çıkarım+karşılaştırma+chatbot+
dashboard API'sinin **tamamını** LLM olmadan sunar (§2.6: kural yolu p95
4,8 ms, chatbot yolu p95 325 ms) — teslim edilen demo konfigürasyonu budur
(CLAUDE.md §11). Yeni eklenen §2.7 ölçümü bunu HTTP katmanı dahil doğruladı:
gerçek `uvicorn` süreci 25 istekten sonra 72,2 MiB RSS'e çıktı, 512 MB
tavanının çok altında.

**LLM'li önerilen (profil B, ikame modelle ölçüldü):** yukarıdaki asgariye
ek olarak **+11,3 GB disk** (iki test modeli — banka gerçek dağıtımda TEK
model seçer, yani pratikte +4,7 ila +6,6 GB) ve **yeterli boş RAM/unified
memory** — bu ölçümde host'un swap'ı %90+ doluyken model her çağrıda yeniden
sayfalandı (§3.2), bu da bankanın sunucusunda **model boyutunun 1,5-2 katı
boş bellek** bırakılmasını (7B Q4 için ~7-8 GB, 9B Q4 için ~10 GB) pratik bir
alt sınır olarak işaret ediyor — bu ölçülmüş bir tavan değil, bu turda
gözlenen swap-thrashing'den çıkarılan bir çıkarımdır ve temiz bir hostta
doğrulanmalıdır. GPU (profil C/D) bu makinede test edilemedi; vLLM+AWQ imajı
tek başına 10,3 GB olduğundan (§6) GPU'lu dağıtımın disk maliyeti kural-only
asgarinin **~40 katı**dır — bu fark GPU olmadan da (registry manifest'inden)
gerçekten ölçülmüştür.

**Pratik tavsiye:** kural-only profil (A) varsayılan/asgari dağıtım olarak
sunulmalı; LLM'li profil (B) yalnızca kuralların kaçırdığı örtük ifadeler
için isteğe bağlı bir ek katman olarak konumlanmalı (CLAUDE.md §3 zaten bu
mimariyi seçmiş) — bu ölçüm o kararı, HTTP-servis düzeyinde gerçek sayılarla
bir kez daha doğruluyor.

---

## Sources

- `docs/offline-proof/transcript-20260731-135858.log` — Profil A ölçümlerinin ham kaynağı
- `docs/offline-proof/latency-20260731-135858.json` — gecikme + RSS + verim, ham JSON
- `scripts/olc_kaynak.py` — bu turda eklenen ölçüm betiği; §2.7 ve §3'teki tüm
  sayıların ÜRETİLDİĞİ komutlar buradadır (çıktıları bu belgeye doğrudan gömülü,
  ayrı transkript dosyası oluşturulmadı — görev kapsamı bu iki dosyayla sınırlıydı)
- `ollama list` / `curl http://localhost:11434/api/tags` / `~/.ollama/models/manifests/...` — §3.1 model boyutu ve SHA-256 kaynağı
- `sysctl vm.swapusage`, `ps -o rss=` — §2.7/§3.2 host durumu ve süreç belleği kaynağı
- `app/CLAUDE.md` §2 (Colab/on-prem ayrımı), §3 (önce kural), §11 (demo stratejisi)
- `raw/teknofest/2026-teknofest-tyda-sartname-2-senaryo.pdf` — §5.9

## Related

- [`OFFLINE-KANIT.md`](OFFLINE-KANIT.md) — ana kanıt belgesi
- [`../scripts/latency_bench.py`](../scripts/latency_bench.py) — gecikme/kaynak ölçüm betiği (Profil A)
- [`../scripts/olc_kaynak.py`](../scripts/olc_kaynak.py) — API servisi + Ollama + disk ölçüm betiği (bu tur)
- [`../scripts/offline_proof.sh`](../scripts/offline_proof.sh) — kanıt koşusu
- [[on-premise-calistirilabilir-mimari]]
