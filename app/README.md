# Anatolia AI — Katılım Bankacılığı Kampanya Bilgi Çıkarımı

[![CI](https://github.com/mehmetefeaytas/anatoliaAI/actions/workflows/ci.yml/badge.svg)](https://github.com/mehmetefeaytas/anatoliaAI/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)
[![Testler](https://img.shields.io/badge/testler-2631%20ye%C5%9Fil-brightgreen.svg)](tests/)
[![Değişmez denetimi](https://img.shields.io/badge/de%C4%9Fi%C5%9Fmez%20denetimi-1774%20belge%20%C2%B7%201%20ihlal-yellow.svg)](eval/properties.py)

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

> **Python 3.11+ gerekir.** Kod `zip(..., strict=)` gibi 3.10+ sözdizimi
> kullanıyor. Stok macOS `/usr/bin/python3` **3.9.6**'dır ve aşağıdaki
> komutlar orada `TypeError: zip() takes no keyword arguments` ile patlar.
> `python3 -V` ile doğrulayın; düşükse `python3.11 -m ...` kullanın.
> "Sıfır bağımlılık" üçüncü taraf **paket** gerekmediği anlamına gelir,
> sürüm bağımsızlığı değil.

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

**Test:** 152 dosyada **2.631** birim/entegrasyon testi, tamamı offline yeşil
(`.venv/bin/python -m unittest discover -s tests`) + 40 arayüz testi
(`cd web && npm run test`)
(`python3 -m unittest discover -s tests`).

## Ölçüm Durumu

Bu bölüm bilinçli olarak **dürüst** tutulur: ölçülmemiş bir sayı buraya yazılmaz.

| Kalem | Durum |
|---|---|
| Korpus | **1.782 gerçek belge**, 10 katılım bankasından canlı toplandı (provenance: `source_url` + `scraped_at` + `content_hash`, 1.772/1.776 tam) |
| Testler | ✅ **2.631 test yeşil**, ağ gerektirmeden koşuyor (bağımlılıksız koşuda 205'i atlanır — API yüzeyi `test-with-deps` işinde sınanır) |
| Değişmez (invariant) denetimi | ⚠️ **1.782 belgede 1 ihlal** (`P4_cumle_sirasi`, kapsam %91,3) — etiketsiz veride otomatik hata avı (`python -m eval.properties`). Eski "849 belgede 0 ihlal" rozeti korpus büyüyünce geçersizleşti |
| Kural katmanı kapsamı | ✅ şartnamenin **12/12** alanı |
| Gold set | **66 tekil belge**, iki farklı statüde — aşağıya bakınız |
| Alan bazında P/R/F1 + %95 GA | ✅ ölçüldü — aşağıdaki tablo |
| Ablasyon + McNemar | ✅ ölçüldü — `docs/rapor/ablasyon.md` |
| Anotatörler arası uyum (κ) | ✅ **Fleiss κ 0,302** · Krippendorff α 0,620/0,787 (260 ortak satır, 4 anotatör). Eşik altı → ilan edilen sonuç uygulandı (kılavuz v1→v2). v2 turu anote EDİLMEDİ, yeniden ölçüm bekliyor |

### Ölçüm sonuçları

Kural katmanı, `gold.v2` (n=48, **kör** etiketlenmiş), strict eşleştirici,
belge düzeyi bootstrap 2000 örnek, tohum 42:

| ölçüt | değer |
|---|---|
| **yapılandırılmış alan mikro-F1** (11 alan) | **0,646** |
| 12-alan mikro-F1 | **0,452** [%95 GA 0,384–0,512] |
| makro-F1 | 0,556 [%95 GA 0,412–0,650] |
| halüsinasyon (bilgi metinde YOK, değer uyduruldu) | **0,059** [26/444] |
| kaçırma | 20 · yanlış çıkarım 40 |

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
| `gold.v2` | 48 | **makine** anotatör (M1–M4), her belge birebir alıntı kanıtıyla | ❌ **insan hakemliği bekliyor** (`adjudicated: false`) |

Yukarıdaki 0,452 **gold.v2 üzerinde** ölçüldü, yani **insan hakemliğinden
geçmemiş** bir sette. Bunu gizlemek yerine yazıyoruz çünkü alternatifi
(0,677'yi manşete koymak) daha kötü — o da modele çapalı bir protokolden
geliyor. İkisi de kısıtlıdır ve ikisi de kısıtıyla birlikte sunulur.

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
> yalnız **3 karar** destekli (TP 1, FN 2). Oradan çıkan F1 = 0,500
> **yorumlanamaz**. Korpusta da alan 70/1.774 belgede (%3,9) var — bu bir
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
> raporlanmıştı (`data/gold/iaa_report.md`), README güncellenmemişti.

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
- **Gold seti büyütmek** — 66 → 150 bandı; GA'lar daralır ve 0,452 nokta
  tahmini savunulabilir hâle gelir.
- **`kampanya_kosullari` ve `vade_ay`** — ikisi mikro-F1'in en büyük tek
  kaldıracı; eşleştirici sertliği mi tanım sorunu mu ayrıştırılmalı.
- **Değişmez denetimini 1.774 belgede tekrarla** — mevcut "0 ihlal" sonucu
  849 belgelik korpusta ölçüldü, korpus o günden beri büyüdü.
- **Ablasyon kolları** — izole ortamlarda kalan kollar (Trendyol-8B hibrit,
  GLiNER geri-çağırma ağı). Başarısız kollar **negatif sonuç olarak
  raporlanır**; üç tanesi zaten öyle raporlandı.
