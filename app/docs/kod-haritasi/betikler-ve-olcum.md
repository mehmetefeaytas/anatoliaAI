# Betikler ve Ölçüm — kod haritası

> Kapsam: `scripts/` (42 `.py`, 16.082 satır + `offline_proof.sh` 397 satır) ve
> `eval/` (9 `.py`, 3.817 satır). Hepsi okundu. Bu belge **referanstır**, öğretici
> değil. Ölçülmüş sayılar kaynak dosyadaki biçimiyle aktarılmıştır; emin
> olunmayan yerler `belirsiz` diye işaretlidir.
>
> Üretim kodu (`src/`) bu haritanın DIŞINDADIR. `scripts/` ve `eval/` üretim
> kodu değil, **anotasyon ve ölçüm araçlarıdır** (`scripts/__init__.py`).

---

## 1. Tek cümle

`scripts/` insanla model arasındaki gold üretim hattını ve veri toplama /
kalite kapılarını taşır; `eval/` o gold üzerinde teslim edilen sistemi
istatistiksel olarak ölçer — ve iki katman da tek bir ilkeye göre yazılmıştır:
**"ölçülmedi" ile "0" asla aynı şeye yazılmaz.**

---

## 2. Betik envanteri

Sütunlar: ne yapar · ne zaman koşulur · çıktısı nereye gider.
`→` çıktı yolu; `∅` dosya yazmaz (yalnız stdout).

### 2.1 `eval/` — ölçüm çekirdeği

| Dosya | Ne yapar | Ne zaman | Çıktı |
|---|---|---|---|
| `run_eval.py` (948) | Gold üzerinde alan bazında P/R/F1 + mikro/makro + bootstrap GA; resmî metrik | Her ölçüm turunda; `offline_proof.sh` adım 7 | → `eval/reports/<ts>/` (5 dosya) |
| `ablation.py` (523) | Kol karşılaştırması (kural/llm/hibrit/hibrit-verify) + McNemar + eşleşmiş fark GA | Kol kararı verilirken; `offline_proof.sh` adım 8 | → `eval/reports/<ts>/` |
| `predictors.py` (280) | Konfig adı → tahmin fonksiyonu **tek kaynağı**; `is_present` semantiği | Kütüphane | ∅ |
| `matchers.py` (450) | `strict` / `tolerant` eşleştirme + kalem düzeyi (Jaccard) sayaç | Kütüphane | ∅ |
| `stats.py` (379) | Küme bootstrap GA + McNemar (tam binom / χ²) — saf stdlib | Kütüphane | ∅ |
| `report.py` (291) | Rapor yazıcı: `metrics.json`, `env.json`, `report.md`, `per_field.csv`, `decisions.csv` | Kütüphane | → `eval/reports/<ts>/` |
| `iaa.py` (253) | Cohen / Fleiss / Krippendorff κ + önceden ilan edilmiş eşik yorumu | Kütüphane | ∅ |
| `properties.py` (426) | Değişmez (P1–P4) denetimi — **etiketsiz** veride hata avlar | CI kapısı; `offline_proof.sh` adım 6 | → `--out` JSONL (kanonik: `eval/reports/<ts>/violations.jsonl`) |
| `ablation_report.py` (267) | `metrics.json` → markdown ablasyon tablosu; **hiçbir sayı hesaplamaz** | Rapor tazelenirken | ∅ (stdout) |

### 2.2 `scripts/` — gold üretim hattı

| Dosya | Ne yapar | Ne zaman | Çıktı |
|---|---|---|---|
| `gold_schema.py` (632) | Gold şema v1: 12 kanonik alan, tip aileleri, `parse/format_gold_value`, protokol sabitleri | Kütüphane (yaprak) | ∅ |
| `preannotate.py` (519) | `data/raw` → hibrit çıkarım → ön-anotasyon JSON; anlaşmazlık sinyali | Tur başlangıcı | → `data/gold/preannotations.json` |
| `to_review_csv.py` (747) | Ön-anotasyon → alan-başına-satır inceleme CSV'si + `belgeler/<doc_id>.txt` | Tur başlangıcı | → `data/gold/review/round*.csv`, `belgeler/`, `_plan.json`, `_atama.md` |
| `lint_review_csv.py` (366) | İnceleme CSV'sini anotasyon anında denetler | Anotasyon sırasında + derleme öncesi kapı | ∅ (exit 1) |
| `build_gold.py` (554) | Doldurulmuş CSV'ler → gold JSON + sha256 | Anotasyon bitince | → `data/gold/gold.v1.json(.sha256)`, `excluded.json`, `build_report.md` |
| `report_iaa.py` (367) | κ + uyuşmazlık raporu (karar uyumu + değer uyumu) | Anotasyon bitince | → `data/gold/iaa_report.md` |
| `xlsx_to_review_csv.py` (321) | Anotatörün `.xlsx`'inden **yalnız kararları** CSV'ye taşır | Anotatör dosya gönderince | → hedef CSV (+ `.yedek-xlsx-oncesi`) |
| `protokol_yukselt.py` (243) | CSV'yi v1 protokolünden v2'ye taşır (damgala / taşı) | Protokol geçişinde | → CSV (+ `.yedek-v1`) |
| `onanotasyon_tazele.py` (239) | CSV'deki `model_value`'yu bugünkü çıkarıcıyla tazeler | Çıkarıcı düzelince, anotasyondan ÖNCE | → CSV (+ `.yedek-tazeleme`), `--degisim-raporu` |
| `sample_gold_v2.py` (258) | gold.v2 aday havuzu — tabakalı, ayrık, deterministik örnekleme | Gold genişletmede | → `data/gold/gold.v2.aday.json`, `data/gold/parca/parca-N.json` |
| `merge_gold_v2.py` (204) | v2 parçalarını birleştirir; **üç kapı** (şema/kanıt/ayrıklık) | v2 etiketleme bitince | → `data/gold/gold.v2.json(.sha256)` |
| `split_gold.py` (457) | Gold'u dev/test böler ve TEST'i **dondurur** (sha256 + erişim kaydı) | Anotasyon bitince BİR KEZ | → `data/gold/splits/` (4 dosya) |
| `kalibrasyon_hakemlik.py` (517) | Kalibrasyon CSV'lerine kılavuz kaynaklı 7 hakemlik kuralı uygular | Kalibrasyon turundan sonra | → CSV (+ `.yedek-hakemlik`), değişim raporu |
| `kalibrasyondan_gold.py` (232) | Kalibrasyondan gold'a ne girer — (b) seçeneğinin ölçümü | Karar anı | ∅ |
| `kappa_durum.py` (174) | κ hazırlık tablosu: hangi dosya ne kadar dolu, κ hangi gruptan çıkar | Anotasyon sürerken | ∅ |
| `onarim_recetesi.py` (462) | Lint hatalarını kalıba indirir, **ayrı dosyaya** öneri yazar | Lint hatası birikince | → `data/gold/review/_oneriler.csv` |
| `calisma_listesi.py` (482) | Anotatör başına ölçülmüş hata kalıbı kartı | Yeni tur öncesi | → `data/gold/review/_calisma-listesi-{A..D}.md` |

### 2.3 `scripts/` — veri toplama, gümüş etiket, demo

| Dosya | Ne yapar | Ne zaman | Çıktı |
|---|---|---|---|
| `reextract_raw.py` (329) | Önbellek HTML'den metni **siteye gitmeden** yeniden çıkarır; kabuk işaretler | Çıkarım mantığı düzelince | → `data/raw/**/*.txt`, `.meta.json`, `_reextract_report.md` |
| `split_trainable.py` (924) | Klasik korpusu eğitilebilir/eğitilemez ayırır; **çerçeve/çekirdek** mekanizmasının kaynağı | Gümüş hattın başı | → `data/silver/trainable.jsonl`, `excluded.jsonl`, `split_report.md` |
| `boilerplate_audit.py` (908) | Çerçeve ayıklamasını yarışma korpusunda **ölçer**; değiştirmez | Mekanizmayı taşımadan önce | → `--rapor` md, `--jsonl` (varsayılan ∅) |
| `build_silver.py` (305) | Gümüş hattı CLI: `prepare` / `prepare-verify` / `merge` / `score` | Gümüş turu | → `data/silver/{batch,silver,queue,rejected}.jsonl`, `silver_report.json` |
| `run_silver_verifier.py` (241) | Üçüncü oyu **yerel** Ollama ile kullanır; kesintiye dayanıklı | `prepare-verify`den sonra | → `data/silver/verdicts_local.jsonl` (append) |
| `resolve_queue.py` (329) | İnsan kuyruğunu sınıf kurallarına göre çözer; çözülemeyeni bırakır | `merge`den sonra | → `silver.jsonl` (append), `queue.jsonl`, `rejected_from_queue.jsonl` |
| `crosscheck_rates.py` (617) | Kâr payı oranını bankanın **ilan ettiği** oranla çapraz doğrular | Anotasyon öncesi süzme | → `data/gold/rate_crosscheck.{csv,md}` |
| `crosscheck_fees.py` (780) | "Masrafsız" iddiasını bankanın **ücret tarifesiyle** karşılaştırır | Çelişki taramasında | → `data/gold/fee_crosscheck.{csv,md}` |
| `tcmb_sozluk_ayristir.py` (118) | TCMB sözlüğü HTML → JSON | Bir kez / kaynak yenilenince | → `data/terminology/tcmb-terimler.json` |
| `tcmb_capraz_analiz.py` (217) | TCMB ile katılım sözlüğünü karşılaştırır (kapsama/çatışma/sahte-dost) | Terminoloji raporu yazılırken | ∅ |
| `build_demo_db.py` (452) | Tüm korpusu `mode="corpus"` ile çıkarımdan geçirip kalıcı SQLite üretir | Demo öncesi / korpus değişince | → `data/demo.db` |
| `check_demo_db.py` (122) | DB korpusla güncel mi — sessiz bayatlama kapısı | CI + demo öncesi | ∅ (exit 1) |
| `build_summaries.py` (266) | LLM özetlerini **önceden** üretip `campaigns.ozet`'e yazar | Demo öncesi (LLM açıkken) | → `data/demo.db` (`ozet` sütunu) |

### 2.4 `scripts/` — kalite kapıları ve ölçüm betikleri

| Dosya | Ne yapar | Ne zaman | Çıktı |
|---|---|---|---|
| `jargon_lint.py` (399) | Katılım jargonu ihlali **tespit eder, değiştirmez** | CI | ∅ / `--json` |
| `css_sinif_denetimi.py` (144) | TSX'te kullanılan her CSS sınıfının tanımı var mı | CI | ∅ |
| `kontrast_kontrol.py` (212) | `tokens.css` paletinin WCAG kontrast oranı (iki tema) | CI | ∅ |
| `belge_metni_denetimi.py` (274) | İnceleme paketinde belge metni eksik mi; `--uret` ile onarır | Paket teslim öncesi | → `data/gold/review/belgeler/*.txt` |
| `eval_injection.py` (286) | Prompt-injection değerlendirmesi (doğrudan + **dolaylı**) | CI | ∅ / `--json` |
| `eval_classifier.py` (222) | 8-sınıf kampanya türünü gold üzerinde ölçer (kural çizgisi + model) | Sınıflandırıcı değişince | ∅ / `--out` |
| `train_berturk.py` (649) | BERTurk ince ayarı, **yerel**; kabul kapısını kendi basar | Sınıflandırıcı denemesi | → `models/berturk-kampanya-8sinif/`, `data/eval/berturk_*.jsonl/json` |
| `eval_o1.py` (401) | Ö1 terim deneyi: temel / sadeleştirme / sözlük kartı üç kolu | Terim kararı için | → `data/eval/o1-*.json` |
| `eval_rag_terim.py` (204) | Fıkhî terim kapsaması — RAG kaynak gösterebiliyor mu (**gold'suz**) | Korpus/RAG değişince | ∅ / `--json` |
| `latency_bench.py` (378) | Üç çıkarım yolunun gecikmesi + kaynak tüketimi | Kaynak raporu; `offline_proof.sh` adım 9 | ∅ / `--json` |
| `mcnemar_report.py` (519) | İki koşumun **eşleştirilmiş** karşılaştırması (`decisions.csv` üzerinden) | İki konfig kıyaslanırken | ∅ / `--json`, `--markdown` |
| `offline_proof.sh` (397) | `docker run --network none` içinde tüm paketi koşar; **negatif kontrol** + onun pozitif kontrolü | Teslim kanıtı | → `docs/offline-proof/transcript-<ts>.log`, `latency-<ts>.json` |

---

## 3. Kümeler — hangi betikler birlikte bir iş akışı

### (a) Veri toplama ve korpus bakımı

```
src/scraping/collector.py  (bu haritanın dışında)
        │  ham HTML + .txt + .meta.json  →  data/raw/
        ▼
reextract_raw.py      çıkarım mantığı düzelince METNİ yeniden üretir
        │              (siteye gidilmez, dosya adları KORUNUR, kabuk işaretlenir)
        ▼
crosscheck_rates.py   ilan edilmiş oranlarla çapraz doğrulama
crosscheck_fees.py    ücret tarifesiyle çapraz doğrulama
        │              ikisi de anotasyon CSV'lerini EZMEZ — ayrı dosyaya yazar
        ▼
tcmb_sozluk_ayristir.py → tcmb_capraz_analiz.py   terminoloji kapsaması
```

Bağımsız kol: `boilerplate_audit.py`, `split_trainable.py`'ın çerçeve
mekanizmasını import edip yarışma korpusunda **ölçer** (taşımadan önce).

### (b) Gold üretim hattı

Bölüm 4'te adım adım. Ayrıca **ikinci, ayrık bir hat** vardır (v2):
`sample_gold_v2 → parça → (insan etiketler, `field_spans` ile) → merge_gold_v2`.

### (c) Ölçüm / eval

```
gold.v*.json
   │
   ├─► run_eval.py    ── predictors.py ─┐
   │      │              matchers.py    │  ORTAK ÇEKİRDEK
   │      │              stats.py       │  (score_document tek yerde)
   │      └─► report.py ────────────────┘
   │             → metrics.json · report.md · per_field.csv
   │               decisions.csv · env.json
   │
   ├─► ablation.py    aynı çekirdek, kol kol + McNemar
   │      └─► ablation_report.py  (metrics.json → markdown)
   │
   └─► mcnemar_report.py  iki KOŞUMUN decisions.csv'lerini eşleştirir

properties.py  gold'a hiç bakmadan, ham korpusta P1–P4 ihlali arar
iaa.py         anotatör uyumu (report_iaa.py'nin çekirdeği)
```

Yan kollar aynı çekirdeği kullanır: `eval_classifier.olc` → `run_eval.Counts` +
`macro_f1`; `train_berturk` → `eval_classifier.olc`; `eval_o1` → `run_eval`
puanlaması + `stats` bootstrap.

### (d) Kalite kapıları

`jargon_lint` · `css_sinif_denetimi` · `kontrast_kontrol` ·
`belge_metni_denetimi` · `lint_review_csv` · `check_demo_db` ·
`eval_injection` · `eval/properties` · `merge_gold_v2` (kapı olarak) ·
`split_gold --verify`.

Ortak imza: **exit 1 = ihlal**, konsola gerekçe, düzeltmeyi insana bırakır.

### (e) Demo DB kurulumu

```
data/raw (korpus)
   ▼
build_demo_db.py --out data/demo.db      mode="corpus", tüm alt klasörler
   ▼
check_demo_db.py                         belge SAYISI ölçütü (mtime DEĞİL)
   ▼
build_summaries.py --devam               LLM özetleri, parçalı yazma
   ▼
offline_proof.sh                         --network none içinde kanıt paketi
```

### (f) Gümüş etiket hattı (yarışma DIŞI korpus)

```
split_trainable.py  data/raw-classic → trainable.jsonl / excluded.jsonl
   ▼
build_silver prepare        → batch.jsonl (+ labeler/verifier system prompt)
   ▼  (repo DIŞI: öneri üretimi — şartname §5.10, harici model bağımlılık olamaz)
build_silver prepare-verify → verify_in.jsonl
   ▼
run_silver_verifier.py      yerel qwen2.5:7b-instruct, üçüncü oy
   ▼
build_silver merge          → silver.jsonl / queue.jsonl / rejected.jsonl
   ▼
resolve_queue.py            kural KESİN olanı çözer, olmayanı kuyrukta bırakır
   ▼
build_silver score          gold varsa insanla örtüşmeyi ölç
```

---

## 4. Gold hattı — adım adım

### Sözleşme: inceleme CSV'si

12 sütun, sıra bağlayıcı (`to_review_csv.COLUMNS` + sonradan eklenen `protokol`):

```
doc_id ; bank ; field ; model_value ; model_conf ; confidence_source ;
disagreement ; snippet ; gold_value ; verdict ; note ; protokol
```

Biçim: ayırıcı `;`, kodlama `utf-8-sig` (BOM), satır sonu `\r\n`. Bu üç sabit
YALNIZ `to_review_csv.py`'de tanımlıdır; beş betik oradan import eder. Tek
istisna `onarim_recetesi`'nin `_oneriler.csv`'si — `;` ama BOM'suz `utf-8`.

**Anotatör yalnız `gold_value`, `verdict`, `note` sütunlarına dokunur.** Diğer
sekizi üreteç sütunudur; taşıma araçları (`xlsx_to_review_csv`,
`protokol_yukselt`) bunlara hiç dokunmaz.

### Adım 0 — `preannotate.py`

- **Girdi:** `data/raw/<banka>/**/*.txt` + `<dosya>.txt.meta.json`
- **Çıktı:** `data/gold/preannotations.json`
- Kural katmanı ve (varsa) LLM, **12 alanın TAMAMI** için ayrı ayrı koşturulur.
  Üretimde `reconcile()` LLM'e yalnız kuralların bulamadığını sorar; burada
  bilerek ikisi de tam koşar, çünkü **iki katmanın aynı alanda ayrışması hatanın
  en yoğun olduğu yerdir** → `disagreement: true`.
- Şemaya uymayan çıkarım `invalid_fields`'a taşınır ve alan "model üretmedi"
  sayılır.
- Örnekleme katmanlı ve deterministik (`--seed 42`), nadir alanlar korunur.

### Adım 1 — `to_review_csv.py`

- **Girdi:** `data/gold/preannotations.json`
- **Çıktı:** `round*.csv` + `belgeler/<doc_id>.txt` + `_plan.json` + `_atama.md`
- İki kaldıraç: (1) boş `verdict` = "model doğru" [v1], (2) **kova sıralaması**:

| Kova | İçerik | Neden |
|---|---|---|
| 0 | anlaşmazlık (kural ≠ LLM) | etiket başına en çok bilgi |
| 1 | güven ∈ [0,50 – 0,90) | |
| 2 | güven < 0,50 **+ şema dışı satırlar** | |
| 3 | güven ≥ 0,90 | toplu onaylanabilir |
| 4 | modelin **bulamadığı** alanlar | recall kontrolü, `absent_fields` |

  Sıralama anahtarı `(_bucket, doc_id, _field_order)`. Zaman biterse kesilen yer
  kova 3–4'ün kuyruğudur; oradaki kayıp en ucuzudur.
- **Kova 4 olmadan `absent_fields` boş kalır ve precision tanımsızlaşır.** Ama
  tam kapsama pahalıdır, o yüzden yalnız `--absent-docs` (varsayılan **100**)
  belgede üretilir: 250 belgede precision + halüsinasyon, 100 belgede AYRICA
  recall ölçülebilir.
- `belgeler/<doc_id>.txt` **aynı `--out-dir` altına** yazılır. İkisi ayrıldığı
  anda paket sessizce sakatlanır (bkz. bölüm 6, `belge_metni_denetimi`).

### Adım 2 — insan

Anotatör CSV'yi Excel/Numbers ile doldurur, `.xlsx` gönderir →
`xlsx_to_review_csv.py` **yalnız kararları** `(doc_id, field)` anahtarıyla geri
taşır. Doğrudan "CSV olarak kaydet" üç sessiz bozulma üretir ve üçü de ölçülmüş:
`model_conf` `0.70 → 0.7`; ayırıcı `;` → `,` ve kodlama CP1254'e döner; satır
sırası kalıcı kayar — sonuncusu Fleiss κ'yı sessizce bozar.

### Adım 3 — `lint_review_csv.py`

12 kontrol kuralı; şiddet `HATA` (exit 1) / `UYARI` (exit 0). Öne çıkanlar:

- Dosya ilk satırında `;` yoksa → elektronik tablo sayfa adı yazmış olabilir,
  tüm karar sütunları görünmez olur.
- `doc_id` slug'a uymuyor (Excel `--` → em-dash `—` çeviriyor; kalibrasyon A'da
  **2 satırda** oldu). `build_gold` bu satırı sessizce ATLAR.
- `verdict=absent` + dolu `gold_value` → yazılan değer atılır, model
  halüsinasyon sayılır.
- `fix` + boş `gold_value`; `fix` + `gold_value == model_value`.
- Tek değerli alana **çoklu değer** (`looks_like_range`).
- `unclear` oranı > %5 → kılavuz eksik olabilir.
- `--eksiksiz`: v2 dosyalarında karar verilmemiş satırları **HATA** yapar
  (derleme öncesi kapsama kapısı). Dosya başına **tek** bulgu üretir — 260
  özdeş satır gerçek hataları görünmez yapardı.

### Adım 4 — `build_gold.py`

- **Girdi:** `preannotations.json` (model değeri **her zaman güncel
  ön-anotasyondan** okunur) + doldurulmuş CSV'ler
- **Çıktı:** `gold.v1.json` + `.sha256`, `excluded.json`, `build_report.md`

**verdict → gold eşlemesi:**

| verdict | `gold_value` | model üretti mi | Sonuç |
|---|---|---|---|
| boş | boş | — | **v1:** `ok` gibi · **v2:** `skipped`, gold'a GİRMEZ |
| boş | dolu | — | `fix` varsayılır |
| `ok` | — | evet | → `fields` |
| `ok` | — | hayır | → `absent_fields` ("kontrol ettim, yok") |
| `fix` | dolu | — | `parse_gold_value` → `fields` |
| `fix` | boş | — | **BuildError** |
| `absent` | — | — | → `absent_fields`; yazılan değer atılır; model ürettiyse FP |
| `unclear` | — | — | → `unclear_fields`, metrik DIŞI |

`campaign_type = absent` ⇒ belge kampanya sayılmaz, `excluded.json`'a düşer.

**Çift anotasyon çelişkisi** (`_merge_decisions`): herhangi biri `unclear` ise
veya karar türleri ayrışıyorsa → `unclear_fields` + `needs_adjudication: true`.
Değerler ayrışıyorsa yine `unclear`. **Çelişki gizlenmez, otomatik de
çözülmez** (CLAUDE.md HARD RULE #4).

### Adım 5 — `report_iaa.py`

İki ayrı uyum, iki ayrı soru:

1. **Karar uyumu** — 2 anotatör → Cohen, >2 → Fleiss. Kılavuzun net olup
   olmadığını ölçer.
2. **Değer uyumu** — her zaman Krippendorff α; sayısal alanlarda (`NUMERIC_FIELDS`,
   7 alan) **`ratio` ölçeği**. `%1,89` yerine `%1,90` yazanı "tamamen
   anlaşmazlık" saymak κ'yı gerçekte olduğundan kötü gösterir. Aralıklar orta
   noktasıyla temsil edilir.

Önceden ilan edilmiş eşik (`eval/iaa.py`, ANNOTATION_GUIDE §7):
**κ ≥ 0,80 kabul · 0,67 ≤ κ < 0,80 notla kabul · κ < 0,67 zorunlu hakemlik.**
Betik **exit 0 döner** — κ bir CI kapısı değil, raporlanan bir karardır.

### Yardımcı araçlar (hattın etrafında)

| Araç | Ne zaman gerekir |
|---|---|
| `kappa_durum.py` | "κ ölçmeye daha ne kadar var?" — κ için iki koşul gerekir ve ikisi de sessizce bozulur: aynı satır kümesi + o satırlarda açık karar |
| `onanotasyon_tazele.py` | Çıkarıcı düzeldi, CSV bayat. **Anotasyondan ÖNCE** koşulmalı; anote edilmiş dosyayı reddeder |
| `protokol_yukselt.py` | v1 → v2 geçişi; boş hücreler taşınmaz |
| `kalibrasyon_hakemlik.py` | Kılavuz kaynaklı 7 kuralı uygular — **anotatör kararını değiştiren tek betik** |
| `onarim_recetesi.py` | Lint hatalarını kalıba indirir; **CSV'ye YAZMAZ**, ayrı öneri dosyası üretir |
| `calisma_listesi.py` | Anotatörün kendi ölçülmüş hata kalıpları (hakemlik ÖNCESİ yedekten) |
| `split_gold.py` | Anotasyon bitince BİR KEZ: dev/test böl, testi dondur |

---

## 5. Ölçüm zinciri

### 5.1 `run_eval.py` neyi nasıl ölçüyor

12 kanonik alan (`EXTRACTION_FIELDS`): `kar_payi_orani`, `finansman_tutari`,
`vade_ay`, `taksit_sayisi`, `tahsis_ucreti`, `masraf_durumu`, `odul_miktari`,
`indirim_orani`, `alisveris_puani`, `kampanya_suresi`, `kampanya_kosullari`,
`hedef_kitle`.

**Karar tablosu (`score_document`) — bu dosyanın çekirdeği:**

| gold | tahmin | sonuç |
|---|---|---|
| değer var, eşleşiyor | var | TP |
| değer var, eşleşmiyor | var | **FP + FN** |
| değer var | yok | FN |
| `absent_fields` ("YOK") | var | FP — **halüsinasyon** |
| `absent_fields` | yok | TN — doğru çekimserlik |
| `unclear_fields` | herhangi | metrik DIŞI |
| gold karar vermemiş | herhangi | metrik DIŞI (`skipped`) |

Son satır disiplinin kendisi: **bilmediğimizi lehimize sayamayız.** Yanlış değer
hem FP hem FN çünkü model hem olmayan bir şeyi iddia etti hem doğruyu kaçırdı.

**Üç hata sınıfı ayrı ölçülür, PAYDALARI AYRIDIR** (mentör talebi):

- `kacirma` = `fn − fp_wrong` → kapsama sorunu (regex/prompt eksik)
- `yanlis_cikarim` = `fp_wrong` → **grounding** sorunu; kanun maddesindeki
  "1 yıl"ı vade sanmak buraya girer, halüsinasyon DEĞİLDİR
- `halusinasyon` = `fp_hallucinated` → zemin sorunu, en tehlikelisi

Çıkarım hatası oranının paydası `support` (gold'da değer olan kararlar),
halüsinasyon oranının paydası `absent_decisions`. Aynı paydaya bölünürlerse
karşılaştırılamaz hale gelirler. Gold'da hiç `absent` kararı yoksa halüsinasyon
oranı **`None`** döner — `0,0` yazmak yalan olurdu ("hiç uydurmadık" değil,
"ölçemedik").

**Mikro + makro birlikte:** mikro alanları gözlem sayısına göre ağırlıklar,
`vade_ay` tabloyu domine eder; makro seyrek alanları görünür kılar.

Makro'nun kendi kör noktası da ölçülmüş ve kapatılmış: süzgeç `support > 0`
olduğu için, gold'da desteği olmayan ama model yalnız uydurma üreten alan
cezasız kalır. **gold.v2'de fiilen gerçekleşti: `tahsis_ucreti` desteksiz, tek
çıktısı bir halüsinasyon. Süzgeçli makro 0,409, alan dâhil edilseydi 0,375 —
+0,034 lehimize, sessizce.** Süzgeç kaldırılmadı; yanına
`macro_f1_uydurma_dahil` eklendi.

**Kalem düzeyi ikinci ölçüt:** liste alanlarında (`kampanya_kosullari`,
`hedef_kitle`) küme eşitliği ikili bir ölçüttür — beş koşuldan dördü doğru olsa
bile TP=0, FP=1, FN=1. **Ölçüldü: `kampanya_kosullari` her iki eşleştiricide de
tam olarak 0,000; bu alan manşet mikro-F1'in ~%28'ini oluşturuyor.** Kalem
ölçütü (jeton-Jaccard ≥ **0,70**, önceden ilan edilmiş) bunu düzeltir ama
raporda **"ölçüm düzelmesi, sistem düzelmesi değil"** diye etiketlenir; ikili
sayı manşet kalır.

Bootstrap: `bootstrap_ci`, örnekleme birimi **BELGE** (küme bootstrap),
`n_resamples=1000`, `seed=42`.

**Çıkış kodları:** 0 · 2 kullanım/veri hatası · **3 konfig ölçülemedi**.

### 5.2 `matchers.py` — bir tahmin ne zaman doğru sayılır

İki mod yan yana raporlanır. Yalnız gevşek raporlamak kredibilite kaybettirir
("toleransı sonuç iyi görünene kadar mı büyüttünüz?"); yalnız katı raporlamak
gerçek olmayan başarısızlık üretir (`1.8900000000000001`). `strict` savunulabilir
alt sınır, `tolerant` üst sınır; **aradaki fark "kaç hata gerçek anlam hatası
değil, biçim hatası" sorusunun ölçüsüdür.**

| | strict | tolerant |
|---|---|---|
| Sayı toleransı | yalnız float gürültüsü (`abs_tol=1e-9`) | **%1 göreli** (`rel_tol=0.01`) |
| Liste sırası | önemli | önemsiz (küme) |
| Serbest metin | birebir | TR katlama + son noktalama atılır |
| Aralık ↔ düz sayı | **hata** | sayı aralığın içindeyse **kısmi kredi** |

**Tolerant modda bile BİREBİR eşleşmesi zorunlu olanlar** — bunlar büyüklük
değil KATEGORİdir:

| Bileşen | Neden |
|---|---|
| `currency` | 500 TRY ≠ 500 USD |
| `has_fee` | "masrafsız" ile "500 TL masraf" zıt bilgi |
| `kind` (alışveriş puanı) | %5 oran ≠ 5 puan |
| `kampanya_suresi` | ISO-8601 kanonik; "yakın tarih" diye bir şey yok |

Ek yapısal kurallar: karşılaştırma **yapıya iner** (aralık `min`/`max` alan
alan), **`bool` önce elenir** (`True == 1` tuzağı), para/masraf/puan
sözlüklerinde **anahtar kümesi** de eşit olmalı. Tek gövde (`_deep_equal`),
davranış farkı yalnız bayraklarda — iki kopya zamanla ayrışırsa "strict vs
tolerant farkı" ölçümü anlamını yitirir.

`%1` gerekçesi: kâr payı oranlarında anlamlı en küçük fark 0,01 puandır
(%1,89 → %1,90, ~%0,5); %1 bunu yutar ama %1,89 ↔ %2,49 farkını (~%32) asla
yutmaz.

Bilinmeyen eşleştirici adı → `MatcherError`; **sessiz varsayılana düşmek yok**
(yanlış eşleştiriciyle üretilmiş metrik, hiç metrik olmamasından kötüdür).

### 5.3 `ablation.py` — hangi konfigürasyonlar

Varsayılan kollar: `kural`, `llm`, `hibrit`, `hibrit-verify`
(+ kayıtlı: `orkestra`, `orkestra-hakemsiz`).

| Konfig | Ne koşar |
|---|---|
| `kural` | yalnız `extract_all` — **resmî varsayılan (K-2)** |
| `llm` | yalnız LLM (kısıtlı decoding) |
| `hibrit` | kural birincil + eksikleri LLM doldurur (API canlı ucunun yolu) |
| `hibrit-verify` | hibrit + düşük güvenli KURAL alanlarını LLM doğrular (eşik **0,75**) |
| `orkestra` | kural + çok-ajanlı LLM + kanıt kapısı + hakem |
| `orkestra-hakemsiz` | aynısı, hakem kapalı (hakemin katkısını yalıtmak için) |

- **Eşleşmiş çift = (belge, alan) kararı.** McNemar yalnız UYUMSUZ çiftlere
  bakar; iki kol aynı kararı verdiğinde test bilgi almaz ve almaması doğrudur.
- Yöntem seçimi: `b + c < 25` → **tam binom**, değilse **süreklilik düzeltmeli
  χ²**. Gerekçe ölçülmüş: `b=8, c=0` → tam **0,0078**, χ² **0,0133**
  (%70 göreli hata); `b=3, c=1` → tam **0,6250**, χ² **0,6171**.
- Ayrıca **eşleşmiş bootstrap fark GA'sı**: aynı yeniden örneklenmiş belge
  kümesi iki kola da verilir. İki bağımsız GA'nın örtüşmesine bakmak yaygın bir
  hatadır.
- `cache_predictions`: `--matcher both` verildiğinde her kol belge başına bir kez
  sorulur. Gerekçe **ölçüm kusuru** (asıl sebep) + maliyet: strict/tolerant
  farkı tanım gereği yalnız eşleştiricinin katılığından gelmelidir; kol iki kez
  sorulursa örnekleme gürültüsü o farka sızar. Maliyet ölçülmüş: kol başına 20
  belge ≈ **12 dk** (Ollama + Qwen2.5-7B, Apple M5); üç LLM kolu × iki
  eşleştirici ≈ **70 dk**, önbellekle **~35 dk**.

### 5.4 `predictors.py` — LLM kapalıyken ne yapar

LLM'e dokunan tüm konfigler (`llm`, `hibrit`, `hibrit-verify`, `orkestra`,
`orkestra-hakemsiz`) `available=False` döner ve çağıranlar bunları **ATLAR**.
Tabloya `ÖLÇÜLMEDİ` yazılır.

> "hibrit = kural" satırı BASILMAZ: bu satır teknik olarak doğru ama iletişim
> olarak yalandır — okuyucu hibridin ölçüldüğünü sanır.

`unavailable_reason` nedenini Türkçe söyler ve nasıl ölçüleceğini yazar
(`LLM_BACKEND=vllm|ollama`, tercihen `LLM_STRICT=1`). `kural` kolu LLM'e hiç
dokunmadığı için offline'da da tam ölçülür.

`llm_summary` bir **property**'dir, saklanan sözlük değil: sayaçlar koşum
sırasında arttığı için erken okunan künye rapora her zaman `calls: 0` yazardı —
yani "hibrit sessizce kural-only mi koştu?" sorusu 60 çağrı yapılmış olsa bile
cevapsız kalırdı.

### 5.5 Ölçümün diske düşen kanıtı

`eval/reports/<UTC ts>/` altına beş dosya:

| Dosya | İçerik |
|---|---|
| `metrics.json` | makine-okur her şey (CI kapısı bunu okur) |
| `report.md` | insan-okur tablo |
| `per_field.csv` | 17 sütun, `scope ∈ {all, hard}` — **`doc_id` YOK** |
| `decisions.csv` | `matcher; doc_id; field; correct` — eşleştirilmiş testin girdisi |
| `env.json` | git sha + git dirty + **gold dosyasının sha256'sı** + Python + seed + eşleştirici |

`decisions.csv` neden ayrı: `per_field.csv` alan×kapsam düzeyinde TOPLAR ve
`doc_id`'yi geri döndürülemez biçimde yitirir; McNemar'ın sorusu ise "AYNI
belgenin AYNI alanında A doğru, B yanlış mıydı?"dır. `matcher` sütunu ŞART —
strict ve tolerant iki ayrı geçiştir. `correct` **0/1 int** yazılır çünkü
`bool("False") == True`.

`env.json`'daki gold sha256 şunu sağlar: gold sessizce değişirse eski
karşılaştırmaların geçersiz olduğu **anlaşılır**.

---

## 6. Kalite kapıları — hangi kusurdan doğdu

Her kapının docstring'i onu doğuran **gerçek** vakayı yazıyor. Aynen:

| Kapı | Neyi korur | Doğduğu ölçülmüş kusur |
|---|---|---|
| `jargon_lint` | Kullanıcıya/modele dönük metinde yasak terim | Kör tarama **494 bulgu** verdi: docs 238 · tests 115 · src 89 · scripts 47 · eval 4 · **web 1 ← tek gerçek ihlal**. "494 bulgu basan bir lint kimsenin koşmadığı bir linttir" → kapsam daraltıldı |
| `css_sinif_denetimi` | `className`'de geçen sınıfın CSS tanımı | Yeniden tasarımdan önce **11 sınıfın CSS karşılığı hiç yazılmamıştı** (`summary-box`, `fairness-item`, `jury-dot`, `fold-open`, `headline-bad` …); **5 bileşen** stilsiz render oluyordu ve hiçbir test yakalamıyordu |
| `kontrast_kontrol` | WCAG AA kontrast, iki temada | Palet iki temaya çıkınca göz kararı yetmez; açık temada okunan gri koyu temada AA altına düşer. Eşik **4,5:1**, büyük metin için gevşetme **yapılmaz** (token sonradan küçük metinde kullanılabilir) |
| `belge_metni_denetimi` | Paketin anote EDİLEBİLİR olması | `round2_zor_vaka.csv` geçici dizine üretildi, yalnız CSV taşındı: **CSV 73 belge / 949 satır diyor, anotatör 41 belge görüyor.** Boş `.txt` yazmak yasak — boş belge `absent` kararı ürettirir ve modelin doğru çıkarımını YANLIŞ sayar |
| `lint_review_csv` | Satır biçimi, anotasyon anında | Kalibrasyon A'nın ilk turunda **9 satır sessizce bozuldu**: `"2026-07-01 - 2026-07-31"` → başlangıç; aralığın üst sınırı düştü; `"85 / 15"` paylaşım oranı kâr payı sanıldı. Değer geçerli ama YANLIŞ olduğu için `build_gold`'da görünmez |
| `check_demo_db` | DB'nin korpusla güncelliği | DB **31 Temmuz**'da kuruldu (**849 belge**), korpus **3 Ağustos**'ta **1761**'e çıktı. Bir hafta boyunca chatbot/dashboard/RAG korpusun **%48'ini** hiç görmedi, fıkhî terim yoğunluğu en yüksek bölümün tamamı erişilemez kaldı — **hiçbir uyarı çıkmadı, hiçbir test kırılmadı**. Ölçüt belge SAYISI; `mtime` değil (checkout sonrası yeniden yazılır) |
| `eval_injection` | Prompt-injection, özellikle **dolaylı** | Tek ölçülmemiş güvenlik boyutuydu. Mevcut set (30 soru) hepsi iyi niyetli. Asıl yüzey: üçüncü taraf banka sayfaları RAG bağlamına giriyor. Ölçülen mimari iddia — kapılar modelin talimata uymasına bağlı değil (regex post-filtre) |
| `eval/properties` | Değişmez ihlali, **etiketsiz** veride | Elle bulunan **beş** hatanın **dördü** bu değişmezlerle otomatik yakalanırdı. Ayrıca exit kodu 2 sonradan eklendi: eski kod belge bulamayınca uyarı basıp **0 döndürüyordu**, yanlış `--raw-dir` yazılmış CI adımı YEŞİL veriyordu |
| `merge_gold_v2` | Gold'a giren her kaydın kanıtlı olması | Üç kapı: şema · kanıt (`field_spans` alıntısı metinde birebir) · ayrıklık. "Kısmen geçerli gold diye bir şey yoktur" |
| `split_gold --verify` | Test bölmesinin donmuş kalması | **Yedi model kolu** aynı gold üzerinde kıyaslanacak; kol seçimi test setine bakılarak yapılırsa **seçim yanlılığı** oluşur |

`eval/properties.py` — P1–P4 tam tanımı:

| Değişmez | Test | Yakaladığı gerçek hata |
|---|---|---|
| **P1** span bütünlüğü | Her alanın offset'i kendi `raw_value`'sunu göstermeli | Vurgulanan yerin raporlanan değerle uyuşmaması — açıklanabilirlik iddiası buna dayanıyor |
| **P2** ortografik değişmezlik | `tr_upper(text)` çıkarılan değerleri değiştirmemeli | **H1:** `'TAŞIT'.lower()` → sınıf kaybı; "ÜCRETSİZ" `has_fee`'yi ters çeviriyordu |
| **P3** alakasız ekleme | 3 nötr cümle tek tek eklenince mevcut alanlar değişmemeli | "31 Aralık"tan uydurulan **hayali 31 TL ücret** |
| **P4** cümle sırası | Cümleleri ters çevirmek çelişki KÜMESİNİ değiştirmemeli | **H2:** "masrafsız … tahsis 500 TL" doğru sırada yakalanıyor, ters sırada kaçırılıyordu |

---

## 7. Önemli kararlar ve gerekçeleri

Ölçülmüş sayılar kaynaktaki biçimiyle.

### K-1 · `absent_fields` şemaya girdi — precision'ın tanımı

v0'da bir alanın `fields`'ta olmaması iki farklı şey demekti: (a) anotatör
kontrol etti, yok → model üretirse FP; (b) anotatör hiç bakmadı → bilinmez.
**Bu ikisi ayrılamadığında precision tanımsızdır ve halüsinasyon oranı
ÖLÇÜLEMEZ.** Projenin merkezindeki "değer uydurmuyoruz" iddiası tam olarak bu
sayıyla ayakta durur.

### K-2 · Resmî metrik kolu `hibrit` değil `kural` (2026-08-07)

Eski gerekçe geriye doğru işliyordu ("dashboard `reconcile()` çağırıyor, öyleyse
resmî metrik de hibrit olsun") — ölçüm kolu, teslim kolunu değiştirmek yerine
ona uyduruluyordu. Ölçüm hibridin aleyhine:

```
n=20 (gold.v1, strict)   kural 0,677 · orkestra 0,672 · hibrit 0,575
halüsinasyon             kural 0,096 · orkestra 0,114 · hibrit 0,163
```

Hibridin kaybı geri çağırma değil **precision** kaybı ve mekanizma alan
kırılımında görünür: `hedef_kitle`'de doğru sayısı **4 → 4** (hiç artmıyor),
buna karşılık uydurma **2 → 6**. LLM'in yazma yetkisi yeni bilgi getirmiyor,
gold'un "YOK" dediği yerleri dolduruyor.

Ölçüm kapısı ilan edilmişti: n=48'de orkestra kolu kural kolunu GA'lar örtüşmeden
geçerse sabit değişecekti. **Geçemedi**, kural kalıyor.

**Kapsam uyarısı (kodda yazılı):** bu sabit tek başına teslim yolunu
DEĞİŞTİRMEZ. `src/api/main.py` canlı çıkarım ucu hâlâ `build_campaign(..., llm=llm)`
çağırıyor, yani LLM açıkken hibrit koşuyor.

### K-3 · Anotasyon protokolü v1 → v2 (boş hücrenin anlamı)

v1'de boş hücre "model doğru" demekti; darboğaz insan zamanı olduğu için
tasarlanmıştı. Bedeli ölçüldü: **aynı belgeler kör protokolde 0,536, çapalı
protokolde 0,677 — 0,141'lik fark model başarısı değil, protokol artefaktıydı.**
v2'de boş = karar verilmedi; gold'a girmez, κ'ya girmez.

Bu sayı üç ayrı dosyada tekrarlanıyor (`gold_schema`, `protokol_yukselt`,
`onarim_recetesi`) ve `predictors.py`'deki `kural 0,677` ile **aynı koşumdur** —
yani resmî kural sayısı çapalı gold.v1 üzerinde üretilmiştir (bkz. bölüm 8).

### K-4 · Bootstrap birimi BELGE, alan değil

Bir belgeden 12 alan çıkar ve bu 12 gözlem bağımsız DEĞİLDİR: aynı metin, aynı
banka şablonu, aynı imla, aynı hata kaynağı. Alan düzeyinde örneklemek güven
aralığını **yapay olarak daraltır**.

> Bu bir tercih değil, İSTATİSTİKSEL BİR HATADIR: gerçekte anlamsız olan
> farkları anlamlı gösterir.

Aynı ilke `mcnemar_report.py`'de de uygulanır.

### K-5 · Eval katmanı sıfır üçüncü parti bağımlılık

Bootstrap ve McNemar elle yazıldı (`math.erfc`, `math.comb` stdlib'de). Gerekçe
on-prem iddiasının parçası: değerlendirme hattı, internet erişimi ve paket
kurulumu olmayan bir kurum ağında birebir tekrar üretilebilir.

### K-6 · Çerçeve ayıklamada finansal sinyal koruması

Yalnız "n-gram 3 belgede tekrar ediyorsa çerçevedir" kuralı gerçek kampanya
gövdesini de yiyordu. Kök neden eşiğin sayısı değil **kampanya şablonu**: bir
banka aynı kampanyayı 3-6 varyantla yayınlıyor.

Ölçüm (`data/raw`, 1684 belge): atılan sözcüklerin **%25,4'ü** belge frekansı
bankanın belgelerinin **%10'unun ALTINDA** olan n-gramlardan geliyordu. Site
kromu ise **%50-100** bandında toplanıyor (Akbank menüsü **63/64**, Yapı Kredi
çerez bandı **106/106**, QNB menüsü **80/80**).

`SIGNAL_MIN_FRACTION = 0.25` eşik taraması:

| oran | içerik kaybeden belge (raw / classic) | çerçeve sızıntısı (raw) |
|---|---|---|
| yok | 244 / 26 | 61 |
| **0,25** | **1 / 0** | **70** |
| 0,50 | 1 / 0 | 148 |
| 1,00 | 0 / 0 | 148 |

Nihai sonuç: içerik kaybeden belge `data/raw`da **244 → 1**, `data/raw-classic`ta
**26 → 0**. Atılan sözcük oranı `raw`da **%49,0 → %43,3**, `raw-classic`ta
**%71,9 → %69,4**. Çerçeve sızıntısı `raw-classic`ta **11 → 11**, `raw`da
**61 → 70**.

Ayrıca `core_text` artık **noktalamayı koruyor** — eskiden `%2,05` → `2 05`,
`1.500,00 TL` → `1 500 00 TL` oluyordu, yani çekirdekte oran işareti ve TR sayı
biçimi hiç görünmüyordu.

### K-7 · Kararı ÇEKİRDEK metin üzerinden ver

"kişisel verilerin korunması" + "çerez politikası" TAM metinde **9 DenizBank +
30 Yapı Kredi** belgesinde geçiyor — hepsi altbilgiden. Tam metinde arayan bir
kural **39 GERÇEK kampanya sayfasını** "KVKK sayfası" sanıp elerdi. Çekirdekte
hiçbirinde geçmiyor.

Aynı desen `resolve_queue.py`'de tekrarlanıyor: karar imzası tam metin değil
`doc_id + BAŞLIK + evidence` — "Ek Hesap" çoğu bankanın menüsünde geçiyor.

### K-8 · Çapraz kontrolde SIKI eşleştirme (K1–K5 kapıları)

Gevşek desenlerin maliyeti iki kez ölçüldü: bir sezgisel **101 belgenin
87'sinde** yanlış pozitif üretti; zor-vaka taramasının ilk desen kümesi
`celiskili`yi **476 belgede** "buldu" (gerçek: **13**).

| Kapı | Kapattığı gerçek yanlış pozitif |
|---|---|
| K1 yakınlık (±60 krk) | Albaraka'nın "masrafsız bir bankacılık sunuyoruz" cümlesi "finansal ihtiyaçlarına"daki `ihtiyaç`a takılıp İhtiyaç Finansmanı iddiası sayılıyordu |
| K2 hizmet masrafsızlığı | `masrafsız (bir) bankacılık` havale/EFT/FAST'i anlatır, tahsis ücretiyle ilgisi yok |
| K3 araya kalem girmesin | Türkiye Finans'ın **"Taşıt Rehin Tesis Ücreti 350,92 TL"** kalemi tahsis ücreti sanılıyordu |
| K4 makullük (%1,0 / 25.000 TL) | Rapor **"Türkiye Finans %4,09 tahsis ücreti ilan ediyor"** diyordu — 4,09 bir KÂR PAYI ORANI. Vakıf'ta **100.000 TL** (finansman tutarı kolonu) ücret sanılıyordu |
| K5 aynı belge yasağı | Aksi hâlde kampanya kendi kanıtı olur |

**Bu betiğin İDDİA ETMEDİĞİ şey:** tarifede ücret olması kendiliğinden çelişki
değildir. **33 ilan edilmiş kayıttan 30'u tam olarak %0,5** ve bu değer beş
bankanın hepsinde geçiyor — BDDK'nın konut finansmanı üst sınırı sektörde
fiilen tek fiyat. Ayırt edici olan **kapsam**: muafiyet bir koşula bağlı mı?
`kosullu_muafiyet` bir kusur değil, **ürünün kendisidir** — kıyas tablosunda
"masrafsız" yazmak yanıltıcıdır, doğrusu "yeni müşteriye masrafsız, aksi hâlde
%0,5".

### K-9 · `data/demo.db` git'e girmez, betik girer (2026-07-31)

```
demo.db                9.46 MB  (VACUUM sonrası da 9.46 MB)
gzip -9                0.97 MB
deponun tüm pack'i    12.28 MB
kurulum süresi         3.3 s
kaynak .txt belgeler    849 — HEPSİ git'te izleniyor
iki koşu bayt-bayt aynı (sha256 eşit) — çıktı deterministik
```

Gerekçe: (1) türetilmiş artefakt — türevi kaynağının yanına koymak iki doğruluk
kaynağı yaratır, biri güncellenip diğeri unutulduğunda jüri eski DB'yi görür;
(2) SQLite ikilidir, delta sıkışmaz — her yeniden kurulum ~1 MB'lık YENİ nesne
ve git geçmişi değişmezdir; kazanç yalnız 3,3 s.

### K-10 · Yeniden HASAT değil yeniden ÇIKARIM

2026-08-04'te üç sessiz hata düzeltildi ama `data/raw` altındaki **1684 `.txt`**
eski mantıkla üretilmişti. Ölçüm: **153 belge (%9)** saf çerez politikası +
navigasyon menüsüydü — **Emlak'ta %34, Vakıf'ta %24**.

Yeniden hasat yerine yeniden çıkarım, çünkü: siteye gidilmez (10 bankaya 1570
istek atılmaz); **dosya adları korunur** — yeniden hasat `doc_id` eşleşmesini
bozar (ölçüldü: bir turda **32 belgenin 10'u** geçersiz kaldı).

Kurtarılamayan belge **silinmez**, `content_status: "kabuk"` ile işaretlenir.
Tespit yöntemi uzunluk eşiği DEĞİL: iki farklı Vakıf ürün sayfası aynı **2551
karakteri** üretti — eşiği rahatça geçen ama içerik taşımayan bir kabuk.

### K-11 · Yerel denetleyici daha zayıf, yine de geçerli üçüncü oy

`qwen2.5:7b-instruct` (Apache-2.0) öneriyi üreten modelden küçük. Uzlaşmanın
istediği şey güç değil **bağımsızlık**: model ailesi farklı, öneri oturumunun
bağlamını görmüyor, sınıf toplamlarını bilmiyor. Zayıflık **yanlış yönde
birikmiyor** — `consensus.py` ayrışmayı insan kuyruğuna gönderir, veri setine
değil; yani zayıf denetleyicinin hatası "gümüş sayısı düşük kalır" demektir,
"veri seti kirlenir" demez.

Doğrudan sebep: harici denetleyici oturumu **on bir kez** `529 Overloaded` ile
düştü ve hatalar iş sırasında değil oturum **başlangıcında** oluyordu — parti
küçültmek çare değil. Asıl sebep şartname §5.10: teslim edilen sistem harici bir
asistana bağlı olamaz.

### K-12 · BERTurk kabul kapısı önceden ilan edildi

BERTurk projeye ancak gold makro-F1'inin **%95 bootstrap GA'sının ALT SINIRI**
kural çizgisinin **0,762** değerini aşarsa alınır. Aralık 0,762'yi içeriyorsa
sonuç "ayırt edilemez"dir ve varsayılan `RuleHintClassifier` kalır. Betik bu
kararı kendi basar ve künyeye yazar.

Lisans kapısı özyinelemeli: `base_model` zinciri **köke kadar** takip edilir,
izinli lisanslar `{mit, apache-2.0}` — türev, kökünden serbest olamaz.

### K-13 · Test bölmesi dev'den BÜYÜK (%60 / %40)

Bu projede test seti eğitim için kullanılmıyor (kural katmanı gold'a bakılmadan
yazıldı). Dev'e yalnız kol seçimi ve kalibratör öğrenmek için ihtiyaç var; asıl
istatistiksel güç nihai sayıda gerekiyor. **Büyük test seti = dar güven
aralığı.**

### K-14 · Çekimserlik FN sayılır, FP sayılmaz

Çekimserliği görmezden gelmek modeli **ödüllendirir**: zor belgelerde susup
kolaylarda konuşan bir model yüksek precision alır. Bu yüzden susmak recall'u
düşürür, precision'ı şişirmez. `--cekimser-esigi` yükseltmek makro-F1'i
**düşürür**.

### K-15 · Öneri üreten araçlar CSV'ye YAZMAZ

`onarim_recetesi`, `crosscheck_rates`, `crosscheck_fees`, `calisma_listesi` —
hiçbiri `verdict`/`gold_value` hücresine dokunmaz. Gerekçe aynı ve ölçülmüş:
gold modelin ölçüldüğü referanstır; bir betiğin onu doldurması değerlendirmeyi
kendi kendini doğrulayan bir döngüye sokar (K-3'teki 0,141'lik artefakt).

---

## 8. Tuzaklar

### 8.1 Tekrar üretilemeyen / elle koşulan adımlar

| Ne | Neden |
|---|---|
| **`to_review_csv.py` yeniden koşulamaz** | `has_annotations()` dolu dosyayı korur ve yeniden üretim satır SIRASINI değiştirebilir. Fleiss κ dört dosyanın **birebir aynı satır kümesini** şart koşar. Sıfırdan üretim geri alınamaz biçimde **79 satırlık** insan kararını silebilir. Protokol/tazeleme işleri bu yüzden ayrı araçlarla, satır kümesine dokunmadan yapılır |
| **Gümüş hattının 2. adımı repo DIŞI** | Öneri üretimi harici bir asistan oturumunda yapılıyor (şartname §5.10 gereği repoya giremez). `proposals.jsonl` elle üretilir; hat bu dosya olmadan koşmaz |
| **`split_gold --record-access`** | Test bölmesi elle, gerekçeyle açılır. >1 erişimde uyarı basar: "tek seferlik ölçüm iddiası artık geçersiz" |
| **`build_summaries`** | LLM açık olmalı (kod 3). Tam korpus **~1400 belge × ~6 sn ≈ 2,5 saat**; `--devam` ve `--parca 25` olmadan tek kesinti tüm işi kaybettirir |
| **`offline_proof.sh`** | Docker + daemon şart; yoksa **kod 2** ("kanıt ÜRETİLEMEDİ") — asla "başarılı" demez |
| **`train_berturk`** | Taban ağırlığın bir kereye mahsus indirilmesi tek çevrimiçi adım |
| **`tcmb_*` betikleri** | argparse yok, yol sabit; `tcmb_sozluk_ayristir` `bs4` ister ve sayfa yapısı değişirse `SystemExit` |

### 8.2 Bayat kalabilecek çıktılar

- **`data/demo.db`** — git'te izlenmiyor, her ortamda yeniden kurulmalı. `check_demo_db`
  tam bu yüzden var. Docstring'ler korpusu **849 → 1761** olarak anıyor;
  bugün `data/raw` altında **1774 `.txt`** var, yani o rakamlar da anlık
  görüntü. Mevcut DB'nin güncel olup olmadığı **belirsiz** (bu haritayı
  üretirken DB sorgulanmadı); karar `check_demo_db`'ye aittir.
- **`data/gold/preannotations*.json`** — çıkarıcı düzeldikçe bayatlar. Ölçülen
  bayatlık: round0 **16/260 (%6)** · round1_A **22/600 (%3,7)** · round1_main_C
  **47/483 (%9,7)** · round1_main_D **39/482 (%8,1)** · round2_zor_vaka
  **29/492 (%5,9)**. İkinci maliyet daha sinsi: anotatör satırı `ok` bırakırsa
  gold'a **anotatörün hiç görmediği** güncel değer girer.
- **`docs/rapor/ablasyon.md`** — `ablation_report.py` bu yüzden var; tablo
  `metrics.json`'dan türetilir, elle yazılmaz.
- **Docstring'lerdeki korpus sayıları** genel olarak tarihli anlık görüntüdür:
  `data/raw-classic` için 427 / 618 / 622 / 724 gibi farklı değerler farklı
  betiklerde geçiyor (bugün **724 `.txt`**, `split_report.md` **722** diyor).
  Sayıyı kullanmadan önce ölçümün tarihine bakın.
- **`eval/reports/<ts>/`** birikir (14 koşum dizini + 4 `violations*.jsonl`);
  hangisinin güncel olduğunu yalnız `env.json`'daki `git_sha` söyler.

### 8.3 Sözleşme boşlukları ve çelişkiler

**(1) İki gold hattı ayrık — `field_spans`.** `merge_gold_v2`'nin kanıt kapısı
`field_spans` ister; `gold_schema.GoldRecord` bu anahtarı **tanımlamaz**,
`build_gold` **üretmez**. Doğrulandı: `gold.v2.json` **48/48** kayıtta
`field_spans` var, `gold.v1.json` **0/20**. Yani v1 hattının çıktısı
(`preannotate → CSV → build_gold`) v2 kanıt kapısından her alanda "değer var,
kanıt YOK" ile düşer. İki hat farklıdır ve karıştırılmamalıdır.

**(2) `merge_gold_v2`'nin ayrıklık kapısı bir kez sessizce geçti.** Ölçüldü
(2026-08-08): gold.v2'nin **48/48** kaydında `content_hash == sha256(text)`,
gold.v1'in **0/20**'sinde. Anahtar uzayı ayrıştığı için kapı yapısal olarak her
zaman "kesişim yok" döndürüyordu. Gerçekte iki belge örtüşüyordu — aynı `id`,
**bayt bayt aynı** metin. Sonuç: ölçüm seti **20+48=68** diye raporlandı,
gerçekte **66** tekil belge. Bu, projede **ikinci kez** görülen "anahtar uzayı
ayrıştı, kapı sessizce geçti" kusuru.

**(3) Protokol tespitinde iki farklı yer.** `report_iaa.file_protocols` ve
`build_gold.build` protokolü dosyanın **ilk satırından** okurken,
`lint_review_csv.check_row` ve `resolve_decision` **her satırın kendi** `protokol`
hücresine bakar. Karışık damgalanmış bir dosyada rapor künyesi ile fiili işlem
ayrışabilir.

**(4) Resmî `kural 0,677` sayısı çapalı gold üzerinde üretilmiştir.**
`predictors.py`'deki `n=20 (gold.v1, strict) kural 0,677` ile K-3'teki "çapalı
protokolde 0,677" **aynı koşumdur**. gold.v1 v1 protokolüyle toplandı, yani boş
hücreler örtük onaydır. Kör protokoldeki karşılığı **0,536**. n=48'lik gold.v2
(v2 protokolü) için `eval_o1`'in referansı **mikro-F1 0,387 [0,329–0,442]**,
halüsinasyon **0,101**, kaçırma **21** — yani iki gold arasındaki fark
protokolden de gelir, sadece zorluktan değil. Bu iki sayı yan yana
konulmamalıdır.

**(5) `kampanya_kosullari` ikili ölçütte tam olarak 0,000** ve manşet mikro-F1'in
**~%28'ini** oluşturuyor. Kalem düzeyi sayı bunu düzeltir ama **ölçüm
düzelmesidir, sistem düzelmesi değildir**; ikisi karıştırılırsa jüriye yanlış
bilgi gider.

**(6) `latency_bench` tablosu LLM içermez.** `LLM_BACKEND` boşken `hybrid` ve
`chatbot` yollarında ölçülen süre **boru hattının LLM DIŞI kısmıdır**. Bilinçli
bir ölçümdür (teslim edilen demo tam bu konfigürasyonda koşar) ama "hibrit
gecikmesi" diye 8B model çıkarımını içeren bir sayı sanılmamalıdır. Ayrıca
jüriye gösterilecek sayı `--recursive` ile üretilendir — kökteki 3 sentetik
örnek gerçek banka HTML'inden mertebe olarak küçüktür.

**(7) `eval_rag_terim`'in kapsama sayısı İYİMSER.** Ölçülmüş tokenizasyon
kusuru: `_tokenize('kâr payı') → ['payı']` ('kâr' tamamen düşüyor),
`_tokenize('vekâlet') → ['vek','let']`. `vekâlet` için kök `'vek'` → "vekil",
"vekaleten", hatta "vektör" kanıt sayılır. Şapkalı ünlü kusuru kapatıldı; kalan
kök-parçalılık tireli terimlerden geliyor.

**(8) `boilerplate_audit`'in düzyazı sinyali beklenenden ZAYIF.** 250 belgelik
örneklem / 5302 blok: 0,04 eşiği içerik bloklarının **%90'ını** korurken krom
bloklarının ancak **%18'ini** eliyor. **Karar bu sinyale tek başına
dayandırılamaz.** Aynı betikte `classify_loss`'un `gercek` kovası da bir tarama
sonucudur, karar değil — kova elle okunmalı, karar ölçütü gold'daki P/R/F1.

**(9) Sayı üreten ama kapı OLMAYAN betikler.** `eval_rag_terim` her zaman 0
döner (kasıtlı: "kapsamayan terim bir kusur olabileceği gibi veri boşluğu da
olabilir"). `report_iaa` κ ne olursa olsun 0 döner. `mcnemar_report`'ta
anlamlılık çıkış koduna yansımaz. `train_berturk` kabul kapısını basar ama exit
kodu 0'dır. Bunları CI kapısı sanmayın.

**(10) Yedek dosyaları birikir.** Dört sonek: `.yedek-v1[-N]`,
`.yedek-xlsx-oncesi[N]`, `.yedek-tazeleme[N]`, `.yedek-hakemlik[N]`. Son ikisi
yalnız arşiv değil, **ölçüm kaynağıdır**: `kalibrasyondan_gold` ve
`calisma_listesi` "insan gerçekte ne yazdı" sorusunu `.yedek-hakemlik`ten
cevaplar. Güncel dosyadan ölçmek "kimse hata yapmamış" der. Yedek yoksa
`calisma_listesi` kalıp basmaz ve nedenini raporun başına yazar — sessizce
"temiz" demez.

**(11) `resolve_queue` boş kuyrukta hiçbir şeye dokunmaz.** Ölçülmüş veri kaybı:
kuyruk boşken ikinci koşuda ilk turun ürettiği **3 reddedilen kayıt SIFIRLANDI**
("silme yok" kuralının sessiz ihlali). Koruma sonradan eklendi.

**(12) `reextract_raw` `bs4` olmadan felakete yol açar.** bs4 yokken
`_extract_main_text` tüm HTML'i metin sayarak zarif bozuluyor. Ölçüldü: sistem
python3 ile kuru koşu **1569 belgenin 1418'ini** "içerik kurtarıldı" diye
raporladı; gerçekte sağlam belgeler birebir aynıydı. Bu yüzden kod 2 kapısı var.

**(13) `kisaldi` sonucu hiç uygulanmaz.** Regresyon sinyalidir; üzerine yazmak
kanıtı yok eder.

---

## İlgili

- `data/gold/ANNOTATION_GUIDE.md` — anotatör kılavuzu (§3.1 protokol, §7 κ eşiği)
- `docs/OFFLINE-KANIT.md` — `offline_proof.sh` transkriptinin işlendiği belge
- `docs/rapor/ablasyon.md` — `ablation_report.py`'nin beslediği tablo
- `docs/sartname-kod-eslesme.md` — şartname maddesi ↔ kod eşlemesi
- `CLAUDE.md` §3 (önce kural), §4 (tek izinli fine-tune), §9–10 (veri modeli,
  normalizasyon), §11 (demo stratejisi), §16 (değerlendirme), §19 (uydurma yok)
