# Kaynak Tüketimi — Donanım Profilleri

**Durum:** kısmen ölçüldü — CPU-only profili **gerçekten ölçüldü**, GPU profilleri `⏳ ölçülmedi`
**Ölçüm tarihi:** 2026-07-31
**Kaynak koşu:** [`offline-proof/transcript-20260731-135858.log`](offline-proof/transcript-20260731-135858.log)
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
| **B — CPU-only + GGUF Q4** | Qwen3-4B GGUF Q4 (Ollama) | 8 çekirdek, 16 GB RAM | `⏳ ölçülmedi` |
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

---

## 3. Profil B — CPU-only + Qwen3-4B GGUF Q4

**`⏳ ölçülmedi — sebep: model ağırlıkları bu ortamda indirilmedi.`**

| Kalem | Durum |
|---|---|
| RAM tavanı | ⏳ ölçülmedi |
| Disk (Ollama imajı) | **2 774,1 MB sıkıştırılmış** (registry manifest'inden, gerçekten sorgulandı) |
| Disk (Qwen3-4B Q4 ağırlığı) | ⏳ ölçülmedi — indirilmedi |
| Soğuk başlatma | ⏳ ölçülmedi |
| Belge/dakika | ⏳ ölçülmedi |
| Token/saniye | ⏳ ölçülmedi |

Ölçmek için:

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
| Model ağırlıkları | ⏳ ölçülmedi | indirilmedi |
| **Minimum (profil A: api + postgres)** | **≈ 255 MB** | ölçülen değerlerin toplamı |
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
| Tüm GPU profilleri (C, D) | Bu makinede GPU yok |
| Profil B (Ollama + GGUF) | Ağırlıklar indirilmedi |
| Model ağırlığı disk boyutu ve SHA-256 | Ağırlıklar indirilmedi (bkz. `OFFLINE-KANIT.md` §9) |
| Token/saniye (her profil) | LLM hiç koşmadı |
| x86_64 (amd64) profili | Host arm64; digest'ler çoklu-mimari ama amd64 **doğrulanmadı** |
| Eşzamanlı kullanıcı yükü / dayanıklılık testi | Kapsam dışı; tek kullanıcı ölçümü yapıldı |
| Postgres kalıcı disk büyümesi | `docker compose` koşulmadı; demo `:memory:` SQLite kullanıyor |

---

## Sources

- `docs/offline-proof/transcript-20260731-135858.log` — tüm ölçümlerin ham kaynağı
- `docs/offline-proof/latency-20260731-135858.json` — gecikme + RSS + verim, ham JSON
- `app/CLAUDE.md` §2 (Colab/on-prem ayrımı), §3 (önce kural), §11 (demo stratejisi)
- `raw/teknofest/2026-teknofest-tyda-sartname-2-senaryo.pdf` — §5.9

## Related

- [`OFFLINE-KANIT.md`](OFFLINE-KANIT.md) — ana kanıt belgesi
- [`../scripts/latency_bench.py`](../scripts/latency_bench.py) — gecikme/kaynak ölçüm betiği
- [`../scripts/offline_proof.sh`](../scripts/offline_proof.sh) — kanıt koşusu
- [[on-premise-calistirilabilir-mimari]]
