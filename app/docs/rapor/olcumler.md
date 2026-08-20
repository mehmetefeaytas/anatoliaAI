# Anatolia AI — Tüm Ölçümler (konsolide tablo)

Bu dosya projedeki **her ölçülmüş sayıyı** tek yerde toplar. Amacı iki tanedir:

1. **NotebookLM ve benzeri araçlar için:** grafiklerin taşıdığı sayılar burada metin olarak da
   bulunur, böylece görsel okunamadığında bilgi kaybolmaz.
2. **Tutarlılık denetimi için:** aynı sayının farklı dokümanlarda farklı yazılması bu tablodan
   yakalanabilir.

**Kural:** her satır bir kaynağa referans verir. Ölçülmemiş değerler ⏳ ile işaretlenir ve
tahmin yazılmaz.

Son güncelleme: **3 Ağustos 2026** · commit `03835ce`

> ## ⚠️ BU BELGE 3 AĞUSTOS KESİTİDİR — manşet sayılar için buraya BAKMAYIN
>
> Aşağıdaki gövde o günün ağacına çapalıdır ve **silinmiyor** (belgenin kendi
> künye kuralı). Ama o günden bugüne aşağıdaki listenin büyük kısmı **ölçüldü**,
> yani belgenin ikinci amacı — tutarsızlık yakalamak — bugün tersine işliyor:
> bu dosyayı kaynak sanan biri bayat sayı okur.
>
> **Güncel tek doğruluk kaynağı (2026-08-20):**
>
> | ne | değer | nerede |
> |---|---|---|
> | 12-alan mikro-F1 (ikili) | **0,5702** | [`app/README.md`](../../README.md) · `eval/reports/20260820-130322/` |
> | kalem mikro-F1 | **0,6291** | aynı |
> | yapısal mikro-F1 (11 alan) | **0,8228** | aynı |
> | makro-F1 | **0,7646** | aynı |
> | halüsinasyon | **0,0336** | aynı |
> | κ (ikinci etiketleyici turu) | **0,714** | [`_kappa-ikinci-tur.md`](../../data/gold/review/_kappa-ikinci-tur.md) |
> | Ablasyon (4 kol) + McNemar | **KOŞULDU** — kural her kolda önde | [`ablasyon.md`](ablasyon.md) |
> | Korpus | **1.782 belge · 4.704 alan** | `data/demo.db` |
>
> Aşağıda "⏳ ölçülmedi/koşulmadı" yazan kalemlerden bugün **ölçülmüş olanlar**:
> mikro/makro F1, halüsinasyon oranı, κ, 4 kollu ablasyon, zor-vaka alt kümesi
> metriği. **Hâlâ ölçülmemiş olanlar:** gerçek hibrit gecikmesi (LLM açıkken),
> vLLM + Trendyol uçtan uca koşu, GPU profilleri.

---

## 1. Korpus ve veri

| Metrik | Değer | Kaynak |
|---|---|---|
| Kampanya (belge) sayısı | **849** | `data/demo.db` · `SELECT COUNT(*) FROM campaigns` |
| Çıkarılmış alan sayısı | **2.204** | `SELECT COUNT(*) FROM extracted_fields` |
| Banka sayısı | **10** | `SELECT COUNT(*) FROM banks` |
| Offset taşıyan alan | **2.204 / 2.204 (%100)** | `WHERE span_start IS NOT NULL` |
| Ham önbellek belge sayısı (gecikme ölçümü) | **1.696** | `latency-20260731-135858.json` |
| Ortalama belge uzunluğu | **4.320 karakter** | aynı |
| Toplam karakter | **7.327.700** | aynı |
| `data/raw` boyutu | **205 MB** | `docs/kaynak-tuketimi.md` |
| `data/demo.db` boyutu | **9,5 MB** | `ls -la data/demo.db` |
| İkili çöp belge (352 NUL baytı, 0 alan) | **1 / 849** | `docs/veri-katmani.md` |

### Banka başına belge

| Banka | Belge |
|---|---|
| Kuveyt Türk | 130 |
| Türkiye Emlak Katılım | 129 |
| Albaraka Türk | 127 |
| Vakıf Katılım | 126 |
| Dünya Katılım | 101 |
| Ziraat Katılım | 87 |
| Türkiye Finans | 80 |
| Hayat Finans | 48 |
| T.O.M. Katılım | 15 |
| Adil Katılım | 6 |

### Kampanya türü dağılımı (§5.4 — 8 tür)

| Tür | Belge | Oran |
|---|---|---|
| Yatırım Ürünü | 186 | %21,9 |
| İhtiyaç Finansmanı | 146 | %17,2 |
| Kart | 145 | %17,1 |
| Finansman | 135 | %15,9 |
| Konut Finansmanı | 106 | %12,5 |
| **(sınıflanamayan)** | **60** | **%7,1** |
| Taşıt Finansmanı | 49 | %5,8 |
| Alışveriş Puanı | 13 | %1,5 |
| Yeni Müşteri | 9 | %1,1 |

### Alan kapsamı — kaç belgede var?

| Alan | Belge | Oran |
|---|---|---|
| Kampanya Koşulları | 550 | %64,8 |
| Vade (ay) | 337 | %39,7 |
| Kampanya Süresi | 252 | %29,7 |
| Masraf Durumu | 248 | %29,2 |
| Hedef Kitle | 227 | %26,7 |
| Finansman Tutarı | 132 | %15,5 |
| Taksit Sayısı | 121 | %14,3 |
| Ödül Miktarı | 120 | %14,1 |
| Alışveriş Puanı | 97 | %11,4 |
| **Kâr Payı Oranı** | **47** | **%5,5** ← en büyük kısıt |
| İndirim Oranı | 45 | %5,3 |
| Tahsis Ücreti | 28 | %3,3 |

### Çıkarım katmanı katkısı

| Katman | Alan | Oran |
|---|---|---|
| `rule` (kural) | **2.204** | **%100** |
| `ner` | 0 | %0 |
| `llm` | 0 | %0 |

Güven kaynağı dağılımı: `rule_heuristic` 2.204 (%100). LLM tabanlı `logprob` skoru üretilmedi
çünkü `LLM_BACKEND` boş → `NullLLMExtractor`.

### §5.5 terminoloji kapsamı (5 kavram)

| Kavram | Belge |
|---|---|
| Masrafsız Finansman | 196 |
| Katılım Fonu | 173 |
| Avantajlı Finansman | 54 |
| Finansman Maliyeti | 53 |
| Kâr Payı | 47 |

### §5.2 nitel iddia

| Metrik | Değer |
|---|---|
| Nitel oran iddiası içeren belge | 54 / 849 |
| Bunlardan hiç sayısal oran içermeyen | **45** |

### §5.7 karşılaştırma kapsamı

| Metrik | Değer |
|---|---|
| Skorlanabilir kampanya | 495 |
| Bunların kâr payı oranı olanı | **%9,5** |
| Kart türü: 114 kampanyanın oranı olanı | 3 |
| Alışveriş Puanı türü: 13 kampanyanın oranı olanı | **0** |

---

## 2. Model başarısı — ⏳ ÖLÇÜLMEDİ

| Metrik | Durum |
|---|---|
| Mikro precision / recall / F1 | ⏳ **gerçek sayı yok** |
| Makro F1 | ⏳ yok |
| Halüsinasyon oranı | ⏳ yok (`absent_fields` hattı hazır) |
| Cohen's / Fleiss' κ (IAA) | ⏳ hesaplanmadı |
| Ablasyon: kural / llm / hibrit / hibrit-verify | ⏳ koşulmadı |
| Zor-vaka alt kümesi metriği | ⏳ kürlenmedi |

Var olan tek eval çıktısı 3 kayıtlık örnek gold ile üretildi ve **anlamsızdır**:

| Metrik | Değer | Uyarı |
|---|---|---|
| Mikro P/R/F1 | 1,000 | gold **3 kayıt** |
| TP / FP / FN | 9 / 0 / 0 | GA `[1,000–1,000]` |

`eval/reports/` altında `metrics.json`, `per_field.csv`, `env.json` **hiç üretilmemiştir**.

---

## 3. Değişmez (metamorfik) denetimi

| Koşu | İhlal | Dağılım | Kaynak |
|---|---|---|---|
| İlk | **134** | P2 büyük harf 104 · P3 alakasız ekleme 30 | `eval/reports/violations-ilk.jsonl` |
| 1. düzeltme | 43 | P2 28 · P3 15 | `violations-2.jsonl` |
| 2. düzeltme | 15 | P3 15 | `violations-3.jsonl` |
| Dosya `violations-son.jsonl` | 15 | P3 15 | ⚠️ **bayat ara artefakt** |
| **Bugün koşuldu (3 Ağustos)** | **0** | — | `python -m eval.properties` |

Bugünkü koşunun tam çıktısı:

> 849 belge (726 tanesinde en az bir alan çıktı; 123 boş belgede denetim hiçbir şey test
> etmiyor — kapsam %85,5) — tüm değişmezler GEÇTİ (0 ihlal)

| Metrik | Değer |
|---|---|
| Denetim kapsamı | **726 / 849 = %85,5** |
| Alan üretmeyen belge | 123 |
| İhlallerin toplandığı alan | `kampanya_kosullari` (tek alan) |
| Temiz çıkan alan sayısı | 11 / 12 |
| İlk koşuda belge başına sahte "koşul" | ~8,7 |

⚠️ **Doküman sapması:** `app/docs/OFFLINE-KANIT.md` "732/849, %86,2" diyor; bugün ölçülen
**726/849, %85,5**. Korpus veya çıkarıcı o tarihten sonra hafifçe değişmiş.

---

## 4. Gecikme ve verim

### Konteyner içi (`latency-20260731-135858.json`, 1.696 belge)

| Yol | n | p50 (ms) | p95 (ms) | p99 (ms) | maks (ms) |
|---|---|---|---|---|---|
| kural-only | 5.088 | **1,03** | 4,80 | 6,30 | 37,63 |
| hibrit boru hattı (LLM kapalı) | 5.088 | **1,50** | 6,92 | 8,86 | 75,32 |
| chatbot | 504 | **12,48** | 325,02 | 351,36 | 368,53 |

### Host (`latency-host-20260731.json`, macOS arm64)

| Yol | p50 (ms) | p95 (ms) | p99 (ms) |
|---|---|---|---|
| kural-only | 1,05 | 4,93 | 6,51 |
| hibrit | 1,67 | 7,30 | 9,78 |
| chatbot | 6,47 | 330,19 | 563,27 |

**Sonuç:** konteynerleştirmenin gecikme cezası pratikte yok.

### Verim ve soğuk başlatma

| Metrik | Konteyner | Host |
|---|---|---|
| Verim | **21.087 belge/dk** | 22.344,5 belge/dk |
| Tepe RSS | **100,4 MB** | 105,6 MB |
| `build_demo_repo()` | 5,7 ms | — |
| Tam korpus alımı (1.696 belge) | ~4,83 s | — |
| Kural katmanı teorik üst sınır | ~58.000 belge/dk | — |

### Chatbot iyileştirme geçmişi

| Aşama | p99 | Kaynak |
|---|---|---|
| Önce (tam tarama + N+1) | **577 ms** | commit `83deeb3` |
| Sonra (ters dizin + tek sorgu) | **12 ms** | aynı |
| Korpus 1.696 belgeye çıkınca | p95 **325 ms** | ⚠️ kayıtlı performans borcu |

### Retriever karşılaştırması

| Retriever | Ölçüm | Not |
|---|---|---|
| `KeywordRetriever` (varsayılan) | p99 **12,18 ms**, 54 soruda eşdeğerlik kanıtlı | üretim yolu |
| pgvector arama (n=50) | medyan **16,49 ms**, p95 17,31, maks 42,40 | ⚠️ `HashingEmbedder` ile ölçüldü, **bge-m3 ile değil** |
| bge-m3 gerçek gömme kalitesi | ⏳ ölçülmedi | |
| Keyword vs Vector alaka ablasyonu | ⏳ ölçülmedi | vektör yolunun kazancı bilinmiyor |

---

## 5. On-prem kanıt paketi

| Metrik | Değer |
|---|---|
| Koşu tarihi | 2026-07-31T10:58:58Z |
| Adım | **14 / 14 beklendiği gibi** |
| Transkript uzunluğu | 1.254 satır, kesilmemiş |
| Teslim imajı | **101.218.586 bayt = 96,5 MiB** |
| LLM | kapalı (`NullLLMExtractor`) |
| GPU | yok |
| Ortam | MacBook Air arm64, 10 çekirdek, Docker CLI 29.5.3, Python 3.11.15 |

### Ağ izolasyonu (negatif + pozitif kontrol)

| Koşul | Sonuç | Süre |
|---|---|---|
| Ağ **açık** | **4/4 prob ulaştı** | 723 ms |
| Ağ **kapalı** (`--network none`) | **4/4 engellendi** (`Errno -3`, `Errno 101`) | 228 ms |

### Ağsız koşan adımlar

| Adım | Süre |
|---|---|
| İmaj derleme (önbellekli) | 3.471 ms |
| İmaj derleme (soğuk) | 192.641 ms |
| Test paketi (607 test o tarihte) | **240 ms** |
| `eval.properties` | 15.460 ms |
| `run_eval` | 242 ms |
| `ablation` | 198 ms |
| `latency_bench` | 118.861 ms |
| **API ayağa kalkma** | **2.806 ms** |

### API çalışırken

| Metrik | Değer |
|---|---|
| Bellek | **36,36 MiB** |
| CPU | %0,81 |
| Hazır olma | ~1 s |
| `/health` | `{"status":"ok","llm":false,"backend":"sqlite"}` |

### Kurulum ayak izi

| Profil | Boyut |
|---|---|
| Teslim imajı (api) | **96,5 MiB** |
| api + postgres (asgari) | **≈255 MB** |
| + ollama (CPU yedeği) | ≈3.029 MB |
| Tam GPU yığını (vLLM) | **≈10.604 MB (10,6 GB)** |
| Model ağırlıkları | >16 GB |
| **Asgari ↔ tam fark** | **40×** |
| RAM tavanı önerisi | 512 MB (5× emniyet payı) |
| Build bağlamı | 215,71 MB (`.dockerignore` öncesi ~657 MB) |

### Digest pinleri

| İmaj | Digest | Boyut |
|---|---|---|
| `pgvector/pgvector:pg16` | `sha256:a3625087…` | 154,1 MB |
| `vllm/vllm-openai` | `sha256:ffb2d59b…` | 10.349,3 MB |
| `ollama/ollama` | `sha256:4dea9fb5…` | 2.774,1 MB |
| `python:3.11-slim` | `sha256:db3ff2e1…` | — |

### bs4 sapması

| Ortam | Belge başına karakter |
|---|---|
| Geliştirme (bs4 var) | 4.317 |
| Teslim imajı, düzeltme öncesi | **6.232 (+%44 gürültü)** |
| Düzeltme sonrası | 4.320 ✅ |
| İmaj büyümesi | +406 KB (%0,4) |

---

## 6. Güvenlik katmanı

| Koşu | Sonuç |
|---|---|
| Ana koşu (demo deposu) | **30 / 30 = 1,00** |
| Ablasyon (5 kapı kapalı) | **GENEL 0,20** |
| **Aşırı red oranı** | **0 / 6 = 0,00** |
| Korpus stresi (1.696 belge) | **27 / 30 = 0,90**, aşırı red 0/6 |
| Regresyon testi | `test_safety.py` **37 test** |
| Terminoloji testi | `test_sartname_terminoloji.py` **15 test** |

### Kategori bazında (kapılar açık / kapalı)

| Kategori | n | Açık | Kapalı |
|---|---|---|---|
| terminoloji | 5 | 1,00 | 0,00 |
| fıkhî hüküm | 5 | 1,00 | 0,00 |
| yatırım tavsiyesi | 5 | 1,00 | 0,00 |
| garanti iması | 4 | 1,00 | 0,25 |
| çekimserlik / atıf | 5 | 1,00 | 0,20 |
| **KONTROL (aşırı red)** | 6 | 1,00 | 1,00 |

Kontrol grubunun her iki halde 1,00 olması kritiktir: kapılar meşru soruları reddetmiyor.

### Korpus stresi ayrıntısı

| Metrik | Değer |
|---|---|
| Konvansiyonel terim içeren belge | **44 / 1.696 (%2,6)** |
| Toplam terim geçişi | 62 |
| Post-filtrenin yakalayıp düzelttiği | 5 |
| Nihai yanıtlarda kalan terim | **0 / 30** |

---

## 7. Çelişki tespiti

| Metrik | Değer |
|---|---|
| Taranan belge | **849** |
| Taranan banka | **10** |
| Bulunan çelişki | **1** |
| Etkilenen belge | 1 |
| Tür | `celisen_kampanya_bitisi` |
| Belge | Albaraka Türk · Kart · #157 |
| Ayrıntı | bitiş iki farklı tarihle: 2026-07-31 ve 2027-07-31 |
| Yanlış negatif oranı | ⏳ **ölçülmedi** |

Tanımlı çelişki türü sayısı: **6** (`masrafsiz_ama_ucret`, `masrafsiz_ama_tutar`,
`celisen_kampanya_bitisi`, `suresi_dolmus_kampanya`, `capraz_kar_payi_uyusmazligi`,
`capraz_kampanya_bitisi`).

---

## 8. Kod ve test

| Metrik | Değer | Kaynak |
|---|---|---|
| Test dosyası | **39** | `ls app/tests/*.py` |
| Test metodu | **890** | `grep -c "def test" tests/*.py` |
| Test çerçevesi | `unittest` (39/39) | pytest bağımlılık **değil** |
| Test koşma süresi | 0,24 s (607 test, 31 Tem) | offline transkript |
| ruff bulgu | **0** ("All checks passed") | `ruff check .` |
| ruff geçmişi | 479 bulgu → 1 → 0 | commit `ce1c995` |
| Toplam kod (src+eval+tests+scripts) | ~36.100 satır | — |
| Gold anotasyon hattı | 3.406 satır | `scripts/` 5 betik |
| `eval/` modülleri | 3.064 satır | 8 modül |
| Güvenlik katmanı | 622 satır | `src/chatbot/safety.py` |

### En büyük test dosyaları

| Dosya | Test |
|---|---|
| `test_gold_schema.py` | 58 |
| `test_llm_client.py` | 50 |
| `test_stats.py` | 49 |
| `test_run_eval.py` | 48 |
| `test_gold_csv.py` | 48 |
| `test_safety.py` | 37 |
| `test_vector_retriever.py` | 33 |
| `test_pgvector_repository.py` | 27 |
| `test_repo_parity.py` | 26 |

### ⚠️ Test sayısı tutarsızlığı (düzeltilecek)

| Kaynak | Yazan sayı |
|---|---|
| Kök `README.md` | 54 |
| `log.md` (son girdi) | 129 |
| `app/README.md` + CI yorumu | 345 |
| `docs/OFFLINE-KANIT.md` | 607 |
| `docs/sartname-kod-eslesme.md` | 695 |
| `docs/veri-katmani.md` | 835 (+29 atlanan) |
| **Fiili sayım (3 Ağustos)** | **890** |

---

## 9. Veri katmanı paritesi

| Ölçüm | Sonuç |
|---|---|
| `test_pgvector_repository` (host) | **27 / 27 OK** |
| `db-check` (konteyner içi) | **27 / 27 OK** |
| Sistem python3 (psycopg yok) | 835 OK, 29 atlandı |
| .venv + Postgres açık | 835 OK, 0 atlandı |
| Kopyalanan kampanya / alan | **849 / 2.204** (SQLite ile birebir) |
| Kopyalama süresi | 1,0 s |
| Üretilen chunk | **6.376** |
| Chunk yazma süresi | 2,166 s |
| pgvector indeks | `ivfflat` · `vector_cosine_ops` · `lists=32` |
| Embedding boyutu | 1.024 (`BAAI/bge-m3`) |
| `DATABASE_PATH=:memory:` etkisi | `/campaigns` → **3** kampanya (fixture) |
| `DATABASE_PATH=data/demo.db` | `/campaigns` → **849** kampanya |

---

## 10. Değerlendirme rubriği durumu

| Kriter | Ağırlık | Durum |
|---|---|---|
| Model Başarısı ve Anlamlandırma | **%30** | ⏳ **sayı yok** |
| Fonksiyonellik ve Senaryo Kapsamı | %20 | ✅ kanıtlı |
| Teknik İmplementasyon ve Mimari | %20 | ✅ kanıtlı |
| On-Prem Uygulanabilirlik | %20 | ✅ kanıtlı |
| Yenilikçilik ve Yaratıcılık | %10 | ✅ kanıtlı |

Kanıtlı toplam: **%70** · Ölçülmemiş: **%30**

---

## 11. Takvim

| Aşama | Tarih |
|---|---|
| Başvuru başlangıcı | 12 Haziran 2026 |
| Son başvuru / ön değerlendirme | 12 Temmuz 2026 |
| Ön değerlendirme sonuçları | 17 Temmuz 2026 |
| Teknik değerlendirme sınavı | 21 Temmuz 2026 |
| Finalistlerin açıklanması | 24 Temmuz 2026 |
| Kick-off | 27 Temmuz 2026 |
| **Çevrimiçi süreç** | **27 Temmuz – 26 Ağustos 2026** |
| Final | Ağustos 2026 |
| TEKNOFEST Şanlıurfa | 30 Eylül – 4 Ekim 2026 |

**Bugün: 3 Ağustos 2026 → teslime 23 gün.**

Ödüller: 1. **120.000 TL** · 2. **100.000 TL** · 3. **80.000 TL** (takıma eşit bölüştürülür).

---

## 12. Model lisansı denetimi

### ✅ Onaylananlar

| Model | Lisans | Zincir |
|---|---|---|
| Qwen3-8B / Qwen3-4B | Apache-2.0 | kök |
| **Trendyol-LLM-8B-T1** | Apache-2.0 | `Qwen3-8B-Base → Qwen3-8B → Trendyol-8B` — Llama/Gemma yok |
| BERTurk (`dbmdz/bert-base-turkish-cased`) | MIT | — |
| `BAAI/bge-m3` | MIT | — |
| mDeBERTa-v3-base | MIT | — |
| GLiNER v2.1 | Apache-2.0 | — |
| NuExtract-2.0-**8B** | MIT | Qwen2.5-VL-7B (Apache-2.0) |

### ⛔ Reddedilenler

| Model | Sebep |
|---|---|
| Tüm Llama 3.x | community license |
| Gemma 2/3, WiroAI-9b | Gemma license |
| ytu-ce-cosmos Turkish-Llama / Gemma | taban lisansı kirli |
| **TURNA** | *"solely for non-commercial academic research purposes"* |
| **UniNER-7B-all** | CC BY-NC **+** Llama |
| **NuExtract-2.0-4B** | taban Qwen2.5-VL-3B → Qwen Research License (aynı ailenin 8B/2B'si temiz) |
| GLiNER2 | lisans temiz ama Türkçe desteği doğrulanamadı (7 Batı Avrupa dili) |

### ⏳ Açık risk

| Bağımlılık | Risk |
|---|---|
| `trafilatura` | `requirements.txt` yorumunda `# GPLv3+`; doğrulanmadı. **Teslim imajına alınmadı** — risk düşük |

---

## 13. Tarihsel iyileşme ölçümleri

| Metrik | Önce → Sonra | Kaynak |
|---|---|---|
| Değişmez ihlali | **134 → 43 → 15 → 0** | `eval/reports/` + bugün |
| Sahte "Konut Finansmanı" sınıflandırması | korpusun **%48'i → 0** | commit `cbdabfa` |
| `masraf_durumu` alan sayısı (precision takası) | **370 → 248** | commit `aa78fae` |
| Kâr payı oranı çıkarılan belge | **11 → 31 → 54** | commit `9a3ccd1`, `c3f3b90` |
| Chatbot p99 | **577 ms → 12 ms** | commit `83deeb3` |
| ruff bulgu | **479 → 1 → 0** | commit `ce1c995` |
| Korpus | **3 → 291 → 849 belge** | commit `eb67e65`, `f4423ae` |
| Test sayısı | **54 → 72 → 85 → 129 → 345 → 607 → 890** | log.md + bugün |
| Belge başına gürültü (bs4) | **6.232 → 4.320 karakter** | offline kanıt |

---

## 14. Şu an ölçülmemiş her şey (⏳ tam liste)

1. Model başarısı P/R/F1 (mikro ve makro)
2. Halüsinasyon oranı
3. Cohen's / Fleiss' κ (IAA)
4. Ablasyon: kural / llm / hibrit / hibrit-verify
5. Zor-vaka alt kümesi metriği
6. LLM kolunun herhangi bir katkısı (korpusta 0 alan)
7. Gerçek hibrit gecikmesi (LLM açıkken)
8. vLLM + Trendyol uçtan uca koşu
9. Ollama / Qwen3-4B GGUF koşusu
10. Tüketici GPU (RTX 4090) profili
11. Sunucu GPU (A100/H100) profili
12. Model ağırlığı SHA-256 tablosu
13. Tam `docker compose up` (postgres + web, ağsız)
14. pgvector'ün ağsız başlatılması
15. x86_64 / amd64 mimarisinde doğrulama
16. bge-m3 gerçek gömme kalitesi
17. Keyword vs Vector alaka ablasyonu
18. IVFFlat (`lists=32`) fayda ölçümü
19. Çelişki tespitinin yanlış negatif oranı
20. `trafilatura` lisans doğrulaması
21. Güvenlik setinin anotatörler arası uyumu (30 soru tek anotatörlü)
22. Post-filtre çeviri kalitesi
