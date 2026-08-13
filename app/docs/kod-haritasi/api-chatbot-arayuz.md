# Kod Haritası — API · Chatbot · Karşılaştırma · Arayüz

> **Kapsam.** Bu belge dört katmanı okur ve birbirine bağlar: `src/api/main.py`
> (1321 satır), `src/chatbot/` (bot · router · structured · rag · safety),
> `src/comparison/` (compare · contradiction) ve `web/app/` (30 dosya: sayfa,
> yerleşim, 19 bileşen, 6 kitaplık modülü, 3 stil dosyası). Toplam ~11.500 satır,
> tamamı satır satır okundu.
>
> **Salt okur.** Bu tur içinde hiçbir kaynak dosyaya yazılmadı.
>
> **EŞZAMANLI DEĞİŞİM UYARISI (2026-08-09).** Bu harita alınırken başka bir ajan
> şu dosyalar üzerinde çalışıyordu; aşağıdaki tarifler o anki hâli anlatır ve
> bayatlayabilir:
>
> | Dosya | Durum (harita anındaki `git status`) |
> |---|---|
> | `src/chatbot/bot.py` | **M — bu turda değişiyor** |
> | `src/chatbot/router.py` | **M — bu turda değişiyor** |
> | `src/api/main.py` | değişmesi bildirildi (o an temiz) |
> | `web/app/components/ChatPanel.tsx` | değişmesi bildirildi (o an temiz) |
> | `web/app/lib/api.ts` | değişmesi bildirildi (o an temiz) |
>
> Özellikle §6'daki "sohbet bağlamı bağlı değil" gözlemi ve §9'daki chatbot
> tuzakları, o ajanın işi bittiğinde geçerliliğini yitirmiş olabilir.

---

## 1. Bir cümle

Tek bir FastAPI süreci, depo sözleşmesi üzerinden okunan önceden doldurulmuş bir
korpusu 13 uçtan sunar; her uç değeri kaynak metindeki karakter aralığına,
üreten katmana ve güven kaynağına bağlı tutar, adil kıyas kapılarını
`src/comparison/` içinde uygular ve Next.js paneli ile hibrit chatbot bu tek
sözleşmeyi tüketir.

---

## 2. API uç envanteri

Tüm uçlar `build_app()` içinde kapanış (closure) olarak tanımlıdır; modül
sonunda `app = build_app()` çağrılır ve `RuntimeError` (fastapi/pydantic yok)
hâlinde `app = None` olur. CORS `allow_origins=["*"]`.

Arayüz tarafında tek çağrı yüzeyi `web/app/lib/api.ts`'deki `api` nesnesidir;
Next `/api/*` yolunu FastAPI'ye proxy'ler (`next.config.js`).

| Yol | Parametreler | Döndürdüğü | Çağıran arayüz bileşeni |
|---|---|---|---|
| `GET /health` | — | `{status, llm: bool, backend}` — `backend` hangi depoya bağlı olduğumuzu **bilerek** açığa çıkarır | **hiçbiri** (`api.ts` sarmalamıyor) |
| `GET /banks` | `otorite_kaynaklari_dahil: bool = False` | Banka listesi; öntanımda `banks.yaml`'da `otorite_kaynak: true` olanlar (TKBB vb.) **süzülür** | `api.banks()` → `BankDeltaPanel` (banka + rakip açılır listeleri) |
| `GET /campaigns` | — | `repo.all_campaigns()` ham çıktısı (`id, bank, bank_name, campaign_type, raw_text, source_url, scraped_at, ozet`) | `api.campaigns()` → `page.tsx`; oradan `AuditPanel` (belge listesi), `campaignTypes` türetimi, `SummaryCoverage` |
| `GET /fields` | — | 12 alan × `{field, label, direction, direction_label, comparable_field}` | `api.fields()` → `page.tsx` → `ComparePanel` → `FieldChips` |
| `GET /campaigns/{campaign_id}/text` | yol parametresi | Metin + `span_reference` + `bloklar` + `ozet`/`ozet_kaynak` + alan başına offset/güven/katman + `contradictions`. 404: "Kampanya bulunamadı" | `api.campaignText(id)` → `AuditPanel`, `ComparePanel`'in `SourceDrawer`'ı |
| `GET /compare` | `field` (zorunlu), `intent∈{lowest,highest,list,filter}`, `type`, `per_bank∈{best,all}` (öntanım `best`) | Satır başına: mevcut sözleşme (`bank, bank_name, value, comparable, note, source_span`) + denetim alanları + `sort_key, rank, contradiction_count, other_count`. Geçersiz `intent`/`per_bank` → **400** | `api.compare(...)` → `ComparePanel` |
| `GET /bank-delta` | `bank` (zorunlu), `type`, `rival` | `{bank, rival, fairness_note, families[]}`; her aile = kampanya türü, her alan = `{kind, abs_diff, rel_pct, position, bank_count, mine, rival}` | `api.bankDelta(...)` → `BankDeltaPanel` |
| `GET /scoring` | `field` (zorunlu), `type` | Tek alan sıralamasının 4 adımlı formülü + `composite_weights` (gerekçeli) + `composite_endpoint` + satırlar | `api.scoring(...)` → `ScoringExplainer` (ComparePanel'in altında) |
| `GET /advantageous` | `type`, `min_coverage: float = MIN_COVERAGE (0,5)` | `{min_group_size, min_coverage, weights, fairness_note, types{tür: {count, note, ranked[]}}}` | `api.advantageous(type?)` → `AdvantageousPanel` |
| `POST /chat` | gövde `{question: str}` | `{answer, handler, field, sources[]}`; her kaynak `campaign_id`/`source_url`/`ozet` alanlarını **her zaman taşır** (bilinmiyorsa `null`) | `api.chat(q)` → `ChatPanel` |
| `POST /extract` | gövde `{text: str, bank: str = "bilinmeyen"}` | Canlı çıkarım: tür + tür güveni + 12 alan (gerçek `ExtractedField` offset'leriyle) + `missing_fields` + `contradictions` | `api.extract(text, bank)` → `ExtractLive` |
| `GET /contradictions` | — | Tüm korpustaki çelişkiler, banka/kampanya bilgisiyle düzleştirilmiş | `api.contradictions()` → `ContradictionAlert` |
| `GET /contradictions/summary` | — | `{scanned_campaigns, scanned_banks, contradiction_count, affected_campaigns, by_kind}` | `api.contradictionSummary()` → `ContradictionAlert` |

**İstek gövdesi şemaları modül seviyesindedir** (`ChatReq`, `ExtractReq`), yerel
kapsamda değil. Gerekçe docstring'de yazılı: `from __future__ import annotations`
yüzünden annotation'lar dizeye dönüşüyor, FastAPI onları **modül global'lerinden**
çözüyor; `build_app()` içinde tanımlıyken `req` bir **query parametresi** sanılıyor
ve iki uç da `422 {"loc": ["query","req"]}` döndürüyordu — yani fiilen
çağrılamıyorlardı.

**Ham SQL yasağı.** Modül docstring'i `repo.rows(<ham SQL>)` kaçış kapısının beş
yerde kullanıldığını ve `?` yer tutucusu taşıdığını (SQLite lehçesi; `psycopg`
`%s` bekler) kaydediyor: Postgres'te her uç `ProgrammingError` verirdi. Beşi de
sözleşme metotlarına çevrildi, `rows()` kaldırıldı. Kural: bu dosyada SQL
yazılmaz.

---

## 3. Önbellekler (`build_app()` kapanışında)

Hepsi **süreç ömrü boyunca** yaşar; TTL, boyut sınırı veya geçersizleştirme
(invalidation) mekanizması **yoktur**. Tek istisna `_view_cache`'in özet
tazelemesidir.

| Önbellek | Anahtar → Değer | Neyi hızlandırıyor | Bayatlama riski |
|---|---|---|---|
| `_view_cache` | `campaign_id → repo.campaign_text()` | `/campaigns/{id}/text` ve `/compare`'in **aynı** metni (`span_reference`) kullanmasını garanti eder; `/compare` her satır için çağırır | **Kısmen korunuyor.** `_ozeti_var()` ile özeti boş olan kayıt önbellekten servis edilmez, her istekte tazelenir — `build_summaries` koşarken jüri aynı belgeyi ikinci açtığında "özet yok" görmesin diye. `None` (bilinmeyen kampanya) hiç tazelenmez. Tazeleme sonrası uzlaştırma (`src/tazeleme_sonrasi.py`) bir özeti DÜŞÜRDÜĞÜNDE ilgili kaydı önbellekten açıkça atar — tersi yön (`dolu → boş`) `_ozeti_var()` kapısına takılmaz, çünkü önbellekteki kopya hâlâ özetli göründüğü için taze sayılırdı. **Özet dışındaki değişiklikler (yeni alan, düzeltilmiş offset) bayat kalır.** |
| `_contra_cache` | `campaign_id → list[dict]` | Kural katmanı + `detect()` kampanya başına bir kez koşar; `/compare`, `/campaigns/{id}/text`, `/contradictions` üçü de paylaşır | **Hiç geçersizleştirilmiyor.** Ayrıca aşağıdaki §9-T1'deki *metin karışması* hatasının taşıyıcısıdır. |
| `_blok_cache` | `campaign_id → görünürlük aralıkları` | `gorunum_araliklari()` bir kez koşar | Hiç geçersizleştirilmiyor. Blok kararları `_cerceve()` çıktısına bağlı olduğu için, çerçeve kümesi sonradan değişse bile bloklar sabit kalır. |
| `_cerceve_cache` | `bank_slug → tekrar eden cümle anahtarları` | `cerceve_cumleler()` banka başına bir kez; tüm korpusu açılışta taramak demonun ilk tıklamasına saniyeler eklerdi (CLAUDE.md §11) | Kurulum anındaki `repo.all_campaigns()` fotoğrafıdır. Sonradan eklenen belge çerçeve frekansını değiştirmez. |
| `_SUZME_HAZIR` | `bool` — `inspect.signature(repo.query_fields)` yoklaması | Her `_field_rows` çağrısında imza yoklamasını önler | Süreç ömrü boyunca sabit; depo değiştirilmediği için sorun değil. **Ama `False` iken sessiz yetenek kaybı üretir** (§9-T3). |
| `Chatbot._retriever` (`bot.py`) | `KeywordRetriever` ters dizini | Docstring: 1696 belgede soru başına ~290 ms → kurulum maliyeti; p99 576 ms → **12,18 ms** | **Kurulum anındaki korpusun fotoğrafı.** `reindex()` var ama **hiçbir uç onu çağırmıyor**; API ayaktayken DB'ye eklenen belge RAG'de görünmez. |

**Önbelleklenmeyen ve pahalı olanlar:**

- `_otorite_kaynak_sluglari()` — `/banks`'in **her** isteğinde `banks.yaml`'ı
  yeniden okur (modül seviyesinde, `try/except` içinde). Config okunamazsa boş
  küme döner ve süzme yapılmaz; karar bilinçli ("eksik liste sessizce yanlış
  kıyas üretir, fazla liste gözle görülür") ve `logger.warning` basar.
- `_field_rows()` — hiç önbelleklenmiyor. `/compare` alan başına 1 sorgu,
  `/bank-delta` **8 sıralanabilir alan** için 8 sorgu, `/advantageous`
  `DEFAULT_WEIGHTS`'teki **5 alan** için 5 sorgu atar.
- `/campaigns` — bilinçli olarak önbelleksiz. `SummaryCoverage`'ın canlı sayaç
  olabilmesi buna dayanıyor (bileşen docstring'inde ölçümüyle yazılı) ve aynı
  belgede önbellekli `/campaigns/{id}/text` ile geçici olarak ayrışabileceği de
  orada kabul ediliyor.

---

## 4. Karşılaştırma motoru (`src/comparison/compare.py`)

### 4.1 Bir alan nasıl sıralanıyor

`rank(rows, field_name) -> list[RankRow]` iki adımdır:

1. **`_numeric_key(field_name, value) -> (sort_key, comparable, note)`**
   - `None` → `(None, False, "değer yok")`
   - `collapse_degenerate_range()` ile `{min: X, max: X}` düz sayıya iner.
     Aynı savunma normalizasyon katmanında da var; **bilerek tekrarlanıyor**
     çünkü LLM katmanı kanonik değeri doğrudan üretebiliyor ve
     `normalize_rate`'ten geçmeyebiliyor.
   - Aralık `{min, max}` → `comparable=False`, not `"aralık — doğrudan
     kıyaslanamaz"`; `sort_key` **yöne göre** seçilir:
     `uc = lo if field_name in _LOWER_IS_BETTER else hi`.
   - Para `{value, currency}` → `currency != "TRY"` ise
     `(None, False, "farklı para birimi (X)")`, aksi hâlde `(float(value), True, None)`.
   - Masraf `{has_fee, amount}` → `has_fee is False` ⇒ `(0.0, True, None)`;
     `has_fee=True, amount=None` ⇒ `(None, False, "ücret var, tutarı belirtilmemiş")`;
     aksi hâlde `(float(amount), True, None)`.
   - Sayı → kendisi; başka her şey → `(None, False, "sayısal değil")`.
2. **Yön ve bölümleme:** `lower_better = field_name in _LOWER_IS_BETTER`;
   `comparables` (yani `comparable and sort_key is not None`) `sort_key`'e göre
   sıralanır, `others` **silinmez**, not'larıyla sona eklenir. Dönüş
   `comparables + others`.

Yön kümeleri:

```
_LOWER_IS_BETTER  = {kar_payi_orani, tahsis_ucreti, masraf_durumu}
_HIGHER_IS_BETTER = {vade_ay, finansman_tutari, odul_miktari, indirim_orani, alisveris_puani}
```

`scoring_direction()` (main.py) yalnız bu küme üyeliğini okur, ağırlık uydurmaz;
kümede olmayan alan `"unranked"` döner ve `FieldChips` onu soluk basar.

### 4.2 `comparable = False` ne zaman?

Beş durum, hepsi `_numeric_key` içinde:

1. Değer `None` ("değer yok")
2. Aralık `{min, max}` — sayı **döndürülür** ama kıyaslanabilir sayılmaz
3. Para birimi TRY değil
4. `has_fee=True` ama `amount=None` ("ücret var, tutarı belirtilmemiş")
5. Değer sayıya indirgenemeyen bir tip ("sayısal değil")

4. maddenin gerekçesi ölçülmüş ve docstring'de duruyor: `has_fee=True,
amount=None` eskiden **sıfır sayılıyordu** ve `masraf_durumu` "düşük iyi" alanı
olduğu için 0,0 sıralamanın tepesiydi — *"1.000 TL başvuru ücreti tahsil
edilecektir"* yazan kampanya "En Düşük Masraf" ekranında gerçekten ücretsiz
olanların önünde görünüyordu. **Ölçüm (2026-08-08): `sort_key == 0.0` olan 509
satırın 35'i ücretliydi; korpusta bu kalıptan 39 kayıt var.** İkiz fonksiyon
`_composite_numeric` bunu zaten doğru yapıyordu; ilke doğru yazılmış, tek alanlı
yola uygulanmamıştı.

Aynı kalıp aralık ucunda da yaşandı: `field_name` parametresi gövdede hiç
kullanılmıyor ve her zaman `min` alınıyordu, yani `vade_ay` alanında
`{min: 12, max: 120}` taşıyan kampanya **12 ay** gibi görünüyordu.

### 4.3 Bileşik skor (`rank_advantageous`)

Şartname §5.7'nin beşinci ölçütü. Dört adım:

1. **Sayısallaştırma** — `_composite_numeric(field_name, value)`:
   `has_fee=False → 0.0`; `has_fee=True, amount=None → None` + not; aralık →
   yöne göre iyimser uç (`best_end = lo if field in _LOWER_IS_BETTER else hi`) +
   `"aralık — en iyi uç kullanıldı"`; para → TRY değilse `None`; **`{"rate": …}`
   biçimli ücret → `None`, `"oran biçimli ücret — TL ile kıyaslanamaz"`.**
2. **Ağırlık dağıtımı** — `active`, popülasyonda **en az bir** ölçülebilir değeri
   olan alanlardır; `total_active = sum(active.values())`. Hiç kimsede
   ölçülemeyen alanın ağırlığı dağıtılır, yoksa herkesin kapsaması sebepsiz
   düşük görünür. `total_active <= 0` ise hepsi `note="hiçbir ölçüt ölçülemedi"`.
3. **Normalizasyon** — `_rank_normalize(values, lower_is_better)`: **sıralama
   tabanlı**, min-max değil. Eşitlikler ortalama sıra alır; tüm değerler eşitse
   herkes `1.0` (kimse cezalandırılmaz); formül `1.0 - r/(n-1)`.
4. **Toplama** — alan başına `contribution = normalized * weight`;
   `covered_w` = ölçülebilen alanların ağırlık toplamı;
   **`score = total / covered_w`** (yani yalnız kapsanan ölçütler üzerinden
   ortalama — eksik alan **sıfır puan değildir**);
   `coverage = covered_w / total_active`;
   `comparable = coverage >= min_coverage and score is not None`.
   Sıralama: kıyaslanabilirler `(-score, -coverage)`, sonra kalanlar.

Ağırlıklar ve **ölçülmüş gerekçeleri** (`DEFAULT_WEIGHTS` / `WEIGHT_RATIONALE`) §8'de.

### 4.4 Adil kıyas garantisi — kodda TAM OLARAK NEREDE

CLAUDE.md §17 sekiz ayrı yerde uygulanıyor. Tek bir kapı yok; katman katman:

| # | Yer | Ne yapıyor |
|---|---|---|
| 1 | `compare._numeric_key` | Birim/tip kapısı — §4.2'deki beş durumu `comparable=False` yapar |
| 2 | `compare.rank` | Yalnız `comparable` satırlar sıralanır; kalanlar not'uyla **sonda kalır, silinmez** |
| 3 | `main._field_rows(..., sozlesme_dahil=False)` | **Belge türü kapısı** — sözleşme/tarife/form metinleri kıyas tablosuna girmez. Süzme **depo katmanında** yapılır ki iki backend aynı kümeyi görsün. Ölçüm docstring'de: *"korpustaki 1761 belgenin 113'ü akit metnidir ve 41'i kıyaslanabilir bir alan taşır"* |
| 4 | `main.compare` → `per_bank="best"` | Tekilleştirme anahtarı **`(bank, campaign_type)`**, yalnız `bank` değil: bir bankanın konut ile taşıt finansmanı **farklı ürünlerdir**. Elenen satırlar saklanmaz, `other_count` ile **sayılır** |
| 5 | `main.compare` → `intent` yön zorlaması | Yalnız `comparable=True` satırlara uygulanır; kıyaslanamayanlar not'larıyla sonda kalır |
| 6 | `ComparePanel.turlereBol` (istemci) | «Tümü» seçiliyken satırlar **kampanya türüne bölümlenir** ve sıra numarası **bölüm içinde** yeniden verilir; `rank === null` satır numara almaz |
| 7 | `main.bank_delta` + `compare.delta_between` | Delta **her zaman kampanya türü içinde**; taraflardan biri sayıya indirgenemiyorsa `"kiyaslanamaz"` ve fark **hesaplanmaz**. Göreli fark rakip 0 ise hesaplanmaz (0 gerçek bir üründür: "masrafsız") |
| 8 | `compare.rank_advantageous_by_type` | Gruplama `campaign_type`; `MIN_GROUP_SIZE = 3` altındaki grup **sıralanmaz ama gizlenmez** (`ranked=[]` + `note`); normalizasyon **grup içinde** koşar |

Ek olarak `contradiction.py` kendi kıyaslanabilirlik korumalarını taşır (§5) ve
`FairnessNotice.tsx` bu kuralların **kullanıcıya dönük tek tanım yeridir**.

**Ölçülmüş gerekçe (`rank_advantageous_by_type` docstring'i):** 849 belgelik
korpusta 495 skorlanabilir kampanya var ama alanlar türlere göre keskin
ayrışıyor — `Kart 114 kampanya → 3'ünde kâr payı`, `İhtiyaç Finansmanı 104 → 5`,
`Alışveriş Puanı 13 → 0`, `Konut Finansmanı 72 → 11`. Toplamda kampanyaların
yalnızca **%9,5'inde** kâr payı oranı var.

### 4.5 Delta (`delta_between`)

```
mine_key veya rival_key None      → ("kiyaslanamaz", None, None)
fark == 0                          → ("esit", 0.0, 0.0)
dusuk_iyi = field in _LOWER_IS_BETTER
daha_iyi  = fark < 0 if dusuk_iyi else fark > 0
goreli    = None if rival_key == 0 else abs(fark)/abs(rival_key)*100
```

`DELTA_KINDS` yedi değerdir ve **`eksik_urun` ile `eksik_veri` bilerek ayrıdır**;
ayrımı `main.bank_delta` `kendi_belgeleri` sayacıyla kurar: banka o ailede hiç
belge taşımıyorsa `eksik_urun`, belgesi var ama alan çıkarılamadıysa `eksik_veri`.

---

## 5. Çelişki tespiti (`src/comparison/contradiction.py`)

### 5.1 Tasarım ilkesi

Modül docstring'i açık: *"Bu modülün değeri bulduğu çelişki sayısında değil,
bulduklarının gerçek olmasındadır."* Üç savunma her kuralda: **kapsam koruması**,
**kıyaslanabilirlik koruması**, **normalizasyon**.

Aday türler **önce ölçüldü, sonra kural yazıldı**; kanıtı olmayan tür için kural
yazılmadı. 849 belge, snapshot 2026-07-30, `python3 -m src.comparison.scan` ile
yeniden üretilebilir. Son durum: **6 çelişki** (5 süresi dolmuş + 1 belge içi
çelişen bitiş), altısı da elle doğrulandı; belgeler arası doğrulanmış çelişki 0.

### 5.2 Belge içi kurallar — `detect(campaign, as_of=None)`

| Kural | `kind` | Nasıl tespit ediliyor | Koruması |
|---|---|---|---|
| `_rule_fee_claim_vs_fee` | `masrafsiz_ama_ucret` | `masraf_durumu.has_fee is False` **ve** `tahsis_ucreti` pozitif. `_positive()` üç kanonik biçimi tanır: `{"value"}`, `{"amount"}`, **`{"rate"}`** (oran tablosundan gelen ücret eskiden atlanıyordu) | `_in_same_scope()` — **`MAX_SCOPE_CHARS = 400`**. Ölçüm: kapsam koruması olmadan üretilen 4 adayın **dördü de hayaletti**; iki tarafın karakter mesafesi **2.176–6.916**'ydı, gerçek çelişkilerde **20–55**. Offsetlerden biri yoksa reddedilmez ("kanıt yok, suçlama yok") |
| aynı kural, ikinci dal | `masrafsiz_ama_tutar` | `masraf_durumu.has_fee is False` ama `amount > 0` | — |
| `_rule_conflicting_end_dates` | `celisen_kampanya_bitisi` | `end_date_claims()` **≥ 2** farklı ISO tarih; ilk ve son rapor edilir | `_END_PATTERNS` **sıkı** kalıptır: "kampanya" sözcüğü en fazla 80 karakter önde, tarihten sonra "geçerli" ya da açık "Başlangıç ve Bitiş" başlığı. Gevşek kalıp ölçümde 138 belgede tetikleniyor |
| `_rule_conflicting_amount_bands` | `celisen_tutar_bandi` | Aynı oran için **çakışan ama aynı olmayan** tutar bantları (`_bands_overlap and not _bands_identical`, tolerans `_BAND_TOLERANCE = 1.0` TL). Gerçek vaka: Kuveyt Türk TOGG sayfasında gövde tablosu ile SSS ayrışıyor | İki koruma: (a) `_looks_like_listing()` — bu koruma olmadan 15 bulgunun **13'ü hayalet**; (b) **`MIN_CLOSED_BANDS = 2`** — belgede en az 2 kapalı aralık yoksa bu bir oran **cetveli** değil, bağımsız harcama eşikleri listesidir. `MAX_SCOPE_CHARS` **burada kullanılamaz**: TOGG'da tablo ile SSS binlerce karakter uzakta ve bulgu gerçek |
| `_rule_expired_but_published` | `suresi_dolmus_kampanya` | **`as_of` verilirse** koşar. Altı zorunlu koşul: (1) URL'de "kampanya" geçiyor, (2) URL arşiv/biten klasörü değil, (3) metin kendini "süresi dolmuştur" diye işaretlemiyor, (4) liste sayfası değil, (5) **tek** bitiş iddiası var, (6) o tarih `as_of[:10]`'dan önce | Aday elemesi ölçülmüş: **63 belgede sıkı bitiş iddiası → 23'ünde tarih toplamadan önce → 20'si kampanya URL'i → 6'sı kendini işaretlemiyor → 5'i liste değil → 5 bulgu.** `_SELF_EXPIRED` koruması olmadan 20 bulgunun 12'si Vakıf Katılım'ın "Kampanya Süresi Dolmuştur" damgalı sayfalarıydı |

`as_of` neden duvar saati değil `scraped_at`: iddia *"biz topladığımızda süresi
çoktan dolmuştu"* biçiminde olmalı; böylece sonuç zamanla sessizce değişmez ve
demo yeniden üretilebilir kalır.

### 5.3 Belgeler arası — `detect_across(campaigns)`

Eşleştirme `product_key()` ile: **URL yaprağı** (son anlamlı yol parçası). Üç
aday ölçüldü (849 belge) — *başlık*: felaket, "Kampanya"/"Detay" gibi jenerik
başlıklar **38 alakasız kampanyayı tek gruba** topluyor; *campaign_type + banka*:
çok kaba, bir bankanın 90 ürün sayfası 8 türe düşüyor; *URL yaprağı*: **71 grup,
40'ı gerçekten farklı metin**. Sıkılaştırmalar: `_PATH_STOPWORDS`, uzantı ve
`-2`/`_1` sürüm soneki kırpma, **8 karakterden kısa yaprak reddedilir**.

`group_by_product` metni tekilleştirir: **korpusta 32 çift belge aynı URL'i
paylaşıyor ve metinleri byte-özdeş**.

| Kural | `kind` | Koruma |
|---|---|---|
| `_cross_rule_rate` | `capraz_kar_payi_uyusmazligi` | `_is_segment_specific()` (banka/kamu çalışanına özel vb.) kıyas dışı — bu koruma olmadan Türkiye Finans grubunda 4 "çelişki" çıkıyordu, dördü de segment kampanyasıydı. `_rate_overlaps()` **0,005 tolerans**la aralık kesişimi bakar; **ölçülemiyorsa uyumlu sayılır (suçlama yok)** |
| `_cross_rule_end_date` | `capraz_kampanya_bitisi` | Taraflardan biri `_SELF_EXPIRED` damgalıysa çelişki değil, **ardışık sürüm**. Ölçüm: bu koruma olmadan çıkan 2 bulgunun ikisi de ardışık sürümdü |

**`detect_across` hiçbir uçtan çağrılmıyor.** `main.py` yalnız `detect`'i
`detect_contradictions` adıyla import ediyor.

---

## 6. Chatbot

### 6.1 Akış (`bot.Chatbot.ask`)

```
soru
 → safety.screen_input(question)          # 5 kapı, HAM metin üzerinde
 → scr.blocked ise: hazır politika yanıtı; veri sorgusu HİÇ yapılmaz
 → _dispatch(): route(question) → structured.answer(...) | rag.answer(...)
 → safety.guard_output(body, scr, has_sources=…, has_rate=…)
 → ChatAnswer(text, handler, field, sources, safety_report, gates)
```

`safety_enabled=False` yalnız **ablasyon/ölçüm** içindir; `_answer_unguarded`
kapıları tamamen atlar. RAG dizini bot ömrü boyunca **bir kez** kurulur
(`_ensure_retriever(require_data=True)` — depo boşsa dizin kurulmaz ve `None`
döner ki sonradan doldurulan depolarda bayat dizin kalmasın).

### 6.2 Router'ın karar ağacı (`router.route`)

```
q = tr_fold_ascii(question)          # 'EN DÜŞÜK' ve 'en dusuk' aynı forma iner

field   = _detect_field(q)           # _FOLDED_FIELD_KEYWORDS içinde alt-dize eşleşmesi
intent  = _detect_intent(q)          # lowest | highest | list
filters = _detect_filters(q)         # vade_ay_min | campaign_type | banks

# Terminoloji yedeği (girdi tarafı):
if field is None and mentions_interest_term(question):
    field = "kar_payi_orani"

# Gevşek eşleme — YALNIZ açık sıralama niyeti varken:
if field is None and intent in ("lowest", "highest"):
    field = _FOLDED_SUP_FIELD_KEYWORDS eşleşmesi   # finansman/kredi/puan/ödül/indirim

# Sohbet bağlamı (context verilmişse):
if context is not None and not context.bos():
    field, intent, filters, inherited = _devral(...)

if field and (intent or filters):              → Route("structured", field, intent or "list", …)
if field and intent in ("lowest","highest"):   → Route("structured", …)     # ULAŞILAMAZ (§9-T7)
otherwise                                       → Route("rag", field, intent, filters, …)
```

Niyet sözlükleri:
- `_SUPERLATIVE_LOW` → `lowest`: en düşük, en az, en ucuz, en avantajlı, minimum
- `_SUPERLATIVE_HIGH` → `highest`: en yüksek, en fazla, en uzun, en çok, maksimum, en büyük
- `_LIST_INTENT` → `list`: hangi banka(lar), listele, göster, var mı, veren, sunan, olanlar

Süzgeç tespiti: `r"(\d{1,3})\s*ay"` + eşik sözcüğü (`veren`, `uzeri`, `ve uzeri`,
`en az`) → `vade_ay_min`; `_FOLDED_TYPE_MAP` günlük kelimeleri de kapsar
(**"araba"/"otomobil"/"sıfır km" → Taşıt Finansmanı** — ölçüldü, `taşıt` geçmediği
için tür filtresi hiç kurulmuyordu); `safety.detect_banks()` çoğul banka döndürür.

**Gevşek eşlemenin ölçülmüş gerekçesi:** *"Araba alımında en yüksek finansman
kimde var?"* sorusunda `finansman` hiçbir alan anahtarına uymuyordu, soru RAG'e
düşüyor ve RAG sorunun yalnız iki yaygın kelimesiyle ('alımında', 'yüksek')
örtüşen bir **SEYAHAT kampanyasını** "ilgili kampanya" diye döndürüyordu.

**Sohbet bağlamı (`ChatContext`, `baglam_birlestir`, `_devral`).** Sunucu
durumsuzdur; bağlamı istemci gönderir, yani kanal **saldırgan denetimindedir**.
Bu yüzden kanalda **hiç serbest metin yoktur**: her değer sonlu bir kümeden
gelmek zorundadır (`FIELD_DISPLAY`, `INTENT_DISPLAY`, `CAMPAIGN_TYPES`,
`BANK_DISPLAY`, `1 ≤ vade ≤ 600`). `ChatContext.dogrula()` uymayan her değeri
**sessizce atar** (hata yükseltmez: "bağlam bir kolaylıktır, sözleşme değil").
`BAGLAM_TUR_SINIRI = 6`; liste yeniden eskiye sıralıdır, her boyut için ilk dolu
değer kazanır. Devralma üç kurala tabi ve hepsinde **kullanıcının söylediği
kazanır**: (1) alan+niyet birlikte çıktıysa hiç devralma yok, (2) özne devralma
("Peki vade?" → önceki cevabın kazananı banka süzgecine çevrilir), (3) kalıp
devralma ("Peki ya Albaraka?" → alan ve niyet önceki turdan).

> **DİKKAT — bu tur:** `bot.py` `route(question)`'ı **bağlamsız** çağırıyor ve
> `ChatReq` yalnız `question` alanını taşıyor. Yani yukarıdaki bağlam altyapısı
> uçtan uca **bağlı değil**; `Route.inherited` hiçbir yanıtta görünmüyor.
> `bot.py` ve `router.py` bu turda değişiyor — büyük olasılıkla tam olarak bu
> bağlanıyor.

### 6.3 Güvenlik kapıları (`safety.py`)

Modül "5 kapı" diyor; kodda **altıncı** kapı da var (`GATE_INJECTION`), ama farklı
bir katmanda (RAG) koşuyor.

| # | Kimlik | Girdi tarafı | Çıktı tarafı |
|---|---|---|---|
| 1 | `terminoloji` | `mentions_interest_term()` — "faiz"/"interest" **kabul edilir**, reddedilmez; `_TERMINOLOGY_NOTICE` eklenir ve `field_hint = "kar_payi_orani"` verilir. `'faizsiz'` ailesi **muaf** | `sanitize_output()` — post-filter. Yasak terim **yeniden yazılır** (bayraklanmaz): "jüriye giden tek yüzey yanıt metnidir". Ham pasajlar `sources` içinde **değiştirilmeden** kalır. **Karşıtlık bağlamı** (`_CONTRAST_RE`) varsa `"konvansiyonel getiri"` kullanılır — gerçek korpusta bankaların kendi eğitim sayfaları *"Kâr Payı ile Faiz Arasındaki Farklar"* diyor ve körlemesine değiştirmek cümleyi anlamsızlaştırırdı. `tr_fold` 1:1 uzunluk korumazsa **yalnızca bayraklanır** (dürüst başarısızlık) |
| 2 | `fikhi_hukum` | `asks_for_ruling()` — **en yüksek öncelik, erken `return`**. `_RULING_STRONG_STEMS` tek başına yeter; `_RULING_WEAK_STEMS` **yakınlık şartına** tabi (kök ile soru edatı arası ≤ 18 karakter), böylece *"Helal gıda alışverişinde puan veren kampanya var mı?"* yakalanmaz | Hazır yanıt: TKBB Danışma Kurulu + bankanın kendi danışma komitesi |
| 3 | `yatirim_tavsiyesi` | `asks_for_advice()` — reddetme **değil**, çerçeveleme. `advice_intent=True` | `_ADVICE_FRAME` başa, `_ADVICE_DISCLAIMER` sona. **`bot._dispatch` ayrıca yolu zorlar**: tavsiye niyeti varsa ve router yapısal sorgu üretmediyse `Route("structured", field or "kar_payi_orani", intent or "list", filters)` kurulur — tavsiye vermeden karşılaştırmalı olgu tablosu sunulur |
| 4 | `garanti_imasi` | `implies_guarantee()` | `_GUARANTEE_CORRECTION` başa, `_GUARANTEE_DISCLAIMER` sona. Ayrıca **çıktıda oran varsa** (`contains_rate`, `r"%\s*\d"`) ve çekimser değilse feragatname **kendiliğinden** eklenir ve kapı raporlanır |
| 5 | `cekimserlik` | `is_in_scope()` — kapsam sözlüğü paralel kurulmaz, mevcut altyapıdan türetilir (`FOLDED_FIELD_TRIGGERS` + `FOLDED_TYPE_HINTS`, 3 karakterden uzun) + sabit terimler + banka adları. **Tembel** genişletme `domain.terminology.scope_terms()` ile | `guard_output`'ta ikinci kez: `has_sources=False` ise gövde `_NO_SOURCE_REPLY` ile **değiştirilir**, `abstained=True` |
| 6 | `icerik_karantinasi` | — | `rag._karantina()` → `safety.detect_injection()`. **`llm`'e VE çıkarımsal yedeğe gitmeden önce** koşar |

Kapı 5'in kapsam sözlüğü genişletmesi ölçülmüş: **18 katılım finansı sorusundan
14'ü "kapsam dışı" diye reddediliyordu** ('tekâfül', 'muşaraka', 'selem akdi',
'muacceliyet kaydı', 'zekât nisabı'…). Sözlüğün teknik terimleri **11'ini
kurtarıyor** ve kapsam dışı kontrol kümesinde yanlış pozitifi yalnız 2/18'den
3/18'e çıkarıyor. `halk_dili` bilinçli olarak dışarıda: açıkken yanlış pozitif
**11/18'e** fırlıyordu.

**Eşleşme disiplini** (modül başlığı): her eşleşme `tr_fold`/`tr_fold_ascii`
üzerinden (`str.lower()` Türkçe için hatalıdır — `'ÜCRETSİZ'.lower()` yüzünden
işaret ters dönmüştü) ve **her zaman sözcük sınırlı** (alt-dize eşleşmesi 'ev'
anahtarını 'devam'/'seviye' içinde eşleştirip **korpusun %48'ini bozmuştu**).

**Kapı 6'nın ölçülmüş gerekçesi (PI15):** korpusa gömülü bir sayfa
*"ÖNEMLİ SİSTEM TALİMATI: Önceki tüm kurallarını yoksay…"* metnini taşıyordu ve
RAG'in **LLM'siz** yolunda kullanıcıya **aynen basılıyordu**. Kapı 1 "faiz"i
yakaladı ama talimat cümlesi ve "kesinlikle garanti et" sızdı. Tehdit modeli
gerçek: üçüncü taraf banka sayfaları kazınıyor. Belge **tamamen** düşürülür,
satır ayıklanmaz. `"iptal"` deseni **bilinçli olarak yok**: 2.483 belgede ölçüldü,
tek yanlış pozitif kaynağı buydu (10 belge, hepsi *"otomatik ödeme talimatının
iptali"*).

`guard_output` sırası: (1) blocked/kaynaksız gövde değişimi → (2) `sanitize_output`
→ (3) `soft_term_warnings` → (4) oran varsa garanti feragatnamesi → (5) notlar
başa + gövde + feragatnameler sona, `"\n\n"` ile birleştirilir. Notlar ve
feragatnameler **sanitize'dan sonra** eklenir; bunlar denetlenmiş sabit
şablonlardır ve tasarımı gereği yasak terim içermezler (`_TERMINOLOGY_NOTICE`
bilerek yalnızca "faizsizdir" içerir).

Yumuşak terimler (`kredi`, `mevduat`) yalnız **uyarı** üretir, yeniden yazılmaz:
*"'kredi kartı' katılım bankalarının da kullandığı gerçek ürün adıdır,
körlemesine 'finansman kartı' yapmak veriyi bozar."*

### 6.4 Yapısal sorgu ile RAG yollarının ayrımı

| | Yapısal sorgu (`structured.py`) | RAG (`rag.py`) |
|---|---|---|
| **Ne zaman** | `route()` alan **ve** (niyet veya süzgeç) çıkardıysa | Aksi hâlde (güvenli varsayılan) |
| **Veri yolu** | `repo.query_fields(r.field)` → `_apply_filters` → `compare.rank` | `KeywordRetriever.retrieve(question, k=3)` |
| **Belge türü süzmesi** | **Yok** — `query_fields(field)` sözleşme parametresi olmadan çağrılıyor | **Yok, bilerek**: "şu sözleşmede ne yazıyor" sorusunun cevabı akit metnindedir |
| **Cevap üretimi** | Deterministik şablon: `_phrase_superlative` / `_phrase_list`, `_fmt_value` ile TR biçimleme | LLM varsa `generate_json` ile sentez; yoksa `_cikarimsal_cevap` (özet varsa özet, yoksa `kisa_alinti` + **"bu özet değildir"** uyarısı) |
| **Kaynaklar** | `[{bank, value, source_span}]` — **tüm** `ranked` satırları | Pasaj sözlükleri: `bank, bank_slug, campaign_id, source_url, text, ozet, score` |
| **`has_rate`** | `field == "kar_payi_orani"` veya `contains_rate(text)` | `contains_rate(text)` |

`_fmt_value`'nun `masraf_durumu` dalı ölçülmüş bir düzeltmedir: bu dal olmadan
kullanıcıya ham sözlük gidiyordu ve **demonun manşet sorusunda görünüyordu** —
`"en düşük masraf durumu: Kuveyt Türk ({'has_fee': False, ...})"`. `amount is
None` hâli ayrıca ayrılmıştır ("ücret var, tutarı belirtilmemiş"), çünkü metinde
de "masrafsız" gibi okunmamalıdır.

`structured._apply_filters` üç süzgeç uygular: `banks` (sorulan banka verimizde
yoksa sonuç **boş kalır** ve çekimserlik kapısı dürüstçe devreye girer — başka
bankaların satırlarını cevap gibi sunmak sessiz halüsinasyondur), `campaign_type`,
ve `vade_ay_min`. Sonuncusu eskiden satır başına bir `field_value()` sorgusu
atıyordu (**N+1**): *"36 ay ve üzeri vade veren konut finansmanları"* sorusu 1696
kampanyalık korpusta tek başına **~23 ms** sürüyordu; artık tek
`query_fields("vade_ay")` çağrısı.

**RAG erişim eşiği.** `MIN_OVERLAP = 2` — 1 örtüşme yetersizdi: *"Helal gıda
alışverişinde puan veren kampanya var mı?"* yalnızca 'kampanya' üzerinden konut
finansmanı metnini getiriyordu. Ama eşik **mutlak** uygulanamaz: `_etkin_esik()`
onu sorunun anlamlı sözcük sayısıyla sınırlar. Ölçüm
(`docs/rapor/rag-terim-kapsama.md`, 15 fıkhî terim): **korpus 1761 belge, mutlak
eşik 2 → 4/15; oransal eşik → 14/15.**

**Tokenizasyon (`_tokenize`).** `str.lower()` kullanılmaz. Tek karakterli
token'lar atılır — *"Karz-ı hasen"* → `['karz','ı','hasen']`; **'i' token'ı
korpusta 672 belgede geçiyor** ve eşiği gürültüyle dolduruyordu. Tek haneli
rakamlar atılır ('5' → **722 belge**), çok haneliler korunur. **Şapkalı ünlüler
tabanlarına indirilir**: `"kâr payı oranı"` → `['payı','oranı']`, yani `'kâr'`
tamamen düşüyordu — ve `kâr payı` bu projenin merkezî terimi, korpusun **319
belgesinde (%18) şapkalı** yazılıyor. İndirgeme 84 belgedeki şapkasız yazımla
319'u birleştirir. Tam ASCII katlaması yapılmaz (`ş ç ğ ı ö ü` ayırt edicidir;
'sac'/'saç' birleşirdi).

**Ters dizin.** İlk sürüm her soruda tüm korpusu tokenize ediyordu: 1696 belgede
soru başına **~290 ms**, chatbot p99'unun (~570 ms) neredeyse tamamı. Sonuçların
**birebir eşdeğerliği** `tests/test_rag_index.py` ile kilitli (skor formülü,
eşik, eşitlik sıralaması korunur).

**`VectorRetriever` yerine geçmiyor, yanına geliyor.** `RAG_RETRIEVER` ortam
değişkeni: `keyword` (varsayılan) | `auto` (düşüş **WARNING** ile loglanır) |
`vector` (zorunlu; kurulamıyorsa **hata yükseltir** — "operatör vektör yolunu
zorunlu kıldı; sessizce başka bir şey çalıştırmak istediğinden farklı bir sistem
teslim etmek olur"). `DEFAULT_MIN_SCORE = 0.5` **kalibre edilmiş değildir**,
muhafazakâr başlangıç değeridir ve docstring bunu açıkça söyler.

---

## 7. Arayüz (`web/app/`)

### 7.1 Bileşen ağacı

```
layout.tsx (RootLayout)
  └─ .shell > .site-header + children
       └─ page.tsx :: Home
            └─ JuryModeProvider                    (lib/juryMode.tsx)
                 └─ Dashboard
                      ├─ JuryModeToggle
                      ├─ SummaryCoverage           (toplam / özetli, istemcide sayılır)
                      ├─ Tabs  (ui/Tabs.tsx)       ← useTabState (lib/tabState.ts)
                      ├─ ErrorNotice ×2            (fields / campaigns ortak hataları)
                      └─ TabPanel
                           ├─ compare       → ComparePanel
                           │                    ├─ FairnessNotice
                           │                    ├─ FieldChips
                           │                    ├─ RowPair → SourceDrawer
                           │                    │      ├─ SummaryNotice
                           │                    │      └─ SourceSpanView → SourceText
                           │                    └─ ScoringExplainer → ConfidenceBadge
                           ├─ advantageous  → AdvantageousPanel (Agirliklar / TurBolumu / SkorSatiri)
                           ├─ delta         → BankDeltaPanel (FairnessNotice, TurBolumu, Manset, Taraf)
                           ├─ audit         → AuditPanel
                           │                    ├─ SummaryNotice
                           │                    ├─ SourceSpanView → SourceText
                           │                    └─ SourceText (alan seçili değilken)
                           ├─ contradictions→ ContradictionAlert
                           ├─ extract       → ExtractLive → SourceSpanView
                           └─ chat          → ChatPanel → ui/Markdown (lib/markdown.ts)
```

Ortak yardımcılar: `ErrorNotice`/`EmptyNotice`/`Loading` (tek dosya),
`ConfidenceBadge`, `lib/useAsync.ts`, `lib/format.ts`, `lib/api.ts`.

`onInspect(campaignId)` deseni: `AdvantageousPanel`, `BankDeltaPanel`,
`ContradictionAlert`, `ChatPanel` bir belgeyi Jüri Audit Paneli'nde açar
(`page.tsx` `inspect` → `setAuditTarget` + `setSekme("audit")`).

### 7.2 Bileşen → uç eşlemesi

| Bileşen | Çağırdığı uç(lar) |
|---|---|
| `page.tsx` (Dashboard) | `/fields`, `/campaigns` |
| `ComparePanel` | `/compare` |
| `ComparePanel > SourceDrawer` | `/campaigns/{id}/text` |
| `ScoringExplainer` | `/scoring` |
| `AdvantageousPanel` | `/advantageous` |
| `BankDeltaPanel` | `/banks`, `/bank-delta` |
| `AuditPanel` | `/campaigns/{id}/text` (belge listesi `page.tsx`'ten prop olarak gelir) |
| `ContradictionAlert` | `/contradictions`, `/contradictions/summary` |
| `ExtractLive` | `/extract` |
| `ChatPanel` | `/chat` |

Hiçbir bileşen `/health` çağırmıyor.

### 7.3 Durum ve hata disiplini

- **`useAsync`** — kendi 57 satırlık kancası; `swr`/`react-query` yeni bağımlılık
  demek (offline + lisans denetimi). `alive` bayrağıyla yarış koruması; **hata
  asla yutulmaz**, `error` çağırana döner.
- **`ApiError`** — `api.ts` her hatayı Türkçe, aksiyon alınabilir bir mesaja
  çevirir. `status >= 500` için ayrı ipucu (Next proxy FastAPI'ye ulaşamıyor).
  Eski `page.tsx` `.catch(() => setRows([]))` ile hatayı yutuyordu ve **jüri
  "veri yok" ile "API kapalı"yı ayırt edemiyordu**.
- **`useTabState`** — sekme `useState`'te değil **URL'de** (`?sekme=`), `pushState`
  + `popstate` ile (sekme bir *konum*dur). Varsayılan sekme adres çubuğunu
  kirletmez.
- **`juryMode`** — `replaceState` (sekmenin aksine: mod bir *tercih*tir). Üç giriş
  yolu: düğme, `?juri=1`, `localStorage`. **URL parametresi localStorage'ı ezer.**
  `NEXT_PUBLIC_*` ortam değişkenine bilerek bağlanmadı (demo makinesinde derleme
  zamanı değişkeni ayarlanmamış olabilir). İkisi de hidrasyon için mount sonrası
  okur ve `ready`/`hazir` bayrağı taşır.
- **`lib/markdown.ts` + `ui/Markdown.tsx`** — ayrıştırıcı **HTML dizgesi üretmez**,
  yapısal token döndürür ve render katmanı onlardan React elemanı kurar. Ham HTML
  enjekte eden React kaçış kapısı **hiç kullanılmaz**, bu yüzden XSS yapı gereği
  imkânsızdır ve sanitizasyon kütüphanesine (yine yeni bağımlılık) gerek kalmaz.
  Dört işaret: `**kalın**`, `_italik_`, `` `kod` ``, `- liste`. `_` yalnız
  **sözcük sınırında** açılır/kapanır — aksi hâlde `kar_payi_orani` içindeki
  `_payi_` italik sanılır ve alan adı bozulurdu. Lookbehind bilerek kullanılmadı
  (eski Safari). Tanınmayan işaret **birebir basılır**. Ayrıştırıcı
  `web/tests/markdown.test.ts` içinde **21 testle** doğrulanır.
- **`SourceText` sözleşmesi** — `normalizeBlocks()` blokların ham metni **bitişik
  ve eksiksiz** kapladığını doğrular; doğrulanamazsa katlama **tamamen** devre
  dışı ("yanlış yeri katlamak, katlamamaktan kötüdür"). **Kanıt gizlenemez:**
  vurgulanan aralığa dokunan blok `gizle: true` olsa bile açılır ve **neden**
  açıldığı yazılır.

### 7.4 Tasarım sistemi: `tokens.css → base.css → components.css`

`layout.tsx` üçünü **bu sırayla** import eder. Sıra anlamlıdır.

**`tokens.css` (167 satır) — tek doğruluk kaynağı.** Eski `globals.css` 16 token
taşıyordu ve **14'ü renkti**: boşluk, tipografi, gölge ve hareket için token
yoktu. Ölçüm: padding değerleri `6/8/10/14/16/20/24/64px` karışık literal, yazı
boyutu `11 · 11,5 · 12 · 12,5 · 13 · 13,5 · 14 · 15 · 18 · 21 · 24px` — modüler
skala değil elle ayar; ayrıca **9 rgba değeri** mevcut tokenların elle çoğaltılmış
kopyasıydı ve token değişince onlar değişmiyordu.

Token aileleri: zemin (`--bg`, `--bg-2`, `--bg-3`), çizgi, metin, vurgu, durum
(`--ok/--warn/--bad/--mark/--on-mark`), yıkamalar, köşe, gölge, **4px tabanlı
boşluk skalası** (`--sp-1..--sp-10`), tipografi (`--fs-xs..--fs-2xl`, satır
yüksekliği, ağırlık, harf aralığı), hareket (`--dur-fast/--dur-base/--ease`),
ölçü (`--shell-max: 1120px`).

Üç karar:
- **İki tema, eşit vatandaş.** Açık tema `:root`'ta **tam** tanımlıdır; koyu tema
  `@media (prefers-color-scheme: dark)` altında yalnız **aynı isimleri** yeniden
  tanımlar. Hiçbir renk tek tanımını media bloğunun içinde bulmaz.
- **Alfa varyantları ayrı token.** `color-mix()` daha zarif olurdu ama Safari 16.2
  / Chrome 111 öncesinde yok; demo makinesinin tarayıcı sürümüne bağımlılık
  bırakılmadı.
- **Kontrast göz kararı değil ÖLÇÜLMÜŞ.** `scripts/kontrast_kontrol.py` bu dosyayı
  okur, `tests/test_kontrast.py` kapıya bağlar. Koyu temada `--on-accent`
  yeniden tanımlanır: parlak mavi zeminde beyaz metin **3,24:1** ölçüldü, AA
  eşiğinin altında.

Ayrıca gölge tokenları koyu temada `none` olur: *"Açık temada yükseklik gölgeyle,
koyu temada kenarlıkla anlatılır — aynı token, farklı fizik."*

**`base.css` (161 satır) — reset, tipografi, odak, kabuk.** Literal renk/boşluk/
yazı boyutu **yoktur**; tek istisna `@media` genişlikleri (CSS custom property'ler
medya sorgusunda kullanılamaz). Tek global `:focus-visible` kuralı; geçişler
yalnız renk/gölge üzerinde (düzen animasyonu yok);
`prefers-reduced-motion` bloğu.

**`components.css` (1009 satır) — bileşen katmanı.** Aynı literal yasağı; istisna
`1px` kenarlık ve `2px` vurgu şeridi gibi **fiziksel çizgi kalınlıkları**.
Dosya başlığı **eskiden tanımsız olan 11 sınıfı** sayıyor —
`summary-box/-label/-body`, `fairness/-item`, `jury-bar/-dot/-toggle`,
`fold/-open/-note/folded-body`, `headlines/headline*` — beş bileşen bu sınıfları
kullanıyordu ama CSS karşılıkları **hiç yazılmamıştı**, yani stilsiz render
oluyorlardı; en görünür sonucu `SummaryNotice`'ın kendi vaadini tutamamasıydı
(özet kaynak metinden görsel olarak ayrışmıyordu).

**Kırılım yerleşimi bir hatanın izidir.** `base.css` başlığı açıkça yazıyor:
bileşen sınıflarının `@media` blokları `components.css`'in **sonundadır**, çünkü
iki dosya aynı özgüllükte kural yazıyor ve `components.css` sonra yükleniyor —
`base.css` içindeki bir `@media` bloğu onun temel kuralı tarafından **sessizce
eziliyordu**: 375px'te sekmeler kaydırmalı şeride hiç dönmüyordu. Kural: *bir
sınıfın duyarlı davranışı, o sınıfın tanımlandığı dosyada yaşar.*

İki kırılım: **900px** — `table.data.stackable` kart yığınına döner (`thead`
görsel olarak gizlenir, her hücre `data-label`'ını `::before` ile taşır; tablo
yapısı korunur, ekran okuyucu için satır/sütun ilişkisi bozulmaz), `.kv` tek
sütuna iner. **600px** — sekmeler kaydırmalı şerit, `.fairness-item`/`.headline`
tek sütun, `.stats` iki sütun, `.source-text` `max-height: none` (mobilde sabit
yükseklik ekranı hapsediyordu).

`.card { min-width: 0 }` da ölçülmüş bir düzeltmedir: grid/flex öğelerinin
varsayılan `min-width: auto` değeri yüzünden **360px'lik görünüm alanında `.card`
910px'e çıkıyor ve tüm sayfa yatay kayıyordu**.

---

## 8. Önemli kararlar ve ölçülmüş gerekçeleri

Aşağıdaki sayılar docstring'lerden **aynen** aktarılmıştır.

### 8.1 Saklanan offset birincil, yeniden hesaplama yedek (`span_info`)

> Ölçüm (`data/demo.db`, **849 belge / 2204 alan**): saklanan offsetlerin
> **2204'ü de doğrulanıyor**, yeniden hesaplama bunların **73'ünde farklı bir
> yer** gösteriyordu — çünkü `str.find` aynı ham değerin ilk geçtiği yeri bulur,
> çıkarımın geldiği yeri değil. Yani arayüz alanların **~%3'ünde yanlış yeri**
> boyuyordu.

Saklanan offset **körü körüne güvenilmez**: `text[span_start:span_end] ==
raw_value` eşitliğini geçmek zorundadır, aksi hâlde yedek yola düşülür.
`window_start`/`window_end`/`span_ambiguous` **her durumda** `locate_span()`
üzerinden hesaplanır (DB'de saklanmazlar).

`confidence_source` da artık DB'den okunur: eskiden "sütunu yok" gerekçesiyle
kampanya başına kural katmanı **yeniden koşturuluyordu**; sütun 31 Tem'de eklendi
ve `data/demo.db`'de **2204/2204 alan dolu**.

### 8.2 Çerçeve KATLANIR, SİLİNMEZ (`bloklar`)

Metin **değişmez**. Çerçeveyi (çerez/KVKK/menü) metinden ayıklamak `span_start`/
`span_end` offsetlerinin tamamını kaydırırdı ve **projenin en özgün iddiası** —
her değerin ham metinde bir karakter aralığına bağlı olması — çökerdi. Bu yüzden
ayıklama **çıkarım yolundan alınıp sunum katmanına taşındı**. `bloklar` ham metni
**eksiksiz ve bitişik** kaplar; garanti `preprocessing/blocks.gorunum_araliklari()`
içinde kurulur ve `tests/test_bloklar_gorunum.py` ile kilitlidir. `gerekce`
değerleri `blocks.py`'nin kendi karar adlarıdır (`alan_disi`, `alan_disi_bolge`,
`tekrar`); API'de yeni ad üretilmez.

### 8.3 Ağırlıklar (`DEFAULT_WEIGHTS` / `WEIGHT_RATIONALE`)

Önce **saf maliyet modeli ölçüldü**. 100.000 TL / 36 ay referans sepetinde
(kâr tutarı ≈ tutar × aylık_oran × (n+1)/2):

```
kâr payı oranı  %1,89 → %5,99   ≈  34.965 TL → 110.815 TL   (fark ~75.850 TL)
tahsis/masraf   0 TL  → 750 TL  ≈       0 TL →     750 TL   (fark ~   750 TL)
ödül miktarı    150 TL → 6.000 TL                (fark ~ 5.850 TL)
```

> Saf TL etkisine göre ağırlık ≈ **%92 / %1 / %7** çıkar. Bunu **kullanmıyoruz**,
> iki ölçülmüş sebeple:
> 1. Alanlar farklı ürün ailelerinde yaşıyor. **Korpusta 849 belgenin yalnız
>    47'sinde kâr payı, 120'sinde ödül miktarı var** ve bu iki küme neredeyse hiç
>    kesişmiyor. %92 ağırlık kâr payına verilirse tüm kart kampanyaları tek bir
>    eksikten dolayı sıralamanın dibine düşer — bu adil kıyas değildir.
> 2. Şartname beş ölçütü **eşit** ölçüt olarak sayar; birini diğerlerini silecek
>    kadar ağırlıklandırmak ölçütü fiilen kaldırmak olur.

Sonuç: `kar_payi_orani 0.40`, `masraf_durumu 0.20`, `odul_miktari 0.15`,
`vade_ay 0.15`, `finansman_tutari 0.10`. **Bu bir ÜRÜN KARARIDIR, ölçümden
türetilmiş bir sabit değildir — bu ayrım bilerek belirtiliyor.**

Gerekçelerden ikisi aynen:
- `masraf_durumu`: *"Tutarı küçük (~750 TL) ama PEŞİN ödenir ve şartname §5.7 'En
  Düşük Masraf'ı ayrı bir ölçüt sayar; nakit akışı etkisi nedeniyle TL oranından
  yüksek tutuldu."*
- `vade_ay`: *"Esneklik ölçütü, maliyet ölçütü değil: uzun vade taksidi düşürür
  ama toplam maliyeti artırır, bu yüzden ödülle eşit ama kâr payının altında."*
- `finansman_tutari`: *"Üst limit nadiren bağlayıcıdır (müşteri genelde limitin
  altında kullanır); ölçüte dahil ama en düşük ağırlıkla."*

### 8.4 Sıralama tabanlı normalizasyon (min-max değil)

> Korpus ölçümü (849 belge) alanlarda çıkarım kaynaklı uç değerler gösteriyor:
> `vade_ay` en büyük değer **24.312**, `tahsis_ucreti` en büyük değer **100.000**.
> Min-max normalizasyonda tek bir uç değer diğer tüm kampanyaları 0'a yapıştırır
> ve sıralama anlamsızlaşır.

### 8.5 `MIN_GROUP_SIZE = 3`

Sıralama tabanlı normalizasyon 2 öğede dejenere olur (biri 1.0, biri 0.0) ve
"en avantajlı" iddiası anlamsızlaşır — 2 kampanyadan birinin en iyi olduğunu
söylemek bilgi taşımaz. **Grup gizlenmez, sebebiyle raporlanır.**

### 8.6 `masraf_durumu` `amount=None` sayılmaz

> Ölçüldü (2026-08-08): `sort_key == 0.0` olan **509 satırın 35'i** ücretliydi;
> korpusta bu kalıptan **39 kayıt** var. Bileşik skor tarafında aynı durum **22
> belgede** var — sessizce sıfırlanmaları sıralamayı ters çevirirdi.

`_composite_numeric`'in gerekçesi: *"sıfır saymak 'masrafsız' demek olurdu
(yalan), popülasyonun en kötüsünü atamak ise değer uydurmak olurdu."*

### 8.7 Çelişki kapsam eşiği `MAX_SCOPE_CHARS = 400`

> Ölçüm (849 belge, 2026-07-30): kapsam koruması olmadan üretilen 4 adayın
> **dördü de hayaletti**; iki tarafın karakter mesafesi **2.176–6.916**'ydı.
> Gerçek (test edilmiş) çelişkilerde bu mesafe **20–55** karakter.

Ve `_looks_like_listing` koruması olmadan tutar bandı kuralı korpusta **15 bulgu
veriyordu, 13'ü hayalet**; `MIN_CLOSED_BANDS` ölçümü ise şu üç belgeyle
belirlendi: `arac-finansmanlari-togg-finansmani.txt` (6 kapalı / 2 açık, gerçek
oran cetveli) vs. iki kampanya liste sayfası (0 kapalı / 7 ve 6 açık).

### 8.8 RAG başarım rakamları

> `KeywordRetriever`: 1696 belgelik korpusta **p99 12,18 ms** (öncesi **576 ms**)
> ve **54 soruda** eski/yeni birebir eşdeğerliği kanıtlanmış durumda. Dizinsiz
> sürüm soru başına **~290 ms** yiyordu.

### 8.9 Belge uzunluğu ve `ozet`

> Korpusta belge başına ortalama **4.744 karakter**; **1774 belgenin 1005'i (%57)
> 2.000 karakteri aşıyor**, en uzunu **178.825 karakter**. Önceden üretilmiş özet
> ortalama **259 karakter**.

Ayrıca `main.py` `_ozet` docstring'i: *"belgelerin **~%81'inde** özet
üretilmemiş"* — ve aynı yerde bir **bayat yorumun** düzeltildiği kaydediliyor:
eski `TODO(G)` "campaign_text() henüz c.ozet sütununu SELECT etmiyor" diyordu ve
teşhisi yanlış yere saptırıyordu; gerçek sebepler arayüzdeydi (tanımsız
`.summary-box` CSS'i) ve veri kapsamındaydı.

> **GÜNCELLEME (2026-08-10):** Bu kusur KAPANDI. `sozlesme_dahil` ve `set_ozet` dört yüzeyin dördünde de uygulanmış durumda; ölü yetenek yoklamaları ve `TODO(G)` metinleri kaldırıldı (commit `9b02152`). Aşağıdaki tarif ölçüldüğü ANIN kaydıdır.


`ozet` istek anında **üretilmez** — 4 dakikalık sunumda canlı model çağrısı
donma riskidir. Özet yoksa `ozet` ve `ozet_kaynak` **null**'dır; kural tabanlı
sahte bir özet (ilk N cümle) asla basılmaz. `ozet_kaynak` bir **sütun değildir**,
türetilmiş alandır: özet üretmenin başka yolu olmadığı için özet varsa kaynağı
tanım gereği modeldir. **Özet hiçbir ölçüm yoluna girmez**: kıyas, çıkarım ve
çelişki tespiti onu görmez.

### 8.10 Tohumlama koşullu olmak zorunda

Koşulsuzken in-memory DB'de zararsızdı ama `DATABASE_PATH` bir dosyayı
gösterdiğinde her yeniden başlatma 3 kampanya daha ekliyordu: **849 → 852 → 855
→ … sonsuza dek**. Şemada UNIQUE kısıtı yok, yani çift kayıtlar sessizce birikir
ve aynı banka kıyas tablosunda birden çok kez görünürdü. `counts()` sözleşme
metodu olduğu için koruma **Postgres yolunda da aynen** çalışır — ve orada daha
kritiktir: kalıcı bir hacim her `docker compose up`'ta aynı veriyi taşır.

### 8.11 `/banks` otorite kaynak süzmesi

Fıkhî terimlerin **tanımı banka sayfalarında yok**; bankalar terimi kullanır ama
açıklamaz (ölçüldü: `docs/rapor/musaraka-veri-boslugu.md`). Bu yüzden TKBB gibi
sektör otoriteleri de korpus kaynağıdır. Süzme olmadan **TKBB bu uçtan "11.
banka" olarak dönüyordu**. Ayrım `bddk_active` üzerinden **yapılmaz** (o alan
"gerçek banka ama lisansı aktif değil" demektir ve lisansı düşmüş gerçek bir
bankayı da katalogdan silerdi); `otorite_kaynak` bayrağıdır ve karar
**config-driven** kalır. Süzme **gizleme değildir**:
`?otorite_kaynaklari_dahil=true` tam listeyi döndürür. `/compare` bu riski zaten
taşımıyor: otorite belgelerinin ikisi de `belge_turu='sozlesme'` (ölçüldü).

### 8.12 Sunum katmanı kararları

- **`per_bank=best` varsayılan** (2026-08-09): şartnamenin çalışılmış örneği
  (s.12–13) banka başına bir satır gösteriyor; uç ise `extracted_fields`'teki
  **her** satırı döndürüyordu — "en düşük kâr payı hangi bankada" sorusunun
  cevabı bir bankanın kendi kampanyalarıyla dolu bir liste hâline geliyordu.
- **`/bank-delta` ayrı uç olarak**: arayüz bunu **8 ayrı `/compare` çağrısının**
  üstüne istemcide kuruyordu; tür süzmesi opsiyonel olduğu için *"Vade: rakip 84
  ay önde"* cümlesi bir **ihtiyaç finansmanı ile bir konut finansmanı** arasında
  üretilmiş olabiliyordu, 8 istek korpusun tamamını 8 kez geziyordu ve fark
  aritmetiği istemcideydi.
- **`intent` ölü parametreydi** — imzada duruyor, gövdede kullanılmıyordu.
  Kaldırılmadı, **uygulandı**: `chatbot/router.py` zaten aynı niyet sözlüğünü
  üretiyor ve ayrışırlarsa aynı soru iki arayüzde farklı sıralanır.
- **`compare.py`'nin bileşik skoru ~420 satır yazılı ve testliydi ama hiçbir
  uçtan çağrılmıyordu**; üstelik `/scoring` *"böyle bir şey yok"* diyerek onu
  yalanlıyordu — yani uç kendi kodunu yalanlıyordu ve jüri kodu okusa bunu
  görürdü. `GET /advantageous` 2026-08-08'de eklendi; `AdvantageousPanel` ise
  arayüzde `advantageous` geçen **tek satır bile yokken** sonradan bağlandı.
- **`ComparePanel` kampanya türü kapısı** (2026-08-09): tablo «elma ile armut
  kıyaslıyor» diye bildirildi. Tür süzmesi vardı ama varsayılanı «Tümü» idi ve
  `comparable` yalnız **birim** uyumunu doğruluyordu: `vade_ay` alanında 120
  aylık bir konut finansmanı 1., 36 aylık bir ihtiyaç finansmanı 2. sırada
  listeleniyordu — **hiçbir uyarı olmadan**. Çözüm süzmeyi zorunlu kılmak değil
  (veriyi gizlerdi), bölümlemek.
- **TEK TERİM kararı** (2026-08-09): aynı kavram (`campaign_type`, 8 sınıf)
  arayüzde iki adla dolaşıyordu — «ürün ailesi» ve «kampanya türü». Kullanıcı
  bunları **iki ayrı süzgeç sandı**. Tek ad seçildi: **kampanya türü**; tanımı
  `FairnessNotice` içinde **bir kez** yazılır.
- **`FieldChips` görünür başlık** (2026-08-09): çipler **etiketsizdi**, başlığı
  yalnız `aria-label` taşıyordu ve görsel olarak alttaki tür süzgeciyle aynı
  satır bandındaydı. Başlık artık görünür ve `aria-labelledby` ile **aynı düğüme**
  bağlı — "gören ve görmeyen kullanıcı aynı metni alır (ikisi ayrışırsa biri
  güncellenip diğeri unutulur)".
- **«LLM özeti» → «AI özeti»**: görünen etiket değişti, **kod içindeki adlar
  değişmedi** (`ozet_kaynak: "llm"`, `.badge-llm`, `KAYNAK_ETIKET`) — onlar
  `extractor` şemasının adlarıdır, DB sözleşmesidir. `SummaryNotice`'ın boşluk
  notu ayrıca **dört cümleden iki cümleye** indirildi; indirilirken korunan iki
  şey: özetin **üretilmediği** ve **uydurulmayacağı**.
- **Jüri modu**: güven skoru bir **denetim sinyalidir**, ürün rozeti değil. Skor
  **kalibre edilmemiştir**. Mod kapalıyken yalnız kıyas tablosundaki rozet
  gizlenir; Audit / Canlı Çıkarım / Şeffaf Skorlama **her hâlde** gösterir.
- **`ChatPanel` dört düzeltmesi**: (a) markdown render edilmiyordu — markdown'ı
  **sunucunun kendi şablonları** üretiyor (`structured.py`, `safety.py`'de 12
  satır) ve ekranda ham `**Kuveyt Türk**` görünüyordu; (b) Enter `busy` kontrol
  etmiyordu, istek uçarken Enter ikinci/üçüncü `POST /chat` başlatıyor,
  `finally` blokları yarışıyor ve **son dönen cevap** ekrana yazılıyordu;
  (c) tek satır `<input>` (Shift+Enter ayrımı yoktu); (d) her cevap bir öncekini
  siliyordu (tek `resp` state'i). Ayrıca soru kutusu artık **boşaltılıyor**:
  eskiden soru kutuda kalıyor, kullanıcı ikinci soruyu yazınca eskisinin ardına
  ekleniyordu ve *"ikinci soru sorulamıyor, sayfayı yenilemek gerekiyor"* gibi
  görünüyordu.

---

## 9. Tuzaklar

### T1 — `_contra_cache` farklı metinlerle doldurulabiliyor (ciddi)

`_campaign_contradictions(campaign_id, text, bank_slug, scraped_at)` **yalnız
`campaign_id`** ile önbelleklenir, ama çağıranlar farklı metin geçirir:

| Çağıran | Geçirilen metin |
|---|---|
| `/campaigns/{id}/text` | `camp["text"]` — `span_reference` (clean_text varsa o) |
| `/compare` | `view.get("text")` — aynı |
| `/contradictions` | **`camp.get("raw_text")`** |

Aynı belge için hangi uç **önce** çağrıldıysa onun metniyle üretilen sonuç
kalıcılaşır. `clean_text` ile `raw_text` ayrıştığında `/contradictions` ile
`/campaigns/{id}/text` **aynı belge için farklı sonuç** verebilir — ve hangisinin
geleceği istek sırasına bağlıdır. Kanıt offsetleri de o metne göre üretilir.

### T2 — «Süresi dolmuş kampanya» kuralı API yolunda hiç ateşlenmiyor (ciddi)

`_campaign_contradictions` şunu çağırıyor:

```python
c = build_campaign(text, bank_slug=bank_slug)
```

`build_campaign` imzası `(text, bank_slug, source_url=None, llm=None,
campaign_type=None, …)` — **`source_url` geçilmiyor**, dolayısıyla
`Campaign.source_url is None`. `_rule_expired_but_published` ilk satırında:

```python
url = campaign.source_url or ""
if not _CAMPAIGN_URL.search(url) or _ARCHIVE_URL.search(url):
    return []
```

yani kural **her zaman boş döner**. Korpusta doğrulanmış 6 çelişkinin **5'i** bu
kuraldan geliyor (contradiction.py modül docstring'i). `main.py` bu kuralın
*"`as_of` geçilmediği için bu uç noktada tamamen kapalıydı"* diye düzeltildiğini
yazıyor ve `scraped_at` artık geçiliyor — ama **`source_url` hâlâ geçilmiyor**,
yani kural pratikte hâlâ kapalı. `/contradictions`, `/campaigns/{id}/text` ve
`/compare`'in `contradiction_count` alanı bu bulgulardan **hiçbirini** göremez.

(`campaign_type` de geçilmiyor, ama mevcut kuralların hiçbiri onu okumuyor.)

### T3 — `_SUZME_HAZIR = False` olursa kıyas sessizce kirlenir

`_field_rows` `sozlesme_dahil` parametresini imza yoklamasıyla test eder; yoksa
**süzme yapılmadan** eski biçimde çağırır. Kodda açık bir `TODO(G)` var ve
"sessizce doğru davranıyormuş gibi yapmamak için bu durum burada açıkça duruyor"
deniyor — ama **çalışma zamanında hiçbir uyarı basılmaz, hiçbir uç bunu
raporlamaz**. Sözleşme/tarife belgeleri kıyas tablosuna karışır ve dışarıdan
görünmez.

### T4 — Chatbot'un yapısal yolunda kampanya türü kapısı YOK

`structured.answer` `repo.query_fields(r.field)` çağırır ve `rank()` sonucu
**tüm türler karışık** sıralanır. Süzgeç yalnız kullanıcı türü **söylediyse**
(`_FOLDED_TYPE_MAP` eşleşmesi) uygulanır. Yani panelde 2026-08-09'da kapatılan
"elma ile armut" boşluğu chatbot tarafında **açık duruyor**: *"En yüksek vade
veren banka hangisi?"* sorusu bir konut finansmanını bir ihtiyaç finansmanının
önüne koyabilir. Ayrıca `structured` yolu `sozlesme_dahil` süzmesini de
uygulamaz (bu ikincisi **bilinçli**, `_field_rows` docstring'inde yazılı).

### T5 — Güvenlik raporu ve karantina `/chat` yanıtında görünmüyor

`ChatAnswer` `safety_report` ve `gates` taşır, `SafetyReport.as_dict()` hazır —
ama `POST /chat` yalnız `{answer, handler, field, sources}` döndürür. Sonuç:
hangi kapının ateşlendiği, hangi yasak terimin yeniden yazıldığı ve **hangi
pasajın karantinaya alındığı** arayüze hiç ulaşmaz. `GATE_INJECTION` sabiti
tanımlı ama **hiçbir yerde `report.gates`'e eklenmiyor**; karantina yalnız
`logger.warning` ve `RagAnswer.quarantined` üzerinden görünür, ikisi de uçta
tüketilmiyor. `web/app/lib/api.ts`'deki `ChatResp` tipi de bu alanları
tanımlamıyor. Aynı şekilde `RagAnswer.retriever` ("hangi retriever konuştu")
alanı da uca çıkmıyor — oysa `rag.py` başlığı *"hangi retriever'ın kullanıldığı
GÖRÜNÜRDÜR"* diyor.

### T6 — RAG dizini ve `_view_cache` API ayaktayken bayatlar

`KeywordRetriever` **kurulum anındaki korpusun fotoğrafıdır** ve `reindex()`'i
çağıran bir uç yok. Aynı şekilde `_view_cache` yalnız *özet* için tazelenir;
düzeltilmiş bir offset ya da yeniden çıkarılmış bir alan **API yeniden
başlatılana kadar** görünmez. `SummaryCoverage` bu ayrışmayı kendi
docstring'inde kabul ediyor ("ikisi geçici olarak ayrışabilir") ama yalnız özet
için.

### T7 — `router.route`'ta ulaşılamaz dal

```python
if field and (intent or filters):             # (1)
    return Route("structured", …)
if field and intent in ("lowest", "highest"): # (2) — ULAŞILAMAZ
    return Route("structured", …)
```

(2)'nin koşulu sağlandığında `intent` doğru (truthy) olduğu için (1) zaten
dönmüştür. Ölü kod; davranışı etkilemiyor ama okuyanı yanıltıyor.

### T8 — Sessiz `except` blokları

| Yer | Yutulan | Sonuç |
|---|---|---|
| `rag.answer` LLM dalı | `except Exception: pass` | LLM hatası **hiç loglanmadan** çıkarımsal yedeğe düşer; "LLM açık" görünürken cevap alıntı olur |
| `main._bloklar` | `except Exception` | Metnin **tamamı görünür** olur; katlama sessizce kaybolur (kapsama garantisi korunur) |
| `main._campaign_contradictions` | `except Exception` | Çelişki listesi **boş** döner **ve önbelleğe yazılır** — kalıcı sessiz kayıp |
| `main._otorite_kaynak_sluglari` | `except Exception` | Süzme atlanır (**loglanır**) |
| `router.ChatContext.dogrula` | tanınmayan değerler | Bilinçli ve belgelenmiş |
| `juryMode` / `tabState` | `localStorage` / `history` hataları | Bilinçli, işlevsel kayıp yok |
| `build_app()` (modül sonu) | `except RuntimeError: app = None` | fastapi/pydantic yoksa modül import edilir ama `app` `None`'dır |

### T9 — `/scoring` ile kıyas tablosu farklı sıralayabilir

`scoring()` gövdesi `compare(field=field, type=type)` çağırır — `per_bank`
verilmez, yani **`"best"`** uygulanır (satırlar banka+tür başına tekilleşir), ama
`ComparePanel` kullanıcı `per_bank="all"` seçtiyse farklı bir küme gösterir.
Ayrıca `/scoring` **türlere bölmez**; `ScoringExplainer` bunu kabul edip bir
"kapsam şeridi" basıyor ("bu tablonun işi bir tavsiye üretmek değil, formülü
göstermek") — ama iki tablo yan yana durduğu için aynı bankayı **farklı sırada**
gösterebilirler.

### T10 — Yapısal yolda kaynak sayısı sınırsız

`bot._dispatch` `sources`'ı `ans.rows`'un **tamamından** kurar (`rank()` çıktısı,
kıyaslanamazlar dâhil). `list`/`filter` niyetli bir soruda bu, korpusun o alandaki
tüm satırları demektir; `ChatPanel > Kaynaklar` hepsini tabloya basar ve
`structured._phrase_list` de **hepsini** cevap gövdesine yazar. Ayrıca
`_kaynaklari_zenginlestir` her satır için `(bank, source_span)` sözlüğü kurar ve
**aynı anahtar ikinci kez görülürse `None` ile zehirlenir** — yani belirsiz
eşleşmede `campaign_id`/`source_url` `null` kalır (bu **bilinçli**: yaklaşık
eşleştirmeyle kampanya seçmek denetlenebilir bağlantı vaadinin tersi olurdu).

### T11 — Kırılganlık noktaları

- **`_ROW_TOKEN_SEP = "\x00"`** — `rank()` girdiye eklenen ek alanları `RankRow`'a
  taşımadığı için satır kimliği `bank` alanına gömülüyor. Sıralama mantığını
  kopyalamamak için doğru bir seçim, ama iki yerde (`compare`, `bank_delta`) elle
  çözülüyor ve `RankRow`'a bir alan eklendiği gün bu hile gereksizleşir.
- **Dört ayrı etiket sözlüğü** — `FIELD_LABELS` (main.py), `_FIELD_LABEL`
  (structured.py), `FIELD_DISPLAY` (router.py) ve `format.ts`. Anahtarlar kısmen
  örtüşüyor; ayrışma sessizdir.
- **Satır numaralı atıflar** — `VALID_INTENTS` yorumu `chatbot/router.py:57`'ye
  atıf yapıyor (o satır artık `_FIELD_KEYWORDS` sonu). Aynı kalıp
  `structured.py:125,136,137`, `safety.py:337`, `compare.py:502-507`,
  `compare.py:65-70`, `page.tsx:21-25` için de var; **hepsi kaymaya açık**.
- **`ComparePanel` satır anahtarı** `${campaign_id}-${tur}-${i}` — `openRow`
  durumu bu anahtara bağlı; `per_bank` veya süzgeç değişince açık satır sessizce
  kapanır.
- **`AuditPanel` başlangıç durumu** `useState(selectedId ?? campaigns[0]?.id)` —
  `campaigns` sonradan dolarsa `id` `null` kalır; `page.tsx` bunu
  `campaigns.loading` kontrolüyle örtüyor, yani koruma **çağıran tarafta**.
- **`useAsync` bağımlılık listesi** `[...deps, nonce]` ve `eslint-disable` ile
  susturulmuş; `loader` her render'da yeniden oluştuğu için doğruluk tamamen
  çağıranın `deps` disiplinine bağlı.
- **`detect_across` çağrılmıyor** — belgeler arası iki kural (`_cross_rule_rate`,
  `_cross_rule_end_date`) yalnız `scan.py` ve testlerden erişilebilir; API'de yok.
- **CORS `allow_origins=["*"]`** — demo için kabul edilebilir, ama `/extract` ve
  `/chat` gövde alan POST uçlarıdır.
- **`.badge-ner` sınıfı ve `Extractor.NER`** — CLAUDE.md §3'e göre bu teslimde
  **hiçbir kod yolunda üretilmiyor**; sınıf ve tip şema uyumluluğu için duruyor.
