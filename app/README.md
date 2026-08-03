# Anatolia AI — Katılım Bankacılığı Kampanya Bilgi Çıkarımı

[![CI](https://github.com/mehmetefeaytas/anatoliaAI/actions/workflows/ci.yml/badge.svg)](https://github.com/mehmetefeaytas/anatoliaAI/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)
[![Testler](https://img.shields.io/badge/testler-345%20ye%C5%9Fil-brightgreen.svg)](tests/)
[![Değişmez denetimi](https://img.shields.io/badge/de%C4%9Fi%C5%9Fmez%20denetimi-849%20belge%20%C2%B7%200%20ihlal-brightgreen.svg)](eval/properties.py)

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
"Önce Kural, Sonra LLM" hibrit çıkarım:
```
scrape → clean → preprocess → extract (kural → NER → LLM) → reconcile →
normalize → PostgreSQL → compare → dashboard + hibrit chatbot (text-to-SQL + RAG)
```
Detay: [`CLAUDE.md`](CLAUDE.md) §3–§6.

## Hızlı Başlangıç (deterministik çekirdek — sıfır bağımlılık)

Normalizasyon + kural çıkarımı + eval saf stdlib ile çalışır:

```bash
cd app
# birim testler (27 test)
python3 -m unittest tests.test_normalize tests.test_extract
# değerlendirme (alan bazında P/R/F1 + zor-vaka alt kümesi)
python3 -m eval.run_eval --gold data/gold/gold.sample.json
```

## Tam Sistem (Docker, offline)
```bash
docker-compose up        # postgres + vllm/ollama + api + web
pip install -r requirements.txt   # geliştirme ortamı
```

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
| Uzlaştırma | `src/extraction/reconcile.py` | ✅ kural birincil + LLM boşluk doldurma |
| Sınıflandırma (8 tür) | `src/extraction/ner/classifier.py` | ✅ kural-ipucu + BERTurk yolu |
| DB | `src/db/` | ✅ SQLite (offline) + Postgres/pgvector şema |
| Karşılaştırma | `src/comparison/compare.py` | ✅ adil-kıyas garantisi |
| Çelişki tespiti | `src/comparison/contradiction.py` | ✅ yenilikçilik |
| Hibrit chatbot | `src/chatbot/` | ✅ router + yapısal sorgu + RAG |
| Scraping | `src/scraping/` | ✅ config-driven + offline fixtures |
| Pipeline | `src/pipeline.py` | ✅ uçtan uca |
| API | `src/api/main.py` | ✅ FastAPI (import-safe) |
| Web | `web/` | ✅ Next.js dashboard + chatbot |
| Eval | `eval/run_eval.py`, `eval/ablation.py` | ✅ P/R/F1 + zor-vaka + ablasyon |

**Test:** 16 dosyada **345** birim/entegrasyon testi, tamamı offline yeşil
(`python3 -m unittest discover -s tests`).

## Ölçüm Durumu

Bu bölüm bilinçli olarak **dürüst** tutulur: ölçülmemiş bir sayı buraya yazılmaz.

| Kalem | Durum |
|---|---|
| Korpus | **849 gerçek belge**, 8 katılım bankasından canlı toplandı (provenance: `source_url` + `scraped_at` + `content_hash`) |
| Değişmez (invariant) denetimi | ✅ **849 belgede 0 ihlal** — etiketsiz veride otomatik hata avı (`python3 -m eval.properties`) |
| Kural katmanı kapsamı | ✅ şartnamenin **12/12** alanı |
| İnsan-etiketli gold set | 🔄 250 belge seçildi ve anotasyona hazır; anotasyon sürüyor |
| Alan bazında P/R/F1 + %95 güven aralığı | ⏳ gold set tamamlanınca — **beklenen: 5 Ağustos 2026** |
| Kalibrasyon (ECE + reliability diagram) | ⏳ aynı tarih |
| Ablasyon (kural / LLM / hibrit + McNemar) | ⏳ aynı tarih |

Neden şimdi sayı yok: kural tabanlı çıkarıcı gold sete **bakılmadan** yazıldı,
bu yüzden 250 kayıt gerçek bir **held-out** test setidir. Bu bilimsel avantajı
korumak için gold set dondurulmadan metrik yayımlamıyoruz.

### Sonraki adımlar
- **Anotasyon** — 250 belge, çift-anote 50'lik alt kümede Cohen κ / Krippendorff α.
- **Split protokolü** — dev (~100, tüm model seçimi) / **TEST (~150, dondurulur, sha256'lanır)**.
- **vLLM'de Trendyol-LLM-8B-T1 (AWQ)** → `LLM_BACKEND=vllm` ile hibridi aç.
  Lisans zinciri doğrulandı: Apache-2.0, `Qwen3-8B-Base → Qwen3-8B → Trendyol-8B`
  (bkz. [`docs/model-license-audit.md`](docs/model-license-audit.md)).
- **Ablasyon kolları** — izole ortamlarda: kural-only · Qwen3-8B hibrit ·
  Trendyol-8B hibrit · GLiNER geri-çağırma ağı · NuExtract-2.0-8B ·
  BERTurk 8-sınıf fine-tune. Hepsi yalnız dev split'te seçilir; başarısız kollar
  **negatif sonuç olarak raporlanır**.
- **On-prem kanıtı** — `--network none` transkripti + negatif kontrol + gecikme/kaynak tabloları.
