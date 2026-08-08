# Anatolia AI — Katılım Bankacılığı Kampanya Bilgi Çıkarımı

[![CI](https://github.com/mehmetefeaytas/anatoliaAI/actions/workflows/ci.yml/badge.svg)](https://github.com/mehmetefeaytas/anatoliaAI/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)
[![Testler](https://img.shields.io/badge/testler-1610%20ye%C5%9Fil-brightgreen.svg)](tests/)
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
| Korpus | **1.774 gerçek belge**, 10 katılım bankasından canlı toplandı (provenance: `source_url` + `scraped_at` + `content_hash`, 1.772/1.776 tam) |
| Testler | ✅ **1.610 test yeşil**, ağ gerektirmeden koşuyor |
| Değişmez (invariant) denetimi | ✅ **849 belgede 0 ihlal** — etiketsiz veride otomatik hata avı (`python -m eval.properties`) |
| Kural katmanı kapsamı | ✅ şartnamenin **12/12** alanı |
| İnsan-etiketli gold set | ✅ **66 tekil belge** (gold.v1 n=20 + gold.v2 n=48, ikisi 2 belgede örtüşüyor) |
| Alan bazında P/R/F1 + %95 GA | ✅ ölçüldü — aşağıdaki tablo |
| Ablasyon + McNemar | ✅ ölçüldü — `docs/rapor/ablasyon.md` |
| Anotatörler arası uyum (κ) | ⏳ **henüz ölçülmedi** — çift anotasyonlu veri yok (aşağıda) |

### Ölçüm sonuçları

Kural katmanı, `gold.v2` (n=48, **kör** etiketlenmiş), strict eşleştirici,
belge düzeyi bootstrap 2000 örnek, tohum 42:

| ölçüt | değer |
|---|---|
| mikro-F1 | **0,389** [%95 GA 0,329–0,442] |
| makro-F1 | 0,409 |
| halüsinasyon (bilgi metinde YOK, değer uyduruldu) | **0,099** [44/444] |
| kaçırma | 21 · yanlış çıkarım 43 |

**Bu sayı düşük ve nedenini saklamıyoruz.** İki şey birden doğru:

- `gold.v1` (n=20) üzerinde aynı sistem **0,677** veriyor. Fark protokol
  kaynaklı: v1'de anotatör modelin çıktısını onaylayarak etiketledi
  (`ANNOTATION_GUIDE.md` §3.1, eski kural), v2 ise **kör** etiketlendi.
  0,677 tek başına sunulmaz — ikisi birlikte sunulur.
- Farkın ~%57'si tek bir alandan geliyor: `kampanya_kosullari` serbest metin
  **liste** alanı ve birebir eşleşmede F1 = 0,000. Kabiliyet çöküşü değil,
  eşleştirici sertliği.

**Tekrarlanan tek sayı halüsinasyon oranıdır** (~%10), payda 166'dan 444'e
çıkarken korundu. İki protokolden de bağımsız çıkan tek metrik budur.

### Ölçümle yanlışlanan üç hipotez

Bu projede "daha güçlü model ekleyelim" refleksi **üç kez** denendi ve
üçünde de kural katmanı önde kaldı:

| deneme | sonuç |
|---|---|
| Hibrit kol (LLM boşlukları doldurur) | 0,575 vs kural 0,677; halüsinasyon %70 fazla |
| Orkestrasyon (ajan önerir, hakem reddeder) | 0,377 vs kural 0,387; McNemar p=0,039, **kazanan kural** |
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

### Bilinen eksik: κ

Anotatörler arası uyum **hesaplanmadı**. Kod (`eval/iaa.py` — Cohen, Fleiss,
Krippendorff), eşikler (κ≥0,80 kabul · 0,67–0,80 notla · <0,67 hakemlik,
**önceden ilan edilmiş**) ve CSV paketi hazır; eksik olan çift anotasyonlu
veridir. gold.v2'nin dört anotatörü **ayrık** kümelere baktığı için örtüşme
sıfır ve κ tanımsız. Bu, şartname §16'nın karşılanmayan tek kalemidir.

### Sonraki adımlar

Öncelik sırasıyla, teslime kalan sürede:

- **κ için çift anotasyon** — 20 belgelik kalibrasyon paketi hazır ve
  boş bekliyor (`data/gold/review/round0_kalibrasyon_v2_*.csv`). Dolunca
  `python -m scripts.report_iaa <dosyalar>` tek komutla Fleiss κ +
  Krippendorff α üretir. §16'nın kapanmayan tek kalemi bu.
- **Gold seti büyütmek** — 66 → 150 bandı; GA'lar daralır ve 0,389 nokta
  tahmini savunulabilir hâle gelir.
- **`kampanya_kosullari` ve `vade_ay`** — ikisi mikro-F1'in en büyük tek
  kaldıracı; eşleştirici sertliği mi tanım sorunu mu ayrıştırılmalı.
- **Değişmez denetimini 1.774 belgede tekrarla** — mevcut "0 ihlal" sonucu
  849 belgelik korpusta ölçüldü, korpus o günden beri büyüdü.
- **Ablasyon kolları** — izole ortamlarda kalan kollar (Trendyol-8B hibrit,
  GLiNER geri-çağırma ağı). Başarısız kollar **negatif sonuç olarak
  raporlanır**; üç tanesi zaten öyle raporlandı.
