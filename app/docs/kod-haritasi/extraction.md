# Kod Haritası — `src/extraction/`

> Salt okur inceleme, 2026-08-09. Kapsam: `src/extraction/` altındaki 15 Python
> dosyasının tamamı (~5.630 satır). Bu belge kod değiştirmez; kodun ne yaptığını
> ve **neden** öyle yaptığını kaydeder. Docstring'lerdeki ölçülmüş sayılar
> AYNEN aktarılmıştır — bu depoda gerekçe docstring'de yaşıyor.

---

## 1. Bir cümlelik özet

`src/extraction/`, temizlenmiş bir banka kampanya metninden 12 finansal alanı
**deterministik kural katmanıyla birincil olarak** çıkarır, kuralların
bulamadığı boşlukları isteğe bağlı bir yerel LLM'e (vLLM/Ollama, kısıtlı JSON
decoding) sorar ve iki katmanı `reconcile.py`'de tek alan kümesinde birleştirir;
her alan bir `canonical_value` + `confidence` + `source_span` + karakter
offset'i taşır ve **bulunamayan alan hiç üretilmez**.

---

## 2. Üç katman gerçekte ne durumda

### 2.1 Plan ile teslimin farkı

`CLAUDE.md §3` üç katman tarif ediyor: **kural → GLiNER2/BERTurk → LLM**.
Teslim edilen sistemde **iki** katman var:

```
kural (birincil)  ──►  LLM (yalnız boşluklar)
```

Bu, `reconcile.py` modül başlığında açıkça yazılı ve gizlenmiyor:

> «Bu başlık "3 katmanı birleştirir" diyordu ve CLAUDE.md §3 de üç katman tarif
> ediyor (kural · NER/GLiNER · LLM). Teslim edilen sistemde **iki** katman var…
> Dürüst bir 2-katman anlatısı, erişilmez bir daldan iyi okunur — özellikle jüri
> kodu okuduğunda.»

### 2.2 `Extractor.NER` üretiliyor mu? — HAYIR (kanıtlı)

Depo genelinde `Extractor.NER` ifadesi **yalnızca `reconcile.py`'de**, dört yerde
geçiyor ve dördü de ya yorum ya öncelik tablosunun kendisi:

```
src/extraction/reconcile.py:17   (docstring)
src/extraction/reconcile.py:26   (docstring)
src/extraction/reconcile.py:90   (yorum)
src/extraction/reconcile.py:95   _PRIORITY = {Extractor.RULE: 3, Extractor.NER: 2, Extractor.LLM: 1}
```

Hiçbir çıkarıcı `extractor=Extractor.NER` ile `ExtractedField` kurmuyor:

- `rules/extract.py::_field()` → sabit `extractor=Extractor.RULE`.
- `llm/extractor.py::_to_fields()` → sabit `extractor=Extractor.LLM`.
- `ner/classifier.py` → hiç `ExtractedField` üretmiyor; dönüşü
  `tuple[Optional[str], float]` yani `(kampanya_türü, güven)`. Bu değer
  `Campaign.campaign_type` alanına gider, `Campaign.fields`'a değil.

Yani `_PRIORITY`nin orta basamağı **erişilmez bir daldır**. Tablodan
çıkarılmama gerekçesi kodda yazılı: `extractor` DB'de saklanan bir sütundur,
şema değeri geriye dönük okunabilir kalmalıdır ve sıralamayı şimdi bozmak,
katman gerçekten eklendiğinde sessizce yanlış önceliğe yol açardı.

Sebep de ölçülmüş: **GLiNER2 projeye hiç girmedi** (`src/extraction/ner/`
yalnız BERTurk sınıflandırıcısını taşır), **BERTurk eğitildi ve ölçüldü ama
kabul kapısından geçemedi** (`docs/rapor/berturk-ince-ayar-plani.md`) — üstelik
aday olduğu iş alan çıkarımı değil, 8-sınıf tür sınıflandırmasıydı.

### 2.3 Hangi yollar GERÇEKTEN çalışıyor

| Yol | Çalışıyor mu | Çağıran |
|---|---|---|
| `rules/extract.extract_all` | **Evet, her koşumda** | `reconcile`, `comparison/scan.py`, `eval/predictors.py`, `eval/properties.py`, 5+ `scripts/` |
| `reconcile.reconcile` / `build_campaign` | **Evet** | `src/pipeline.py:187`, `src/api/main.py:580,1244`, `src/chatbot/run_safety_eval.py`, `scripts/latency_bench.py` |
| `llm/extractor.LLMExtractor` | **Koşullu** — `LLM_BACKEND` boşsa `NullLLMExtractor` | `pipeline.py`, `api/main.py:361`, `eval/predictors.py` |
| `ner/classifier.default_classifier` | Evet ama **alan çıkarımı değil**, tür sınıflandırma | `pipeline.py`, `api/main.py`, `extraction/run.py` |
| `llm/orchestrator.LLMOrchestrator` | **Yalnız ölçüm kolu** | Sadece `eval/predictors.py:244` (`orkestra`, `orkestra-hakemsiz` konfigleri). Üretim yolunda (`pipeline.py`, `api/main.py`) hiç kurulmuyor. |
| `silver/*` | **Hattan tamamen ayrı** | Yalnız `scripts/build_silver.py`, `scripts/run_silver_verifier.py`, `scripts/eval_classifier.py`. Çıkarım hattında çağrılmıyor. |
| `reconcile(verify_low_conf=…)` | **Üretimde kapalı** (varsayılan `0.0`) | Yalnız `eval/predictors.py` `hibrit-verify` kolu (`DEFAULT_VERIFY_THRESHOLD = 0.75`) |

**Pratik sonuç:** varsayılan offline teslimde (`LLM_BACKEND` boş) sistem
fiilen **tek katmanlıdır** — `default_extractor()` `NullLLMExtractor` döndürür,
`reconcile` LLM'e hiç sormaz. `LLM_BACKEND=vllm|ollama` verildiğinde iki katman
olur. Üç katman hiçbir konfigürasyonda oluşmaz.

### 2.4 Ölü ya da yarı-ölü olmayan ama yanıltıcı görünen şeyler

- `_PRIORITY[Extractor.NER]` — erişilmez, bilerek bırakıldı (yukarıda).
- `verify_low_conf` — bir dönem "ölçülüyor" iddiası **yalandı**; `reconcile.py`
  bunu kendi başlığında itiraf ediyor ve düzeltmeyi anlatıyor:
  «Yukarıdaki "ablasyonda ayrı satır olarak ölçülür" cümlesi bir süre
  **yalandı**… İki seçenek vardı: özelliği KALDIRMAK ya da iddiayı GERÇEK
  yapmak. **İkincisi seçildi**.» Bugün `eval/predictors.py`'de `hibrit-verify`
  kolu olarak gerçekten kuruluyor.
- `llm/orchestrator.py` — üretimde değil ama ölü de değil; ablasyonun iki kolu.
- `silver/` — çıkarım değil, **8-sınıf sınıflandırıcının eğitim verisi** üretim
  hattı. Aynı pakette durması tarihsel; işlevsel bağı yok (yalnız
  `ner/classifier.RuleHintClassifier`'ı üçüncü oy olarak kullanır).

---

## 3. Dosya dosya

### `__init__.py` (0 satır)
Boş. Paket işaretleyici.

### `run.py` (44) — CLI, tek metin çıkarımı
`python -m src.extraction.run --input <dosya> [--bank <slug>]`.
`normalize_text` → `default_classifier().classify` → `build_campaign` →
alanları JSON olarak stdout'a basar. Debug/inceleme aracı; hattın parçası değil.
**Not:** `build_campaign`'e `llm=default_extractor()` geçiriyor, yani
`LLM_BACKEND` doluysa burada LLM gerçekten çalışır.

### `reconcile.py` (165) — uzlaştırma
Giriş noktaları: `reconcile(text, llm, verify_low_conf)` ve
`build_campaign(text, bank_slug, source_url, llm, campaign_type, verify_low_conf)`.
Çağıranlar: `pipeline.py`, `api/main.py`, `chatbot/run_safety_eval.py`,
`eval/predictors.py`, `eval/ablation.py`, `scripts/eval_o1.py`,
`scripts/latency_bench.py`, `extraction/run.py`. Ayrıntı §5.

### `rules/__init__.py` (0)
Boş.

### `rules/extract.py` (1709) — kural katmanı, sistemin ağırlık merkezi
12 tekil çıkarıcı + oran tablosu ayrıştırıcısı + `extract_all` orkestrasyonu.
Tek dış bağımlılığı `src/normalization/normalize.py` (kanonikleştirme) ve
`src/preprocessing/clean.py` (`split_sentences`, `tr_fold`).
Giriş noktaları: `extract_all(text)` (asıl), ayrıca her tekil çıkarıcı ve
`parse_rate_table` / `extract_dipnotlar` / `kampanya_tarih_araligi` dışarıdan
çağrılabilir. Çağıranlar: `reconcile`, `comparison/scan.py`,
`scraping/harvest_products.py`, `eval/predictors.py`, `eval/properties.py`,
`scripts/onanotasyon_tazele.py`, `scripts/boilerplate_audit.py`,
`scripts/crosscheck_rates.py` (yalnız `extract_kar_payi`),
`scripts/preannotate.py`, `scripts/latency_bench.py`.

### `rules/confidence.py` (232) — kural katmanının GERÇEK güven skoru
`score(field_name, canonical, *, trigger_distance, candidate_count, window)
-> (skor, gerekçe)`, `is_plausible`, `looks_like_chrome`, `PLAUSIBLE_RANGES`.
Yalnız `rules/extract.py::_field()` ve `extract_all` (taban makullük kontrolü)
çağırıyor. Saf stdlib, deterministik.

### `rules/ihtar.py` (59) — genel yasal ihtar, TEK DOĞRULUK KAYNAĞI
`IHTAR_RE`, `ihtar_mi(cumle)`, `ihtar_ayikla(cumleler)`.
Çağıranlar: `rules/extract.py::extract_kampanya_kosullari` (üreten taraf) ve
`scripts/kalibrasyon_hakemlik.py` (anotasyon tarafı, `IHTAR_RE`'yi doğrudan
alıyor). `tests/test_ihtar_tek_kaynak.py` kopyaların ayrışmasını kapıda tutuyor.

### `rules/synonyms.py` (223) — eşanlamlılar, tetikleyiciler, §5.5 terminolojisi
`FIELD_TRIGGERS`, `TYPE_HINTS`, `TERMINOLOGY_5_5`, `TERMINOLOGY_TRIGGERS`,
`QUALITATIVE_RATE_CLAIMS`, `qualitative_rate_claim`, `terminology_hits`,
`keyword_pattern`, `matches`, `FOLDED_TYPE_HINTS`, `FOLDED_FIELD_TRIGGERS`,
ve `normalization.normalize.NEGATION_RE`'nin yeniden ihracı.
Çağıranlar: `ner/classifier.py`, `preprocessing/blocks.py`,
`domain/terminology.py`, `chatbot/safety.py`, `rules/extract.py`.
**Dikkat:** `FIELD_TRIGGERS` sözlüğü `extract.py` tarafından KULLANILMIYOR —
oradaki tetikleyiciler her fonksiyonun kendi regex'ine gömülü. Katlanmış
görünümü (`FOLDED_FIELD_TRIGGERS`) yalnız `preprocessing/blocks.py:148` ve
`chatbot/safety.py:404` okuyor.

### `ner/__init__.py` (0)
Boş.

### `ner/classifier.py` (160) — 8-sınıf kampanya türü
`RuleHintClassifier` (anahtar kelime, sıfır bağımlılık) ve
`BerturkClassifier` (transformers pipeline, `BERTURK_MODEL_DIR`, model yoksa
sessizce değil **loglayarak** RuleHint'e düşer). `default_classifier()`.
Çağıranlar: `pipeline.py`, `api/main.py`, `extraction/run.py`,
`chatbot/run_safety_eval.py`, `scripts/preannotate.py`,
`scripts/latency_bench.py`, `scripts/eval_classifier.py`,
`silver/consensus.py` (dolaylı: üçüncü oy).
**Alan çıkarımı yapmaz** — bu yüzden `Extractor.NER` üretmez.

### `llm/__init__.py` (0)
Boş.

### `llm/schema.py` (367) — kısıtlı decoding şeması + Türkçe prompt
`EXTRACTION_FIELDS` (12 alan, tek doğruluk kaynağı), `HEDEF_KITLE_LABELS`,
`FIELD_VALUE_SCHEMA`, `guided_json_schema(fields)`, `json_schema_envelope`,
`SYSTEM_PROMPT`, `FEWSHOT` (6 zor-vaka örneği).
Çağıranlar: `llm/extractor.py`, `llm/agents.py`, `reconcile.py`,
`eval/run_eval.py`, `scripts/gold_schema.py`, `scripts/to_review_csv.py`,
`scripts/preannotate.py`, `scripts/calisma_listesi.py`, `api/main.py`.

### `llm/extractor.py` (425) — LLM çıkarıcı, "sessiz hata yutmanın sonu"
`LLMExtractor` (`call` → `LLMCallResult`, `extract` → `list[ExtractedField]`,
`summary()`), `NullLLMExtractor`, `LLMExtractionError`, `default_extractor()`.
`self.stats` = `{calls, ok, parse_error, http_error, schema_violation, repairs}`.
`LLM_STRICT=1` → hata yutulmaz.
Çağıranlar: `pipeline.py`, `api/main.py`, `eval/predictors.py`,
`llm/agents.py`, `llm/orchestrator.py`, `scripts/preannotate.py`,
`scripts/latency_bench.py`, `scripts/eval_o1.py`.

### `llm/parse.py` (229) — ham LLM çıktısından JSON söken ayrıştırıcı
`parse_llm_json` (ASLA exception fırlatmaz; `(nesne, None)` veya
`(None, hata)`), `strip_think`, `strip_fence`, `find_balanced_object_span`,
`find_balanced_object`, `_kapanmamis_dizgeyi_onar`.
Çağıranlar: `llm/extractor.py`, `llm/clients.py`, `llm/orchestrator.py`,
`llm/confidence.py` (offset arayışı için).

### `llm/confidence.py` (261) — logprob tabanlı güven
`field_confidences(logprobs, fields)`, `find_value_span`, `span_confidence`,
`token_offsets`, `clamp` (`[0.01, 0.99]`), `self_reported`,
`SOURCE_LOGPROB` / `SOURCE_SELF_REPORTED`.
Yalnız `llm/extractor.py::_to_fields` çağırıyor.

### `llm/clients.py` (509) — vLLM ve Ollama istemcileri
`VLLMClient` (yetenek pazarlığı: `json_schema` → `structured_outputs` →
`guided_json` → `prompt_only`), `OllamaClient`, `LLMResponse`,
`_urllib_transport` (duvar-saati sınırlı), hata sınıfları
`LLMTransportError` / `LLMHTTPError`. Saf `urllib`, ücretli API yok.
Çağıran: `llm/extractor.default_extractor()` (tembel import).

### `llm/agents.py` (242) — çok-ajanlı roller
`AgentRole`, `ROL_SAYISAL` (9 alan), `ROL_BAGLAMSAL` (3 alan), `ROLLER`,
`sistem_kurucu()`, `ajan_kur()`, `kart_metni()`, `HAKEM_SYSTEM`,
`HAKEM_SEMASI`, `hakem_user_prompt()`.
Çağıranlar: `llm/orchestrator.py`, `scripts/eval_o1.py`.

### `llm/orchestrator.py` (431) — T0 → A1‖A2 → K → J akışı
`LLMOrchestrator` (`LLMExtractor` ile aynı arayüz: `.available` + `.extract`),
`OrkestrasyonRaporu`, `default_orchestrator()`, `rapor_ozeti()`.
Deterministik kapılar: `_kanit_kapisi` (alıntı metinde yoksa düş),
`_kalem_kapisi` (ücret alanında komşu kalem karışması).
Çağıranlar: `eval/predictors.py:244`, `scripts/eval_o1.py`. **Üretimde yok.**

### `silver/__init__.py` (49) — yeniden ihraç yüzeyi
### `silver/contract.py` (188) — JSONL sözleşmesi
`LabelProposal`, `VerifyVerdict`, `evidence_is_verbatim` (deterministik
halüsinasyon kapısı, `MIN_EVIDENCE_CHARS = 12`), `read_jsonl` / `write_jsonl`,
`load_proposals` / `load_verdicts` (mükerrer `doc_id`'de patlar).
### `silver/consensus.py` (189) — üç oylu uzlaşma
`decide(document_text, proposal, verdict, rule_label) -> SilverRecord`;
durumlar `silver` / `queue` / `reject`; `summarize`, `class_balance_warnings`,
`score_against_gold`.
### `silver/prompts.py` (152) — etiketleyici/denetleyici prompt'ları
`LABELER_SYSTEM`, `VERIFIER_SYSTEM`, `labeler_user_prompt`,
`verifier_user_prompt`, `MAX_PROMPT_CHARS = 24000`.
Bu üçlünün çağıranı yalnız `scripts/build_silver.py`,
`scripts/run_silver_verifier.py` ve `scripts/eval_classifier.py`.

---

## 4. 12 alan — çıkarıcı, aranan kalıplar, sınır vakaları

`EXTRACTION_FIELDS` (llm/schema.py) ile `rules/extract.py::_EXTRACTORS`
birebir örtüşür: 12 alan, 12 çıkarıcı. `kampanya_turu` bu listede **yoktur**
(sınıflandırıcının işi).

### 4.1 `kar_payi_orani`
**Fonksiyon:** `extract_kar_payi` → düşerse `_extract_kar_payi_ileri`; ayrıca
`extract_from_rate_table` (tablo varsa **önce** çalışır ve kazanır).
**Kanonik:** `float` ya da `{"min": x, "max": y}` (`normalize_rate`).
**Aranan kalıplar:**
- Geri yön (`_KAR_PAYI_ONCE_RE`): `(%\s*\d[\d.,]*)\s{0,3}(kâr|kar)\s*payı(\s*oranı)?`
  — `%` **zorunlu**, araya en fazla 3 boşluk.
- İleri yön: `kâr payı (oranı)? [^%\d]{0,15} (değer)`, aralık ayıracı
  `- – ile ila`, sonuna `_BIRIM_SONEKLI` negatif ileri-bakışı.
- Tablo yolu: `_ORAN_TABLOSU_BASLIK_RE` + `parse_rate_table` → aralık
  `{min, max}`.

**Bilinen sınır vakaları (hepsi kodda kapatılmış):**
| Vaka | Koruma | Ölçüm |
|---|---|---|
| "kâr payı **paylaşım** oranı %55'e %45" | `_PAYLASIM_ORANI_RE` → belge için `None` | korpusta **3 belge** |
| "…%20'ye kadar **devlet katkısıyla**", "10 **puanlık** kısmı KOSGEB" | `_YABANCI_KAVRAM_RE`, 30 karakter sağ pencere | 2026-08-03, 1684 belge: `kar_payi_orani` üreten **64 belgenin 7'sinde (%11)** değer yabancı kavrama aitti (6 devlet katkısı, 1 KOSGEB puanı) |
| "Gecikme Cezası Oranı, akdi kâr payı oranının %30 fazlasını geçemez" | `_CEZA_BAGLAMI_RE` (90 kr sol pencere, cümle sınırlı) | 2026-08-07, 1761 belge (`data/demo.v2.db`): 84 kaydın **15'i (%17,9)** ceza maddesinden |
| "oranının **yüzde 5'i**", "brüt kâr payının **%50'si**", "(… * 0,05)" | `_TUREV_ORAN_RE` + `_CARPAN_RE` (90 kr) | 2026-08-08, `data/demo.db`, 70 kayıt: **4 + 4 + 3 = 11 kayıt** |
| "%1,89 kâr payı oranı ile **120 aya** kadar" → 120 dönüyordu | geri yön önce denenir + `_BIRIM_SONEKLI` | docstring'de anlatılıyor |
| "36 ay vadeli faizsiz finansman" → 36.0 | `(?![\d.,])` + birim soneki | ikisi de tek değer korumasızken oluyordu |

**"akdi kâr payı oranı" BİLEREK dışlanmadı:** o sözleşmedeki GERÇEK orandır;
"Bankamızca, akdi kâr payı oranı %0 olarak belirlenmiştir" cümlesindeki %0
tutulmalıdır.

**Açık risk:** `extract_kar_payi` **ilk geçerli** eşleşmeyi döndürür. Aynı
belgede birden çok ürünün oranı varsa hangisinin seçildiği metin sırasına
bağlıdır; `candidate_count > 1` güveni `-0.10` düşürür ama seçim değişmez.

### 4.2 `finansman_tutari`
**Fonksiyon:** `extract_tutar`. **Kanonik:** `{"value": float, "currency": "TRY"}`.
**Kalıplar:** `_TUTAR_PAT` = `(finansman|kredi|tutar|limit)([^\d]{0,20})(sayı + TL/₺/TRY/Türk Lirası)`;
ayrıca `_TOPLAM_AZAMI_PAT` (`toplamda azami <tutar>`) ve `_ARALIK_UST_RE`
(hemen ardından gelen ikinci tutar → üst sınıra yükselt).
**Sınır vakaları:**
- **Cümle sınırı** (`_CUMLE_SINIRI_RE`): eski `[^\d]{0,20}` boşluğu nokta
  içerebiliyordu → "…ürünüdür. Fiyatı 20.000 TL'ye kadar olan cep telefonu"
  tutar sanılıyordu (`turkiye-emlak-katilim--finansmanlar-ihtiyac-finansmani`).
- **Varlık fiyatı** (`_VARLIK_FIYATI_RE`): fiyat/değer/bedel/ekspertiz →
  finansman tutarı değil. Gold sette de iki kez karışmış
  (`data/gold/review/_hakem-turu-01-finansman-tutari.md`).
- **Örnek tablo** (`_ORNEK_TABLO_RE`, 150 kr sol pencere): "Örnek İhtiyaç
  Finansmanı Tablosu | Finansman Tutarı … 30.000,00 ₺" — gold `absent` diyor.
- **Aralığın alt sınırını seçmek**: `search()` ilk adayı alıyordu; biçim kartı
  §3.4 üst sınırı kanonik sayıyor (`tom-katilim`: 5.000 değil 150.000).
- **ÖLÇÜLMÜŞ YANLIŞ DENEME — tekrarlanmasın:** "adayların EN BÜYÜĞÜNÜ seç"
  denendi ve `tom-katilim`'i daha da bozdu (**5.000 → 11.891,83**, çünkü
  belgedeki en büyük tutar "Geri Ödenecek Tutar" satırıydı). §3.4 *bir aralığın*
  üst sınırını istiyor, **belgedeki en büyük sayıyı** değil.
- **Birden fazla üst sınır**: `vakif-katilim--kentsel-donusum` — "her bir
  bağımsız bölüm için 1.250.000 TL'yi aşmamak koşulu ile toplamda azami
  3.000.000 TL" → toplam sınır kanonik. `_TUTAR_PAT` 3.000.000'u aday olarak
  HİÇ görmüyordu (tetikleyici 20 karakterden uzak).

### 4.3 `vade_ay`
**Fonksiyon:** `extract_vade`; tablo varsa `extract_from_rate_table` (en uzun
vade). **Kanonik:** `int` ay (`normalize_term_months`).
**Kalıp:** `(\d[\d.,]*)\s*(ay|yıl|yil|sene)(?:a|da|ta|dan|tan|ı|i|lık|lik)?\b`,
ardından `vade` sözcüğüne uzaklığa göre skorlama; `ilk` öneki taşıyan adaylar
geri itilir ("ilk 6 ay ödemesiz" gerçek vade değildir).
**Sınır vakaları:**
- **Takvim yılı** (`_takvim_yili`): "2026 yılı" → 2026 × 12 = **24312 ay**
  okunuyordu. Güvenlik setindeki K02 ("en yüksek vade hangi bankada?")
  **"Albaraka Türk, 24312 ay"** cevabını veriyordu. `demo.db`'de bu sınıftan
  **10 kayıt** vardı (2024/2025/2026 yılı) ve bir açılır menü döküntüsü
  ('2021 Ay' → ≈168 yıl). Artefaktlar dışlandığında korpustaki meşru en yüksek
  vade **120 ay**. İki kapı: `1900 ≤ sayı ≤ 2100` + birim yıl/sene, ve
  `ay > MAKS_VADE_AY (600)`.
- `tr_fold` kullanımı zorunlu: `'İLK 6 AY'.lower()` → `'i̇lk'` promo tespitini
  kaçırıyordu. Katlama karakter sayısını korur, offset'ler hizalı kalır.

### 4.4 `taksit_sayisi`
**Fonksiyon:** `extract_taksit`. **Kanonik:** `int`.
**Kalıp:** `(?<![:.,\d])(\d{1,3})\s*taksit` **veya**
`taksit\s*(sayısı)?\s*[:\-]?\s*(?<![:.,\d])(\d{1,3})`.
**Sınır vakası — YENİ DÜZELTİLMİŞ:** `turkiye-finans--bireysel-urun-hizmet-ucretleri`
sayfasında "**02.01.2026 00:00:00** Taksitli Ticari Taşıt Finansmanı" geçiyor ve
desen **zaman damgasının son iki hanesini** yakalayıp `taksit_sayisi = 0`
üretiyordu — hem şema dışı (pozitif olmalı) hem uydurma. Belgenin gerçek
taksit bahsi çok daha sonra geliyordu ama `search` ilk eşleşmede duruyordu.
İki koruma: sayının solunda `:` ya da rakam olamaz, **ve 0 taksit yoktur**
(`canon < 1` → atla, `finditer` ile aramaya devam).

### 4.5 `tahsis_ucreti`
**Fonksiyon:** `extract_tahsis_ucreti(text, taban_tutar)`; taban
`extract_all` içinde `extract_tutar`'dan gelir.
**Kanonik:** `{"value": float, "currency": "TRY"}` — **her zaman para, asla oran**.
**Tetikleyici:** `tahsis ücret*|tahsis ucret*|dosya masraf*|tahsis bedel*`,
`finditer` ile TÜMÜ taranır.
**Değer üç yoldan biriyle bulunur (`_ucret_degeri`):**
- **A** `_BITISIK_TABAN_RE`: "100.000 TL'**nin** %2,5'i" — iyelik eki ZORUNLU.
- **B** `_ADLA_TABAN_RE`: "finansman tutarının binde 5'i" → belge düzeyindeki
  `finansman_tutari` taban olarak kullanılır.
- **C** İlk sayısal belirteç (`_ILK_SAYISAL_RE`) + komşu sütun kesme; **oran
  görülüp taban bilinmiyorsa değer ÜRETİLMEZ**.
Ayrıca negasyon (`NEGATION_RE`) → `{"value": 0.0}`, ve sol pencere
`_ONCEKI_TUTAR_RE` (bitişik `\s*$` şartıyla).

**Ölçümler:**
- 2026-08-07, 1759 belge: tahsis/dosya tetikleyicisi olan **101 belgenin
  62'si** ücreti oran olarak veriyor. Hesap katmanı yokken **51 belge hiçbir
  değer üretmiyordu**, kalanlarda oran TL sanılıyordu — `%0,25` → **0,25 TL**
  (`hayat-finans/products/urun-ve-hizmet-ucretleri`), **~400 kat sapma**.
- `{"rate": X}` yazma denemesi gold'da `tahsis_ucreti` F1'ini **0.400 → 0.333**
  düşürdü (2 belgede halüsinasyon).
- 849 belgelik korpusta değişmez denetimi (P4): `re.search` (ilk eşleşme)
  yüzünden sonuç yazım sırasına bağlıydı — **15 belgede** yakalandı. Karar:
  `masraf_durumu`da "masrafsız iddiası her sırada kazanır", burada simetrik
  olarak **pozitif ücret her sırada kazanır**.
- Açık para birimi şartı olmadan ürün adı "2B Finansmanı" olan sayfada "2"
  sayısı **2,00 TL tahsis ücreti** oluyordu.
- Sol pencere (2026-08-09, Türkiye Finans arsa/işyeri/konut): "Alınacak
  ücretler: 60 ay vadede **500 TL tahsis ücreti**, 3.000 TL ipotek tesis
  ücreti, 16.500 TL Ekspertiz ücreti." İleri pencere **3.000 TL**'yi (İPOTEK
  TESİS) üretiyordu.
- `tom-katilim--hesaplama-araclari`: "%0.5 tahsis ücreti YAPILAN HARCAMA
  üzerine eklenir" — taban harcamadır; kaydırıcı sınırıyla çarpmak **750 TL'lik
  uydurma bir ücret** üretirdi. Bu yüzden **adlandırma yoksa hesap yapılmaz**.
- Taban makullüğü (`extract_all`): ücret tarifesi PDF'lerinde `extract_tutar`
  çöp yakalıyordu (**0,27 TL / 1,04 TL / 2 TL**) ve bu taban **0 TL tahsis
  ücreti** üretiyordu — "ücretsiz" görünen uydurma değer. **Üç belgede**
  ölçüldü; `PLAUSIBLE_RANGES["finansman_tutari"] = (100, 100_000_000)` üçünü
  de eler.

**Hesaplanan değerin açıklanabilirliği:** hesaplanan tutar metinde geçmediği
için `source_span` sonuna `[hesap: 200.000 TL × %0,5 = 1.000 TL]` eklenir.

### 4.6 `masraf_durumu`
**Fonksiyon:** `extract_masraf`; yedek olarak `extract_from_rate_table`.
**Kanonik:** `{"has_fee": bool, "amount": float|None}` (`normalize_fee_status`).
**Kalıp:** `masrafsız|ücretsiz|masraf|tahsis|ücret`, `finditer` ile tümü;
ileri pencere 40 karakter, **cümle sınırında** ve **komşu sütun başlığında**
kesilir.
**Sınır vakaları:**
- Sıra bağımlılığı (düzeltildi): "Masrafsızdır. Tahsis ücreti 500 TL." vs
  "Tahsis ücreti 500 TL. Masrafsızdır." — ikincisinde çelişki kaçıyordu.
  Karar: **"masrafsız" iddiası her sırada kazanır** (`has_fee=False` bulunur
  bulunmaz döner). Gerçeği `tahsis_ucreti` söyler, uyuşmazlığı
  `contradiction.detect()` yakalar.
- Cümle sınırı: "… alınmaz. Kampanya 31 Aralık 2026" → **31 TL'lik hayali
  ücret**. Nokta binlik ayırıcı da olduğu için `(?<!\d)[.;](?!\d)` lookaround
  şart.
- Tablo sütun kayması (`_COLUMN_HEADERS_RE`, `_truncate_at_next_column`):
  849 belgelik korpus (31 Tem 2026) üç makul olmayan masraf tutarı gösterdi —
  **100.000 TL, 30.000 TL, 28.076,27 TL** — ve üçü de tablo başlık satırından
  geliyordu ("Kâr Oranı | Tahsis Ücreti | Yıllık Maliyet Oranı | 100.000 TL").

### 4.7 `kampanya_suresi`
**Fonksiyon:** `extract_kampanya_suresi` → `kampanya_tarih_araligi`.
**Kanonik:** ISO-8601 **bitiş** tarihi (tek dize).
**Aday deseni** (`_TARIH_RE`): `gg.aa.yyyy` / `gg/aa/yyyy` / `yyyy-aa-gg` /
`gg <AyAdı> yyyy` — ay adı **serbest sözcük değil**, `N.TR_AY_ADLARI`'ndan.
**Üç aşama:** (1) açık aralık (iki tarih yan yana, `_TARIH_AYIRAC_RE`),
(2) gün-gün aralığı (`_GUN_GUN_RE`, "1-31 Temmuz 2026"), (3) tek tarih +
rol tetikleyicisi (`_BITIS_TETIK_RE` / `_BASLANGIC_TETIK_RE`, 60 kr pencere).
**Sınır vakaları:**
- **ÖLÇÜLMÜŞ KUSUR (2026-08-07, 1759 belge):** eski çıkarıcı `re.search` ile
  ilk tarihi alıyordu. Başlangıç-bitiş çifti içeren **492 belgenin 442'sinde
  (%90)** bu ilk tarih **başlangıç** tarihiydi; yani bitiş alanına kampanyanın
  başladığı gün yazılıyordu. Dashboard'da bu, süresi dolmuş kampanyayı "hâlâ
  geçerli" göstermek demek.
- **Kanun atfı** (`_KANUN_ATIF_RE`): "konutun **22/11/2001 tarihli ve 4721
  sayılı** Türk Medeni Kanununun…" → 2001-11-22 kampanya bitişi yazılıyordu;
  gold `absent` diyor.
- Takvimde olmayan tarih ("31.06.2026") `normalize_date` tarafından elenir.
- Yalnız başlangıç biliniyorsa alan **hiç üretilmez** — bitiş uydurulmaz.
- Eski davranış korunan tek nokta: **rolsüz tek tarih bitiş sayılır**. Bu bir
  varsayımdır; belgede yalnız bir başlangıç tarihi varsa ve tetikleyici yoksa
  yanlış olabilir.

### 4.8 `odul_miktari`
**Fonksiyon:** `extract_odul_miktari`. **Kanonik:** para sözlüğü.
**Kalıp:** ödül sözcükleri `hediye|para puan|cashback|nakit iade|iade|bonus|
çek|kazan*|ödül`; tutar **önce solda 30 karakterde** (ödüle en yakın olan),
yoksa sağda 30 karakterde aranır; adaylar arasından **en yakın** seçilir.
**Sınır vakası:** koşul/ödül ayrımı — "500 TL alışveriş yapana 50 TL hediye"de
500 TL koşul, 50 TL ödüldür. Sol-öncelik + en küçük uzaklık bunu hedefliyor
ama **garanti etmiyor**: "hediye" sözcüğünden 30 karakter içinde koşul tutarı
da bulunabilir.

### 4.9 `indirim_orani`
**Fonksiyon:** `extract_indirim_orani`. **Kanonik:** `float` (`normalize_rate`).
**Kalıp:** `%X … indirim` (araya ≤20 karakter, cümle içinde) → bulunamazsa
`indirim (oranı)? … %X` (araya ≤12 karakter).
**Sınır vakası:** "%5 **puan** iadesi" bir indirim değil `alisveris_puani`'dır;
değerin ±25 karakterinde `puan` geçiyorsa alan **hiç üretilmez**.
**Not:** bu çıkarıcı tek `search` kullanıyor (finditer değil), yani ilk eşleşme
kesindir — sıra bağımlılığı burada hâlâ var.

### 4.10 `alisveris_puani`
**Fonksiyon:** `extract_alisveris_puani`.
**Kanonik:** `{"kind": "rate"|"points", "value": float}` — iki şekil ayrı
tutulur ki §5.7 kıyasında elmayla armut sıralanmasın (CLAUDE.md §17).
**Tetikleyiciler** (`_PUAN_TRIGGER_RE`): `chip-para|parafpara|maximiles|
worldpuan|world puan|bonus puan*|alışveriş puan*|puan iade*|puan` — markalı
birimler önce, genel `puan` en sonda.
**İki ölçülmüş halüsinasyon mekanizması burada kapatıldı (19 halüsinasyonun 2'si):**
- (a) **Site kromu**: "3D Secure Nedir, Ne İşe Yarar? Kredi Notu (Kredi Puanı)
  Nedir?" — iki Türkiye Finans sayfasında `puan` sözcüğünün geçtiği TEK yer
  buydu ve ikisinde de ilgisiz bir sayı (**10.0**) üretiliyordu.
  `_PUAN_KROM_RE` (±40 kr pencere) bunları atlar.
- (b) **Birim opsiyonelliği**: sayı birimi opsiyonel olduğu için ±30
  karakterdeki *herhangi* bir sayı kabul ediliyordu. `_PUAN_SAYI_RE` artık
  birimi zorunlu kılıyor ve sayının **rakamla bitmesini** şart koşuyor —
  sözleşmedeki "**24.** Puan Uygulaması 24.1…" madde numarası 24 puanlık ödül
  sanılıyordu.
- Ayrıca ilk eşleşme yerine tüm tetikleyiciler taranıyor; kromdaki bir eşleşme
  gerçek ödülü artık gölgelemiyor.
- İlgili ölçüm: `alisveris_puani` düşüşü "veri kaybı değil, **39/41 yanlış
  pozitifin** temizliği" olarak doğrulanmış (commit `d2cc832`).

### 4.11 `hedef_kitle`
**Fonksiyon:** `extract_hedef_kitle`. **Kanonik:** `sorted(list[str])`,
etiketler `yeni_musteri | mevcut_musteri | maas_musterisi | belirli_segment`
(LLM şemasıyla **birebir aynı küme**, `HEDEF_KITLE_LABELS`).
**Çok etiketli**: her segment için ayrı `re.search`.
**Negasyon penceresi:** eşleşmeden sonraki 25 karakterde
`olmayan*|hariç|dışında|geçerli değil` varsa etiket **üretilmez** ("yeni müşteri
olmayanlar").
**Sınır vakası:** sinyal yoksa `None` — "mevcut müşteri" varsayılanı YAPILMAZ.
`span` yalnız İLK bulunan segmentin yerini gösterir; çok etiketli çıktıda
kaynak vurgulama diğer etiketleri kapsamaz (bilinen sınır).

### 4.12 `kampanya_kosullari`
**Fonksiyon:** `extract_kampanya_kosullari` (+ `extract_dipnotlar`).
**Kanonik:** `list[str]`, en fazla **8** cümle. Skaler değil; eval'de
küme-F1 / token-Jaccard ile ayrı bölümde raporlanır.
**Gövde tetikleyicileri:** `şart*|koşul*|gerekmekte*|gerekli*|zorunlu*|asgari|
en az \d|minimum|yalnızca|sadece|hariç|için geçerli|olması gerek`.
**Dışlananlar:**
- **Tek başına "geçerli\w*" TETİKLEYİCİ DEĞİL** — neredeyse her metin
  "…tarihine kadar geçerlidir" ile bitiyor; bu `kampanya_suresi`'nin işi.
- **Boilerplate filtresi**: çerez/cookie/KVKK/kişisel veri/aydınlatma metni/
  gizlilik/açık rıza/veri sorumlusu/telif/tüm hakları/sosyal medya/bilgi
  toplumu/çağrı merkezi/müşteri hizmetleri/şubelerimiz. 291 belgelik korpusta
  değişmez denetimi `kampanya_kosullari`nı **tek suçlu** olarak işaretlemişti;
  filtresiz hâlde belge başına **~8,7 "koşul"** çıkıyordu.
- **Genel yasal ihtar** (`ihtar_mi`) — §7.1'e bakın.
- Uzunluk bandı: `20 ≤ len ≤ 400`.

**Dipnotlar** (`extract_dipnotlar`, `_DIPNOT_ISARET_RE` = `*`, `**`, `(*)`,
`•`, `‣`): `split_sentences` bunları ayıramıyor (ileri-bakış `*`'ı sınıfta
görmüyor), bu yüzden segmentasyon burada ayrı yapılıyor. Dipnotlara **daha dar**
ölçüt uygulanır: yalnız `_KISIT_RE` taşıyanlar girer.
**Ölçümler (2026-08-07, 1759 belge):**
- Yıldızlı dipnot içeren **165 belgenin 53'ünde** dipnot gerçek kısıt taşıyordu;
  **35 belgede** bu kısıtların en az biri (**toplam 89 kısıt**)
  `kampanya_kosullari`ndan tamamen düşüyordu.
- En pahalı kaçırma sınıfı **kontenjan**: "ilk 2.000 kişi ile
  sınırlandırılmıştır" — **25 belgede** geçiyor ve tetikleyici listesinde
  "sınırl…" **HİÇ YOKTU**.
- Bu 25 belgenin **8'inde** kısıt yıldızlı dipnotta değil, `•` madde imli
  "Kampanya Şartları" listesindeydi ve tek bir 400+ karakterlik "cümle" olarak
  gelip uzunluk filtresine takılıyordu.
- **Gövdeye yalnız kontenjan eklendi, tüm `_KISIT_RE` değil:** tamamını gövde
  tetikleyicisi yapmak alanın F1'ini **0.733 → 0.400** (TP **11 → 6**),
  mikro-F1'i **0.647 → 0.571** düşürdü — kazanılan kontenjan görünürlüğünden
  (**4 → 12 belge**) çok daha pahalı.

---

## 5. Uzlaştırma (`reconcile.py`)

### 5.1 Akış

```python
by_field = {f.field_name: f for f in rule_extract(text) if f.is_present}
missing  = [ad for ad in EXTRACTION_FIELDS if ad not in by_field]
verify   = {ad for ad, f in by_field.items()
            if f.extractor is Extractor.RULE and f.confidence < verify_low_conf}   # 0.0 ise boş
ask = missing + sorted(verify)
if ask and llm.available:
    for f in llm.extract(text, ask):
        if f.is_present and (mevcut yok or _wins(f, mevcut, relaxed=f.field_name in verify)):
            by_field[f.field_name] = f
```

### 5.2 Kural ile LLM çakışınca ne olur

- **Varsayılan akış (`verify_low_conf = 0.0`):** LLM'e **yalnızca kuralların
  bulamadığı alanlar** sorulur. Kural bir alanı bulduysa o alan LLM'e hiç
  gitmez, dolayısıyla çakışma çoğu zaman **hiç oluşmaz**.
- Yine de çakışma olursa (`_wins`, `relaxed=False`): önce **katman önceliği**
  (`RULE 3 > NER 2 > LLM 1`), eşitse **güven**. Kural her zaman kazanır.
- **Doğrulama modu (`relaxed=True`):** yalnız `verify` kümesindeki alanlarda
  öncelik **atlanır** ve sadece güven karşılaştırılır. Bu, LLM'in düşük güvenli
  bir kural değerini düzeltebilmesinin **tek yoludur**.

Kodda yazılı gerekçe: «kural katmanı yanlış bir değer üretirse LLM onu asla
düzeltemez, çünkü o alan hiç sorulmaz. Regex'in emin olmadığı yerde hata
olasılığı en yüksektir ve tam orada ikinci bir göz yoktur.»

### 5.3 Güven skoru nasıl hesaplanıyor

Üç ayrı kaynak var ve hangisi kullanıldığı `ExtractedField.confidence_source`'a
yazılır (kalibrasyon farklı kaynakları karıştırmasın diye).

**(a) `rule_heuristic` — `rules/confidence.py::score`**
```
BASE = 0.70
tetikleyici uzaklığı:  ≤15 kr → +0.25 | ≤60 kr → +0.12 | yok/uzak → −0.15
makullük:              aralık dışı → −0.45   (PLAUSIBLE_RANGES)
belirsizlik:           candidate_count > 1 → −0.10
aralık değeri:         {min,max} → −0.05
gezinme/SSS bağlamı:   looks_like_chrome(window) → −0.30
kırpma:                [0.05, 0.98], 3 basamak yuvarlama
canonical is None      → 0.0, "normalize edilemedi"
```
Her kalem insan okunur bir **gerekçe** dizesi de üretir (açıklanabilirlik).
Skorlar **kalibre edilmemiştir**, sıralayıcıdır; gerçek kalibrasyon
`eval/calibration.py`'de gold set üzerinde sıcaklık ölçekleme ile yapılacak.

`PLAUSIBLE_RANGES`: `kar_payi_orani (0,15)`, `indirim_orani (0,100)`,
`vade_ay (1,480)`, `taksit_sayisi (1,480)`, `finansman_tutari (100, 1e8)`,
`tahsis_ucreti (0, 1e6)`, `odul_miktari (0, 1e7)`, `alisveris_puani (0, 1e7)`.
Aralık değerlerinde **min ve max'ın ikisi de** kontrol edilir — yalnız min'e
bakmak `{min: 1.89, max: 120.0}` gibi bozuk bir aralığı gizlerdi.

**Krom cezasının gerekçesi (ölçülmüş ayrışma):** `alisveris_puani` alanında
**41 belge**, site kromundaki "Kredi Notu (Kredi Puanı) Nedir?" gezinme
bağlantısından **0,95 güvenle** değer üretiyordu. 0,95 aynı zamanda DOĞRU
alanların da modu (**612 kayıt**), yani hiçbir eşik ikisini ayıramıyordu ve
`reconcile.verify_low_conf` kolu bu yüzden **yapısal olarak ölüydü**
(`docs/rapor/ablasyon.md §7b`). Ölçüm (`data/gold/preannotations.json`,
**945 alan**):
```
krom kaynaklı kayıtlar : 82/82  (%100) hem nav işareti hem "?" taşıyor
diğer kayıtlar         : 29/863 (%3,4) taşıyor
```
**VETO DEĞİL CEZA**, ve sebebi ölçüldü: sinyali tetikleyen o 29 kayıt karışık —
bir kısmı gerçek ("Hesap açılışı için minimum tutar 50.000 TL"), bir kısmı
yanlış ("Findeks Kredi Notu, 12 ay boyunca…" → `vade_ay = 12`).
İki koşul BİRLİKTE aranıyor (nav kalıbı **ve** `?`): tek sözcüklü bir sezgisel
("ana sayfa"/"müşteri ol") bir kez **101 belgenin 87'sinde** yanlış pozitif
üretmişti — o sözcükler bazı bankaların HER sayfasındaki kırıntı yolunda geçiyor.

**(b) `logprob` — `llm/confidence.py`**
Token listesi birleştirilir, her alanın JSON'daki `"value"` değerinin karakter
aralığı bulunur (`find_value_span`), o aralıkla **örtüşen** token'ların logprob
ortalaması alınır ve `conf = exp(mean(logprob))` (geometrik ortalama olasılık =
perplexity'nin tersi) ile olasılığa çevrilir. `[0.01, 0.99]`'a kırpılır: `1.0`
bir "kesinlik" iddiasıdır ve hiçbir LLM çıktısı için doğru değildir; `0.0` ise
alanı eşiğin altına atıp uzlaştırmada sessizce yok eder.
Gerekçe: «Şemada bir `confidence` alanı var ve model onu dolduruyor. Ama bu
sayı da modelin ürettiği bir token dizisidir: kalibre değildir, neredeyse her
zaman 0.9'a yakındır ve yanlış cevaplarda da yüksektir.»

**(c) `self_reported`** — logprob gelmezse (Ollama **hiç** vermez) modelin kendi
bildirdiği değer `clamp` edilerek kullanılır, varsayılan `0.5`.

**(d) `constant`** — `_field(..., conf=…)` açıkça verildiğinde. Kodda
`_RULE_CONF = 0.95` sabiti tanımlı ama **hiçbir çıkarıcı onu kullanmıyor**;
tüm çağrılar `conf` vermeden geçiyor, yani pratikte hepsi `rule_heuristic`.

### 5.4 `source_span` nasıl üretiliyor

**Kural katmanında** (`rules/extract.py::_window`): eşleşmenin `[start-40,
end+40]` penceresi, `.strip()`'li. Ayrıca `span_start` / `span_end` **kesin
karakter offset'leri** ayrı taşınır. Gerekçe (`schemas.py`): `source_span` bir
±40 karakterlik pencere metnidir ve orijinal metinde güvenilir biçimde geri
bulunamaz (aynı pencere iki kez geçebilir, `.strip()` kenarları kaybeder);
dashboard'daki kaynak vurgulaması kesin offset ister.

**Hesaplanan değerlerde** pencerenin sonuna formül eklenir:
`… [hesap: 100.000 TL × %2,5 = 2.500 TL]`.

**LLM katmanında** (`llm/extractor.py::_locate`): model `source_span`'i
metinden birebir kopyalamak zorunda (prompt kuralı #9). `text.find(span)` ile
offset aranır; bulunamazsa `span_start = span_end = None` — «yanlış yeri
vurgulamaktansa hiç vurgulamamak yeğdir». Orkestrasyonda bu, `_kanit_kapisi`
tarafından **red gerekçesi** olarak kullanılır.

`ExtractedField.verify_span(text)` offset'lerin gerçekten `raw_value`'yu
gösterdiğini doğrular; eval bunu tüm çıktılar üzerinde koşturur.

**Ölçülmüş kanıt kopukluğu (2026-08-08, `data/demo.db`):** `_ORAN_TABLOSU_BASLIK_RE`
bir zamanlar **iki kopyaydı ve kopyalar ayrışmıştı** — `parse_rate_table` gevşek
olanı, `extract_from_rate_table` katı olanı kullanıyordu. Sonuç sessizdi: tablo
ayrışıyor ve değer üretiliyor, ama ikinci arama tutmadığı için konum `(0, 0)`a
düşüyordu — `raw_value` boş, `span` yok, güven yine 0,95. **70 `kar_payi_orani`
kaydının 26'sı (%37) böyleydi.** Yani projenin en özgün iddiası — "her değer bir
karakter aralığına bağlıdır" — bu alanın üçte birinde tutmuyordu; üstelik değer
YANLIŞ değil, yalnız **KANITSIZ**dı, bu yüzden hiçbir doğruluk metriği bunu
göstermiyordu.

### 5.5 `extract_all` içindeki iki sıra kararı

1. **Oran tablosu ÖNCE.** Tablo varsa `kar_payi_orani` ve `vade_ay` oradan
   gelir; tekil çıkarıcıların tablo gövdesinden yanlış değer devşirmesi
   engellenir.
2. **`masraf_durumu` tabloda YEDEKTİR** (`_TABLO_YEDEK_ALANLARI`). Tekil
   `extract_masraf` sustuysa devreye girer. Ters sıra bilgi kaybettirirdi:
   ölçüldü (`data/demo.db`, 2026-08-09) — **19 oran-tablolu belgenin 11'inde**
   tekil çıkarıcının değeri daha zengin (`{"has_fee": true, "amount": 60}`),
   **8'inde hiç değer yok** — yedek tam o 8 belgede kazandırıyor.

---

## 6. Önemli kararlar ve GEREKÇELERİ

### 6.1 Kural katmanı birincil, LLM yalnız boşluk doldurucu
`llm/agents.py` ve `llm/orchestrator.py` başlıklarında **ablasyon sayısı** aynen:

> «Ablasyon ölçtü: **hibrit kol kuraldan daha kötü** (mikro-F1 0,612 → 0,575,
> halüsinasyon 0,102 → 0,163). Yani "LLM ekleyelim" refleksi bu projede ölçümle
> yanlışlanmış durumda.»

Bu tek sayı çifti, `extraction/` mimarisinin çoğunu açıklıyor.

### 6.2 Yetki asimetrisi (orkestrasyon)
```
çıkarım ajanları  -> yalnız ÖNERİR
hakem             -> yalnız REDDEDER (asla değer yazmaz)
reddedilen alan   -> kural değerine düşer
```
> «Böylece orkestrasyonun en kötü hâli kural-only'dir, yani bugünkü en iyi
> ölçülmüş kol. Hibrit kolun regresyonu **yapısal olarak tekrarlanamaz**.»

Hakem karar vermediği alanı **kabul** sayar: «hakemin yetkisi reddetmektir.
Hakkında hiç karar üretmediği bir alanı reddetmek, ona sessizce yazma yetkisi
vermek olurdu.»

### 6.3 Rol ayrımı prompt düzeyinde, model düzeyinde değil
> «Donanım (RTX 5060, 8 GB) iki 8B modeli aynı anda kaldırmıyor; ayrım bu
> yüzden **model düzeyinde değil, prompt ve şema düzeyinde**. Bu sınır rapora
> yazılır, gizlenmez.»

### 6.4 Mekanik kapı, LLM'e sormadan önce
`_kalem_kapisi` neden hakem prompt'u değil de deterministik kapı:
> «ÖLÇÜLDÜ: hakem beş kontrol vakasının **dördünü** doğru bildi ama tam bu
> vakayı kaçırdı ("Taşıt Rehin Tesis Ücreti 350,92 TL" alıntısını
> `tahsis_ucreti` önerisi için KABUL etti). … Sistematik ve bilinen bir hata
> için LLM'e güvenmek yerine mekanik kapı konur; hakem prompt'unu bu vakaya
> göre yamalamak, ölçüm kümesine aşırı uydurma olurdu.»

Kapı DAR: alıntı alanın kendi etiketini de taşıyorsa düşürülmez ("Tahsis ücreti
alınmaz; rehin ücreti ayrıca tahsil edilir" meşrudur).

### 6.5 Şema, biçimi zorlamak için var
`llm/schema.py` üç değişikliği gerekçeleriyle sayıyor:
1. `{"type": ["object","null"]}` yerine **`anyOf`** — xgrammar type union'ı
   güvenilir derlemiyor; derlenmeyince sunucu 400 döner ve tüm çağrı düşer.
2. **Alan-tipli değer şeması**: eskiden her `value` `["string","number",
   "object","null"]` idi, yani vade için `"120 ay"` (string) üretmek şemaya
   UYGUNdu ve normalizasyonda sessizce düşüyordu. «Kısıtlı decoding'in asıl
   faydası: **yanlış biçim ÜRETİLEMEZ.**»
3. Üst seviyede `required` = istenen tüm alanlar: «Aksi halde "modelin atladığı
   alan" ile "metinde olmayan alan" ayırt edilemez — ve bu ayrım recall hata
   analizinin tamamıdır.»

`maxItems` zorunluluğu **Colab'da qwen3:32b ile ölçüldü**: `maxItems` yokken
gramer sonsuz tekrara izin verdiği için model
`"hedef_kitle": ["belirli_segment", "belirli_segment", …]` üretip token
limitine kadar döndü ve JSON kesildi. «Kısıtlı decoding BİÇİMİ garanti eder,
İÇERİĞİ değil — sınırı şema koymak zorunda.»
`minimum`/`maximum` ve `pattern` **bilerek yok**: bazı gramer derleyicileri
desteklemiyor ve şemanın tamamı reddedilebiliyor.

### 6.6 Hata bir DEĞERDİR, yok sayılan bir olay değil
`llm/extractor.py` başlığı eski kodu gösteriyor (`except Exception: return []`)
ve üç farklı durumun (servis yok / şema reddedildi / JSON bozuk) aynı çıktıya
indiğini söylüyor:
> «Ablasyon tablosu bu yüzden `hibrit = kural-only` satırını **hata olmadan**
> basabiliyordu; yani jüriye gösterilecek en önemli artefakt **sessizce yalan
> söyleyebiliyordu**.»

Çözüm üç dayanaklı: `LLMCallResult` (hata + gecikme + ham çıktı + logprob +
onarım sayısı), `self.stats` sayaçları, ve `LLM_STRICT=1` (eval/ablasyon bu
modda koşar; sahte satır basmak **imkânsız** olur).

Aynı disiplin `default_extractor()`'da: `LLM_BACKEND` verilip istemci
kurulamazsa katı modda exception, hoşgörülü modda **gerekçeli log**.

### 6.7 Yetenek pazarlığı: tahmin etme, ölç
`clients.py` dört modu (`json_schema` → `structured_outputs` → `guided_json` →
`prompt_only`) **1 token'lık gerçek bir istekle** sırayla deniyor; ilk çalışan
`self.structured_mode`'a yazılıyor ve bir daha denenmiyor.
HTTP hatası = "bu parametreyi bilmiyorum" → sıradaki mod.
Taşıma hatası = "servis ayakta değil" → hemen yükselt.

### 6.8 Duvar-saati sınırı — ölçülmüş donma
> «`urlopen(..., timeout=t)` bir SOKET zaman aşımıdır… Ölçüldü (2026-08-08):
> `build_summaries` koşumu `OLLAMA_TIMEOUT=900` verilmiş olmasına rağmen
> Ollama'ya **açık bir TCP soketiyle 18 dakika uykuda** bekledi — %0 CPU, log'a
> tek satır yazmadan. … Demo açısından bu, tek gerçek donma riskiydi.»

Çözüm: çağrı daemon iş parçacığında, `join(timeout × LLM_DEADLINE_CARPANI)`
(varsayılan 1.5).

### 6.9 Ollama çıktı token sınırı
Varsayılan sınırsız ve bu ölçülmüş bir arızaya yol açıyordu (2026-08-08, özet
üretimi, `qwen2.5:7b-instruct`): model geçerli özet üretiyor, JSON'u kapatmadan
`<tool_call>` yazıp çöp döngüsüne giriyordu. **10 belgelik ölçümde 4'ü
düşüyordu ve iki hang tek başına 360 sn yiyordu.** Sınır (`num_predict = 512`)
+ durdurucu (`stop: ["<tool_call>"]`) ile aynı belgeler **4-8 sn**'de bitiyor.
`num_ctx = 8192` de açıkça set ediliyor: Ollama varsayılanı 2048 ve altı
few-shot + uzun metin bunu **sessizce baştan kırpıyor**, yani sistem yönergesi
kayboluyordu.

**512 ÖZET yolunun sayısıdır; çıkarım yolu ayrı bütçe kullanır (2026-08-14).**
Eski yorum "12 alan + span çıktısını rahat kapsıyor" diyordu; ölçüm bunu
yanlışladı. Gerçek çıkarım yolunda (few-shot prompt + `format` şeması, bütçe
bilerek 4096'ya açılıp `eval_count` okunarak, `qwen2.5:7b-instruct`,
gold.v2'nin **48 belgesinin tamamı**; 48/48 çağrı `done_reason=stop`, yani
hiçbiri tavana çarpmadı — sayılar gerçek ihtiyaç):

| ihtiyaç | değer |
|---|---|
| ortanca | 390 token |
| en çok | 955 token |
| 512'yi aşan belge | 12/48 |
| 1024'ü aşan belge | 0/48 |

Yani bu varsayılan altında **her dört belgeden biri** JSON'u kapatamadan
kesiliyordu; 2026-08-13 ablasyonunun `OLLAMA_NUM_PREDICT=2048` ile **elle**
koşulmak zorunda kalmasının sebebi buydu.

Ayrım kolaylıktan değil şemaların şeklinden geliyor:

- **özet** → `{"ozet": <string>}` — tek sınırsız dizge; gramer sonsuza kadar
  üretmeye izin verir, kaçan üretim ÖLÇÜLDÜ, sıkı tavan gerçek bir emniyet
  supabıdır.
- **çıkarım** → 12 tipli nesne; gramerin kendisi sınırlar, tavanın işi kaçağı
  kesmek değil **sığdırmak**.

Uygulama: `LLMExtractor.CIKARIM_NUM_PREDICT` (**1536** — ölçülen en yüksek
ihtiyacın ~1,6 katı, hiçbir belgenin yaklaşmadığı 1024 çizgisinin üstünde ve
`VLLMClient.max_tokens` ile aynı sayı, yani iki kol aynı bütçede buluşuyor;
`LLM_EXTRACT_NUM_PREDICT` ile ezilebilir). Paylaşılan
istemci nesnesi **değiştirilmez**; her çağrıda `butceyle()` ile sığ bir kopya
kullanılır, çünkü aynı nesneyi özet ve sohbet yolları da paylaşıyor
(`sicaklikla()` ile aynı gerekçe).

> **Tuzak — pazarlık kopyadan ÖNCE yapılır.** `VLLMClient.negotiate()` çalışan
> modu ölçüp `self.structured_mode`'a yazar. Kopya sığ olduğu için pazarlık
> kopyada yapılırsa sonuç paylaşılan nesneye dönmez: istemci her çağrıda
> yeniden pazarlık eder (4 boş HTTP gidiş-dönüşü) ve
> `LLMExtractor.structured_mode` `None` raporlar — rapor "hangi modda koştuk"
> sorusunu cevaplayamaz. Regresyon testi:
> `test_llm_cikti_siniri.py::test_pazarlik_PAYLASILAN_nesnede_onbelleklenir`.

**Uçtan uca doğrulandı (2026-08-14).** Dünkü arızanın yapılandırması aynen
kuruldu — `LLM_BACKEND=ollama` + `default_extractor()` + `LLM_STRICT=1`,
**hiçbir bütçe ortam değişkeni verilmeden** — ve 48 gold belgenin tamamı
koşuldu:

```
cagri=48  ok=48  parse_error=0  http_error=0  onarim=0
DUSEN BELGE: 0/48
paylasilan istemci num_predict = 512   (değişmedi)
```

Dün aynı yapılandırma **ilk belgede** `dengeli JSON nesnesi kapanmamis` ile
düşüyordu. Ablasyon artık elle `OLLAMA_NUM_PREDICT=2048` verilmeden koşulur.

Koşumun künyesi de düzeltildi: `LLMExtractor.summary()` (ve orkestrasyon
karşılığı) artık `num_predict` raporluyor, yani `eval/reports/*/env.json`
hangi bütçeyle koşulduğunu kaydediyor. 2026-08-13 raporunda bu satır yok —
o koşum elle verilen bir bütçeyle yapıldı ve künye bunu göstermiyordu.

### 6.10 Ollama zaman aşımı ortamdan
> «Sabit 180 sn DEĞİL. Bu sınır boştaki makinede bol, yüklü makinede yetersiz:
> 48 belgelik bir ablasyon, aynı anda koşan bir ince ayarla çakışınca
> `timed out` ile düştü. … `LLM_STRICT=1` altında zaman aşımı sessiz bir
> kural-only düşüşü değil, gürültülü bir hata üretir — yani sınır fazla dar
> olduğunda **ölçüm kaybedilir, bozulmaz**.»

### 6.11 Sözcük sınırlı eşleşme (`synonyms.keyword_pattern`)
291 belgelik gerçek korpusta ölçüldü:
```
'ev'  (Konut Finansmanı anahtarı) -> 'devam', 'seviye', 'evet', 'evrak' içinde eşleşiyor
'fon' (Yatırım Ürünü anahtarı)    -> 'fonksiyon' içinde eşleşiyor
```
Sonuç: "Modanisa'da %15 indirim" ve "hisse senedi işlemleri" gibi belgeler
**Konut Finansmanı** olarak sınıflanıyordu. **Korpusun %48'i sahte Konut
Finansmanı çıkmıştı.** Kural: ≤4 karakter → iki taraftan sınırlı; uzun
anahtarlar sol sınırlı (Türkçe sondan eklemeli, "konutunuz" eşleşmeli).

### 6.12 §5.2 nitel iddialar sayıya çevrilmez
`QUALITATIVE_RATE_CLAIMS` ("avantajlı kâr payı", "özel oranlı", "düşük
maliyetli"…) yalnızca **tanınır**, `kar_payi_orani`'na yazılmaz:
> «Bunlardan bir oran üretmek halüsinasyondur ve CLAUDE.md §19'un ("bilgi
> yoksa null") doğrudan ihlalidir.»
Pratik değeri: oran vermeyen bir kampanya, oran verenle **kıyaslanamaz**; adil
kıyas garantisi bunu "doğrudan kıyaslanamaz" diye işaretlemeli — sessizce
sıralama dışı bırakmak yerine.

### 6.13 §5.5 terminolojisi kural katmanına da indirildi
İki kavram (finansman maliyeti, katılım fonu) 31 Tem'e kadar **yalnızca LLM
prompt'unda** tanımlıydı — «yani LLM kapalıyken, ki offline varsayılanımız bu,
sistem o kavramları hiç bilmiyordu.» `TERMINOLOGY_5_5` ayırt etme içindir,
değer çıkarma değil; özellikle "finansman maliyeti" (TL) ile "kâr payı oranı"
(%) karıştırılmamalı.

### 6.14 Gümüş hat: model repoya konamaz, sözleşme konur
> «Etiketleyici model **repoya konamaz**. Şartname §5.10 açık kaynak olmayan
> bağımlılığı yasaklıyor… Repodaki kod bu iki dosyayı **tüketir, üretmez**.»

Prompt şablonları repoda: «"Bir LLM etiketledi" bir yöntem açıklaması değildir.»

Kırpma penceresi 6000 → **24000** kararı ölçüldü (2026-08-04,
`data/raw-classic/*/products/`, 106 ürün belgesi) — sınıfı gerekçelendiren
alıntının konumu:
```
Yapı Kredi (10 belge)  : ~17.500-18.400 karakter
Garanti BBVA (10 belge): ~6.000-6.200 karakter
kalan 76 belge         : < 6.000 karakter
```
Yani etiketlenebilir **96 belgenin 20'sinde (%21)** gövde pencerenin tamamen
dışındaydı. «Daha kötüsü **sessiz bir başarısızlıktı**: `consensus.decide`
kanıtı TAM metinde arıyor, denetleyici ise kırpılmış metinde.»

Denetleyicinin `own_label`'ı ayrı alan olması kasıtlı: «Aksi hâlde denetleyici
**lastik damgaya** döner (bilinen başarısızlık kipi) ve iki oy aslında tek oy
olur.» Kural katmanının **veto hakkı yok**, yalnız güveni yükseltir — çünkü
kendi ölçülmüş hatası var (%48 sahte Konut Finansmanı).

### 6.15 Offline zorlaması koşulsuz
`BerturkClassifier` `local_files_only=True` **koşulsuz** veriyor:
> «Bayrak olmadan `transformers`, eksik bir yardımcı dosya için (tokenizer,
> config) **sessizce ağa çıkar** — çevrimdışı makinede bu, yükleme anında değil
> ÇALIŞMA ANINDA patlar. … kod konteyner dışında da koşuyor ve doğruluğu ortam
> değişkenine bağlı olmamalı.»

Lisans beyanı da düzeltilmiş: `dbmdz/bert-base-turkish-cased` →
`cardData.license = "mit"`, `base_model` beyanı YOK.
> «Bu satır eskiden "Apache-2.0" diyordu; ikisi de izinli listede ama **yanlış
> lisans beyanı uyumluluk iddiasını çürütür**.»

---

## 7. Tuzaklar

### 7.1 YENİ DÜZELTİLMİŞ — `ihtar.py` (genel yasal ihtar)
«Bankamız … kampanya koşullarını değiştirme … hakkını saklı tutar.» cümlesi
**koşul değildir**; her metinde birebir geçtiği için kıyasta sıfır ayırt edici
bilgi taşır.
**Kusurun şekli:** kural önce yalnız ANOTASYON tarafında uygulandı
(`kalibrasyon_hakemlik.py`, `kosul-ihtar`, **18 hücre** temizlendi) ama ÇIKARICI
cümleyi üretmeye devam etti. Sonuç ölçüldü (2026-08-09):
- **20 kalibrasyon belgesinin 5'inde** model değeri ihtar cümlesi taşıyor, gold
  taşımıyor — yani model o satırlarda **haksız yere** yanlış sayılıyordu.
- `data/demo.db` genelinde aynı sızıntı **1774 belgenin 248'inde** vardı.

**Genel ders (bu depoda tekrarlanan hata sınıfı):** *desen iki kopya olarak
yaşarsa hata sessizce geri gelir.* Aynı sınıf `_ORAN_TABLOSU_BASLIK_RE`'de de
oldu (%37 kanıtsız değer) ve `NEGATION_RE`'nin `normalize.py`'den yeniden ihraç
edilmesinin de sebebi bu. `tests/test_ihtar_tek_kaynak.py` kapıda tutuyor.

### 7.2 YENİ DÜZELTİLMİŞ — tahsis ücreti oranı
İki yönü var:
- **Tabloda olmayan kolonu okumak** (`_TAHSIS_KOLON_RE`): tahsis ücreti eskiden
  "kâr payından sonraki ilk makul yüzde" diye tahmin ediliyordu. `data/demo.db`
  ölçümü (2026-08-09): oran tablosundan üretilen **19 `tahsis_ucreti`
  değerinin 4'ü** tabloda hiç bulunmayan bir kolondan geliyordu — **%3,80 ve
  %8,07** aslında "Aylık/Yıllık Maliyet Oranı" (Kuveyt Türk), **%0,00** ise
  yalnızca "Vade / Kredi Tutarı / Kâr Oranı" kolonları olan bir tablodan
  (Albaraka TOGG). «Değer metinde YOKTU; bu bir halüsinasyondur ve üstelik
  **"%0,00 tahsis" en zararlı biçimidir: kampanyayı ücretsiz gösterir.**»
- **Oranı `tahsis_ucreti`'ne yazmak**: `{"rate": X}` üç şeyi aynı anda
  bozuyordu — (1) şema ihlali (`lint_review_csv` round1'de **10 hatanın 9'u**),
  (2) `compare._scalar` zaten `None` döndürüyor (adil kıyas: %0,50 ile 500 TL
  aynı sütunda sıralanamaz), (3) gold F1 **0.400 → 0.333**.
  Bilgi kaybolmuyor: `masraf_durumu = {"has_fee": true, "amount": null}` —
  "ücret VAR, TL tutarı metinde YOK".

### 7.3 YENİ DÜZELTİLMİŞ — taksit sayısı zaman damgası
`extract_taksit`, "02.01.2026 **00:00:00** Taksitli Ticari Taşıt Finansmanı"
metninden **`taksit_sayisi = 0`** üretiyordu. Bkz. §4.4. Kalan risk: koruma
`(?<![:.,\d])` sola bakıyor; sağdan gelen bir bağlam ("… 12 taksit sonrası")
hâlâ ilk geçerli eşleşmede durur.

### 7.4 Halüsinasyon üretebilecek yerler (hâlâ açık ya da kısmen kapalı)
1. **`extract_odul_miktari` — koşul/ödül karışması.** ±30 karakter penceresi
   "500 TL alışveriş yapana 50 TL hediye" gibi cümlelerde koşul tutarını
   ödül sanabilir. Sol-öncelik + en-yakın seçimi azaltıyor, **elemiyor değil**.
2. **`extract_indirim_orani` tek `search` kullanıyor.** Diğer alanlar
   `finditer`'a geçirilmişken burası ilk eşleşmede duruyor; belgede birden çok
   indirim oranı varsa sonuç yazım sırasına bağlı.
3. **`kampanya_tarih_araligi` son dalı**: rolsüz tek tarih **bitiş** sayılıyor.
   Belgede yalnız bir başlangıç tarihi varsa ve tetikleyici yoksa bu yanlış
   ve **sessiz** olur.
4. **`extract_kar_payi` ilk geçerli eşleşmeyi döndürüyor.** Çok ürünlü
   sayfalarda hangi ürünün oranının kazandığı belirsiz — güven düşer ama seçim
   değişmez.
5. **LLM `source_span` uydurması**: `_locate` offset üretmezse alan yine de
   kaydedilir (`raw_value = span_text`, `span_start = None`). Yani **temel
   akışta** (orkestrasyon yokken) kanıtsız bir LLM değeri uzlaştırmaya girebilir.
   Kanıt kapısı yalnız `LLMOrchestrator` yolunda var — ve o yol üretimde
   çalışmıyor (§2.3).
6. **`parse.py::_kapanmamis_dizgeyi_onar`** JSON'u onarıyor. Dar tutulmuş
   (üç koşul birlikte) ama yine de içerik üzerinde bir varsayım. Ölçüm:
   `qwen2.5:7b-instruct` **8 belgede 4 kez** kapanış tırnağını düşürüyordu.
7. **`_single_to_double_quotes`** son çare dönüşümü: metinde çift tırnak yoksa
   tüm tek tırnakları çift yapıyor. Türkçe kesme işareti (`'`) yerine düz `'`
   kullanılmış bir çıktıda bozma riski var (kod `'` ve `’` ayrımını burada
   yapmıyor).

### 7.5 Sessiz başarısızlıklar
1. **`LLM_BACKEND` boşsa hiçbir şey uyarmaz** — `default_extractor()` sadece
   `logger.info` basar ve sistem kural-only koşar. Eval tarafında bu
   `unavailable_reason` ile açığa çıkıyor; API/dashboard tarafında çıkmıyor.
2. **`LLMExtractor.extract()` hoşgörülü modda boş liste döndürür.** Hata
   `self.stats` ve `self.last_result`'ta duruyor ama **çağıran onlara bakmak
   zorunda değil** — `reconcile()` bakmıyor.
3. **`_to_fields` şema ihlallerini yalnız loglar** (`violations`), çağırana
   bir istisna dönmüyor; `LLMCallResult.error` `None` kalıyor, yani
   `LLM_STRICT` bile bunu yakalamıyor.
4. **`BerturkClassifier` her başarısızlıkta RuleHint'e düşüyor** — davranış
   kasıtlı ama «model beklerken kural koşuyorsa çıktıyı okuyan kişi hangi kolun
   ölçüldüğünü bilemez». Görünürlük eklenmiş (log), ama dönüş değerinde
   hangi kolun koştuğu **yok**.
5. **`extract_kampanya_kosullari`'nda `text.find(first)`** — bulunamazsa
   `span_start/span_end = None` ve `raw_value = first` olur; alan yine de
   üretilir, ama offset'siz. Dipnottan gelen koşullarda bu normal (dipnot
   metni `.strip()`'li).
6. **`_field(conf=…)` yolu kullanılmıyor** ama `_RULE_CONF = 0.95` sabiti
   dosyada duruyor; okuyan biri "kural katmanı 0.95 veriyor" sanabilir.
   Gerçekte hepsi `rules/confidence.score()` üzerinden geçiyor.
7. **`FIELD_TRIGGERS` (synonyms.py) `extract.py` tarafından okunmuyor.**
   Tetikleyiciler her fonksiyonun kendi regex'inde. İkisi ayrışırsa hiçbir test
   bunu yakalamaz — §7.1'in aynı hata sınıfı, henüz gerçekleşmemiş hâli.
   (**belirsiz:** ayrışma olup olmadığını bu incelemede alan alan
   doğrulamadım.)
8. **Orkestrasyonda sadeleştirme kolu** `source_span`'i **değiştirilmiş metne**
   bağlıyor; kaynak vurgulama özgün belgeye götürmüyor. Bu bedel modül
   başlığında yazılı ve kol varsayılan olarak **kapalı**.

### 7.6 Kod okurken yanıltabilecek noktalar
- `_PRIORITY`'de `Extractor.NER` görünüyor ama üretilmiyor (§2.2).
- `reconcile.py` docstring'i 77 satır ve iki ayrı tarihli karar taşıyor
  (2026-07-31 ve 2026-08-08); ikisi de hâlâ geçerli.
- `run.py` CLI'ı `LLM_BACKEND`'e duyarlı, `pipeline.py` de öyle — ama
  `api/main.py:580` (`build_campaign(text, bank_slug=bank_slug)`) **LLM'siz**
  çağırıyor, `api/main.py:1244` (canlı çıkarım ucu) `llm=llm` ile çağırıyor.
  Aynı uygulamada iki farklı davranış.
- `silver/` paketi `extraction/` altında ama çıkarım hattının parçası değil.

---

## 8. Hızlı referans

| Alan | Fonksiyon | Kanonik tip | En kritik koruma |
|---|---|---|---|
| `kar_payi_orani` | `extract_kar_payi` / tablo | `float` \| `{min,max}` | ceza + türev + yabancı kavram + paylaşım |
| `finansman_tutari` | `extract_tutar` | `{value,currency}` | cümle sınırı, varlık fiyatı, örnek tablo |
| `vade_ay` | `extract_vade` / tablo | `int` | takvim yılı, `MAKS_VADE_AY=600` |
| `taksit_sayisi` | `extract_taksit` | `int` | zaman damgası, `>= 1` |
| `tahsis_ucreti` | `extract_tahsis_ucreti` | `{value,currency}` | taban adlandırılmazsa hesap yok |
| `masraf_durumu` | `extract_masraf` (+tablo yedek) | `{has_fee,amount}` | masrafsız her sırada kazanır |
| `odul_miktari` | `extract_odul_miktari` | `{value,currency}` | ödüle en yakın tutar |
| `indirim_orani` | `extract_indirim_orani` | `float` | `puan` bağlamı → üretme |
| `alisveris_puani` | `extract_alisveris_puani` | `{kind,value}` | krom filtresi + birim zorunlu |
| `kampanya_suresi` | `extract_kampanya_suresi` | ISO tarih | başlangıç≠bitiş, kanun atfı |
| `kampanya_kosullari` | `extract_kampanya_kosullari` | `list[str]` ≤8 | boilerplate + ihtar + dipnot |
| `hedef_kitle` | `extract_hedef_kitle` | `list[str]` | negasyon penceresi |

**Ortam değişkenleri:** `LLM_BACKEND` (`vllm`\|`ollama`\|boş), `LLM_STRICT`,
`VLLM_URL` (vars. `:8001`), `VLLM_MODEL` (vars. `Qwen/Qwen3-8B`),
`VLLM_STRUCTURED_MODE`, `LLM_DEADLINE_CARPANI` (vars. 1.5), `OLLAMA_URL`,
`OLLAMA_MODEL` (vars. `qwen2.5:7b-instruct`), `OLLAMA_TIMEOUT` (vars. 180),
`OLLAMA_KEEP_ALIVE` (vars. `30m`), `OLLAMA_NUM_CTX` (vars. 8192),
`OLLAMA_NUM_PREDICT` (vars. 512 — **özet yolunun** bütçesi),
`LLM_EXTRACT_NUM_PREDICT` (vars. 1536 — **çıkarım yolunun** bütçesi, §6.9),
`BERTURK_MODEL_DIR`.
