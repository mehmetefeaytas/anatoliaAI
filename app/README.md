# Anatolia AI — Katılım Bankacılığı Kampanya Bilgi Çıkarımı

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
python -m src.scraping.run --config config/banks.yaml   # scraping
python -m src.extraction.run --input data/processed/sample.txt
python -m eval.run_eval --gold data/gold/               # değerlendirme + ablasyon
pytest
cd web && npm run dev
```

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

**Test:** 54 birim/entegrasyon testi, tamamı offline yeşil (`python3 -m unittest discover -s tests`).

### Sonraki adımlar (gerçek veri/donanım gerektirir)
- Gerçek banka HTML'lerini `data/raw/<slug>/` altına çek (canlı scraping veya manuel).
- 150–300 kampanyalık çift-anotasyonlu gold set + zor-vaka alt kümesi (kappa).
- vLLM'de Trendyol-LLM-8B-T1 (AWQ) ayağa kaldır → `LLM_BACKEND=vllm` ile hibridi aç.
- BERTurk 8-sınıf sınıflandırıcıyı fine-tune et → `BERTURK_MODEL_DIR`.
