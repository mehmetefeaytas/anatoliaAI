# Anatolia AI — Günlük (Log)

Kronolojik ingest / değişiklik günlüğü. En yeni en üstte.

## [2026-07-27] kod+yöntem | Gün 1c: Veri modeli, gerçek güven, 12/12 alan, değişmez denetimi

Üç blok iş yapıldı. Sonuncusu bir **yöntem değişikliğidir** ve kalan 29 günün
verimini doğrudan etkiler.

### 1. Veri modeli (sonraki her katman buna bağlanacağı için önce)

- `ExtractedField`'a `span_start`/`span_end` eklendi. `source_span` yalnızca
  ±40 karakterlik bir pencere METNİydi ve orijinalde güvenilir bulunamıyordu;
  dashboard'daki kaynak vurgulaması (yenilikçilik hedefi #1) kesin offset ister.
  `verify_span(text)` kendi kendini denetler.
- `confidence` sabit 0.95'ti. Sabit skor kalibre edilemez (ECE tek bin'e düşer),
  abstain eşiği ayrım yapamaz, jüriye savunulamaz. `rules/confidence.py` eklendi:
  tetikleyici yakınlığı + makullük + belirsizlik + aralık cezasından hesaplanır.
  Ölçülen ayrım: ideal 0.95, aralık 0.90, belirsiz 0.85, makul dışı 0.50.
  Skorlar **kalibre edilmemiştir** (yalnız sıralayıcı); `confidence_source`
  alanında işaretli.

### 2. Kural katmanı 7/12 → 12/12 alan

§5.3'ün "Kampanya Bilgileri" ve "Hedef Kitle" kolonları tamamen boştu; §5.7'nin
"En Yüksek Ödül Miktarı" kriteri cevaplanamıyordu. Eklenen 5 çıkarıcının her
biri bir ayırt etme tuzağı çözüyor (koşul/ödül, indirim/puan, oran/adet,
segment/negasyon).

### 3. YÖNTEM: değişmez (invariant) denetimi

Bugün bulunan **beş hatanın hiçbiri çökme değildi** — hepsi sessizce yanlış
değer üretiyordu. Bu, asıl riskin "model yeterince iyi değil" değil
**"kendinden emin çöp üretiliyor ve fark edilmiyor"** olduğunu gösteriyor.

`eval/properties.py` — girdinin anlamını değiştirmeyen dönüşümler çıktıyı
değiştiriyorsa doğru cevabı bilmeden hata olduğu kesindir. Dolayısıyla
**gold etiketi gerekmez**:

| Değişmez | Yakalayacağı hata |
|---|---|
| P1 span bütünlüğü | vurgulanan yer ≠ raporlanan değer |
| P2 ortografik değişmezlik | **H1** (ALL-CAPS işaret ters çevirme) |
| P3 alakasız ekleme | **hayali 31 TL ücret** |
| P4 cümle sırası | **H2** (çelişkinin sıraya bağlılığı) |

Bugünkü beş hatanın **dördü** bunlarla otomatik yakalanırdı.

Bu, gold set kritik yolda beklerken (anotasyon insan işi, yavaş) anote
**edilmemiş** 150–250 belgede hemen hata avlar. Kritik yolu kısaltmaz ama
paralel bir kalite hattı açar.

META test eklendi: her zaman geçen bir denetleyici işe yaramaz. `tr_fold`
düzeltmesi geçici geri alındığında denetleyicinin gerçekten ihlal ürettiği
doğrulanıyor (`masraf_durumu` has_fee False→True). Bu test geçmezse diğer
"0 ihlal" sonuçları anlamsızdır.

### Bu bloklarda bulunan gerçek hatalar (hepsi düzeltildi)

1. **Sahte aralık:** `"kâr payı oranı %1,89 ile 120 aya kadar"` →
   `{min: 1.89, max: 120.0}`. 'ile' bağlacı aralık ayırıcı sanılıyor, bir
   VADE oran üst sınırı olarak karşılaştırma tablosuna yazılıyordu.
   İlk düzeltme denemesi regex geri izlemesiyle atlatıldı (`"36"`dan `"3"`),
   `(?![\d.,])` ile sayının tamamının tüketilmesi zorlandı.
2. **Fiil negasyonu eksikti:** `normalize_fee_status` yalnızca sıfat
   biçimlerini biliyordu. `"Yıllık kart ücreti alınmaz. Kampanya 31 Aralık
   2026..."` → `{has_fee: True, amount: 31.0}` — hem negasyon kaçıyor hem
   tarihten **hayali ücret** uyduruluyordu. `NEGATION_RE` tek doğruluk
   kaynağına alındı + ücret penceresi cümle sınırında kesiliyor.
3. **Koşul/geçerlilik karışması:** tek başına "geçerli" tetikleyicisi her
   belgedeki *"Kampanya <tarih> tarihine kadar geçerlidir"* cümlesini koşul
   sanıyordu (zaten `kampanya_suresi` yakalıyor). Her belgede yanlış pozitif.
4. **is_plausible yalnız min'e bakıyordu** — bozuk aralıkları makul gösteriyordu.

Dokunulan dosyalar:
- `app/src/schemas.py` (span offsetleri, confidence_source, verify_span)
- `app/src/extraction/rules/confidence.py` (yeni)
- `app/src/extraction/rules/extract.py` (5 yeni alan, offsetler, düzeltmeler)
- `app/src/normalization/normalize.py` (NEGATION_RE, fiil negasyonu)
- `app/src/extraction/rules/synonyms.py` (NEGATION_RE yeniden ihracı)
- `app/src/preprocessing/clean.py` (tr_upper)
- `app/eval/properties.py` (yeni, CLI dahil)
- `app/tests/{test_confidence_span,test_kampanya_alanlari,test_properties}.py` (yeni)

Test durumu: **129 test yeşil** (85 → 129), tamamen offline.

Açık uçlar (değişmedi): gerçek scraping, gold set 3→250, LLM'in Colab'da ilk
kez çalıştırılması. Bunlar kritik yolda ve insan katılımı gerektiriyor.

## [2026-07-27] sorun+kod | Gün 1b: Çelişki tespiti canlandırıldı (H2)

Bağlam: `contradiction.detect()`'in birincil kuralı `masrafsiz_ama_ucret` hem
`masraf_durumu` hem `tahsis_ucreti` alanını istiyor. Kural katmanı
`tahsis_ucreti` alanını hiç üretmediği için bu kural **bugüne kadar hiç
tetiklenemedi** — yani `decisions/daraltilmis-yenilikcilik-hedefleri.md`'deki
yenilikçilik hedefi #2 ölü kodmuş.

Yapılanlar:
- `extract_tahsis_ucreti()` eklendi. `masraf_durumu`'ndan **bağımsız** koşar.
  Negasyon ("alınmaz", "talep edilmez", "yoktur") → `{value: 0.0}`, yani
  "bilgi yok" değil "ücret sıfır" (§5.5 "masrafsız finansman" yorumu).
- `synonyms.py`'ye `NEGATION_RE` eklendi (sözcük listesi değil desen — fiil
  çekimlerini yakalasın diye).

Bu sırada bulunan iki hata:

1. **Binlik ayırıcı / cümle sonu karışması.** Cümlecik ayırıcı naif olarak
   `[.;\n]` üzerinden bölüyordu; `.` Türkçede aynı zamanda binlik ayırıcı
   olduğu için `"1.500,00 TL"` ifadesi `"1"`de kesilip **1500 yerine 1.0**
   üretiliyordu. Düzeltme: `(?<!\d)[.;](?!\d)` — rakamlar arasındaki noktada
   bölme.

2. **Çelişki tespiti yazım sırasına bağlıydı.** `extract_masraf` `re.search`
   (yalnız ilk eşleşme) kullanıyordu:
   - `"Masrafsızdır. Tahsis ücreti 500 TL."` → çelişki yakalanıyor ✓
   - `"Tahsis ücreti 500 TL. Masrafsızdır."` → **kaçıyordu** ✗

   Düzeltme: `finditer` ile tüm masraf bahisleri taranır. `masraf_durumu` artık
   kampanyanın **iddiasını** taşır — metinde herhangi bir yerde "masrafsız"
   iddiası varsa `has_fee=False` döner; gerçekte ücret olup olmadığını
   `tahsis_ucreti` söyler, uyuşmazlığı `contradiction.detect()` yakalar.
   Böylece her iki yazım sırası ve ALL-CAPS çalışıyor, yanlış pozitif yok.

**Değerlendirme semantiği bulgusu (H3'ün somut kanıtı):** yeni alan eklenince
eval `tahsis_ucreti` için P=0.00, FP=1 raporladı. İnceleyince görüldü ki bu
**doğru bir çıkarım**: gold kayıt #1'in metni birebir "Tahsis ücreti 500 TL"
diyor, ama gold `fields` sözlüğü bu alanı hiç anote etmemiş. Yani doğru çıkarım
yanlış pozitif sayılıyordu. Gold kaydı düzeltildi.

Bu, gold formatının **"gerçekten yok" ile "anote edilmemiş"i ayırt edemediğini**
gösteriyor — `absent_fields` alanı olmadan precision tanımsız, halüsinasyon
oranı ölçülemez. Gold şema göçü (İH2b) sırasında bu ayrım eklenecek.

Dokunulan dosyalar:
- `app/src/extraction/rules/extract.py` (extract_tahsis_ucreti, extract_masraf)
- `app/src/extraction/rules/synonyms.py` (NEGATION_RE)
- `app/data/gold/gold.sample.json` (kayıt #1'e tahsis_ucreti eklendi)
- `app/tests/test_contradiction.py` (yeni — 13 test)

Test durumu: **85 test yeşil** (72 → 85).

UYARI: eval şu an MICRO F1 = 1.00 raporluyor ama gold set **3 kayıt** —
istatistiksel olarak anlamsız, yalnızca "regresyon yok" demek. Gerçek sayı
gold set 150–300'e çıkınca (İH2b) üretilecek; o zamana kadar hiçbir yerde
başarı iddiası olarak kullanılmayacak.

## [2026-07-27] sorun+kod | Gün 1: Türkçe küçük-harf hatası (H1) + lisans denetimi

Bağlam: Yarışmanın çevrimiçi süreci bugün başladı (Kick Off; 26 Ağustos'a kadar
30 gün). Kod tabanı denetlenirken, gerçek veriye geçildiğinde sistemi sessizce
bozacak bir hata bulundu ve düzeltildi.

**Bulunan hata (H1):** Python'un `str.lower()` metodu Türkçe için hatalıdır —
`'TAŞIT'.lower()` → `'taşit'` (I→i, olması gereken ı) ve `'ÜCRETSİZ'.lower()`
→ `'ücretsi̇z'` (İ→i + U+0307 birleşen nokta). Banka sitelerindeki başlıklar
büyük harflidir; kod tabanındaki 7 çağrı yeri etkileniyordu. Bugüne kadar
görülmemesinin tek sebebi test fixture'larının küçük harfle yazılmış olması.

Ölçülen etki (gerçek ALL-CAPS banka metniyle, önce/sonra):

| | önce | sonra |
|---|---|---|
| kampanya türü sınıflandırma | `None` (tamamen kaçırıldı) | `Taşıt Finansmanı` |
| `masraf_durumu` | `has_fee: True` (**işaret ters**) | `has_fee: False` |

İkincisi bir kaçırma değil **yanlış değer**: "ÜCRETSİZ" yazan metni sistem
"masraf var" diye okuyordu ve bu değer karşılaştırmaya akıp §5.7 "En Düşük
Masraf" kriterinde bankayı yanlış sıralardı.

Çözüm: `preprocessing/clean.py`'ye `tr_fold()` (TR-doğru küçük harf, **uzunluk
koruyan** → source_span offset'leri güvenli) ve `tr_fold_ascii()` (+ diakritik
sadeleştirme) eklendi. Tüm eşleşme sözlükleri modül yüklenirken katlanmış
görünüme çevriliyor (`FOLDED_TYPE_HINTS`, `_FOLDED_FREE_TOKENS` vb.);
varyantlar frozenset ile tekilleştirildiği için mükerrer sayım yok.

Diğer Gün 1 kalemleri:
- `docs/model-license-audit.md` açıldı (şartname §5.10 kanıt katmanı).
  Trendyol-LLM-8B-T1 **BLOKE** — taban model zinciri doğrulanmadan kullanılamaz
  (Llama tabanlıysa Community License → §5.10 ihlali). Birincil model Qwen3-8B.
- `trafilatura` opsiyonele alındı: kendi yorumunda "GPLv3+" yazıyordu, Apache-2.0
  ile dağıtımda uyumsuz. Kod onsuz çalışıyor (`strip_html` fallback). Lisansı
  doğrulanana kadar teslim imajına girmiyor.
- `gliner` ve `zeyrek` yorum satırına alındı — kod tabanında sıfır referansları
  var; §9 "bağımlılıkların eksiksiz listesi" şartı yanıltıcı olmasın diye.
- `requirements-api.txt` ayrıldı (ince teslim imajı).
- `Dockerfile.api` düzeltildi: elle paket listesi yerine requirements dosyası,
  offline env bayrakları, ve `eval/` + `tests/` imaja dahil edildi — bunlar
  olmadan `docker run --network none ... unittest` kanıt koşusu imkânsızdı.
- `VLLMClient` varsayılan portu 8000 → 8001 (8000 API'nin kendi portuydu).

Dokunulan dosyalar:
- `app/src/preprocessing/clean.py` (tr_fold, tr_fold_ascii)
- `app/src/extraction/rules/synonyms.py` (katlanmış görünümler)
- `app/src/extraction/ner/classifier.py`, `app/src/extraction/rules/extract.py`
- `app/src/normalization/normalize.py`, `app/src/chatbot/router.py`
- `app/src/extraction/llm/clients.py`, `app/Dockerfile.api`
- `app/requirements.txt`, `app/requirements-api.txt` (yeni)
- `app/docs/model-license-audit.md` (yeni)
- `app/tests/test_turkish_fold.py` (yeni — 18 regresyon testi)

Test durumu: **72 test yeşil** (54 → 72), tamamen offline, 0,01 sn.

Açık uçlar:
- trafilatura lisansı doğrulanacak (ağ gerekli)
- Trendyol-LLM-8B-T1 taban model zinciri doğrulanacak
- Kalan 6 çıkarım alanı (`tahsis_ucreti` dahil) henüz yok → çelişki tespiti (H2)
  hâlâ tetiklenemiyor

## [2026-06-16] kod | app/ uçtan uca çekirdek inşa edildi

Bağlam: Kararlaştırılan v2 mimarisine göre `app/` altındaki tüm katmanlar kuruldu;
ağır modeller (vLLM/BERTurk) bu ortamda çalışamadığı için her katman **gerçek
kütüphane yolu + offline fallback** ile yazıldı. Tüm sistem modeller olmadan da
uçtan uca koşar (on-prem/offline kanıtı).

Kurulan katmanlar (hepsi test edildi):
- preprocessing, normalization (oran/para/vade/tarih/TR-sayı/aralık/negasyon)
- extraction: rules (birincil), llm (guided_json + vLLM/Ollama + Null-fallback),
  reconcile (kural birincil), ner/classifier (kural-ipucu + BERTurk yolu)
- db (SQLite offline + Postgres/pgvector şema), comparison (adil-kıyas) +
  contradiction (yenilikçilik), chatbot (router + yapısal sorgu + RAG)
- scraping (config-driven banks.yaml + offline fixtures), pipeline, api (FastAPI),
  web (Next.js dashboard+chatbot), eval (run_eval + ablation)

Doğrulama:
- **54 birim/entegrasyon testi, tamamı offline yeşil.**
- 10 banka config'ten yüklendi; 3 fixture uçtan uca işlendi.
- Chatbot doğru yönlendirdi: "en düşük kâr payı" → Kuveyt Türk %1,89 (yapısal),
  "taşıt koşulları" → RAG. Ablasyon dürüst rapor (LLM offline notu).

İlgili kararlar: [[hibrit-chatbot-text-to-sql-rag]],
[[ner-fine-tune-yerine-kural-few-shot]], [[zor-anlama-vakalari-merkezi]],
[[daraltilmis-yenilikcilik-hedefleri]], [[demo-onceden-doldurulmus-db]].

## [2026-06-16] karar | kod-projesi-mimari-v2 (5 kritik karar)

Bağlam: Önceki oturumda kullanıcının paylaştığı kod projesi planı (`CLAUDE.md v1`)
değerlendirildi; kazandıran 5 mimari değişiklik kararlaştırıldı ve `app/CLAUDE.md`
(v2) yazıldı. Bu kararlar şartname kaynağına dayanır.

Dokunulan dosyalar:

- **app/CLAUDE.md** (oluşturuldu — kod projesinin v2 operasyon kılavuzu)
- **decisions/** hibrit-chatbot-text-to-sql-rag.md,
  ner-fine-tune-yerine-kural-few-shot.md, demo-onceden-doldurulmus-db.md,
  zor-anlama-vakalari-merkezi.md, daraltilmis-yenilikcilik-hedefleri.md (oluşturuldu)
- index.md (Decisions bölümüne 5 yeni karar eklendi)
- entities/chatbot.md, syntheses/teknik-cozum-mimarisi.md (geri-bağlantı eklendi)
- _oturum-devir.md (oluşturuldu — eski `anatoliaal` oturumunun bağlam devri)

Notlar:
- Kararların 5'i de şartname değerlendirme ağırlıklarına (%30 model başarısı, %20
  fonksiyonellik, %20 on-prem, %10 yenilikçilik) dayandırıldı.
- Sıradaki adım: deterministik kural/normalizasyon katmanı + eval harness (kod).

## [2026-06-16] ingest | teknofest-tyda-sartname-2-senaryo

Kaynak: `raw/teknofest/2026-teknofest-tyda-sartname-2-senaryo.pdf`
(sembolik link → TEKNOFEST TYDA Şartname 2. Senaryo, 25 sayfa, ~36k karakter).
Tek pass kurulum + ilk ingest.

Dokunulan dosyalar:

- **sources/teknofest/** 2026-06-16-teknofest-tyda-sartname-2-senaryo.md (oluşturuldu)
- **entities/** teknofest.md, bilisim-vadisi.md, bddk.md,
  turkiye-acik-kaynak-platformu.md, t3kys-basvuru-sistemi.md, github.md,
  chatbot.md, dashboard.md, veri-seti.md, katilim-bankalari.md (oluşturuldu)
- **concepts/** katilim-bankaciligi.md, kar-payi-orani.md, nlp.md,
  bilgi-cikarimi.md, metin-siniflandirma.md, kampanya-turleri.md,
  veri-on-isleme.md, veri-normalizasyonu.md, yapilandirilmis-veri-formati.md,
  on-premise-uygulanabilirlik.md, acik-kaynak-yaklasimi.md, web-scraping.md,
  urun-karsilastirma.md (oluşturuldu)
- **decisions/** on-premise-calistirilabilir-mimari.md,
  apache-2-acik-kaynak-lisansi.md, python-tabanli-veri-toplama.md,
  dashboard-ve-chatbot-arayuzu.md, bddk-listesi-veri-kaynagi-kapsami.md,
  yapilandirilmis-veri-formati-zorunlulugu.md (oluşturuldu)
- **sorun/** standart-veri-formati-eksikligi.md,
  katilim-bankaciligi-terminoloji-farkliligi.md, farkli-ifade-bicimleri.md,
  manuel-karsilastirma-zorlugu.md (oluşturuldu)
- **syntheses/** yarisma-genel-bakis.md, teknik-cozum-mimarisi.md,
  teslim-ve-degerlendirme-rehberi.md (oluşturuldu)
- index.md, lint-report.md (güncellendi/oluşturuldu)

Notlar:
- Çelişki tespit edildi (demo videosu süresi 5 dk vs 1 dk) →
  teslim-ve-degerlendirme-rehberi.md içinde `## ÇELİŞKİ` ile işaretlendi.
- Slug çakışması düzeltildi: decisions kararı
  `yapilandirilmis-veri-formati-zorunlulugu` olarak adlandırıldı (concept
  `yapilandirilmis-veri-formati` ile çakışmaması için).
