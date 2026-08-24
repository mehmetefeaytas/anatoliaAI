# SSB EVREN Çıkarım Servisi — Ölçüm, Entegrasyon ve Kapsam Sınırları

**Durum:** entegre (opsiyonel kademe) · ölçüldü · teslim yoluna KOŞULLU
**Ölçüm tarihi:** 2026-08-24
**İlgili şartname kalemleri:** §5.9 (on-prem, %20), §5.10 (ücretli API yasağı), §8
**İlgili kod:** `src/extraction/llm/clients.py`, `src/extraction/llm/cascade.py`,
`src/extraction/llm/extractor.py` (`default_extractor`)

---

## 1. Servis nedir

TEKNOFEST 2026 Yapay Zekâ Dil Ajanları Yarışması kapsamında T.C. Cumhurbaşkanlığı
Savunma Sanayii Başkanlığı (SSB) tarafından **tüm takımlara ücretsiz** açılan
çıkarım servisi. Yarışmaya tahsis edilmiş 8 × NVIDIA H200 üzerinde vLLM · BF16
(kuantizasyon yok). Kota, senaryo kısıtı ve takım başına model listesi yok;
on modelin tamamı bütün takımlara açık. Takım başına izole Qdrant vektör
veritabanı da veriliyor.

Uç: `https://evren-llmapi.ssyz.org.tr/v1` — **OpenAI-uyumlu**.
Belgeler: `https://evren-teknofest.ssyz.org.tr`

### Model listesi (canlı çekildi, 2026-08-24)

| Takma ad | Bağlam | Ölçüm sonucu | Bize yararı |
|---|---|---|---|
| `llm-large` | 262.144 | Qwen3.5-122B-A10B; 3,8 s/belge | ✗ kural hattının altında (§5) |
| `llm-fast` | 262.144 | 4,1 s/belge — **`llm-large`'dan YAVAŞ** | ✗ ad yanıltıcı, fark yok |
| `router` | 40.960 | yönlendirici değil, **kendisi bir LLM**; çıkarım yapıyor | ~ ayrı bir değeri yok |
| `vlm` | 262.144 | **HTTP 400: "At most 0 image(s) may be provided"** | ✗ görüntü desteği KAPALI |
| `guard` | 32.768 | çalışıyor: `Safe/None` · enjeksiyonda `Controversial/Jailbreak` | ~ bizde zaten var (`safety.py`) |
| `embed` | 32.768 | 2560 boyut; R@1 %97, MRR 0,983; 3,3 s | ~ `bge-m3-embed` kadar iyi, daha pahalı |
| `bge-m3-embed` | 8.192 | 1024 boyut; **R@1 %97, MRR 0,983**; 2,3 s | ✓✓ **en değerli uç** (§8) |
| `bge-m3-sparse` | 8.192 | **HTTP 501 Not Implemented** | ✗ uç yok |
| `bge-m3-colbert` | 8.192 | **HTTP 501 Not Implemented** | ✗ uç yok |
| `rerank` | 32.768 | kısa/temiz belgede doğru; **gerçek korpusta MRR 0,68 → 0,29** | ✗ sıralamayı BOZUYOR (§7) |

Ölçüm yöntemi (gömme ve rerank): gerçek korpustan (`data/demo.db`, 2.708
kampanya) 30 kayıt; her kampanyanın `ozet` alanı **sorgu**, `clean_text` alanı
**hedef pasaj**. Altın etiket kampanya kimliğidir — elle etiketleme gerekmez.

---

## 2. Mimarimize uyum — neden entegrasyon ucuz oldu

`VLLMClient` zaten OpenAI-uyumlu `/v1/chat/completions` ucunu konuşuyor ve
gömme katmanımız zaten `BAAI/bge-m3` (1024 boyut). EVREN ikisini de birebir
sunuyor. Gereken tek kod eklemesi **bearer başlığı** oldu:

- `bearer_transport(api_key)` — `Transport` imzası `(url, payload, timeout)`
  olarak SABİT tutuldu (onlarca test sahte taşıma enjekte ediyor); anahtar bir
  closure'a kapatıldı.
- `VLLMClient(api_key=...)` — argüman > `VLLM_API_KEY` env. Anahtar boşsa
  `Authorization` başlığı **hiç gönderilmez** (yerel vLLM/Ollama geriye uyumu).
- Açıkça enjekte edilmiş `transport` her koşulda kazanır; ağsız CI env'den
  etkilenmez.

Testler: `tests/test_llm_bearer.py` (7 test).

---

## 3. Ölçülen KUSURLAR — ve bunların bizde açtığı gerçek hata

### 3-a. Karmaşık şemamız `json_schema`da HTTP 500 veriyor

`guided_json_schema()` 12 alanlı, **39 `anyOf`** ve **37 `null`** dalı içeren
5.548 karakterlik bir şema. EVREN bunu hem `strict:true` ile hem strict'siz
reddediyor:

```
litellm.InternalServerError: Hosted_vllmException - {"code":500}
```

Basit bir şema (4 düz alan) ise **çalışıyor** — yani sorun şemanın
karmaşıklığında, servisin yeteneğinde değil. Alan başına çağrıda (tek alanlık
şema) `json_schema` gerçekten devreye giriyor (bkz. §5).

### 3-b. `guided_json` SESSİZCE yok sayılıyor — pazarlığın kör noktası

Bu, servisin değil **bizim kodumuzun** kusuruydu ve ölçümle ortaya çıktı.

`negotiate()` bir modu "çalışıyor" saymak için yalnızca **HTTP 200**'e
bakıyordu. EVREN `guided_json` parametresini tanıyıp 200 döndürüyor ama kısıtı
**hiç uygulamıyor**:

| İstek | Yanıt |
|---|---|
| `guided_json` + `max_tokens=1` | `'P'` — yani "Pong!" |
| `guided_json` + `max_tokens=8` | `'Pong! 🏓\n\nHow'` |

Kısıt uygulanıyorsa ilk token `{` olmak **zorundadır**. Pazarlık `guided_json`'u
seçiyor, gerçek çağrı serbest Türkçe metin döndürüyor, `parse.py` onu
ayrıştıramıyor ve sonuç üst katmanda **"LLM hiç alan bulamadı"** olarak
görünüyordu — `clients.py` modül docstring'inin önlemek için yazıldığı hata
sınıfının tam olarak aynısı, yeni bir kılıkta.

**Düzeltme:** prob artık kısıtın UYGULANDIĞINI da sınıyor (`_kisit_uygulandi`).
Muhafazakârlık kuralı: prob yanıtı **boşsa** mod elenmez (kararsızlığı "kısıt
yok" diye okumak çalışan bir modu eler). `prompt_only` hiç proba tabi değil —
orada kısıt zaten yok, son çaredir ve elenirse hiç mod kalmaz.
Kaçış kapısı: `VLLM_KISIT_PROBU=0`.

Testler: `tests/test_llm_kisit_probu.py` (7 test).

### 3-b-2. Şema desteği ALAN BAZINDA değişiyor — pazarlığın ikinci kör noktası

Alan başına çağrı modunda (`LLM_ALAN_BASINA=1`, tek alanlık şema) pazarlık
`json_schema`'yı seçiyor: yani **gerçek şema kısıtı tek alanlık şemada
çalışıyor**. Ama 12 alandan biri, `hedef_kitle`, aynı modda HTTP 500 veriyor
ve `LLM_STRICT=1` altında koşum düşüyor (11 alan geçtikten sonra):

```
LLMHTTPError: HTTP 500 ... | alan=hedef_kitle | mode=json_schema | ham=''
```

Pazarlık modu **istemci başına** ölçüp cache'liyor; altında yatan varsayım
"sunucu bu parametreyi ya destekler ya desteklemez". EVREN bu varsayımı
kırıyor: desteği **şemaya göre** değişiyor. Açık kalem — düzeltmenin iki yolu
var (şema-başına pazarlık, ya da sorunlu alan şemasının sadeleştirilmesi) ve
ikisi de ölçülmeden seçilmemeli.

### 3-c. ÇÖZÜM: `tool_calling` — şemayı taşıyan alan değişince kabul edildi

Resmi dokümantasyon (`evren-teknofest.ssyz.org.tr`) tool/function calling'in
desteklendiğini yazıyor. Denendi ve **aynı şema kabul edildi**:

| yol | 12 alanlı şemamız (39 `anyOf`, 5.548 krkt) |
|---|---|
| `response_format: json_schema` | **HTTP 500** |
| `structured_outputs` | **HTTP 500** |
| `guided_json` | HTTP 200, kısıt **yok sayılıyor** |
| **`tools` + `tool_choice`** | **200 — 12 alanın TAMAMI doğru yapıda** |

Yani uç şemayı derleyebiliyor; kabul etmediği şey `response_format`
sarmalayıcısıydı. Bu, ablasyon raporlarındaki "gerçek şema kısıtı hiç devreye
girmedi" uyarısını kapatan bulgudur.

Mod `STRUCTURED_MODES`'a eklendi ve sırası kısıt gücüne göre belirlendi:
`json_schema → structured_outputs → guided_json → tool_calling → json_object
→ prompt_only`. `json_object`tan ÖNCE, çünkü o yalnız JSON biçimini kısıtlar.

Bir incelik: tool calling'de model çıktıyı
`message.tool_calls[0].function.arguments` içine yazar ve `content` **boş**
kalır. Yalnız `content`e bakan bir okuyucu bunu "model boş cevap verdi" diye
okur ve üst katman çıkarımı sessizce kaybeder — `_yanit_metni` bu yüzden var.
Kısıt probu da `tool_calls` varlığını kısıtın kanıtı sayar; saymasa bu modu
eler ve daha zayıf `json_object`a düşerdik.

Testler: `tests/test_llm_tool_calling.py` (13 test).

#### Ve hipotez ÇÜRÜDÜ — kısıt kaliteyi artırmadı

Ablasyon raporlarındaki uyarı ("gerçek şema kısıtı hiç devreye girmedi") bir
hipotez taşıyordu: kısıt devreye girse kalite yükselirdi. Kısıt devreye
sokuldu ve **aynı gold üzerinde** ölçüldü (`gold.v1`, 20 kayıt, `strict`):

| mod | kural | llm | hibrit | uydurma | FP |
|---|---|---|---|---|---|
| `json_object` (kısıtsız) | 0,469 | **0,331** | 0,510 | 23 | 46 |
| `tool_calling` (gerçek kısıt) | 0,469 | **0,304** | 0,483 | **18** | **41** |

Kısıt kaliteyi **artırmadı, hafifçe düşürdü**. Yön okunabilir: kısıtlı model
daha MUHAFAZAKÂR — daha az uydurma (18 vs 23) ve daha az yanlış pozitif
(41 vs 46) üretiyor, ama daha az doğru alan da buluyor (TP 19 vs 22).

**Sonuç:** EVREN'in çıkarım kolunun kural hattımızın altında kalması bir
yapılandırma eksiği DEĞİL. Şema kısıtı elde edildi ve tablo değişmedi; fark
modelin Türkçe finansal çıkarım kabiliyetinde. Bu, `evren` kademesinin
teslimde kapalı kalması kararını **güçlendirir**.

Yine de mod kalıcı bir kazanç: `response_format` reddedilen her uçta artık
gerçek şema kısıtı elde edebiliyoruz ve uydurma oranı ölçülebilir biçimde
düşüyor — çıkarım kolu bir gün açılırsa doğru mod hazır.

### 3-d. Eklenen mod: `json_object`

`json_schema` 500 verip `guided_json` yok sayıldığında elimizde yalnız
`prompt_only` (hiç kısıt yok) kalıyordu. Araya `response_format={"type":
"json_object"}` eklendi: şema kısıtı yok ama **JSON kısıtı var**.

Pazarlık zinciri artık: `json_schema → structured_outputs → guided_json →
json_object → prompt_only`. EVREN'de seçilen mod `json_object`.

**Ama ölçüldü: kalite kazancı SIFIR.** `prompt_only` ile `json_object`
koşumları birebir aynı sonucu verdi (aşağıdaki tablo). Gerekçe: model
`temperature=0`'da zaten geçerli JSON üretiyordu (şema yönergesi prompt'a
gömülü); darboğaz JSON *biçimi* değil, şema/içerik uyumu. Mod yine de değerli —
biçim garantisi bedava geliyor ve başka bir sunucuda fark yaratabilir.

---

## 4. Kademe zinciri — teslim yoluna nasıl KONULABİLİR

`LLM_BACKEND` artık virgüllü bir **kademe listesi** kabul ediyor:

```
LLM_BACKEND=evren,ollama     # EVREN'i dene, düşerse yerel Ollama devralsın
```

`CascadingClient` (`src/extraction/llm/cascade.py`) tek bir istemci gibi
davranır; `LLMExtractor` farkı görmez.

- **Geçiş tetiği:** yalnız `LLMError` soyu — `LLMTransportError`
  (ulaşılamadı / duvar-saati sınırı) ve `LLMHTTPError` (sunucu reddetti).
  `ValueError`/`KeyError` bizim kodumuzla ilgilidir, yedeğe geçerek gizlenmez.
- **Devre kesici:** düşen kademe `LLM_CASCADE_COOLDOWN` (vars. **300 sn**)
  boyunca ATLANIR — denenmez bile. Zorunlu, çünkü 48 belgelik bir koşum aksi
  hâlde 48 kez duvar-saati sınırını bekler. Zincirde denenecek kimse kalmazsa
  körü körüne beklemek yerine gene denenir.
- **Devre durumu kademe İNDEKSİYLE anahtarlanır**, nesne kimliğiyle değil:
  `LLMExtractor._butceli_istemci` çalışma sırasında her kademenin bütçeli bir
  kopyasını çıkarıyor; ilk hâli `id()` kullandığı için kopyada kesici sessizce
  devre dışı kalıyordu.
- **Hata türü korunur:** zincirin tamamı düşerse son hata olduğu gibi yükselir;
  kademe kademe gerekçe `son_hatalar` listesinde ve log'da durur.
- **Anahtarsız `evren` kademesi sessizce atlanır.** Teslim edilen kopyada
  `EVREN_API_KEY` yoktur; orada zincirin yerel kademeye düşmesi **beklenen**
  davranıştır, kurulum hatası değil. Ama zincirde başka kademe de yoksa bu
  gerçek bir kurulum hatasıdır ve `LLM_STRICT` altında yükselir.

Testler: `tests/test_llm_cascade.py` (17), `tests/test_llm_zincir_fabrikasi.py` (11).

### Fallback KANITI (gerçek koşum, 2026-08-24)

`LLM_BACKEND=vllm,evren` ile yerel uç kapalıyken:

```
WARNING cascade: VLLMClient(Qwen/Qwen3-8B) dustu (LLMTransportError)
                 -> siradaki istemci
aktif kademe    : VLLMClient llm-large
structured_mode : json_schema
düşen kademe    : http://localhost:8001/... ulasilamadi: [Errno 61]
                  Connection refused
alanlar         : kar_payi_orani=3.45 (conf 0.99, logprob, span 43–63)
                  vade_ay=6          (conf 0.99, logprob, span 13–24)
```

İki gözlem: (1) geçiş çalışıyor, (2) EVREN **logprob döndürüyor** — yani
`confidence.py`'nin alan bazlı güven skoru vLLM yolunda gerçek ölçümle
besleniyor (Ollama logprob hiç vermez, orada skor modelin kendi beyanıdır).

---

## 5. Ölçüm — EVREN teslim yoluna değer mi?

Ablasyon, `data/gold/gold.v2.json` (48 kayıt, 40 zor), eşleştirici `strict`,
`LLM_STRICT=1`, önbellek kapalı, 96 gerçek çağrı/koşum.

| Kol | mod | F1 (tüm) | F1 (zor) | TP | FP | FN | Uyd. |
|---|---|---|---|---|---|---|---|
| kural | — | **0,570** | **0,587** | 65 | 54 | 44 | 15 |
| llm (EVREN 122B) | `prompt_only` | 0,329 | 0,332 | 35 | 69 | 74 | 14 |
| llm (EVREN 122B) | `json_object` | 0,329 | 0,332 | 35 | 69 | 74 | 14 |
| hibrit | `json_object` | 0,556 | 0,571 | 67 | 65 | 42 | 25 |

McNemar (eşleşmiş çiftler):

- `kural vs llm` [tüm]: b=47 c=18, p=0,00051 → **ANLAMLI, kazanan kural**;
  mikro-F1 farkı 0,242 [0,157–0,323] → GA dışında, fark **kanıtlandı**
- `kural vs llm` [zor]: p=1,47e-05 → **ANLAMLI, kazanan kural**; fark 0,255
- `kural vs hibrit`: fark 0,014 [−0,007–0,036] → GA **içinde**, fark
  kanıtlanmadı
- `llm vs hibrit`: p=0,0081 → hibrit kazanıyor (yani uzlaştırma katmanı LLM'in
  hatalarını gerçekten süzüyor)

**Okuma:** tam şemayla çağrıldığında kural hattımız EVREN'in 122B modelini
istatistiksel olarak **yeniyor**, ve hibrit kol kural-only'nin üstüne
ölçülebilir bir şey koymuyor.

### Alan başına çağrı — kısıt devreye giriyor ama kazandırmıyor

"Şema kısıtı hiç devreye girmedi, o yüzden düşük" hipotezi ayrıca sınandı.
`LLM_ALAN_BASINA=1` ile şema tek alana iner ve pazarlık gerçekten
`json_schema`'yı seçer (§3-b-2). **Aynı gold** üzerinde karşılaştırma
(`gold.v1`, 20 kayıt, `json_object`'e sabitlenmiş — çünkü `hedef_kitle` alanı
`json_schema`'da 500 veriyor ve `LLM_STRICT=1` koşumu düşürüyor):

| Mod | kural | llm | hibrit | gerçek çağrı |
|---|---|---|---|---|
| tam şema | 0,469 | **0,331** | 0,510 | 40 |
| alan başına | 0,469 | **0,323** | 0,507 | **413** |

10 kat çağrı maliyetine karşılık hafif bir **düşüş**. Hipotez çürüdü: kısıtın
devreye girmesi tek başına yetmiyor, darboğaz başka yerde (muhtemelen
normalizasyon/eşleştirme uyumu — `per_field.csv` ile alan alan incelenmeli).

**Karar için sonuç:** bugünkü hâliyle `evren` kademesinin AÇIK olması için
gerekçe yok. Altyapı hazır ve sınanmış bekler; kalite kazancı ölçülene kadar
teslimde `LLM_BACKEND` boş (kural-only) ya da yerel kalır. Hibritin kural'ı
geçtiği tek koşum `gold.v1`'dedir ve fark **güven aralığı içindedir**;
`gold.v2`'de ise hibrit kural'ın *altındadır*. İki gold arasında yön değiştiren
bir fark karar dayanağı olamaz.

---

## 6. Şartname konumu ve kapsam sınırları

**§5.10 (ücretli API/servis yasağı) — ihlal YOK.** EVREN ücretsizdir ve
yarışmanın kendi altyapısıdır. `.env.example`'da yalnız **boş** bir
`EVREN_API_KEY` alanı ve uç adresi durur; anahtar repoya **girmez**.

**Teslimde erişim VAR (takım beyanı, 2026-08-24).** Yarışma anında EVREN'e
erişimimiz olacağı bildirildi. Bu, `evren` kademesinin teslim yolunda AÇIK
olabileceği anlamına gelir — ama neyin açılacağına ÖLÇÜM karar verir, erişimin
varlığı değil: çıkarım kolu kural hattımızın altında (§5, §3-c) ve orada açmak
kaliteyi düşürür. Açılması ölçümle desteklenen kalemler: gömme/erişim (§8),
uzun belge çıkarımı (§9), özet üretimi (§10).

**§5.9 (on-prem uygulanabilirlik, %20) — kademe mimarisi bunu KORUR.** Sistemin
çalışması EVREN'e bağlı değildir: anahtar yoksa kademe atlanır, kademe düşerse
yerel yol devralır, hepsi düşerse kural-only koşar. Yani uzak uç sistemi
**iyileştiren** bir katmandır, **ayakta tutan** bir katman değildir. Mevcut
ağsız kanıt paketi (`docs/OFFLINE-KANIT.md`, 14/14 + tam yığın 3/3 · 39/39)
geçerliliğini korur.

Teslimde erişim olması bu yapıyı GEREKSİZ kılmaz: jüri "internet olmadan
çalışıyor mu" diye sorabilir ve %20'lik kalem tam bunu ölçüyor. Kademe,
iki soruyu birden cevaplamayı mümkün kılan yapıdır — "EVREN ile daha iyi"
ve "EVREN olmadan da çalışır".

### Kendimiz yazıyoruz — kalan sınırlar

- **Servis paylaşımlıdır.** Tüm takımlar aynı 8×H200'ü kullanıyor; gecikme
  garanti edilmez. Demo yolunda §11 kuralı (canlı LLM'e bağlanma) hâlâ
  geçerlidir: EVREN kademesi demo için **önerilmez**, veri önceden doldurulur.
- **Tüm modeller sınandı** (24 Ağu, §1 tablosu ve §7–§8). Sınanmayan tek
  kalem: `vlm`'in video girdisi — görüntü girdisi zaten kapalı olduğu için
  video de denenmedi. `guard`ın Türkçe kapsamı yalnız iki örnekle yoklandı.
- **`llm-large` lisansı** modelin kendi beyanına dayanıyor (Qwen3.5-122B-A10B);
  `docs/model-license-audit.md` disipliniyle (HF model kartı + `base_model`
  zinciri köke kadar) **bağımsız doğrulanmadı**. Ağırlıkları biz indirmiyor
  olsak da ölçüm raporlarında model kimliği geçtiği için bu açık kalemdir.
- **Ablasyon tek gold sürümünde** (`gold.v2`, 48 kayıt) koşuldu.

---

---

## 7. rerank — ölçüldü, işimize YARAMIYOR

Kontrollü bir testte (4 kısa, birbirinden farklı konuda belge) rerank hem
Türkçe hem İngilizce doğru sıralıyor. Ama **gerçek korpusta sıralamayı
bozuyor**, ve bu her pasaj uzunluğunda geçerli:

| Pasaj boyu | gömme R@1 | gömme MRR | +rerank R@1 | +rerank MRR | sonuç |
|---|---|---|---|---|---|
| 250 krkt | %53 | 0,622 | %7 | 0,252 | **kayıp** |
| 500 krkt | %70 | 0,768 | %13 | 0,337 | **kayıp** |
| 1000 krkt | %53 | 0,680 | %3 | 0,293 | **kayıp** |

Sorgular kasten zorlaştırıldı (özetin ilk 10 kelimesi), çünkü tam özetle gömme
%97'de tavana vuruyor ve rerank'in katkısı ölçülemez hâle geliyor.

Kod tarafı elenmiş bir açıklama: rerank kırpma yapmıyor (8 belge → 8 sonuç) ve
`index` alanı giriş sırasını veriyor; sıralama mantığımız doğru. Kalan
açıklama modelin kendisi: gerçek korpustaki 30 kampanya metni birbirine
**benziyor** (aynı menü/altlık gürültüsü, aynı bankacılık dili) ve rerank bu
ince ayrımları yapamıyor — gömme modeli yapıyor.

**Karar:** `rerank` kullanılmaz. Kullanılsaydı chatbot erişim kalitesini
düşürürdü.

---

## 8. En değerli bulgu — gömme yolu şu an KAPALI ve EVREN onu açıyor

`data/demo.db` içinde `embeddings` tablosu **boş (0 satır)**, çünkü bu makinede
`sentence-transformers` **kurulu değil**:

```
EmbeddingModelUnavailable: `sentence-transformers` kurulu değil,
bge-m3 gömmeleri üretilemez.
```

Sonuç: `chatbot/rag.py` içindeki `VectorRetriever` hiç devreye girmiyor
(kurulum koşulu: gömme modeli + dolu `embeddings` tablosu). Chatbot bugün
yalnız `KeywordRetriever` ile çalışıyor — yani **anlamsal erişim kolu eksik**.

EVREN bu boşluğu tam olarak doldurabiliyor:

- `bge-m3-embed` **bizim modelimizin aynısı** (`BAAI/bge-m3`, 1024 boyut) —
  `EMBEDDING_DIM` değişmeden takılır. **Ölçülerek doğrulandı** (24 Ağu):
  aynı metin iki uçla gömülüp karşılaştırıldı, kosinüs **0,99993**
  (çapraz kontrol 0,436). Yani tablo EVREN ile doldurulup teslimde YEREL
  modelle sorgulanabilir; uzaylar ayrışmıyor. Bu, kademenin güvenli
  olduğunun kanıtıdır — varsayım değil.
- Ölçülen kalite: **Recall@1 %97, MRR 0,983** (30 gerçek kampanya).
- Hız: 30 pasaj 2,3 s → 2.708 kampanyanın tamamı için makul.
- `build_embeddings(repo, embedder=...)` bir `Embedder` **enjekte etmeye açık**;
  protokol yalnız `dim` + `encode(texts)` istiyor. Yani EVREN destekli bir
  `Embedder` yazmak küçük bir iştir.
- **En önemlisi:** çıktı vektörler `embeddings` tablosuna YAZILIR. Yani bu
  kullanım *tek seferlik* bir üretim adımıdır; teslim edilen sistemde ağ
  gerekmez ve §5.9 (on-prem) hiç zedelenmez.

Bu, EVREN'in ölçülmüş net kazancıdır ve LLM çıkarım kolundan bağımsızdır.

### Yapıldı (24 Ağu 2026) — tablo DOLDURULDU

`EvrenEmbedder` + `KademeliEmbedder` yazıldı (`src/rag/embedding.py`,
22 test) ve tam koşum yapıldı:

```
ran: true · backend: sqlite · model: "evren:bge-m3-embed -> BAAI/bge-m3"
campaigns_seen: 2708 · campaigns_embedded: 2708 · campaigns_empty: 0
chunks_written: 51556 · elapsed_s: 647.5 · errors: []
```

`VectorRetriever` artık **kuruluyor** (önce `EmbeddingModelUnavailable` ile
düşüyordu). Yedek yol da kapatıldı: `sentence-transformers==6.0.0` kuruldu,
SBOM tazelendi, sürüm pinlendi (`requirements.txt`'teki notun kendi talimatı).
`requirements-api.txt` onu hâlâ **bilerek dışlıyor** — torch ince imajı
GB'lara çıkarır ve §5.9 paket boyutu ölçümünü bozar.

### Kazanç ÖLÇÜLDÜ — banka hedeflemede 8/10 → 10/10

`eval/rag_eval.py`'ye `--vektor` kolu eklendi (araç yalnız `KeywordRetriever`'ı
ölçebiliyordu; doldurulan tablonun kazancı ölçülmeden değerlendirilemezdi).
Üç kol, aynı soru kümesi, k=5:

| kol | terim kapsama (15 soru) | banka hedefleme (10 soru) | toplam isabet |
|---|---|---|---|
| keyword (üretim) | 13 · R@1 0,867 · MRR 0,867 | 8 · R@1 0,800 · MRR 0,800 | 21/25 |
| bm25 | 13 · R@1 0,867 · MRR 0,867 | 8 · R@1 0,800 · MRR 0,800 | 21/25 |
| **vector (EVREN)** | 13 · R@1 0,800 · **R@5 0,867** · MRR 0,833 | **10 · R@1 1,000 · MRR 1,000** | **23/25** |

Vektör kolu, keyword'ün kaçırdığı iki soruyu (*"Dünya Katılım kampanyaları"*,
*"T.O.M. Katılım kampanyaları"*) buluyor. Terim kapsamada isabet aynı (13/15)
ama bir vakada doğru belge ilk sırada değil (R@1 0,867 → 0,800; R@5 değişmiyor).
Çekimserlik iki kolda da 30/30 — yani vektör kolu "bilmiyorum" demesi gereken
yerde konuşmaya başlamıyor.

### BÜYÜK erişim testi (255 soru) — iki soru tipi ZIT yönde

`rag_eval`'in 25 sorusu karar için yetersizdi. 255 soruluk, iki bölümlü ve
**otomatik altın etiketli** bir test kuruldu:

| kol | A. özet-tabanlı sorgu (n=200) | B. banka hedefleme (n=55) |
|---|---|---|
| keyword (üretim) | **R@1 %69,0 · R@10 %91,5 · MRR 0,774** | 23/55 (**%42**) |
| vector | R@1 %49,5 · R@10 %68,0 · MRR 0,559 | **43/55 (%78)** |
| hibrit (RRF) | R@1 %66,0 · **R@10 %92,5** · MRR 0,761 | 39/55 (%71) |

**Metodolojik uyarı — A bölümündeki keyword üstünlüğü YAPAY.** Sorgular
belgenin kendi özetinden türetiliyor, dolayısıyla kelime örtüşmesi doğal
olmayan biçimde yüksek ve anahtar-kelime kolunu ödüllendiriyor. Gerçek
kullanıcı belgenin cümlelerini kopyalamaz; "Kuveyt Türk kâr payı oranı" diye
sorar — yani **B bölümü gerçek kullanıma daha yakın** ve orada vektör kolu
keyword'ü %42 → %78 ile geçiyor.

Hiçbir tek kol iki tipte de iyi değil. Bu yüzden `HybridRetriever` yazıldı
(RRF; skorlar farklı ölçekte olduğu için toplam değil sıra birleştirilir) ve
`RAG_RETRIEVER=hibrit` modu eklendi — 10 test.

#### Ama hibrit MİMARİDE beklendiği gibi çalışmadı

Test betiğindeki RRF banka hedeflemede 39/55 (%71) veriyordu; mimarideki
`HybridRetriever` aynı soru kümesinde **27/55 (%49)** verdi. Fark **aday
derinliğinde**: betik her koldan 10 aday alıyordu, sınıf ise `k`'nın dört katını
alıyor — `k=1` çağrısında yalnız 4 aday. O derinlikte iki kolun birinci adayı
RRF'de **eşit skor** alıyor (`1/(60+1)`) ve eşitlik anahtar-kelime kolu lehine
bozuluyor (listede o önce geliyor). Sonuç: hibrit, kötü olan kola yakınsıyor.

| kol | banka hedefleme (n=55) |
|---|---|
| keyword | 23/55 (%42) |
| **vector** | **43/55 (%78)** |
| hibrit (mimari, derinlik 4×) | 27/55 (%49) |
| hibrit (betik, derinlik 10) | 39/55 (%71) |

**Karar:** hibrit hiçbir derinlikte `vector`ü geçmedi; bu soru tipinde en iyi
kol **tek başına vektördür**. `hibrit` modu kodda opsiyonel olarak duruyor
(zararsız, testli) ama ÖNERİLMEZ. Eşitlik bozma ve kol ağırlığı ölçülmeden
üzerine bir şey inşa edilmemeli.

**Yan kanıt:** koşum sırasında EVREN gömme ucu düştü ve log'a
`gomme kademesi dustu -> siradaki` yazıldı; yerel model devraldı, ölçüm
bozulmadı. Kademe gerçek bir kesintide çalıştı — uzaylar aynı olduğu için
(kosinüs 0,99993) sonuç geçerli kaldı.

**Kalan uyarı:** ham vektör aramasında uzun sözleşmeler baskın çıkabiliyor.
"en yüksek kâr payı oranı hangi bankada" sorgusu *Genel Kredi Sözleşmesi*
pasajları döndürdü (982 sözleşme, 51.556 chunk'ın büyük kısmı) — jenerik
hukuki metin her sorguya orta benzerlik veriyor. Ölçüm kümesi bunu
cezalandırmıyor; gerçek kullanımda `belge_turu` süzgeci ya da hibrit skor
gerekebilir. `RAG_RETRIEVER` varsayılanı bu yüzden hâlâ `keyword`; açmak için
`RAG=auto make baslat`.

---

## 9. 262k bağlam — iddia GERİ ÇEKİLDİ (ölçüm hatası bizdeydi)

Korpusta **245 belge** 8k token (~24.000 karakter) sınırını aşıyor;
`OLLAMA_NUM_CTX=8192` ile koşan yerel LLM yolu onları kırpıyor. Buradan
"262k bağlam net kazanç" sonucu çıkarıldı ve **o sonuç yanlıştı.**

### Yanlış ölçüm

Aynı belge iki kez çıkarıma verildi (24k'ya kırpılmış / tam metin) ve tam
metinde "12 alanın tamamı" bulundu diye raporlandı. Hata: sayılan şey alan
**anahtarıydı**, dolu **değer** değil. Şema her alanı döndürür ve boş olanı
`{"value": null, "confidence": 0, "source_span": null}` biçiminde verir — bu
bir boş sözlük OLMADIĞI için "dolu" sayıldı. Gerçekte o 12 anahtarın çoğunun
değeri `null`'dı.

### Doğru karşılaştırma — ve kural hattı KAZANIYOR

İkinci hata karşılaştırmanın kendisindeydi: kırpık-vs-tam, LLM kolunun kendi
içinde kıyasıdır. Kural hattı regex tabanlıdır ve metnin **tamamını** tarar;
kırpma yalnız LLM yolunu etkiler. Nitekim 245 uzun belgenin **243'ünde kural
hattı zaten alan bulmuş** (741 alan, ~3/belge) — o belgeler boş değildi.

Doğru ölçüm (6 en uzun belge, dolu DEĞER sayımı):

| belge | KURAL | EVREN (262k) | EVREN'in ekstrası |
|---|---|---|---|
| 345 (361k krkt) | 3 | 2 | 0 |
| 343 (321k) | 3 | 3 | 0 |
| 446 (306k) | **5** | 1 | 0 |
| 1827 (290k) | 3 | 3 | 0 |
| 607 (272k) | **5** | 1 | 0 |
| 445 (266k) | **5** | **0** | 0 |
| **toplam** | **24** | **10** | **0** |

EVREN, kural hattının bulduklarının bir **alt kümesini** buluyor ve **tek bir
yeni alan katmıyor**. Bir belgede hiç alan bulamadı; kural orada 5 buldu.

**Sonuç:** 262k bağlamın uzun sözleşmelerde ölçülebilir bir kazancı YOK ve bu
kalem üretime alınmamalıdır. Uzun bağlam bir yetenek olarak duruyor (45.959
token'lık bağlam sorunsuz işlendi, bkz. §14 prefix caching) ama bizim çıkarım
işimizde karşılığı çıkmadı — §3-c'deki tool_calling bulgusuyla aynı yön:
EVREN'in çıkarım kolu kural hattımızın altında ve bu bir yapılandırma eksiği
değil.

## 10. Özet yenileme ve SAYI KAPISI — iki kez ölçüldü, ilki yanlıştı

### İlk ölçüm ve onun çürütülmesi

Mevcut 2.676 özet yerel qwen ile üretildi; EVREN ile yenilemek 2.676 çağrılık
bir iştir ve ölçülmesi gerekiyordu. İlk ölçüm (14 kampanya) EVREN aleyhine
çıktı: özetler iki kat zengin ama sayıların **%16'sı** kaynakta bulunamıyor
(mevcut özetlerde %0).

**O ölçüm yanlıştı ve hata bizdeydi.** İki kademeli bir kusur:

1. İlk sürüm `%3.54` ile `%3,54`yi farklı saydı → oran %23 çıktı. Çıplak
   rakamlar kaynakta VARDI; fark yalnız ondalık ayırıcıdaydı.
2. Ölçüt çıplak rakama çevrilince %16'ya indi — ama **prompt hâlâ bizim
   basit test prompt'umuzdu**, projenin `SISTEM_PROMPT`'u değil.

Gerçek özet hattıyla (`ozet.ozetle()` — sistem promptu + şema) 14 kampanyada
**14/14 özet üretildi ve tek bir sayı ihlali çıkmadı**. Sıcaklık merdiveni
kapatılıp yalnız ilk basamakla (0,0) koşulduğunda da sonuç aynı: 14/14, 0
ihlal. Yani merdiven kurtarmıyor — EVREN gerçek hatta sayı **uydurmuyor**.

**Sonuç:** "EVREN sayı uyduruyor" iddiası geri çekilmiştir.

### Üçüncü ve doğru ölçüm — altı ölçüt, 25 kampanya

Gerçek hat (`ozetle()`), altı ölçüt, aynı 25 kampanya. Mevcut özetler de bu
hattan geçmişti (yerel qwen ile), yani kıyas adil:

| ölçüt | mevcut (yerel qwen) | EVREN `llm-large` |
|---|---|---|
| üretilen özet | 25/25 | 25/25 |
| özetteki finansal sayı | 21 | **29** |
| bunlardan kaynakta olan (**doğruluk**) | 21 → **%100** | 29 → **%100** |
| kaynaktaki 141 finansal sayıdan yakalanan (**kapsama**) | 21 → %15 | **29 → %21** |
| ondalık-nokta ihlali (Türkçe hata) | 5 | **5 — eşit** |
| terminoloji ihlali | 0 | 0 |
| toplam uzunluk | 6.547 krkt | 10.345 krkt (1,58×) |
| retrieval R@1 (özet kendi kaynağını buluyor mu) | **23/25 (%92)** | 22/25 (%88) |
| retrieval MRR | **0,960** | 0,933 |

**İkinci karşı gerekçe de çürüdü:** EVREN Türkçe ondalık ayırıcıyı mevcut
modelden **daha kötü yazmıyor** (5-5). Önceki 9-5 farkı da bizim basit test
prompt'umuzun ürünüydü.

**Net değerlendirme:** kazanç kapsamada — EVREN kaynaktaki finansal bilgiden
%40 rölatif daha fazlasını yakalıyor (29 vs 21 sayı) ve doğruluğu bozmadan
yapıyor. Kayıp retrieval'da bir belge (23→22, n=25'te gürültü seviyesi) ve
1,58 kat depolama.

**Karar (yenilenmiş):** yenileme artık savunulabilir ama net kazanç
MARJİNAL — 2.676 çağrılık bir iş için kapsamada +6 puan. Panelde daha
bilgilendirici özet isteniyorsa değer; erişim kalitesi öncelikse mevcut
özetler biraz daha iyi. Ölçüm iki yönü de gösteriyor; karar ürün tercihidir,
teknik bir zorunluluk değil.

### Kapı yine de eklendi — ve gerçek iş yaptı

`_sayi_ihlali` kapısı `ozet.py`'ye eklendi (alfabe ve terminoloji kapılarının
eşi): özetteki her **finansal** sayı kaynak metinde bulunmak zorunda; ihlal
varsa özet reddedilir ve sıcaklık merdiveninde yeniden denenir. Sebep kodu
`sayi_dogrulanmadi`, kalıcı DEĞİL.

Kapının değeri gelecekteki EVREN çağrılarında değil, **geçmişteki yerel
çıktılarda** ortaya çıktı. Mevcut korpusa uygulandığında:

| aşama | takılan özet |
|---|---|
| ilk regex (tarih tuzağı) | 114 (%4,3) — **hepsi yanlış pozitif** |
| `(?!\d)` sıkılaştırmasından sonra | **9 (%0,34)** — hepsi gerçek |
| düşürülüp EVREN ile yeniden üretildikten sonra | **0** |

Yanlış pozitif dersi ayrıca kayda değer: ilk desen `01.04.2025` tarihindeki
`4.202` parçasını "binlik gruplu sayı" sanıyordu, yani kapı hiç uydurma
yakalamadan 114 geçerli özeti eliyordu. Karşı-örnek testleri (`TestMESRU_
OZETE_DOKUNMUYOR`) tam bu yüzden var.

Yakalanan 9 ihlal elle doğrulandı ve gerçekti — örnekler:

| id | özette | kaynakta |
|---|---|---|
| 1123 | `%50` indirim | yalnız `300 TL` geçiyor |
| 311 | `%25` | yalnız `3 gün` geçiyor |
| 2528 | `5000 TL` | `5001 TL` — yakın ama **farklı** sayı |

Dokuzu da düşürüldü (`ozet_sebep` yazıldı — sessiz kayıp yok) ve EVREN ile
yeniden üretildi (15,4 sn). Korpus artık kapıdan **0 ihlalle** geçiyor.

Testler: `tests/test_ozet_sayi_kapisi.py` (11 test + 7 alt test).

### Eksik özetler

71 özetsiz belgeden 39'u EVREN ile üretildi. Kalan 32 üretilemedi ve nedeni
dürüst: `metin_bos` 29, `bos_cikti` 2, `terminoloji_ihlali: faiz` 1 — yani
özetlenecek metin yok ya da terminoloji kapısı reddetti.

---

## 11. Otomatik özetleme zinciri — tazeleme sonrası

`alt_akis_kur(..., yeniden_ozetle=...)` eklendi (`src/tazeleme_sonrasi.py`).
Tazeleme metni değişen belgenin bayat özetini zaten düşürüyordu; artık
düşüşten sonra bir özetleme işi de başlatılıyor. Üç kural bilinçli:

1. Yalnız özet DÜŞTÜYSE tetiklenir (boşuna iş başlatmaz).
2. Bloklamaz — `OzetYoneticisi.baslat()` işi arka planda kurar.
3. Düşmesi tazelemeyi HATA'ya çevirmez; hata `yeniden_ozet_hata` olarak
   rapora yazılır (yutulmaz). LLM kapalıysa sessizce atlanır.

Kapatma kapısı: `TAZELEME_SONRASI_OZET=0`.

---

## 12. Başlatma — `LLM=evren`

`scripts/baslat.sh` artık kademe seçiyor ve seçimi EKRANA BASIYOR
("LLM=1 dedim, Ollama sanıyordum" durumu sessizce kural-only'ye düşmek kadar
pahalıdır):

| `LLM` | Davranış |
|---|---|
| `0` | kural-only |
| `1` (varsayılan) | `EVREN_API_KEY` **varsa** EVREN, yoksa yerel Ollama |
| `yerel` | Ollama'yı zorlar (anahtar olsa bile) |
| `evren` | EVREN'i zorlar; anahtar yoksa AÇIK hata |

EVREN seçildiğinde yerel Ollama hiç başlatılmaz (4,7 GB ağırlık ve ~6 sn model
yükleme beklemesi yok). Ollama daemon'u ayakta ise zincire ikinci kademe
olarak eklenir (`LLM_BACKEND=evren,ollama`); değilse tek kademe kalır ve
düştüğünde sistem kural-only'ye iner — hiçbir durumda EVREN'e BAĞLI değildir.

---

## 13. guard çapraz doğrulama — anlamlı fark YOK

Soru "guard'ı kullanalım mı" değil: bizde zaten on-prem `chatbot/safety.py`
var. Soru şu — bağımsız bir 122B denetleyici bizim enjeksiyon kapımızın
gördüğünü görüyor mu?

| küme | bizim `detect_injection` | EVREN `guard` |
|---|---|---|
| prompt injection (26 vaka) | 4/26 (%15) | 5/26 (%19) |
| meşru sorular (23 vaka) — yanlış alarm | **0/23** | **0/23** |

Fark anlamsız. **Ölçüm uyarısı:** ilk koşumda guard %100 yakalamış görünüyordu
ve bu tamamen ağ hatalarından geliyordu (kod `URLError`'u "riskli" sayıyordu);
düzeltilmiş koşumda hata alan vaka ölçümden çıkarıldı. İkinci uyarı: bizim
%15'i tek kapının sonucudur — `safety.py` çok kapılı bir hat (sanitize_output,
terminoloji kapısı, dayanak zorunluluğu) ve tam hattın geçme oranı
`run_safety_eval.py` ile ölçülür. Buradaki karşılaştırma dar bir kapıya aittir.

**Karar:** `guard` kullanılmaz — dış bağımlılık ekler, ölçülebilir bir şey
katmaz.

### İzole Qdrant — çalışıyor, ama şu an gerekli değil

Qdrant 1.19.0, `api-key` başlığıyla erişiliyor, koleksiyon oluşturma/upsert/
cosine arama/silme tam çalışıyor (40 nokta upsert 0,89 s; arama kendi pasajını
skor 1,0 ile buldu). Ancak vektör deposu olarak zaten `pgvector`/SQLite
kullanıyoruz ve uzak bir vektör deposu §5.9'u zedeler. Kullanılmaz — ama
geliştirme sırasında hızlı deney için elverişli.

---

## 14. Resmi dokümantasyondan öğrenilenler (24 Ağu)

`https://evren-teknofest.ssyz.org.tr` okundu ve **üç şeyi yanlış test ettiğimiz**
ortaya çıktı:

| konu | bizim ilk denememiz | doğrusu | sonuç |
|---|---|---|---|
| sparse/ColBERT | `/v1/embeddings` → **HTTP 501** | **`/pooling/<alias>`** | ✓ çalışıyor |
| görüntü (vision) | `vlm` modeli → *"At most 0 image(s)"* | **`llm-fast` / `llm-large`** (en çok 2 görüntü) | ✓ çalışıyor |
| şema kısıtı | `response_format` → HTTP 500 | **tool calling** | ✓ çalışıyor (§3-c) |

`vlm` modeli video İÇİN; görüntü kabul etmemesi kasıtlı bir tasarım.

### Vision — panel tablosunu doğru okudu

`llm-large`'a `docs-ekran/ss/05-kiyas-cetveli.png` verildi (596 KB base64,
5,7 sn) ve kıyas tablosunu okudu: *Türkiye Emlak Katılım %0 · Türkiye Finans
%1,9 · Kuveyt Türk %3,49*, konut finansmanında *%1,69 · %1,89 · %3,85–%3,95 ·
%2,95*. Yani görselden finansal değer çıkarımı mümkün — taranmış sözleşme
sayfaları ve görsel kampanya afişleri için açık bir kapı.

### `/pooling` — sparse ve ColBERT

`/pooling/bge-m3-sparse` token-ağırlık dizisi, `/pooling/bge-m3-colbert` token
matrisi döndürüyor. **Uyarı belgede de var:** sparse çıktı biçimi
`FlagEmbedding` kütüphanesinden farklı — hangi terime hangi ağırlığın
verildiğini bilmek için tokenizer eşlemesi gerekiyor, bu yüzden doğrudan
kullanımı zor. ColBERT matrisi MaxSim skorlamasıyla kullanılabilir ama belge
başına matris saklamak pahalı.

### `/key/info` — kullanım metriği

Takım kimliği, `spend: 0.0`, `max_parallel_requests: null` (paralel istek
sınırı YOK), `qdrant_prefix: team16`. Kota olmadığı duyuruda yazılıydı; bu uç
onu doğruluyor.

### TUZAK — bilinmeyen model adı SESSİZCE kabul ediliyor

Belgenin kendi uyarısı: *"Unknown model names silently default to llm-fast."*
Doğrulandı — `model: "llm-buyuk-yanlis-ad"` ile istek **HTTP 200** döndü ve
yanıtın `model` alanı o uydurma adı geri verdi.

Bu, bizim "sessiz hata yok" ilkesine doğrudan aykırı: `EVREN_MODEL` yanlış
yazılırsa koşum farklı bir modelle yapılır, artefakt yanlış model adını
raporlar ve kimse fark etmez. **Açık kalem:** istemci kurulurken model adının
`/v1/models` listesinde bulunduğu doğrulanabilir (bir kerelik, ucuz).

### Prefix caching — ÖLÇÜLDÜ: 5,1×

İlk deneme 4.823 token'lık bağlamla yapıldı ve fark gürültü seviyesinde çıktı
(1,76 → 1,62 sn); bağlam küçük olduğu için görünmüyordu. Gerçek bir uzun
sözleşmeyle (**45.959 token**) yeniden ölçüldü:

| soru | süre |
|---|---|
| 1 (soğuk) | **3,86 sn** |
| 2 | 0,75 sn |
| 3 | 0,73 sn |
| 4 | 0,78 sn |

**~5,1× hızlanma** — dokümantasyonun 4,8× iddiası doğrulandı.
`prompt_tokens_details` yine `None` döndü, yani kazanç sayaçtan değil süreden
okunuyor. Alan başına çağrı modunda aynı belge 12 kez gönderildiği için kazanç
doğrudan oradadır: ilk çağrı tam maliyet, sonraki 11'i ~5× hızlı.

### Model adı doğrulaması — tuzak KAPATILDI

`VLLMClient` artık model adını `GET /v1/models` listesine karşı doğruluyor
(bir kez, pazarlığın başında). Canlı doğrulandı: `llm-buyuk-yanlis-ad` artık
`LLMError` ile yakalanıyor ve mesajda geçerli adlar listeleniyor.

Üç tasarım kararı:

1. **Liste alınamazsa koşum DURMAZ.** Doğrulama bir güvencedir, ön koşul
   değil; geçici bir ağ dalgalanmasının tüm ablasyonu düşürmesi, önlediği
   hatadan pahalı olurdu. Uyarı loglanır, pazarlık sürer.
2. **Açık `transport` doğrulamayı kapatır.** O, "burada gerçek sunucu yok"
   demenin kendisidir — onlarca test sahte taşımayla koşuyor.
3. **Anahtarsız yerel uçta kapalı.** Tuzak yalnız uzak uçta ölçüldü ve yerel
   model adı HF yolu olabiliyor.

Kapatma kapısı: `VLLM_MODEL_DOGRULA=0`. Testler: 9.

### Diğer notlar

- Sistem maksimum `timeout=1800`; istemci varsayılanı (600 sn) sunucu
  tamamlanmadan kesebilir.
- Düşünme (reasoning) modu kapalı olmalı; açıksa `max_tokens ≥ 2048` — aksi
  hâlde boş yanıt döner (bizim `enable_thinking=False` varsayılanı bununla
  uyumlu).
- Video 77 sn sonra 720p'ye, 134 sn sonra 540p'ye **sessizce** düşürülüyor.
- `/status` ve `/durum` uçları ana dokümantasyon alanında; `/v1/` altında
  değil (denendi, 404).

---

## 15. Kurulum

```bash
# Anahtar repoya GİRMEZ — kabuğa ya da .env.local'e:
export EVREN_API_KEY=sk-evren-<takim>-<...>

# Tek kademe (ölçüm/geliştirme):
export LLM_BACKEND=evren LLM_STRICT=1

# Kademeli (teslim adayı): EVREN düşerse yerel Ollama devralır
export LLM_BACKEND=evren,ollama

# Gömme kademesi (vektör üretimi):
export EMBEDDING_BACKEND=evren,yerel
export EVREN_EMBEDDING_BATCH=128

# Varsayılanlar (gerekirse):
export EVREN_URL=https://evren-llmapi.ssyz.org.tr
export EVREN_MODEL=llm-large
export LLM_CASCADE_COOLDOWN=300
```

Ablasyon koşumu:

```bash
LLM_BACKEND=evren LLM_STRICT=1 EVREN_API_KEY=... \
  .venv/bin/python -m eval.ablation --gold data/gold/gold.v2.json \
  --arms kural,llm,hibrit --out-dir eval/reports/evren-ceiling
```

Gömme tablosunu doldurmak (tek seferlik üretim adımı — sonrası ağ istemez):

```bash
EMBEDDING_BACKEND=evren,yerel EVREN_API_KEY=... EVREN_EMBEDDING_BATCH=128 \
  .venv/bin/python -m src.rag.build_embeddings \
  --database-path data/demo.db --strict --json
# 2708 kampanya -> 51.556 chunk, ~11 dk
```

Vektör kolunu ÖLÇMEK (üretim yolunu değiştirmez):

```bash
EMBEDDING_BACKEND=evren,yerel EVREN_API_KEY=... \
  .venv/bin/python -m eval.rag_eval --db data/demo.db -k 5 --kiyas --vektor
```

Uygulamayı EVREN kademesiyle başlatmak:

```bash
export EVREN_API_KEY=sk-evren-...
make baslat            # LLM=1 varsayılanı anahtarı görüp EVREN'i seçer
LLM=yerel make baslat  # Ollama'yı zorla
RAG=auto make baslat   # vektör kolunu da aç (ölçüm için)
```

---

## Sources

- SSB duyurusu (2026-08-24, takım listesi ve erişim bilgileri) — takım kimliği
  `team16`
- `https://evren-teknofest.ssyz.org.tr` — model kartları, donanım, servis durumu
- Canlı ölçümler: bu belgedeki tüm tablo ve alıntılar 2026-08-24 tarihli gerçek
  isteklerden alınmıştır
- `eval/reports/evren-ceiling/20260824-080634/` — `prompt_only` koşumu
- `eval/reports/evren-ceiling-jsonobject/20260824-081456/` — `json_object` koşumu

## Related

- `docs/SARTNAME-UYUM.md` — §5.9 ve §5.10 satırları
- `docs/OFFLINE-KANIT.md` — ağsız kanıt paketi (EVREN'den etkilenmez)
- `docs/model-license-audit.md` — lisans denetim disiplini
- `src/extraction/llm/cascade.py` — kademe zinciri
