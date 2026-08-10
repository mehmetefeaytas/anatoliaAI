# Kod Haritası — Veri Katmanı

> Salt okur kod haritası. Kapsam: `src/db/`, `src/normalization/`,
> `src/preprocessing/`, `src/rag/`, `src/summarize/`, `src/schemas.py`,
> `src/pipeline.py`.
> Okuma tarihi: 2026-08-09. Bu belge kod okumasından üretildi; buradaki her
> sayı ilgili modülün docstring'inden **aynen** alınmıştır.
>
> Not: `src/config.py` **yoktur**. Yapılandırma iki yerden gelir: ortam
> değişkenleri (`DATABASE_URL`, `DATABASE_PATH`, `RAG_RETRIEVER`,
> `EMBEDDING_MODEL_DIR`, `EMBEDDING_MODEL`, `OLLAMA_NUM_CTX`) ve
> `src/scraping/config.py` (`config/banks.yaml`).

---

## 1. Bir cümlelik özet

Veri katmanı, tek bir depo sözleşmesinin (`RepositoryProtocol`) arkasına
konmuş iki backend'den (stdlib SQLite = offline/test, PostgreSQL+pgvector =
üretim) ve bu depoya yazılmadan önce metni Türkçeye-doğru katlayan / kanonik
birime çeviren saf-stdlib bir ön işleme + normalizasyon zincirinden oluşur;
RAG ve özet katmanları bu deponun **üstüne** oturur ve ikisi de üretim
kararlarına girmez.

---

## 2. Depo sözleşmesi

### 2.1 `RepositoryProtocol` (`src/db/base.py:98-143`)

`runtime_checkable` bir `Protocol`. Bir alan + 15 metot:

| Üye | İmza | Yön |
|---|---|---|
| `backend` | `str` (`'sqlite'` \| `'postgres'`) | okuma |
| `upsert_bank` | `(name, slug, website_url=None, bddk_active=True) -> int` | yazma |
| `insert_campaign` | `(c: Campaign, clean_text=None, scraped_at=None) -> int` | yazma |
| `set_belge_turu` | `(atamalar: Mapping[int, Optional[str]]) -> int` | yazma |
| `set_ozet` | `(atamalar: Mapping[int, Optional[str]]) -> int` | yazma |
| `field_value` | `(campaign_id, field_name) -> Any` | okuma |
| `query_fields` | `(field_name, *, sozlesme_dahil=False) -> list[dict]` | okuma |
| `campaign_text` | `(campaign_id) -> Optional[dict]` | okuma |
| `all_banks` | `() -> list[dict]` | okuma |
| `counts` | `() -> dict[str,int]` | okuma |
| `belge_turu_counts` | `() -> dict[str,int]` | okuma |
| `field_coverage` | `(*, sozlesme_dahil=True) -> dict[str,int]` | okuma |
| `campaigns_per_bank` | `() -> dict[str,int]` | okuma |
| `fields_by_extractor` | `(*, sozlesme_dahil=True) -> dict[str,int]` | okuma |
| `all_campaigns` | `(*, belge_turu=None) -> list[dict]` | okuma |
| `close` | `() -> None` | — |

**`sozlesme_dahil` varsayılanlarının asimetrisi bilinçlidir:**
`query_fields` → `False` (kıyas yolu, akit elenir);
`field_coverage` / `fields_by_extractor` → `True` (üretim ölçüsü, akit de
gerçekten üretilmiş alandır).

### 2.2 Ayrışmayı önlemek için merkezileştirilenler

Üç şey iki backend'de **kopyalanmaz**, tek yerde durur:

- `belge_turu_dogrula()` (`base.py:57`) — tek doğrulama noktası. Şemada
  `CHECK` **yoktur**, çünkü SQLite `ALTER TABLE ADD COLUMN` ile CHECK eklemeye
  izin vermez; kısıt yalnız `CREATE TABLE`'a konsaydı sıfırdan kurulan DB ile
  göçle güncellenen DB farklı davranırdı.
- `kiyas_where()` (`base.py:77`) — üretilen SQL:
  `(c.belge_turu IS NULL OR c.belge_turu <> 'sozlesme')`. Değer SQL metnine
  **gömülür**, yer tutucu kullanılmaz, çünkü `sqlite3` `?`, `psycopg` `%s`
  bekler ve parça iki backend'de birebir aynı metin olmalıdır.
- `finalize_campaign_text()` (`base.py:146`) — `campaign_text()` çıktısının
  JSON çözümü + `span_verified` denetimi.

`ThreadSafeRepository` (`base.py:178`) iki backend için ortak `RLock`
serileştirmesidir; `factory.create_repository(thread_safe=True)` onu kurar.

### 2.3 AYRIŞMA HARİTASI — nerede farklılar

> Her satır bir risktir. "İki backend destekliyoruz" iddiasının tek kabul
> kriteri aynı soruya aynı cevaptır.

| # | Konu | SQLite (`repository.py`) | Postgres (`postgres.py`) | Risk |
|---|---|---|---|---|
| A | **NUL (0x00) baytı** | Hiç denetlenmez; sessizce yazılır | `_text()` ile denetlenir, `on_nul='error'` varsayılan | ⚠️ **Ölçülmüş**: 849 belgelik korpusta kuveyt-turk belgesinde 352 NUL. Aynı korpus SQLite'ta geçer, Postgres'te patlar |
| B | `set_ozet()` NUL denetimi | **Yok** | `_text(v,"ozet",...)` var | ⚠️ Özet metninde NUL varsa SQLite kabul eder, Postgres reddeder |
| C | `_SONRADAN_EKLENEN` vs `_LATER_COLUMNS` | 5 sütun: `extracted_fields.span_start/span_end/confidence_source`, `campaigns.belge_turu/ozet` | 7 sütun: yukarıdakiler **+ `embeddings.chunk_index` + `embeddings.model`** | ⚠️ **Asimetrik.** Postgres'in kendi yorumu bunu yasaklıyor ("iki liste ayrışırsa bir backend sütunu olan, diğeri olmayan bir şemayla koşar") ama liste bugün ayrışık. `chunk_index`/`model` eklenmeden önce oluşmuş bir `.db` dosyasında `SqliteVectorStore.replace_campaign()` INSERT'i patlar |
| D | `extractor` CHECK kısıtı | `CHECK (extractor IS NULL OR extractor IN ('rule','ner','llm'))` — yalnız `CREATE TABLE`'da | `CHECK (extractor IN ('rule','ner','llm'))` | ⚠️ SQLite tarafında kısıt **eski dosyalara geçmez**: `CREATE TABLE IF NOT EXISTS` mevcut tabloda no-op'tur, `_migrate()` de CHECK ekleyemez. Diskteki `data/demo.db` kısıtsız olabilir |
| E | `field_value()` | `SELECT ... fetchone()`, `LIMIT` yok, `ORDER BY` yok | `... LIMIT 1`, `ORDER BY` yok | Aynı alan iki kez yazılmışsa hangi satırın döneceği **iki tarafta da tanımsız** ve farklı olabilir |
| F | `scraped_at` | ISO metni **olduğu gibi** TEXT'te | `TIMESTAMPTZ`; okurken `_SCRAPED_AT_ISO` ile ISO-8601 UTC'ye geri çevrilir | **KASITLI**: girdi `+03:00` ise okunan değer UTC'ye normalize dönmüş olur. Modül başlığında yazılı |
| G | `bddk_active` | INTEGER 0/1, `all_banks()` içinde `bool()` | BOOLEAN, `all_banks()` içinde `bool()` | Parite iki dönüşümle sağlanmış (`1` vs `true` JSON'a sızmıyor) |
| H | Okuma işlemi | İşlem yönetimi yok | `_read()` bağlam yöneticisi her okumadan sonra `rollback()` | Postgres'te bu olmadan bağlantı `idle in transaction` kalır (bkz. §8) |
| I | Protokol dışı yüzey | `conn` | `conn`, `dsn`, `on_nul`, `ensure_schema()`, `_migrate()` | ⚠️ `ThreadSafeRepository`'nin `__getattr__`'ı **yoktur**: sarılmış bir Postgres deposunda `repo.ensure_schema()` `AttributeError` verir |

**Halihazırda kapatılmış ayrışmalar** (kod yorumlarında hata olarak
işaretlenmiş): `query_fields`'ta `ORDER BY f.id`, `field_coverage` /
`fields_by_extractor`'da ikincil `ORDER BY ... , field_name` / `, extractor`,
`all_campaigns`'te `ORDER BY c.id`. Üçü de "Postgres yolunda vardı, SQLite'ta
yoktu" diye eklenmiş.

### 2.4 Backend seçimi (`factory.py`)

```
DATABASE_URL dolu  -> PostgresRepository(DATABASE_URL)         [üretim / pgvector]
DATABASE_URL boş   -> Repository(DATABASE_PATH | ':memory:')   [offline / test]
```

`psycopg` yoksa **sessiz düşme yok**: `PsycopgUnavailable` yükselir.
`postgres` alt modülü `src/db/__init__.py`'de bilerek import edilmez ve
`factory` içinde tembel import edilir — offline ortamda `import src.db`
çökmemeli.

---

## 3. Şema

Kaynak: `src/db/schema.sql` (Postgres, hedef) ve `repository._SQLITE_SCHEMA`
(uyumlu alt küme).

### `banks`
| Kolon | Tip (PG / SQLite) | Yazan | Okuyan |
|---|---|---|---|
| `id` | SERIAL / INTEGER PK | `upsert_bank` | JOIN'ler |
| `name` | TEXT NOT NULL | `upsert_bank` ← `pipeline.run_pipeline` (bank.name) | `all_banks`, `query_fields` (`bank_name`), `campaign_text` |
| `slug` | TEXT UNIQUE NOT NULL | `upsert_bank` | `all_banks`, `campaigns_per_bank`, retriever'ların `bank_slug` alanı |
| `website_url` | TEXT | `upsert_bank` | `all_banks` |
| `bddk_active` | BOOLEAN / INTEGER | `upsert_bank` | `all_banks` (her iki tarafta `bool()`'a çevrilir) |

> `insert_campaign` bankayı `upsert_bank(c.bank_slug, c.bank_slug)` ile açar —
> yani doğrudan çağrıldığında `name` = slug olur. Gerçek ad yalnız
> `run_pipeline`'ın ayrı `upsert_bank(bank.name, bank.slug, ...)` çağrısından
> gelir; `upsert_bank` var olan satırı **güncellemez**, id döndürür.

### `campaigns`
| Kolon | Tip | Yazan | Okuyan |
|---|---|---|---|
| `id` | SERIAL / INTEGER PK | — | her yer |
| `bank_id` | INTEGER FK→banks | `insert_campaign` | JOIN'ler, `counts`, `campaigns_per_bank` |
| `raw_text` | TEXT NOT NULL | `insert_campaign` ← `Campaign.raw_text` | `campaign_text`, `all_campaigns`, `KeywordRetriever.reindex`, `VectorRetriever._meta`, `build_embeddings.chunk_text`, `api._cerceve` |
| `clean_text` | TEXT | `insert_campaign(clean_text=...)` ← `pipeline`'da `normalize_text(doc.clean_text)` | `campaign_text` → `finalize_campaign_text` (span referansı) |
| `source_url` | TEXT | `insert_campaign` | `campaign_text`, `query_fields`, pasaj sözlükleri |
| `scraped_at` | TIMESTAMPTZ / TEXT | `insert_campaign(scraped_at=...)` ← `RawDoc.scraped_at` | `campaign_text`, `query_fields`, `all_campaigns` — çelişki tespitinin `as_of` girdisi |
| `campaign_type` | TEXT | `insert_campaign` ← `classifier.classify()` (8 sınıf) | `campaign_text`, `query_fields`, `all_campaigns` |
| `belge_turu` | TEXT | **yalnız** `set_belge_turu()` ← `scripts/build_demo_db.py:184` | `kiyas_where()` (SQL içinde), `belge_turu_counts`, `all_campaigns(belge_turu=)`, `campaign_text` |
| `ozet` | TEXT | **yalnız** `set_ozet()` ← `scripts/build_summaries.py:_yaz` | `campaign_text`, `all_campaigns` → `rag._ozet_alani()`, `api._ozeti_var()` |

`campaign_type` ile `belge_turu` **farklı sorulardır**: ilki kampanyanın 8
sınıflık türü (Konut Finansmanı, Kart, …), ikincisi belgenin kampanya sayfası
mı akit/tarife metni mi olduğu.

### `extracted_fields`
| Kolon | Tip | Yazan | Okuyan |
|---|---|---|---|
| `id` | SERIAL / INTEGER PK | — | `ORDER BY f.id` (parite) |
| `campaign_id` | INTEGER FK | `insert_campaign` | JOIN, `campaign_text` |
| `field_name` | TEXT NOT NULL | `insert_campaign` ← `ExtractedField.field_name` | `query_fields`, `field_value`, `field_coverage` |
| `raw_value` | TEXT | `insert_campaign` | `finalize_campaign_text` (span doğrulaması), `/compare` |
| `canonical_value` | TEXT (**JSON metni**) | `insert_campaign` (`json.dumps(..., ensure_ascii=False)`) | `query_fields` / `field_value` / `finalize_campaign_text` (`json.loads`) |
| `confidence` | REAL | `insert_campaign` | `/compare`, kalibrasyon |
| `source_span` | TEXT | `insert_campaign` | arayüz (±40 karakterlik pencere metni) |
| `extractor` | TEXT + CHECK | `insert_campaign` ← `f.extractor.value` | `fields_by_extractor` (ablasyon) |
| `span_start` / `span_end` | INTEGER | `insert_campaign` | `finalize_campaign_text` → `span_verified`, kaynak vurgulaması |
| `confidence_source` | TEXT | `insert_campaign` ← `getattr(f,"confidence_source",None)` | ECE / kalibrasyon |

### `embeddings`
| Kolon | Tip | Yazan | Okuyan |
|---|---|---|---|
| `id` | SERIAL / INTEGER PK | — | — |
| `campaign_id` | INTEGER FK | `store.replace_campaign` | `VectorRetriever._meta` eşlemesi |
| `chunk_index` | INTEGER NOT NULL DEFAULT 0 | `replace_campaign` (enumerate) | `VectorHit.chunk_index` |
| `chunk_text` | TEXT | `replace_campaign` ← `chunking.chunk_text` | `VectorHit.chunk_text` → pasajın `chunk` alanı |
| `vector` | `vector(1024)` / BLOB (float32) | `replace_campaign` | `PgVectorStore.search` (`<=>`), `SqliteVectorStore.search` (Python kosinüs) |
| `model` | TEXT | `replace_campaign` ← `embedder.name` | karışık korpus tespiti |
| — | `UNIQUE (campaign_id, chunk_index)` | | yeniden gömmede hedefleme |

İndeksler: `idx_fields_campaign`, `idx_fields_name`, `idx_campaigns_bank`
(yalnız PG), `idx_embeddings_campaign`, `idx_embeddings_vector`
(IVFFlat, `vector_cosine_ops`, `lists = 32`).

---

## 4. Normalizasyon kuralları (`src/normalization/normalize.py`)

Tümü saf, yan etkisiz, `None` güvenli. Bulamazsa `None` döner — asla uydurmaz.

| Kural | Fonksiyon | Kanonik biçim | Sınır vakaları |
|---|---|---|---|
| **TR sayı** | `parse_tr_number` | `float` | `1.500,00`→1500.0; `%2,05`→2.05; `2.05`→2.05; **çok gruplu binlik** `2.500.001`→2500001 (tüm parçalar 3 haneliyse); tek nokta + 3 hane → binlik, 1-2 hane → ondalık; baş/son ayıraç kırpılır (`1,89,`); rakam yoksa `None` |
| **Oran** | `normalize_rate` | `float` veya `{"min","max"}` | Aralık ayırıcıları: `- – — ile ila arası arasında /`. Aralık tek değere **indirgenmez**. `collapse_degenerate_range` ile `{min:X,max:X}`→`X` |
| **Oransal ücret** | `parse_oran_ifadesi` | `float` (yüzde) | 4 yazım: `%2,5`, `2,5%`, `yüzde 2,5`, **`binde 5` → 0.5**. "binde"/"yüzde" karışırsa 10 kat hata. `500 TL`→`None` |
| **Oransal ücret hesabı** | `hesapla_oransal_ucret(oran, taban)` | `({"value","currency"}, formül_metni)` | `taban is None` / `taban<=0` / `oran<0` → `None`. Formül döner çünkü hesaplanan değer metinde **geçmez**, `source_span` ile gösterilemez |
| **TR gösterim** | `bicimle_tr_sayi` | `str` | Tam sayıda ondalık yazılmaz: `2500.0`→`'2.500'` |
| **Para** | `normalize_money` | `{"value": float, "currency": "TRY"}` | `tl ₺ try "türk lirası" lira`, **katlanmış** sözlükle (`tr_fold_ascii`) → ALL-CAPS `TÜRK LİRASI` eşleşir. Birim bulunamazsa yine `TRY` varsayılır |
| **Vade** | `normalize_term_months` | `int` (ay) | `12 ay`→12; `1 yıl`→12; `1,5 yıl`→18. Çekim ekleri (`aya, ayda, ayı, yıla, aylık`) desende. Rakam önde şart olduğu için `ayrıca` eşleşmez |
| **Tarih** | `normalize_date` + `_iso` | ISO-8601 `YYYY-MM-DD` | 3 biçim: ISO, `gg.aa.yyyy` / `gg/aa/yyyy`, `gg Ay yyyy`. **`_iso` `datetime.date` ile takvim doğrular**: `31.06.2026`, `30.02.2026`, `29.02.2025` → `None` (eskiden sözdizimsel olarak geçerli ama var olmayan ISO üretiyordu) |
| **Masraf (negasyon)** | `normalize_fee_status` | `{"has_fee": bool, "amount": float\|None}` \| `None` | Aşağıda ayrıca |

### `normalize_fee_status` karar sırası

1. **Serbest token** (`masrafsız`, `ücretsiz`, `dosya masrafı yok`, `sıfır
   masraf`, `tahsis ücreti yok`, …) → `{has_fee: False, amount: 0.0}`
2. Masraf **bahsi** yoksa (`masraf`/`ücret`/`tahsis` geçmiyorsa) → `None`
3. **Fiil negasyonu** `NEGATION_RE` (`alınmaz`, `tahsil edilmez`, `talep
   edilmez`, `yansıtılmaz`, `yoktur`, `muaf`, `bedelsiz`, …) → `has_fee: False`
4. Tutar varsa → `{has_fee: True, amount: money["value"]}`
5. **Oran kanıtı** (`%\s*\d` veya `\d[\d.,]*\s*%`) → `{has_fee: True, amount: None}`
6. **Tahsil fiili** `_CHARGE_VERB_RE` (`alınır`, `tahsil edil(?!me)`, `tabidir`,
   `uygulanır`, `ödenir`, `ücretlidir`, `talep edil(?!me)`, …) →
   `{has_fee: True, amount: None}`
7. Çıplak isim bahsi ("Ücret Tarifesi", "tahsis politikaları") → **`None`**

Adım 7 ölçülmüş bir hatanın düzeltmesidir: kelimenin varlığını kanıt sanmak
(bkz. §8).

`NEGATION_RE` bu modülde tanımlıdır ve `extraction/rules/synonyms.py` onu
**yeniden ihraç eder** — çıkarım ve normalizasyon aynı deseni kullanır.

---

## 5. Ön işleme

### 5.1 `tr_fold` neden var (`clean.py:30`)

Python'un `str.lower()` Türkçe için **hatalıdır** ve bu hata sistemi sessizce
bozar; banka sitelerindeki başlıklar büyük harflidir:

```
'TAŞIT FİNANSMANI'.lower()  ->  'taşit fi̇nansmani'
                                   ^          ^^
       I → i (olması gereken ı)     İ → i + U+0307 (birleşen nokta)
```

Sonuç: `taşıt` anahtarı `taşit` içinde bulunamaz; sınıflandırma ve tetikleyici
eşleşmesi çöker. `tr_fold` önce `I→ı, İ→i` çevirir, sonra `lower()`'a bırakır.

**Önlediği somut hatalar (kodda yazılı):**
- `'ÜCRETSİZ'.lower()` hiçbir token'a eşleşmiyor, `normalize_fee_status`
  `has_fee=True` döndürüyordu — "masrafsız" yazan metni "masraf var" diye
  okuyordu (`_FOLDED_FREE_TOKENS`).
- `KeywordRetriever._tokenize` içinde eskiden `.lower()` vardı ve ALL-CAPS
  banka başlıklarını sessizce kaçırıyordu.

Türevleri: `tr_upper` (simetrik; `'ihtiyaç'.upper()` → `IHTIYAÇ` yerine
`İHTİYAÇ`) ve `tr_fold_ascii` (`tr_fold` + diakritik sadeleştirme + NFKD
birleşen karakter atma) — `Kâr Payı Oranı` ile `KAR PAYI ORANI` aynı forma
iner.

### 5.2 `normalize_text` zinciri

`strip_html` → `_CONTROL_CHARS_RE` (C0 denetim karakterleri, **NUL dahil**;
`\s+` bunları yakalamaz) → NBSP/zero-width temizliği → tipografik tırnak
sadeleştirme → `normalize_whitespace`. TR karakterler **korunur**;
sadeleştirme yalnız `slugify_tr` içindir.

NUL temizliği burada, "en yakın ortak katmanda" yapılır: bir KVKK aydınlatma
PDF'inde 177.768 baytın 352'si NUL'du ve SQLite yutup Postgres reddediyordu.

### 5.3 `split_sentences`

`. ! ?` + boşluk + harf/rakam. **Küçük harf de kabul edilir** — eskiden yalnız
büyük harf aranıyordu ve `"...gerekmektedir. www.cartersoshkosh.com.tr web
sitesinden..."` bölünmüyor, iki cümle tek koşul olarak çıkıyordu (291 belgelik
korpusta değişmez denetimiyle yakalandı). Aşırı bölme riski `_ABBREV`
birleştirmesiyle kapatılır; ondalık sayılar güvende çünkü bölme için araya
**boşluk** şart.

### 5.4 Blok katlama (`blocks.py`) — nasıl çalışır

**Amaç:** site çerçevesini (çerez/KVKK/menü/altbilgi) içerikten ayırmak.
Tek sinyalle (tekrar) iki ayrı soru cevaplanamaz:
- "Bu blok site çerçevesi mi?" → tekrar **iyi** kanıt
- "Bu blok ürünle ilgili mi?" → tekrar **kötü** kanıt

**Üç sinyal, öncelikli: alan-dışılık > sayısal değer > tekrar.**

Akış (`kararlar()`, `blocks.py:246`):

1. `bloklara_ayir()` — `split_sentences` ile böler, `BLOK_CUMLE = 1` (yani
   **cümle düzeyi**). Belgeler HTML çıkarımından tek satır geldiği için düzen
   ipucu yoktur. Cümleler orijinal metinde **sırayla** aranır (imleç ileri
   taşınır) ki aynı cümlenin ikinci kopyası birincinin konumunu almasın.
2. **`anti_skoru`** — `_ANTI_RE`: 14 yüksek kesinlikli ifade deseni (çerez
   politikası, KVKK, 6698 sayılı, aydınlatma metni, veri sorumlusu, gizlilik
   politikası, site haritası, cookie policy…). Tek başına siler, tekrar kanıtı
   aranmaz → yanlış pozitif = doğrudan içerik kaybı, bu yüzden liste dar ve
   **ifade** düzeyinde ("veri" tek başına değil).
3. **Bölge yayılımı** — alan-dışılık bir işaret gördüğünde `YAYILIM_BLOK = 6`
   blok daha sürer. Gerekçe: *"en geç otuz (30) gün içinde ÜCRETSİZ olarak
   sonuçlandırılmaktadır"* cümlesinde hiçbir alan-dışı işaret yoktur; onu KVKK
   yapan şey cümlelerce önce geçen "Kişisel Veri"dir. Bölgeyi ancak
   `deger >= SONDURME_DEGERI = 3` söndürür (düşük tutulursa KVKK metni geri
   gelir).
4. **`sayisal > 0`** (`_DEGER_RE`: yüzde, TL/TRY/₺, ay/yıl/taksit, gg.aa.yyyy)
   → **KORU**, tekrarı ezer. Yalnız sayı+birim bu ayrıcalığı alır: alan
   *sözcüğü* tek başına yeterli sayılınca menü blokları da kurtuluyor ve
   halüsinasyon geri geliyordu.
5. **`tekrar`** (`cerceve_cumleler`, `min_docs = CERCEVE_MIN_BELGE = 3`) → SİL.
   Cümle-DF kullanılır, 8-gram değil: karar birimi cümleye inince cümlelerin
   çoğu 8 sözcükten kısa kaldığı için n-gram sinyali **sessizce hiç
   ateşlenmiyordu** (eşiği değiştirmek sonucu hiç değiştirmedi).
6. **`deger > 0`** → KORU (tekrar eşiğini geçmeyen şablonlaşmış gerçek içerik).
7. Hiç sinyal yok → **KORU** ("çerçeve olduğunu ispatlayamıyoruz").

**Silme değil katlama — pazarlıksız kısıt.** `temizle()` metni gerçekten
kısaltır, ama üretimde kullanılan yol `gorunum_araliklari()` / `gorunur_metin()`
sunum katmanıdır: metin **değişmez**, yalnızca hangi karakter aralığının
katlanacağı bildirilir. Sebep: span offset'lerini silme kaydırır ve projenin
en özgün iddiası (her değer bir karakter aralığına bağlı) sessizce çöker.

`gorunum_araliklari()` **kapsama garantisi** verir:
`araliklar[0].start == 0`, `araliklar[i].end == araliklar[i+1].start`,
`araliklar[-1].end == len(text)`, `"".join(...) == text`. Bloklar arası
boşluklar iki kuralla sahiplenilir: yalnız beyaz karakterse ve iki yanı aynı
kararı taşıyorsa o kararı devralır; **diğer her durumda gösterilir** ("sinyal
yok → KORU" ilkesi sunum katmanında delinmez).

---

## 6. RAG — chunk → embed → store → retrieve

### 6.1 Zincir

```
campaigns.raw_text
  └─ rag.chunking.chunk_text(max=800, overlap=120)     # cümle sınırlı
       └─ rag.embedding.BgeM3Embedder.encode()          # bge-m3, dim=1024, L2-norm
            └─ rag.store.{Pg,Sqlite}VectorStore.replace_campaign()
                 └─ embeddings tablosu
                      └─ chatbot.rag.VectorRetriever.retrieve()
```

Sürücü: `rag/build_embeddings.py` (CLI + `build_embeddings()`).

**`chunking`** — cümle sınırında bölünür çünkü *"İlk 6 ay %0 kâr payı"*
ortadan kesilirse parça `%0`'ı taşır ama `ilk 6 ay` koşulunu kaybeder;
retriever alakalı görünen ama yanlış pasaj döndürür. Cümle tek başına
sığmıyorsa sert karakter kesimine düşülür — sessizce atılmaz.

**`embedding`** — model yoksa `EmbeddingModelUnavailable` yükselir.
İki yanlış davranıştan kaçınılır: sessizce boş vektör dönmek (veri VARKEN
"verimde yok" demek) ve sessizce indirmeye çalışmak (offline iddiasını ihlal).
`local_files_only=True` varsayılan. Yüklenen modelin boyutu 1024 değilse yine
hata — `db/schema.sql`'deki `vector(1024)` ile ayrışırsa INSERT patlar.

**`store`** — `pgvector` Python paketi **bilerek kullanılmıyor**; vektör
`'[0.1,0.2,...]'` metin biçiminde gönderilip sunucuda `::vector`'e çevriliyor
(kullanılmayan bağımlılık ilan etmemek için). `replace_campaign` önce siler
sonra yazar: `UNIQUE` çakışmasına güvenmek parça sayısı azaldığında eski
fazlalık satırları bırakırdı.

**`build_embeddings`** — model yoksa `ran=False`, çıkış kodu 3, sıfır satır.
Boş tabloyu "gömme tamamlandı" diye raporlamak, bu projede daha önce yaşanmış
"bağlantı hatasını BAŞARILI raporlama" hatasının aynısı olurdu. Depo boşsa
çıkış kodu 2.

### 6.2 `KeywordRetriever` vs `VectorRetriever` (`src/chatbot/rag.py`)

| | `KeywordRetriever` | `VectorRetriever` |
|---|---|---|
| **Yöntem** | TF-örtüşme + ters dizin (`token → {belge_id}`) | bge-m3 gömme + kosinüs araması |
| **Bağımlılık** | Sıfır | `sentence-transformers` + dolu `embeddings` |
| **Kaynak** | `repo.all_campaigns()` → `raw_text` | `store.search()` + `all_campaigns()` üstverisi |
| **Eşik** | `MIN_OVERLAP = 2`, `_etkin_esik` ile sorunun anlamlı sözcük sayısını **aşamaz** | `DEFAULT_MIN_SCORE = 0.5` (kalibre **edilmemiş**) |
| **Tekilleştirme** | Belge bazında | `k*5` parça çekilip **kampanya bazında** en iyi parça |
| **Kurulum** | `reindex()` — korpusun fotoğrafı | `reindex()` yalnız üstveriyi tazeler; gömme üretmez |
| **Yokluk davranışı** | — | Model / boş tablo / eksik kampanya → `VectorRetrieverUnavailable` |
| **ÜRETİM YOLU** | ✅ **Evet** | ❌ Hayır — yanına gelir, yerine geçmez |

**Seçim:** `RAG_RETRIEVER` ortam değişkeni, `build_retriever()`:
- `keyword` (**VARSAYILAN**) → yalnız `KeywordRetriever`
- `auto` → vektörü dene, olmazsa **WARNING loglayarak** düş
- `vector` → zorunlu; kurulamazsa hata yükselt

Seçim **görünürdür**: `RagAnswer.retriever` yanıtla taşınır. Sessizce düşmek,
"vektör aramamız var" derken anahtar-kelime araması yapmak olurdu.

**Neden keyword üretim yolu:** anahtar-kelime retriever'ı bugün p99 **12,18 ms**
ve 54 soruda davranışı kilitli; vektör yolu ölçülmüş bir kazanç göstermeden
üretim yolunu değiştirseydi ölçülmemiş bir iddia demoya girerdi.

---

## 7. Özet katmanı (`src/summarize/ozet.py`)

### YAPTIĞI
- `blocks.gorunur_metin()` ile **çerçevesi katlanmış** metni alır (ham metin
  değişmez; katlama yalnız modele giden kopyada).
- `MAKS_GIRDI_KARAKTER = 6000`'i aşarsa kırpar ve kırpmayı
  `OzetSonucu.kirpildi` ile **görünür** bırakır.
- `llm.client.generate_json(SISTEM_PROMPT, ..., SEMA)` ile
  `{"ozet": "..."}` şemasında çağırır (serbest metin parse edilmez).
- Sonucu `OzetSonucu(ozet, kaynak, sebep, kirpildi, girdi_karakter)` olarak
  döndürür; `uzun` özelliği `HEDEF_OZET_KARAKTER = 400` aşımını işaretler
  (aşan çıktı **reddedilmez**).

### BİLEREK YAPMADIĞI
- **Hiçbir karar yolunun girdisi değildir**: kıyas/sıralama
  (`comparison/compare.py`), alan çıkarımı (`extraction/**`), çelişki tespiti
  (`comparison/contradiction.py`), chatbot'un yapısal sorgu yolu
  (`chatbot/structured.py`) — hiçbirine girmez. Sebep: özet doğrulanmamıştır;
  her alan bir karakter aralığına bağlıyken özetin böyle bir dayanağı yoktur.
  Onu ölçüm yoluna sokmak, doğrulanmış kanıt zincirine doğrulanmamış bir halka
  eklemek olurdu.
- **Kural tabanlı sahte özet üretmez.** LLM kapalıysa `ozet=None` +
  `sebep="llm_kapali"`. İlk N cümleyi "özet" diye sunmak, ölçülmemiş bir
  yeteneği ölçülmüş gibi göstermektir. `OZET_KAYNAK_LLM = "llm"` tek geçerli
  kaynaktır.
- **Özeti kendisi yazmaz.** `set_ozet()` çağrısı `scripts/build_summaries.py`
  içindedir; `ozet.py` saf bir üretim fonksiyonudur.
- Boş çıktıyı hata saymaz: `sebep="bos_cikti"`, yine `None` — arayüzde boş bir
  özet kutusu göstermemek doğrudur.

Sebep kodları: `llm_kapali`, `metin_bos`, `llm_hatasi: <TipAdı>`, `bos_cikti`.

**Tüketici tarafı ayrımı** (`chatbot/rag.py`): `_ozet_alani()` yalnız taşır,
üretmez; `kisa_alinti()` adı bilerek "özet" değildir ve çağıran taraf bunu
kullanıcıya **söylemek zorundadır** ("aşağıdaki satır özet değil, ham metnin
başlangıcıdır").

---

## 8. Önemli kararlar ve ÖLÇÜLMÜŞ gerekçeleri

> Sayılar docstring'lerden aynen aktarılmıştır.

**Belge türü ayrımı** (`base.py`, `schema.sql`, `repository.py`)
> Korpustaki **1761** belgenin **113'ü (%6,4)** kampanya sayfası değil,
> sözleşme/tarife/form PDF'idir ve **43'ü** kıyaslanabilir alan (oran/vade/
> tutar) taşıdığı için `/compare` tablosuna karışıyordu.

**`kiyas_where()` biçimi**
> `= 'kampanya'` yerine `IS NULL OR <> 'sozlesme'`: sütunu henüz doldurulmamış
> bir DB'de `= 'kampanya'` **hiçbir satır döndürmezdi** — karşılaştırma tablosu
> sessizce boşalırdı.

**NUL baytı** (`postgres.py`, `clean.py`)
> 31 Tem 2026'da **849** belgelik demo korpusu Postgres'e aktarılırken bir
> belge (kuveyt-turk, **352 NUL** baytı) metin değil ikili çöptü.
> `177.768` baytın `352`'si NUL. Hiçbir alan çıkmadığı için SQLite yolunda
> görünmüyordu.

**`_read()` / `idle in transaction`** (`postgres.py`)
> `tests/test_api_backend.py` `/banks` çağırdıktan sonra `DROP TABLE`
> **sonsuza kadar bloklandı**:
> `pid 255 | idle in transaction | ClientRead | SELECT b.slug AS bank, ...`
> `pid 256 | active | Lock/relation | DROP TABLE IF EXISTS embeddings, ...`
> `autocommit=True`'ya geçmek yanlış çözüm olurdu: `insert_campaign()`
> atomikliğini kaybederdi.

**`ThreadSafeRepository`** (`base.py`)
> `sqlite3.ProgrammingError: SQLite objects created in a thread can only be
> used in that same thread.` — DB'ye dokunan HER uç (`/banks`, `/campaigns`,
> `/compare`, `/chat`) düşüyordu; dashboard'un boş tablo göstermesinin sebebi
> buydu. Postgres tarafında da gerekir: `psycopg` `threadsafety = 2` ilan eder
> ama işlem sınırı bağlantı başınadır.

**`_SONRADAN_EKLENEN`** (`repository.py`)
> 4 Ağu 2026: diskteki **21,6 MB**'lık `data/demo.db` `belge_turu` / `ozet`
> satırları olmadan açıldığında `no such column: belge_turu` ile ölürdü.

**TR sayı — çok gruplu binlik** (`normalize.py`)
> `float("2.500.001")` patlıyor ve fonksiyon `None` dönüyordu; yani
> **1.000.000 ve üzeri TÜM TR-biçimli tutarlar normalize edilemiyordu**
> (2026-08-03'te Kuveyt Türk TOGG tutar bantlarında yakalandı).

**Dejenere aralık** (`collapse_degenerate_range`)
> Colab'da **qwen3:32b**, "kâr payı oranı %1,89" için `{"min":1.89,"max":1.89}`
> döndürdü — değer doğru, gösterim yanlış. `compare.py` min/max içeren HER
> değeri "kıyaslanamaz" sayıp sıralama dışına attığı için gerçek en iyi banka
> kaçırılıyordu.

**Oransal ücret** (`_ORAN_IFADE_RE`)
> Korpus ölçümü (2026-08-07, **1759** belge): tahsis/dosya tetikleyicisi olan
> **101** belgenin **62'sinde** ücret yüzde olarak veriliyor ve bunların
> **51'i hiçbir değer üretmiyordu**. `binde` ile `yüzde` arasındaki **10 kat**
> fark sessizce yanlış sıralama üretir.

**Çıplak isim kanıt değil** (`normalize_fee_status`)
> Korpus ölçümü (**849** belge, 31 Tem 2026): `masraf_durumu`nun **370**
> çıkarımından **158'i** çıplak isimden tetikleniyordu ve hepsi
> `has_fee=True` üretiyordu:
> "Uçak bileti ÜCRETİ dışında..." (**107** vaka), "kredi ve TAHSİS
> politikaları çerçevesinde" (**39** vaka), "MASRAFLARI görüntüleyin" (**12**
> vaka). Etkisi tek alanla sınırlı değildi: `contradiction.detect()` bunları
> **hayalet çelişki** üretiyordu.

**Blok kapsamı** (`blocks.py`)
> Ayıklamanın kaybettiği **8** alanın **7'si** çöptü (KVKK'daki "ücretsiz",
> çerez metnindeki "1 yıl", "Hoş Geldin Ramazan!" afişi, blog başlıkları) ama
> **1'i** gerçek içerikti — her ürün sayfasında geçtiği için silinen meşru bir
> başvuru koşulu cümlesi.

**Ters dizin** (`KeywordRetriever`)
> İlk sürüm her soruda tüm korpusu tokenize ediyordu: **1696** belgelik
> korpusta soru başına **~290 ms**, chatbot p99'unun (**~570 ms**) neredeyse
> tamamı. Şimdi p99 **12,18 ms** (öncesi **576 ms**) ve **54** soruda
> eski/yeni birebir eşdeğerliği kanıtlı (`tests/test_rag_index.py`).

**Oransal eşik** (`_etkin_esik`)
> `docs/rapor/rag-terim-kapsama.md`, 15 fıkhî terim, kanıt şartı dönen pasajın
> terimi gerçekten içermesi:
> korpus **1761** belge, mutlak eşik 2 → **4/15**; oransal eşik → **14/15**.

**Tokenizasyon** (`_tokenize`)
> `'i'` token'ı korpusta **672** belgede geçiyor; "Hüsn-i niyet nedir?" üç
> pasaj döndürüyor ve **hiçbiri iki gerçek terimi de taşımıyordu**.
> `'5'` korpusta **722** belgede geçiyor.
> Şapkalı ünlü indirgemesi: `kâr payı` korpusun **319 belgesinde (%18)**
> şapkalı yazılıyor ve hepsi erişim dizininden düşüyordu; **84** belgedeki
> şapkasız `kar payı` ile artık aynı token.

**Pasajlarda özet taşıma** (`chatbot/rag.py`)
> Belge başına ortalama **4.744** karakter; **1774** belgenin **1005'i (%57)**
> 2.000 karakteri aşıyor, en uzunu **178.825** karakter. Önceden üretilmiş
> özet ortalama **259** karakter.

**Özet bağlam penceresi** (`ozet.py`)
> Ollama'nın varsayılan bağlamı **2048**'dir ve fazlasını sessizce baştan
> kırpar — sistem yönergesi kaybolur. `OLLAMA_NUM_CTX` öntanımı **8192**.
> `MAKS_GIRDI_KARAKTER = 6000` (~2000 token).

**Parçalı yazma** (`scripts/build_summaries.py`)
> Tam korpus koşusu **~1400** belge, belge başına **~6 sn**, yani **~2,5 saat**.
> Tek seferde sonda yazmak o 2,5 saatin tamamını tek bir kesintiye bağlar.
> `YAZMA_PARCASI = 25`.

**Pipeline mod sayıları** (`pipeline.py`, 2026-07-31)
> `fixture` → **3** belge (özyinelemesiz, `data/raw/<slug>/` kökü);
> `corpus` → **849** belge (`**/*.txt`); `live` → değişken (offline: 0).
> Eski demo yolu sessizce 3 belge yükleyip "hazır" diyordu ve
> `GET /contradictions` boş dönüyordu.

**IVFFlat** (`schema.sql`)
> `lists = 32` — teslim korpusu ~**850** belge / birkaç bin parça mertebesinde.
> IVFFlat **yaklaşıktır**; dizin varlığı sorgu doğruluğunun ön koşulu değildir.

---

## 9. Tuzaklar

### 9.1 Sessiz başarısızlıklar

1. **`extractor` CHECK kısıtı eski SQLite dosyalarına geçmez.**
   `CREATE TABLE IF NOT EXISTS` mevcut tabloda no-op'tur ve `_migrate()`
   yalnız `ADD COLUMN` yapar. `repository.py:57-63` bunu zaten bir hata sınıfı
   olarak işaretliyor ama düzeltme yalnız **sıfırdan kurulan** DB'de geçerli.
   Diskteki `data/demo.db` kısıtsız olabilir → geçersiz `extractor` sessizce
   yazılır, aynı yazma Postgres'te hata verir.

2. **`_SONRADAN_EKLENEN` eksik: `embeddings.chunk_index` / `embeddings.model`
   yok.** Postgres tarafında var. Bu iki sütun eklenmeden önce oluşmuş bir
   SQLite dosyasında `SqliteVectorStore.replace_campaign()` INSERT'i düşer;
   `_SQLITE_SCHEMA` da onları yalnız `CREATE TABLE` içinde tanımlıyor.

3. **`set_ozet()` SQLite'ta NUL denetlemiyor.** Postgres `_text()` uyguluyor.
   NUL'lu bir özet SQLite'ta yazılır, aynı veri Postgres'e taşınırken patlar.
   `on_nul="strip"` seçeneği ise **span offset'lerini kaydırır** ve
   `span_verified` sessizce `False` olur (bu yüzden varsayılan değil).

4. **`insert_campaign` SQLite'ta hiçbir metin denetimi yapmaz.** NUL'lu belge
   korpusa girdiğinde SQLite yolunda hiç görünmez — çünkü genellikle o
   belgeden hiçbir alan da çıkmaz.

5. **`field_value()` hangi satırı döndüreceğini garanti etmez.** İki backend'de
   de `ORDER BY` yok. Aynı `(campaign_id, field_name)` iki kez yazılmışsa
   dönen değer backend'e göre değişebilir.

6. **`_iso()` geçersiz tarihte `None` döner.** Bu **doğru** davranış ama
   çağıran taraf `None`'ı "tarih yok" ile karıştırırsa "31 Haziran" yazan bir
   kampanyanın süresi hiç bilinmiyor sanılır.

7. **`normalize_money` birim bulamasa da `TRY` varsayar.** Metinde para birimi
   geçmiyorsa çıplak sayı TRY olarak kanonikleşir.

8. **`upsert_bank` var olan satırı güncellemez.** `insert_campaign` bankayı
   `upsert_bank(slug, slug)` ile açtığı için, `run_pipeline` dışındaki bir yol
   bankayı önce açarsa `banks.name` kalıcı olarak slug kalır.

9. **`normalize_rate` aralık ayırıcısı `/` içerir.** `"%1,99/ay"` gibi bir
   metinde iki sayı bulunursa aralık üretebilir — desen `re.search(_RANGE_SEP)`
   + `len(nums) >= 2` koşuluna dayanır.

### 9.2 Önbellek bayatlığı

10. **`KeywordRetriever` dizini kurulum anının fotoğrafıdır.** Depoya
    kurulumdan sonra eklenen kampanyalar **görünmez**; `reindex()` elle
    çağrılmalıdır. Docstring bunu açıkça yazıyor.

11. **`VectorRetriever.reindex()` gömme üretmez.** Yalnız `campaign_id →
    üstveri` eşlemesini tazeler. Yeni kampanyalar aranabilir olsun diye
    `build_embeddings` ayrıca koşturulmalıdır — aksi hâlde yeni belgeler
    sessizce aranamaz.

12. **`embeddings` ile `campaigns` senkron olmayabilir.** `VectorRetriever`
    bilinmeyen `campaign_id` gördüğünde pasajı atlar ve WARNING loglar —
    ama arama sonucu sessizce kısalır (k'dan az sonuç).

13. **API `_view_cache` / `_blok_cache` / `_contra_cache` / `_cerceve_cache`
    süreç ömrüdür.** `_view_cache` yalnızca **özeti olmayan** kayıtları
    tazeler (`_ozeti_var`); metin, alanlar veya belge türü DB'de değişirse
    API yeniden başlayana kadar bayat kalır.

14. **`build_embeddings` `raw_text`'i parçalar, `clean_text`'i değil.**
    Bugün pipeline ikisini **aynı** metinle doldurduğu için sorun çıkmaz
    (`build_campaign(text=...)` → `Campaign.raw_text = text` ve
    `insert_campaign(clean_text=text)`). Bu eşitlik **yazılı bir değişmez
    değildir**; bozulursa RAG bir metni, span vurgulaması başka bir metni
    kullanır.

### 9.3 İki backend'in ayrışabileceği yerler

15. **`ThreadSafeRepository` `__getattr__` taşımaz.** Yalnız protokoldeki 15
    metodu proxy'ler. Sarılmış bir Postgres deposunda `ensure_schema()`,
    `dsn`, `on_nul` erişilemez.

16. **`repo.conn` kilidin DIŞINDADIR.** `rag/store.py` bağlantıyı doğrudan
    alır ve sorgularını kendi koşturur. `base.py` bunu açıkça yazıyor:
    doğrudan dokunan çağıran `with repo.lock:` almalıdır. API demo yolu
    (`RAG_RETRIEVER=keyword`) buraya girmediği için bugün tetiklenmiyor —
    yani bu **uykuda bir yarış koşulu**.

17. **`src/api/main.py:390-449` ve `scripts/build_summaries.py:98-111`
    bayat savunmalar taşıyor.** `_SUZME_HAZIR = "sozlesme_dahil" in
    inspect.signature(repo.query_fields).parameters` ve
    `getattr(repo, "set_ozet", None)` — her iki backend de bugün ikisini de
    uyguluyor, yani bu dallar **ölü koddur** ama `TODO(G)` metinleri
    "bu backend'de henüz yok" diyor. Yanıltıcı; ayrıca imza yoklaması bir
    sarmalayıcı `*args/**kwargs` kullanmaya başlarsa **sessizce** süzmeyi
    kapatır.

> **GÜNCELLEME (2026-08-10):** Bu kusur KAPANDI. `sozlesme_dahil` ve `set_ozet` dört yüzeyin dördünde de uygulanmış durumda; ölü yetenek yoklamaları ve `TODO(G)` metinleri kaldırıldı (commit `9b02152`). Aşağıdaki tarif ölçüldüğü ANIN kaydıdır.


18. **Ölçüm çelişkisi: 43 mü 41 mi?** Aynı olgu iki farklı sayıyla yazılı:
    `src/db/base.py:44`, `src/db/repository.py:238`, `src/db/schema.sql:35`
    → *"113'ün **43'ü** kıyaslanabilir alan taşıyor"*;
    `src/api/main.py:436` → *"113'ü akit metnidir ve **41'i** kıyaslanabilir
    bir alan taşır"*. İkisi aynı ölçümü anlatıyor. Kaynak
    `docs/rapor/belge-turu.md` ile doğrulanmalı.

19. **`scraped_at` normalizasyonu geri döndürülemez.** Postgres yolunda
    `+03:00` girdi UTC'ye çevrilerek okunur. Çelişki tespitinin `as_of`
    girdisi buradan geldiği için, iki backend aynı korpusta aynı kuralı
    **farklı saat damgasıyla** değerlendirebilir (UTC anı korunur, gösterim
    değişir).

20. **Tip ipuçları somut sınıfa bağlı.** `pipeline.run_pipeline(repo:
    Repository, ...)`, `chatbot/rag.py`'deki `Repository` ipuçları ve
    `build_demo_repo() -> Repository` protokolü değil **SQLite sınıfını**
    işaret eder. Çalışma zamanında Postgres deposu geçmek çalışır, ama tip
    denetimi "yeni metot yalnız bir backend'e eklendi" hatasını burada
    yakalayamaz — `RepositoryProtocol`'ün var oluş amacı tam olarak buydu.

21. **`_migrate()` sütun ekler, kısıt/indeks eklemez.** Her iki tarafta da
    `NOT NULL`, `CHECK`, `UNIQUE` ve indeksler yalnız `CREATE TABLE` /
    `CREATE INDEX IF NOT EXISTS` yolundan gelir. SQLite'ta `CREATE INDEX IF
    NOT EXISTS` her açılışta koşar (indeksler güvende), ama tablo kısıtları
    koşmaz.

---

## İlgili dosyalar

| Yol | Rol |
|---|---|
| `src/db/base.py` | Sözleşme, belge türü doğrulama, `kiyas_where`, `finalize_campaign_text`, `ThreadSafeRepository` |
| `src/db/repository.py` | SQLite uygulaması + `_SQLITE_SCHEMA` + `_SONRADAN_EKLENEN` |
| `src/db/postgres.py` | Postgres uygulaması + NUL politikası + `_read()` + `_LATER_COLUMNS` |
| `src/db/schema.sql` | Postgres şeması (hedef), pgvector + IVFFlat |
| `src/db/factory.py` | `DATABASE_URL` / `DATABASE_PATH` seçimi, `thread_safe` |
| `src/normalization/normalize.py` | Oran / para / vade / tarih / TR sayı / masraf negasyonu |
| `src/preprocessing/clean.py` | `tr_fold`, `tr_upper`, `tr_fold_ascii`, `normalize_text`, `split_sentences`, `slugify_tr` |
| `src/preprocessing/blocks.py` | Blok kararları + görünürlük aralıkları (katlama) |
| `src/rag/chunking.py` | Cümle sınırlı parçalama (800/120) |
| `src/rag/embedding.py` | bge-m3 sarmalayıcı, `EMBEDDING_DIM = 1024` |
| `src/rag/store.py` | `PgVectorStore` + `SqliteVectorStore` + `open_vector_store` |
| `src/rag/build_embeddings.py` | Gömme üretim betiği/CLI |
| `src/summarize/ozet.py` | LLM özeti — yalnız gösterim |
| `src/schemas.py` | `Extractor`, `ExtractedField` (+`verify_span`), `Campaign`, `CAMPAIGN_TYPES` |
| `src/pipeline.py` | scrape → extract → classify → store; `PipelineResult` kapsam raporu |
| `src/chatbot/rag.py` | `KeywordRetriever` (üretim) / `VectorRetriever` / `build_retriever` |
| `docs/veri-katmani.md` | Aynı katmanın **operasyon** belgesi (hangi backend ne zaman) — bu dosya onun kod haritası tamamlayıcısıdır |
