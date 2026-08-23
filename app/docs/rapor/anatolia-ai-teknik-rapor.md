# Anatolia AI — Teknik Rapor ve Durum Değerlendirmesi

**TEKNOFEST 2026 · Türkçe Yapay Zekâ Dil Ajanları Yarışması · 2. Senaryo**
Katılım bankacılığı kampanya metinlerinden finansal bilgi çıkarımı, karşılaştırma ve doğal dil arayüzü

| | |
|---|---|
| **Takım** | Anatolia AI |
| **Ekip** | Mehmet Efe Aytaş (kaptan), Irmak Altay, Ayça Engindeniz, Ecegüneş Dağ |
| **Rapor gövdesinin ölçüm tarihi** | 3 Ağustos 2026 · commit `03835ce` |
| **Son güncelleme** | 13 Ağustos 2026 (aşağıdaki "Ölçüm künyesi" bölümü) |
| **Teslim tarihi** | 26 Ağustos 2026 |
| **Lisans** | Apache-2.0 |

---

## ⚠️ Ölçüm künyesi — hangi sayı ne zaman ölçüldü

Bu raporun **A–D bölümlerindeki sayılar 3 Ağustos 2026 koşusuna aittir** ve o
günün korpusuna (**849 belge**) çapalıdır. Korpus o tarihten sonra **2.708
belgeye** çıktı (16 Ağustos'ta 1.782'ydi); çıkarım kuralları ve RAG sıralaması
değişti.

**Eski sayılar bilerek olduğu gibi bırakıldı.** "849"u "1.782" ile değiştirmek
tek satırlık bir iş olurdu ama o ölçümler yeniden koşulmadı: değiştirilmiş sayı,
ölçülmüş sayı gibi görünürdü. Bu raporun tek kuralı (§ okuma kılavuzu) tam da
bunu yasaklıyor. Aşağıdaki tablo güncel durumu **ayrı** verir; ikisi
karıştırılmaz.

| Ne | 3 Ağustos (rapor gövdesi) | 13 Ağustos | 16 Ağustos (koşuldu) |
|---|---|---|---|
| Korpus | 849 belge | 1.782 satır / 1.677 farklı içerik | **1.782** (değişmedi) |
| Banka | 10 | 10 katılım bankası + TKBB | aynı |
| Test | 890 | 2.649 toplanan · 2.596 geçen | 3.046 toplanan (kirli ağaç — kanıt sayılmadı) · temiz koşum aşağıdaki güncel blokta |
| Gold seti | `gold.v1` (20 kayıt) | `gold.v2` (48 kayıt) · v3 turu dağıtıma hazır (+26) | aynı · toplam **66 tekil** belge (v1 20 + v2 48, 2 örtüşme — ölçüldü) |
| Yapılandırılmış alan mikro-F1 | ölçülmemişti | 0,646 | **0,671** |
| 12-alan mikro-F1 | 0,400 | 0,452 [%95 GA 0,384–0,512] | **0,464** [%95 GA 0,398–0,522] |
| makro-F1 | ölçülmemişti | 0,556 | **0,601** |
| Halüsinasyon oranı | 0,083 | 0,059 (yapısal kesitte 0,047) | **0,047** [21/444] (yapısal kesitte **0,035**) |
| Değişmez denetimi | 0 ihlal · 849 belge · kapsam %85,5 | 1 ihlal (`P4`) · kapsam %91,3 | **0 ihlal** · 1.782 belge · kapsam **%89,6** (1.597/1.782) |
| Çelişki tespiti | 849 belgede 1 | ölçülmedi | **5** (`as_of` yok) / **15** (`as_of` var) · 1.782 belge — bkz. §A9 güncel blok |
| RAG terim kapsama R@5 | modül yoktu | **0,867** | yeniden ölçülmedi |
| RAG banka hedefleme R@5 | modül yoktu | **0,800** (BM25 sıralama) | yeniden ölçülmedi |
| Reddetme kararı doğruluğu | ölçülmemişti | **30/30** | yeniden ölçülmedi |
| Güvenlik seti | ölçülmemişti | **29/30** · aşırı red 0/6 | yeniden ölçülmedi |
| Anotatör uyumu | ölçülmemişti | Fleiss κ **0,302** · Krippendorff α 0,620 / 0,787 | yeniden ölçülmedi |

### 🔄 23 Ağustos 2026 — EN GÜNCEL KESİT (yukarıdaki sütunların yerine geçmez, yanına durur)

16 Ağustos sütunu **artık en güncel değildir**; korpus 1.782'den 2.708'e çıktı ve
ölçüm hattı iki gold tabanına ayrıldı. Aşağıdaki sayıların tek kanonik kaynağı
`app/README.md`'dir; bu tablo onun kesitini taşır ve `scripts.kanit_tazeligi`
kapısı her koşumda ikisini karşılaştırır (16 iddia · 0 sapma).

| Ne | 16 Ağustos | **23 Ağustos (koşuldu, temiz ağaç)** |
|---|---|---|
| Korpus | 1.782 belge | **2.708** belge · 7.022 çıkarılmış alan · 999 PDF |
| Banka | 10 | **10/10** katılım bankası |
| Test | 3.046 (kirli ağaç) | **3.647** toplanan · **3.593** geçti · 54 atlandı · **0** başarısız |
| Gold seti | `gold.v2` (48) | `gold.v2` **48** + `gold.round1` **134** — iki ayrı taban, iki ayrı kapı |
| Yapısal alan mikro-F1 | 0,671 | **0,823** (`gold.v2`) · 0,826 (`gold.round1`) |
| 12-alan mikro-F1 | 0,464 | **0,570** (`gold.v2`) · 0,795 (`gold.round1`) |
| Kalem düzeyi mikro-F1 | ölçülmemişti | **0,629** (`gold.v2`) · 0,779 (`gold.round1`) |
| makro-F1 | 0,601 | **0,765** (`gold.v2`) · 0,650 (`gold.round1`) |
| Halüsinasyon oranı | 0,047 [21/444] | **0,034** (`gold.v2`, payda 447) · 0,284 (`gold.round1`, payda 74) |
| Anotatör uyumu | Fleiss κ 0,302 | Cohen κ **0,714** (2. tur) · **0,716** (insan turu) |

**İki halüsinasyon sayısı niçin bu kadar farklı:** paydalar aynı şeyi saymıyor.
`gold.v2`nin 447 `absent` kararı kasten zor seçilmiş bir sette dağılmıştır;
`gold.round1`in 74 kararı ise **inceleme kuyruğundan** gelir — bir hücre oraya
zaten model bir şey ürettiği için girer, yani düşmanca seçilmiş bir alt kümedir.
Payda 447'den 74'e inince oran doğal olarak fırlar. İkisinden birini seçip
manşete koymuyoruz; ikisi de yayımlanıyor (bkz. `eval/esikler-round1.json`
`_halusinasyon_neden_YOK` bloğu).

**Artefaktlar:** `eval/reports/20260823-073019/` (`gold.v2`) ve
`eval/reports/20260823-073045/` (`gold.round1`), ikisi de `git_dirty: false`.
Gold bütünlüğü: `make gold-butunluk` (sha256 tanığı + eşik künyesi).
| Güven kalibrasyonu | ölçülmemişti | ECE **0,306** · MCE 0,550 · Brier 0,316 | yeniden ölçülmedi |
| Gold kanıt zinciri | araç yoktu | **48/48** izlenebilir (45 birebir + 3 içerik kayması) | yeniden ölçülmedi |

> **16 Ağustos sütununun künyesi.** F1/halüsinasyon satırları
> `eval/reports/20260815-195653/` koşumundan gelir ve 2026-08-16'da
> `python3 -m eval.run_eval --gold data/gold/gold.v2.json --config kural`
> ile yeniden koşularak **birebir doğrulandı** (`eval/reports/20260816-102045/`).
> Değişmez ve çelişki satırlarının komutları `app/README.md` §"Ölçüm Durumu" içindedir
> (`app/docs/invariants.md` daha ayrıntılı ölçüm geçmişi tutar ama `vitrin`
> dalındadır — `main`'de bulunmaz).
> *"Yeniden ölçülmedi"* yazan satırlar 13 Ağustos değerini taşır — bilerek
> kopyalanmadı, çünkü kopyalanan sayı ölçülmüş sayı gibi görünürdü.

Güncel sayıların üreten komutları kök `README.md`'nin "Ölçülebilir Durum"
tablosunda satır satır yazılıdır. Metodoloji (hata taksonomisi, küme bootstrap,
McNemar, κ eşik politikası, kalibrasyon) aynı dosyanın "Ölçüm metodolojisi"
bölümündedir.

### Gövdedeki hangi iddialar yeniden ölçülmeli

Aşağıdakiler 849 belgeye dayanıyor ve 1.782 belgede **tekrarlanmadı**. Sayıyı
kullanmadan önce yeniden koşun:

- §A3 korpus dağılımı ve nitel-ifade sayımı (54 belge / 45'inde sayısal karşılık yok)
- ✅ ~~§A9 çelişki tespiti (849 belgede 1 çelişki)~~ — **2026-08-16'da 1.782
  belgede yeniden ölçüldü**; sonuç §A9'un sonuna ayrı blok olarak eklendi
  (5 çelişki / 2 tür ya da 15 çelişki / 3 tür — hangi kod yolunun koştuğuna
  bağlı). Gövdedeki 849'luk sayı yerinde bırakıldı.
- ✅ ~~Bölüm C değişmez kapsamı (726/849, %85,5)~~ — **2026-08-16'da 1.782
  belgede yeniden ölçüldü**: **0 ihlal**, kapsam **%89,6** (1.597/1.782).
  Komut: `app/README.md` §"Ölçüm Durumu". Ayrıntılı ölçüm geçmişi tablosu
  `app/docs/invariants.md` içindedir (`vitrin` dalı; `main`'de yok).
- §A5 çıkarılmış alan sayısı (2.204) — ⚠️ 2026-08-16 korpus koşumu **4.709
  alan** üretti (`repo.fields_by_extractor()` → `{'rule': 4709}`), ama bu sayı
  §A5'in saydığı şeyle birebir aynı kapsamda mı doğrulanmadı; §A5 hâlâ
  yeniden ölçülmeli sayılır.

---

## Bu raporun okuma kılavuzu

Rapor iki kısımdan oluşur ve **kısımların hedef kitlesi farklıdır**:

- **Bölüm A–D** şartname §6.3'ün istediği "Proje Dokümantasyonu"dur. Jüriye gider. On zorunlu
  başlığın tamamını kapsar.
- **Bölüm E** iç ektir: eksikler, riskler, açık sorular, yol haritası, rakip analizi ve uzman
  toplantısı soruları. **Teslimde çıkarılır.**

**Rapordaki tek kural:** her sayı ya bir komutun çıktısıdır ya da bir dosyaya referans verir.
Ölçülmemiş şey ⏳ ile işaretlenir; tahmin yazılmaz. Bu disiplin bir üslup tercihi değil —
şartname §15.1 sonuç manipülasyonunu diskalifiye sebebi sayıyor ve rubriğin %30'u ölçüme dayanıyor.

İşaretler: ✅ koşulup doğrulandı · ⚠️ kısmi · ⏳ ölçülmedi · ❌ yapılmadı

---

# Yönetici Özeti

## Tek paragrafta durum

Sistem uçtan uca çalışıyor: 10 katılım bankasının resmî sitelerinden toplanan **849 belge**,
kural tabanlı çıkarımla **2.204 alana** dönüştürülmüş, hepsi kaynak metindeki karakter
offsetine bağlı, PostgreSQL ve SQLite üzerinde birebir aynı sonucu veriyor, dashboard ve
chatbot ile sunuluyor, ve **internet erişimi olmadan** (`docker run --network none`) ölçülmüş
biçimde ayağa kalkıyor. Rubriğin %70'i (fonksiyonellik, teknik implementasyon, on-prem,
yenilikçilik) ölçülmüş kanıta dayanıyor. **Rubriğin en ağır maddesi olan Model Başarısı %30
için hâlâ ölçülmüş bir precision/recall/F1 yok** — ölçüm altyapısının tamamı (gold anotasyon
hattı, bootstrap güven aralığı, eşleşmiş McNemar, IAA, 4 kollu ablasyon, dondurulmuş test
bölmesi) yazılmış ve test edilmiş durumda, ama **hiç koşulmadı**. 23 günün birinci işi budur.

![Rubrik durum panosu](grafikler/g07-rubrik-panosu.svg)

## Üç cümlede ne yaptık

1. **Kural-öncelikli hibrit çıkarım hattı kurduk.** Sayısal ve yapısal alanları deterministik
   regex + Türkçe-farkında normalizasyon çıkarır; yerel LLM yalnızca kuralların kaçırdığı örtük
   ifadeler için devreye girer. Her alan `raw_value` + `canonical_value` + `confidence` +
   `span_start/span_end` + hangi katmanın ürettiği ile birlikte saklanır.
2. **Doğruluğu etiketsiz veride ölçen bir denetim mekanizması yazdık.** Metamorfik değişmez
   denetimi, gold seti olmadan da sessiz hataları yakalar; ilk koşuda 134 ihlal buldu, bugün
   849 belgede 0 ihlal veriyor.
3. **Katılım bankacılığına özgü bir güvenlik katmanı ekledik.** Beş kapı: çıktıda "faiz" terimi
   üretilmez, fıkhî hüküm verilmez, yatırım tavsiyesi verilmez, kâr payı garanti gibi
   sunulmaz, kaynak yoksa cevap verilmez. Ablasyonla ölçüldü: kapılar açıkken 1,00, kapalıyken 0,20.

## Üç cümlede ne yapmadık

1. **Gold seti dondurmadık** → %30'luk kriter için sayı yok. Anotasyon hattı hazır, 4 anotatör
   ataması yapılmış, ama anotasyon başlamadı.
2. **LLM kolunu hiç ölçmedik.** GPU olmadığı için korpus üretiminde LLM devreye girmedi;
   teslim edilen 2.204 alanın **%100'ü kural katmanından**. Hibridin LLM'e karşı üstünlüğü
   iddia edildi ama ölçülmedi.
3. **Üç zorunlu teslim kalemi eksik:** veri setinin herkese açık indirme bağlantısı (§9),
   demo videosu (§6.2), sunum PDF+PPTX (§6.4).

## En kritik tek karar

Kural katmanı **gold sete bakılmadan** yazıldı. Bu, 250 kayıtlık anotasyon setini gerçek bir
*held-out* test setine dönüştürür — literatürdeki en değerli ölçüm koşulu. Bu avantaj yalnızca
gold dondurulup metrik **ondan sonra** üretilirse korunur. Metriği önce koşup kuralı ona göre
ayarlamak, yarışmanın en büyük puanını kağıt üstünde yükseltirken gerçek değerini sıfırlar.

---

# BÖLÜM A — Proje Dokümantasyonu (§6.3)

## A1. Sistem mimarisi ve veri akışı

Sistem tek bir orkestrasyon fonksiyonunda toplanır: `src/pipeline.py:149` `run_pipeline()`.
On bir aşama, her biri bağımsız test edilebilir bir modül:

![Uçtan uca mimari](grafikler/g01-mimari.svg)

### Aşamaların sorumlulukları

| # | Aşama | Modül | Ana giriş noktası |
|---|---|---|---|
| 1 | Veri toplama | `src/scraping/` | `collector.py:170 collect_from_fixtures()`, `:227 collect_live()` |
| 2 | Ön işleme | `src/preprocessing/clean.py` | `:112 normalize_text()`, `:30 tr_fold()` |
| 3 | Sınıflandırma (8 tür) | `src/extraction/ner/classifier.py` | `:26 RuleHintClassifier` |
| 4 | Kural çıkarımı (12 alan) | `src/extraction/rules/extract.py` | `:856 extract_all()` |
| 5 | LLM katmanı | `src/extraction/llm/extractor.py` | `:97 LLMExtractor.extract()` |
| 6 | Uzlaştırma | `src/extraction/reconcile.py` | `:69 reconcile()` |
| 7 | Normalizasyon | `src/normalization/normalize.py` | `:75 normalize_rate()`, `:135 normalize_money()` |
| 8 | Çelişki tespiti | `src/comparison/contradiction.py` | `:323 detect()` |
| 9 | Depolama | `src/db/factory.py` | `:52 create_repository()` |
| 10 | Karşılaştırma | `src/comparison/compare.py` | `:82 rank()`, `:454 rank_advantageous_by_type()` |
| 11 | Sunum | `src/api/main.py` + `web/` | `:236 build_app()` |

### Dört çalışma modu

`src/pipeline.py:50-53` dört mod tanımlar. Bu, aynı kod yolunun hem üç belgelik hızlı testte
hem 849 belgelik tam korpusta koşabilmesini sağlar:

- `MODE_FIXTURE` — 3 sabit belge, saniyenin altında; birim testler ve duman testi
- `MODE_CORPUS` — 849 belge, özyinelemeli tarama; teslim edilen demo veritabanı
- `MODE_LIVE` — canlı scraping
- `MODE_AUTO` — mevcut veriye göre karar verir

### Neden iki veritabanı arka ucu

`src/db/base.py:38` `RepositoryProtocol` 13 metotlu tek bir sözleşme tanımlar. SQLite ve
PostgreSQL/pgvector bu sözleşmeyi ayrı ayrı uygular; `create_repository()` `DATABASE_URL`
doluysa Postgres'i, boşsa SQLite'ı seçer.

Bunun bir maliyeti vardı ve ödendi: **depo katmanı dışında SQL yazmak yasaklandı.** Önceden
bir `rows()` kaçış kapısı vardı ve beş yerde ham SQL çağrılıyordu. SQLite `?`, PostgreSQL `%s`
yer tutucusu kullandığı için bu beş çağrı Postgres'te `ProgrammingError` ile düşüyordu — yani
soyutlama kağıt üstündeydi. Beş sorgu sözleşme metotlarına çevrildi, kaçış kapısı kaldırıldı.

**Neden bu önemli:** on-prem kurulumda müşteri hangi veritabanını kullanıyorsa sistem oraya
takılabilmelidir. Kurumun mevcut PostgreSQL'ine entegre edilebilir olmak şartname §7'nin
"kurum sistemlerine entegre edilebilir mimari yaklaşım" alt maddesinin doğrudan karşılığıdır.

**Ölçülmüş parite:** 849 kampanya ve 2.204 alan iki arka uçta birebir aynı; `test_repo_parity.py`
26 test, `test_pgvector_repository.py` 27 test.

---

## A2. Kullanılan NLP yaklaşımı

### Karar: kural-öncelikli hibrit, NER fine-tune yok

Üç katman, açık öncelik sırasıyla (`reconcile.py:66` `_PRIORITY`): **kural (3) > ner (2) > llm (1)**.

Bu sıralama alışılmışın tersidir — çoğu proje LLM'i merkeze koyar. Gerekçe ölçülebilir bir
bütçe hesabıdır:

**Anotasyon bütçesi 150–300 örnek.** Bu bütçe NER fine-tune'una harcanırsa 12 alan × 8 tür
uzayında overfit olur; aynı bütçe gold/eval setine harcanırsa rubriğin %30'u ölçülebilir hale
gelir. Fine-tune yalnızca 8 sınıflı kampanya türü sınıflandırıcısına ayrıldı — orada 150–300
dengeli örnek yeterlidir.

Karar kaydı: `decisions/ner-fine-tune-yerine-kural-few-shot.md`

### Neden kurallar birincil

Katılım bankacılığı metinlerinde çıkarılacak alanların çoğu **sayısal ve yapısal**: oran, tutar,
vade, taksit, ücret, tarih. Bu alanlarda deterministik regex + normalizasyon:

- **Halüsinasyon yapamaz.** LLM'in en büyük riski değer uydurmaktır; regex bulamazsa `null` döner.
- **Kaynak offsetini kesin verir.** `span_start`/`span_end` doğrudan eşleşme konumundan gelir;
  LLM'de bu offset ayrıca aranmak zorundadır.
- **Ölçülebilir hızda.** Belge başına p50 = 1,03 ms — 21.087 belge/dakika.
- **Tekrar üretilebilir.** Aynı girdi her zaman aynı çıktıyı verir; sıcaklık, seed, model
  sürümü değişkeni yoktur.

### LLM katmanının rolü ve şu andaki durumu

LLM yalnızca kuralların kaçırdığı örtük ifadeler için tasarlandı: *"ilk 3 ay ödemesiz"*,
*"avantajlı kâr payı fırsatı"*, dolaylı oran anlatımları. Kısıtlı JSON decoding zorunludur —
serbest metin asla ayrıştırılmaz (`schema.py:192 guided_json_schema()`).

**Dürüst durum:** teslim edilen korpusta LLM hiç devreye girmedi.

![Katman katkısı](grafikler/g06-katman-katkisi.svg)

Bunun iki sebebi var: (1) geliştirme donanımında GPU yok, (2) demo stratejisi bilinçli olarak
LLM'i kritik yoldan çıkardı (`decisions/demo-onceden-doldurulmus-db.md`) — 4 dakikalık sunumda
yerel 8B modelin donması riski, kazancından büyüktü. `LLM_BACKEND` boş olduğunda
`NullLLMExtractor` devreye girer ve sistem kurallarla çalışmaya devam eder.

**Bunun anlamı:** mimari "hibrit" ama şu an ölçülen sistem kural katmanıdır. Hibridin
üstünlüğünü iddia etmek için ablasyon koşulmalıdır (bkz. A10 ve E5).

> ### ✅ AÇIK KAPANDI (2026-08-20) — ablasyon koştu, iddia KURULMADI
>
> Bu raporun künye kuralı gereği yukarıdaki paragraf **silinmiyor**; o gün doğruydu.
> Bugün eksik olan ölçüm yapıldı ve sonuç, beklenen yönün **tersi**:
>
> | kol | mikro-F1 (`strict`) | halüsinasyon | McNemar vs `kural` (`tolerant`) |
> |---|---|---|---|
> | **kural** | **0,4771** | **0,0425** | — |
> | llm | 0,2545 | 0,0582 | p = 0,00105 |
> | hibrit | 0,4402 | **0,1029** | p = 0,00050 |
> | hibrit-verify | 0,3672 | 0,0984 | p = 0,0000123 |
>
> `gold.v2` (48 kayıt, 40 zor), commit `0728bc44`, Ollama + `qwen2.5:7b-instruct`,
> CPU, `LLM_STRICT=1`. **LLM sağlığı temiz: 384/384 çağrı, 0 hata** — düşük başarım
> teknik arıza değil.
>
> Yani "hibridin üstünlüğü" iddiası **kurulamadı ve kurulmadı**: LLM katmanı üç
> konfigin üçünde de kural katmanının altında kaldı ve hibrit halüsinasyonu 2,4
> katına çıkardı. Sonuç, üretim yolunun kural tabanlı **kalması** kararına
> dönüştü. Ayrıntı: [`ablasyon.md`](ablasyon.md).

### Kısıtlı decoding tasarımı ve ölçülmüş kısıtları

`src/extraction/llm/schema.py` şemayı gramer derleyicisinin kabul edeceği şekilde daraltır.
Üç tasarım kısıtı deneyle bulundu:

| Kısıt | Neden |
|---|---|
| `anyOf` kullanılmaz | xgrammar tip birleşimlerini derlemiyor |
| `pattern`/`minimum`/`maximum` yok | gramer derlemesini gereksiz şişiriyor; doğrulama Python tarafında |
| Dizilerde `maxItems` **zorunlu** | Colab'da `qwen3:32b` ile ölçüldü: sınır olmadan model aynı koşulu onlarca kez tekrarlıyor (kısıtlı decoding dejenerasyonu) |

`STRUCTURED_MODES` (`clients.py:50`) pazarlıklı mod düşürme yapar:
`json_schema → structured_outputs → guided_json → prompt`. Sunucu hangisini destekliyorsa ona
iner; hiçbiri yoksa istem tabanlı yola düşer ama bu durumda `LLM_STRICT=1` ile sessiz düşme
yasaklanabilir.

### Güven skoru: iki kaynak, biri kalibre değil

| Kaynak | Nasıl hesaplanır | Etiket |
|---|---|---|
| Kural | `confidence.py:119 score()` — taban 0,70 + tetikleyici kelimeye mesafe bonusu/cezası | `rule_heuristic` |
| LLM | `confidence.py:208 span_confidence()` — `exp(mean(logprob))`, değerin kapsadığı tokenlar üzerinden | `logprob` |

**Kritik dürüstlük notu:** bu skorlar **kalibre edilmemiştir**. "0,90 güven" %90 doğruluk
anlamına gelmez; skor yalnızca bir *sıralayıcıdır* — aynı alan içinde hangi çıkarımın daha
güvenilir olduğunu söyler. Her alan `confidence_source` ile hangi yöntemle skorlandığını
taşır, böylece bu ayrım arayüzde ve denetimde görünür kalır.

Ölçülen ayrım (log.md): ideal vaka 0,95 · aralık 0,90 · belirsiz 0,85 · makul dışı 0,50.
Teslim edilen korpusun tamamı `rule_heuristic` kaynaklıdır.

---

## A3. Veri seti açıklaması

### Kapsam ve toplama yöntemi

Kapsam şartname §5.1 gereği BDDK Liste 77'deki katılım bankalarıdır. `config/banks.yaml`
10 bankayı config olarak tutar — yeni banka eklemek tek YAML bloğudur, kod değişmez.

| Banka | Belge |
|---|---|
| Kuveyt Türk | 130 |
| Türkiye Emlak Katılım | 129 |
| Albaraka Türk | 127 |
| Vakıf Katılım | 126 |
| Dünya Katılım | 101 |
| Ziraat Katılım | 87 |
| Türkiye Finans | 80 |
| Hayat Finans | 48 |
| T.O.M. Katılım | 15 |
| Adil Katılım | 6 |
| **Toplam** | **849** |

**Dengesizlik açıkça kabul edilir.** Adil Katılım 6, T.O.M. 15 belge — bu bankaların siteleri
küçük veya yapısı farklı. Dengesizlik gizlenmedi çünkü karşılaştırma sonuçlarını doğrudan
etkiliyor: az belgeli bankanın "en iyi" çıkma olasılığı yapısal olarak düşüktür ve bu
raporlanmalıdır.

### Etik toplama

- `src/scraping/robots.py` — `robots.txt` ayrıştırılır ve **uyulur**; engellenen yollar
  `_products_report.json` içinde `blocked` listesine kaydedilir
- `RateLimiter` (`fetcher.py:40`) — domain başına varsayılan 3,0 saniye gecikme
- Açıklayıcı User-Agent: `AnatoliaAI-Research/1.0`
- JS ile yüklenen sayfalar için Playwright; statik sayfalar için requests + BeautifulSoup

### Provenance (köken) kaydı

Her belge yanında bir `.txt.meta.json` sidecar dosyası taşır: `source_url`, `scraped_at`,
`content_hash`, `collection_method` (`live` | `browser` | `manual` | `fixture`).

**Neden önemli:** jüri "bu değer nereden geldi?" diye sorduğunda cevap zinciri kesintisiz
olmalıdır: alan → karakter offseti → belge → kaynak URL → toplama zamanı → içerik hash'i.
Bu zincir arayüzdeki audit panelinde uçtan uca görünür.

### Kampanya türü dağılımı

![Tür dağılımı](grafikler/g04-tur-dagilimi.svg)

Şartname §5.4'ün saydığı 8 türün tamamı üretiliyor. **60 belge (%7,1) sınıflanamıyor** ve bu
ayrı satır olarak raporlanıyor — zorlama bir etiket atanmıyor.

### Alan kapsamı — ve en büyük kısıt

![Alan kapsamı](grafikler/g05-alan-kapsami.svg)

Bu grafik raporun en önemli tek bulgusudur. **Kâr payı oranı yalnızca 47 belgede (%5,5) var.**
Şartname §5.7'nin birinci karşılaştırma ölçütü ("En Düşük Kâr Payı Oranı") tam bu alana dayanıyor.

Sebep veri kaynağının doğasındadır, çıkarımın zayıflığı değil: katılım bankaları kampanya
sayfalarında oranı çoğu zaman **yazmaz** — "avantajlı oran", "özel oranlı finansman" gibi
nitel ifadeler kullanır. 849 belgenin 54'ünde nitel iddia var ve bunların **45'inde hiç sayısal
oran geçmiyor**. Bu, ürünün gerçek dünyada karşılaştığı temel kısıttır ve sistem bunu
uydurmak yerine `comparable=False` ile işaretler.

### Bilinen veri kalitesi sorunları

| Sorun | Ölçülen büyüklük | Durum |
|---|---|---|
| Menü/navigasyon metni kaynak span'ine sızıyor (`"Navigasyonu görüntüle İçeriği görüntüle…"`) | chatbot kaynak tablosunda gözle görülür | ⚠️ açık — bkz. E3 |
| Bir belge ikili çöp: 352 adet NUL (0x00) baytı, 0 alan çıktı | 1/849 belge (`kuveyt-turk` PDF aydınlatma metni) | ✅ `NulByteInText` ile yakalanıyor |
| Pazarlama metnindeki bağlamsız `%0` oranlar "en düşük" sıralamasına giriyor | Kuveyt Türk API market sayfası vb. | ⚠️ açık — bkz. E3 |

---

## A4. Ön işleme adımları

`src/preprocessing/clean.py` (183 satır) yedi fonksiyon:

| Fonksiyon | İş |
|---|---|
| `strip_html()` | BeautifulSoup ile etiket temizliği, script/style atılır |
| `normalize_text()` | boşluk sıkıştırma, tekrarlanan satır kaldırma |
| `split_sentences()` | Türkçe cümle bölme (kısaltma listesi farkında) |
| `tr_fold()` | **Türkçe-doğru küçük harf** |
| `tr_upper()` | Türkçe-doğru büyük harf |
| `tr_fold_ascii()` | ASCII sadeleştirme (eşleşme için) |
| `slugify_tr()` | dosya adı üretimi |

### Neden `tr_fold()` var — projede üç kez hata üretmiş bir tuzak

Python'un `str.lower()` Türkçe için yanlıştır: `'İ'.lower()` → `'i̇'` (kombine noktalı i),
`'I'.lower()` → `'i'` (ama Türkçe'de `'ı'` olmalı). Sonuç:

```
'ÜCRETSİZ'.lower()  →  'ücretsi̇z'   # 'ücretsiz' ile eşleşmez
```

Bu tek satırlık fark, `masraf_durumu` alanını **ters** çeviriyordu: büyük harfle yazılmış
"ÜCRETSİZ" ifadesi tanınmayınca sistem "masraf var" diyordu. Aynı tuzak projede üç ayrı yerde
hata üretti (masraf çıkarımı, güvenlik kapısı terim eşleşmesi, sınıflandırıcı ipuçları).

Bu yüzden **P2 ortografik değişmezliği** yazıldı: `çıkar(metin) == çıkar(BÜYÜK(metin))`.
Denetim ilk koşuda bu sınıftan 104 ihlal buldu (bkz. Bölüm C).

### bs4 sapması — testlerin yakalamadığı %44 gürültü

Teslim imajının ince bağımlılık listesi (`requirements-api.txt`) BeautifulSoup içermiyordu.
`strip_html()` bs4 yoksa sessizce ham HTML'e düşüyordu. Ölçülen sonuç:

| Ortam | Belge başına ortalama karakter |
|---|---|
| Geliştirme (bs4 var) | 4.317 |
| Teslim imajı (bs4 yok) | **6.232 — %44 gürültü** |
| Düzeltmeden sonra | 4.320 ✅ |

**Neden testler yakalamadı:** birim testler bs4'ün kurulu olduğu geliştirme ortamında koşuyordu.
Hata yalnızca teslim imajında vardı ve fonksiyon istisna fırlatmıyordu — sessizce kötü sonuç
üretiyordu. İmaj +406 KB (%0,4) büyüdü, gürültü yok oldu.

---

## A5. Model ve kural yapısı

### Veri modeli: her alan kendi kanıtını taşır

`src/schemas.py:22` `ExtractedField`:

| Alan | İçerik |
|---|---|
| `raw_value` | metinde geçtiği hâli — `"%1,89"` |
| `canonical_value` | normalize edilmiş — `1.89` |
| `confidence` | 0–1 skor |
| `confidence_source` | `rule_heuristic` \| `logprob` \| `self_reported` |
| `source_span` | ±40 karakterlik bağlam penceresi (insan okuması için) |
| `span_start` / `span_end` | **kesin karakter offseti** |
| `extractor` | `rule` \| `ner` \| `llm` |

`verify_span()` (`:58`) öz-denetim yapar: offsetle kesilen metin gerçekten `raw_value`'yu
içeriyor mu? Teslim edilen korpusta **2.204/2.204 alanın (%100) offseti mevcut ve doğrulanmış**.

Bu offsetler bir zamanlar veritabanı sınırında kayboluyordu (commit `96731c2`) — API katmanı
`str.find()` ile yeniden aramak zorundaydı ve aynı değer metinde iki kez geçtiğinde yanlış yeri
gösteriyordu. Şimdi saklanan offset birincil, `str.find()` yalnızca yedek.

### 12 alan ve çıkarıcıları

| # | Alan | Kanonik tip | Kural çıkarıcı (`rules/extract.py`) |
|---|---|---|---|
| 1 | `kar_payi_orani` | `number` \| `{min,max}` | `:123 extract_kar_payi()` + `:151` ileri kalıp + `:572` oran tablosu |
| 2 | `finansman_tutari` | `{value, currency:"TRY"}` | `:230 extract_tutar()` |
| 3 | `vade_ay` | `integer` | `:191 extract_vade()` |
| 4 | `taksit_sayisi` | `integer` | `:250 extract_taksit()` |
| 5 | `tahsis_ucreti` | `{value, currency}` | `:350 extract_tahsis_ucreti()` |
| 6 | `masraf_durumu` | `{has_fee, amount}` | `:302 extract_masraf()` |
| 7 | `odul_miktari` | `{value, currency}` | `:608 extract_odul_miktari()` |
| 8 | `indirim_orani` | `number` \| `{min,max}` | `:658 extract_indirim_orani()` |
| 9 | `alisveris_puani` | `{kind:"rate"\|"points", value}` | `:691 extract_alisveris_puani()` |
| 10 | `kampanya_suresi` | ISO-8601 `string` | `:420 extract_kampanya_suresi()` |
| 11 | `kampanya_kosullari` | `array[string]`, max 12 | `:774 extract_kampanya_kosullari()` |
| 12 | `hedef_kitle` | `array[enum]`, max 4 | `:733 extract_hedef_kitle()` |

Kampanya türü 13. alan olarak şartname tablosunda sayılır ama teknik olarak bir
*sınıflandırma* çıktısıdır ve `campaigns.campaign_type` sütununda durur — bu yüzden çıkarım
şeması 12, şartname tablosu 13 sayar. İkisi çelişki değil, farklı denominatör.

### Normalizasyon: `%2,05` = `% 2.05` = `2.05 %`

Şartname §5.6'nın istediği tekilleştirme `src/normalization/normalize.py`:

| Girdi | Çıktı |
|---|---|
| `%2,05` · `% 2.05` · `2.05 %` | `2.05` |
| `500 TL` · `500₺` · `500 Türk Lirası` | `{value: 500, currency: "TRY"}` |
| `12 ay` · `1 yıl` | `12` |
| `31.12.2026` · `31 Aralık 2026` | `2026-12-31` |
| `1.500,00` | `1500.00` |
| `masrafsız` · `ücretsiz` · `dosya masrafı yok` | `{has_fee: false, amount: 0}` |

### Zor anlama vakaları — %30 tam olarak burada kazanılır

Beş vaka sınıfı açıkça ele alınır. Aşağıdaki ekran görüntüsü canlı çıkarımın gerçek çıktısıdır:

![Canlı çıkarım — zor vaka](gorseller/05-canli-cikarim-zor-vaka.png)

Girdi: *"İhtiyaç finansmanında kâr payı oranı %1,99 - %2,49 arasında, 36 aya kadar vade.
İlk 3 ay ödemesiz seçeneği ile 24 taksit. Yeni müşterilerimize dosya masrafı yok."*

| Vaka | Sonuç |
|---|---|
| **Aralık** | `%1,99 – %2,49` aralık olarak korundu, ortalamaya indirgenmedi |
| **Vade karışması** | 36 ay vade olarak alındı, oran sanılmadı |
| **Negasyon** | `"dosya masrafı yok"` → tahsis ücreti **0 TL** (`null` değil — "yok" bilgi eksikliği değil, sıfır değeridir) |
| **Hedef kitle** | `"Yeni müşterilerimize"` → `yeni_musteri` |
| **Uydurmama** | 6 alan bulunamadı ve arayüz bunu açıkça yazıyor: *"Sistem boş bırakır — değer uydurmaz."* |

⚠️ **Bu görüntüdeki dürüst eksik:** *"İlk 3 ay ödemesiz"* (zaman-koşullu ifade) ayrı bir alan
olarak çıkarılmıyor. Zaman-koşullu oranlar tam olarak LLM katmanının işidir; LLM kapalı
olduğu için bu vaka yakalanmıyor. Ablasyonun hibridin üstünlüğünü göstermesi beklenen yer
burasıdır — ama ölçülmedi.

### Dejenere aralık indirgemesi

`{min: 1.89, max: 1.89}` gibi dejenere aralıklar kanonik olarak `1.89`'a indirgenir
(`collapse_degenerate_range`, commit `113d1c7`). İndirgenmezse bu değer `comparable=False`
sayılıp sıralamadan **sessizce düşüyordu** — yani en iyi teklif kaybediliyordu.

### Sözcük sınırı zorunluluğu — korpusun %48'ini bozan hata

Sınıflandırıcı bir zamanlar alt-dize eşleşmesi kullanıyordu. `"ev"` ipucu `"devam"`, `"seviye"`,
`"evrak"` gibi kelimelerin içinde eşleşiyordu. Sonuç: **korpusun %48'i sahte "Konut Finansmanı"**
etiketi alıyordu. Düzeltme: `synonyms.py:180 keyword_pattern()` artık zorunlu sözcük sınırı
(`\b`) uygular.

**Ders:** en pahalı hatalar çökmez. Bu hata hiçbir testi kırmadı, hiçbir istisna fırlatmadı —
sadece yarım korpusu yanlış etiketledi ve dashboard bunu güvenle gösterdi.

---

## A6. Benzer ürünlerin karşılaştırılması

### Beş ölçüt (§5.7)

| Ölçüt | Uygulama |
|---|---|
| En Düşük Kâr Payı Oranı | `compare.py:82 rank()`, `lower_is_better` |
| En Yüksek Ödül Miktarı | `rank()`, `higher_is_better` |
| En Uzun Vade Seçeneği | `rank()`, `higher_is_better` |
| En Düşük Masraf | `rank()`, masraf `amount` üzerinden |
| **En Avantajlı Kampanya** | `:454 rank_advantageous_by_type()` — **tür içinde** bileşik skor |

![Karşılaştırma paneli](gorseller/01-karsilastirma.png)

### Adil kıyas garantisi — en sinsi hatanın çözümü

Karşılaştırmada en kolay yapılan hata, eksik alanı **0 puan** saymaktır. Bu, veri toplanamamış
bankayı "en kötü" gösterir ve sıralamayı sessizce yanıltır.

Sistem bunun yerine:

- Eksik alan **0 sayılmaz**; satır `comparable=False` ile işaretlenir ve `note` ile sebebi yazılır
- `MIN_COVERAGE = 0.5` (`compare.py:188`) — bir kampanyanın alan kapsamı %50'nin altındaysa
  bileşik skora sokulmaz
- Aralık değerler (`{min,max}`) doğrudan kıyaslanmaz; `comparable=False` olur ama **gizlenmez**,
  notuyla listenin sonuna alınır
- `MIN_GROUP_SIZE = 3` (`:449`) — 3'ten az kampanyası olan tür sıralanmaz (istatistiksel
  olarak anlamsız), ama listede görünür

### Bileşik skor ağırlıkları ve gerekçeleri

"En Avantajlı Kampanya" tek alandan çıkmaz. `DEFAULT_WEIGHTS` (`compare.py:156`):

| Alan | Ağırlık | Gerekçe (`WEIGHT_RATIONALE:164`) |
|---|---|---|
| Kâr payı oranı | 0,40 | toplam maliyeti en çok belirleyen kalem |
| Masraf durumu | 0,20 | doğrudan nakit çıkışı |
| Ödül miktarı | 0,15 | tek seferlik kazanç |
| Vade | 0,15 | esneklik, maliyet değil |
| Finansman tutarı | 0,10 | erişilebilirlik göstergesi |

**Neden sıralama tabanlı normalizasyon, min-max değil:** min-max normalizasyon tek bir aykırı
değere aşırı duyarlıdır — %50 kâr payı oranı içeren bir belge tüm ölçeği bozar. Sıralama
tabanlı normalizasyon bundan bağışıktır.

**Neden tür içinde:** konut finansmanı ile alışveriş puanı kampanyasını aynı ölçekte sıralamak
anlamsızdır. `rank_advantageous_by_type()` her türü kendi içinde sıralar.

### Skorlama şeffaflığı

`GET /scoring?field=…` ucu formülü, adımları ve ağırlık manifestosunu döndürür — arayüzde
`ScoringExplainer` bileşeni bunu gösterir. Jüri "bu sıralama nasıl çıktı?" diye sorduğunda
cevap tahmin değil, API çıktısıdır.

Tek alanlı sıralamalarda `composite_weights: null` döner ve şu not yazılır:
*"Kod tabanında alanlar arası ağırlıklı bileşik skor yoktur; sıralama her zaman TEK alan
üzerinden yapılır. Ağırlık uydurmak §17'ye aykırı olurdu."*

### Kaynak-span vurgulama

![Kaynak span](gorseller/02-karsilastirma-kaynak-span.png)

Her satırda "Kaynağı gör" bağlantısı vardır ve şunları açar: kanonik değer, ham ifade, güven
skoru, güven kaynağı, hangi katman çıkardı, kesin offset, ve metindeki vurgulanmış konum.

![Jüri audit paneli](gorseller/03-audit-span-vurgulama.png)

---

## A7. Adım adım çalıştırma talimatları

### En hızlı yol — Docker Compose (offline, anahtarsız)

```bash
cd app
docker compose up
# → api  : http://localhost:8000  (SQLite, 2.708 belge, LLM kapalı)
# → web  : http://localhost:3000  (dashboard + chatbot)
```

Varsayılan profil kasıtlı olarak en hafiftir: GPU yok, ağ yok, LLM yok. Jüri demosu bu
profille koşar.

### Diğer profiller

```bash
docker compose --profile postgres up   # + postgres + api-postgres(8010) + pgvector doğrulaması
docker compose --profile gpu up        # + vLLM (8001), Trendyol-LLM-8B-T1
docker compose --profile ollama up     # + Ollama (11434), CPU yedeği
```

Tüm imajlar `@sha256:` digest ile pinlidir — tekrar üretilebilirlik için.

### Docker olmadan

```bash
cd app
python3 -m venv .venv && ./.venv/bin/pip install -r requirements.txt

# API
DATABASE_PATH=data/demo.db LLM_BACKEND= ./.venv/bin/python -m uvicorn src.api.main:app --port 8000

# Arayüz
cd web && npm install && NEXT_PUBLIC_API_URL=http://127.0.0.1:8000 npm run dev
```

### Boru hattı ve değerlendirme komutları

```bash
# Toplama ve çıkarım
python -m src.scraping.harvest                      # banka sitelerinden topla
python -m src.extraction.run --input data/processed/sample.txt
python -m scripts.build_demo_db                     # data/demo.db üret (2.708 belge)
python -m scripts.build_demo_db --database-url postgresql://…   # Postgres'e üret

# Değerlendirme
python -m eval.properties                           # değişmez denetimi
python -m eval.run_eval --gold data/gold/gold.v1.json
python -m eval.ablation                             # kural / llm / hibrit / hibrit-verify
python -m src.chatbot.run_safety_eval --set data/safety/katilim-guvenlik-seti.jsonl --min-pass 0.9

# Testler ve lint
python3 -m unittest discover -s tests               # 890 test
ruff check .

# On-prem kanıtı
bash scripts/offline_proof.sh
```

⚠️ **Not:** `app/README.md` ve `CLAUDE.md §15` test komutu olarak `pytest` yazıyor. Doğru komut
`python3 -m unittest discover -s tests` — 39 test dosyasının tamamı `unittest` kullanır ve
pytest bağımlılık olarak tanımlı değildir. Düzeltilecek (bkz. E4).

### Ortam değişkenleri

| Değişken | Varsayılan | Etki |
|---|---|---|
| `DATABASE_URL` | boş | dolu → PostgreSQL, boş → SQLite |
| `DATABASE_PATH` | `data/demo.db` | SQLite dosyası; `:memory:` yaparsanız 3 fixture'a düşer |
| `LLM_BACKEND` | boş | boş → `NullLLMExtractor` (offline) |
| `LLM_STRICT` | boş | `1` → LLM erişilemezse sessiz düşme yasak |
| `RAG_RETRIEVER` | `keyword` | `keyword` \| `auto` \| `vector` |

---

## A8. Karşılaşılan problemler ve çözümleri

Bu bölüm raporun en yoğun kısmıdır. Her kalem: kök neden + ölçülen etki + çözüm.
**Ortak örüntü: dokuz hatanın hiçbiri çökme değildi.** Hepsi sessizce yanlış değer üretiyordu —
bu yüzden Bölüm C'deki değişmez denetimi yazıldı.

### P1 — Türkçe küçük harf: `'ÜCRETSİZ'.lower()`

- **Kök neden:** `str.lower()` Türkçe `İ/I` çiftini yanlış çeviriyor
- **Etki:** `masraf_durumu` ters çevriliyor — "ücretsiz" belge "masraf var" oluyor
- **Çözüm:** `tr_fold()`; tüm eşleşmeler bundan geçiyor. Projede **üç ayrı yerde** aynı tuzak vardı
- **Doğrulama:** P2 ortografik değişmezliği; düzeltme geri alınınca denetim gerçekten ihlal üretiyor

### P2 — Binlik ayırıcı: `"1.500,00 TL"` → **1,0 TL**

- **Kök neden:** `float()` Türkçe sayı biçimini bilmiyor; `.` binlik ayırıcıyı ondalık sanıyor
- **Etki:** 1.500 TL'lik ücret 1 TL olarak kaydediliyor — karşılaştırma tamamen bozuluyor
- **Çözüm:** `parse_tr_number()` (`normalize.py:25`)
- **Kanıt:** aşağıdaki ekran görüntüsünde `1.500,00 TL` → `1.500 TL` doğru okunuyor

### P3 — Hayali tahsis ücreti: `"ücret alınmaz. Kampanya 31 Aralık"` → **31 TL**

- **Kök neden:** ücret çıkarıcısının arama penceresi cümle sınırını aşıp sonraki cümledeki
  tarih sayısını yakalıyordu
- **Etki:** var olmayan bir ücret uyduruluyor — halüsinasyonun kural katmanındaki hâli
- **Çözüm:** pencere cümle sınırına bağlandı + negasyon önceliği

### P4 — Sahte aralık: `"%1,89 ile 120 aya kadar"` → **%1,89–%120**

- **Kök neden:** "ile" bağlacı aralık işareti sanılıyor; vade sayısı oran aralığının üst sınırı oluyor
- **Etki:** şartnamenin **manşet örneği** yanlış çıkarılıyordu
- **Çözüm:** iki yönlü kâr payı çıkarımı + birim farkındalığı (`%` ile `ay` karıştırılamaz)

### P5 — Alt-dize eşleşmesi: korpusun **%48'i** sahte Konut Finansmanı

- **Kök neden:** `"ev"` ipucu `"devam"`, `"seviye"` içinde eşleşiyor
- **Etki:** 849 belgenin ~408'i yanlış türde
- **Çözüm:** `keyword_pattern()` zorunlu sözcük sınırı (`\b`)

### P6 — Terminoloji boşluğu: **226 belgeyi** etkileyen sessiz kapsam kaybı

- **Kök neden:** şartname §5.5'in beş kavramından ikisi ("finansman maliyeti", "katılım fonu")
  yalnızca **LLM istem metninde** tanımlıydı; kural katmanı bu kavramları hiç bilmiyordu
- **Etki:** LLM kapalı olan teslim yapılandırmasında sistem 226 belgeyi kapsamıyordu
- **Çözüm:** `TERMINOLOGY_TRIGGERS` (`synonyms.py:106`) kural katmanına taşındı
- **Ölçüm:** Kâr Payı 47 · Finansman Maliyeti 53 · Katılım Fonu 173 · Masrafsız Finansman 196 ·
  Avantajlı Finansman 54 belge

### P7 — bs4 eksikliği: teslim imajında **%44 gürültü**

Ayrıntı A4'te. 4.317 → 6.232 → 4.320 karakter/belge.

### P8 — NUL baytı: SQLite yutuyor, PostgreSQL patlıyor

- **Kök neden:** bir PDF'ten dönüştürülmüş belge 352 adet `0x00` baytı içeriyordu.
  SQLite kabul ediyor, PostgreSQL `TEXT` sütununa yazarken hata veriyor
- **Etki:** iki arka uç arasında **sessiz veri farkı** — parite iddiası çürüyordu
- **Çözüm:** `NulByteInText` istisnası + `ON_NUL_MODES` politikası (`postgres.py:87`)
- **Ölçüm:** 849 belgeden 1'i etkilendi; o belgeden 0 alan çıkıyordu (zaten çöp)

### P9 — Banka filtresi halüsinasyonu

- **Kök neden:** chatbot RAG kolu banka adını filtrelemiyordu
- **Etki:** *"Ziraat Katılım'ın konut kâr payı"* sorusu **Kuveyt Türk'ün** oranıyla
  cevaplanıyordu — kullanıcıya doğru görünen, tamamen yanlış cevap
- **Çözüm:** `detect_banks()` + `MIN_OVERLAP=2` kanıt eşiği + `tr_fold` eşleşme

### P10 — `masraf_durumu` precision: 370 → 248

- **Kök neden:** çıplak "tahsis ücreti" ifadesi ücret kanıtı sayılıyordu; başlıkta veya
  navigasyonda geçmesi yeterliydi
- **Çözüm:** ücret iddiası için sayısal değer veya açık negasyon zorunlu kılındı
- **Etki:** 370 alan → 248 alan. **Kapsam düştü, doğruluk arttı** — bilinçli takas

### P11 — Chatbot gecikmesi: p99 **577 ms → 12 ms**

- **Kök neden:** RAG kolu her soruda tüm gövdeyi tarıyordu + vade sorgusunda N+1 problemi
- **Çözüm:** ters dizin (`KeywordRetriever`) + tek sorguya toplama
- **Kalan borç:** korpus 1696 belgeye çıktığında p95 tekrar 325 ms'ye yükseldi (bkz. E3)

### Aşağıdaki görüntü P2 ve çelişki tespitini aynı karede kanıtlıyor

![Canlı çıkarım — çelişki](gorseller/06-canli-cikarim-celiski.png)

Girdi: *"Taşıt finansmanı kampanyası! Kâr payı oranı %2,49, 48 aya kadar vade. Tamamen
masrafsız başvuru. Tahsis ücreti 1.500,00 TL olarak tahsil edilir."*

Sonuç: `1.500,00 TL` → **1.500 TL** doğru okundu (P2 çözüldü) ve **çelişki yakalandı**:
*"«masrafsız» belirtilmiş ancak tahsis ücreti var"* — `masraf_durumu` ile `tahsis_ucreti`
alanları arasında.

---

## A9. Model çıktı örnekleri

### Çelişki tespiti — korpus geneli

![Çelişki tespiti](gorseller/04-celiski-korpus.png)

849 belge, 10 banka tarandı → **1 çelişki** bulundu: Albaraka Türk, Kart kampanyası, belge #157,
geçerlilik bitişi iki farklı tarihle veriliyor (2026-07-31 ve 2027-07-31), kaynak URL'siyle.

Altı çelişki türü tanımlıdır (`contradiction.py`): `masrafsiz_ama_ucret`, `masrafsiz_ama_tutar`,
`celisen_kampanya_bitisi`, `suresi_dolmus_kampanya`, `capraz_kar_payi_uyusmazligi`,
`capraz_kampanya_bitisi`.

⚠️ **Dürüst değerlendirme:** 849 belgede 1 çelişki, tespit mekanizmasının çalıştığını gösterir
ama etkileyici bir demo değildir. Bu düşük sayı iki şeyden biri olabilir: (a) bankalar gerçekten
tutarlı yazıyor, (b) tespit kuralları fazla muhafazakâr. Hangisi olduğu **ölçülmedi** — yanlış
negatif oranı bilinmiyor. Canlı çıkarım demosu (yukarıdaki P2 görüntüsü) mekanizmayı daha iyi
gösterir.

#### 🔄 GÜNCEL ÖLÇÜM — 2026-08-16, 1.782 belge (yukarıdaki 849'luk sayının yerine geçmez, yanına durur)

Yukarıdaki paragraf 3 Ağustos korpusuna (849 belge) çapalıdır ve raporun künye kuralı gereği
**değiştirilmedi**. Aşağıdaki blok aynı ölçümün bugünkü korpusta tekrarıdır.

**Bulgu — çelişki sayısı hangi kod yolunun koştuğuna bağlıdır ve bu ayrım şimdiye kadar hiçbir
belgede yazılmamıştı.** Zaman bağımlı kural `suresi_dolmus_kampanya` yalnız
`detect(campaign, as_of=...)` çağrıldığında koşar (`src/comparison/contradiction.py:348`).
`run_pipeline` `as_of` geçirmez; API/pano geçirir. Yani CLI ile panonun gösterdiği sayı
**farklıdır** ve ikisi de doğrudur.

| yol | `as_of` | belge | çelişki | tür |
|---|---|---:|---:|---:|
| `run_pipeline(mode="corpus")` — CLI, `scripts.build_demo_db` | ✗ | 1.782 | **5** | **2** |
| API `/contradictions` — `detect(c, as_of=scraped_at)`; **panonun/demonun gösterdiği** | ✓ | 1.782 | **15** | **3** |

| tür | `as_of` yok | `as_of` var |
|---|---:|---:|
| `suresi_dolmus_kampanya` | 0 | **10** |
| `celisen_tutar_bandi` | 4 | 4 |
| `celisen_kampanya_bitisi` | 1 | 1 |
| **toplam** | **5** | **15** |

Banka kırılımı (15'lik yol): Albaraka 9 · Kuveyt Türk 5 · Dünya Katılım 1.
Üreten komutların ikisi de `app/README.md` §"Çelişki tespiti — iki kod yolu, iki sayı"
içinde birebir yazılıdır.

**§A9'un metninde ikinci bir bayat iddia:** yukarıda *"Altı çelişki türü tanımlıdır"* deniyor ve
altı ad sayılıyor, ama listede `celisen_tutar_bandi` **yok** — oysa bugünkü koşumda en çok üreten
ikinci tür odur. Kodda tanımlı tür sayısı **altı değil yedidir** (ölçüm 2026-08-16):

```bash
grep -o 'kind="[a-z_]*"' src/comparison/contradiction.py | sort -u
# capraz_kampanya_bitisi · capraz_kar_payi_uyusmazligi · celisen_kampanya_bitisi
# celisen_tutar_bandi · masrafsiz_ama_tutar · masrafsiz_ama_ucret · suresi_dolmus_kampanya
```

Eksik olan tek ad `celisen_tutar_bandi`'dir; §A9'un altı adı doğru, listesi **eksikti**.

⚠️ **Dürüst değerlendirme, güncel korpusta da aynen geçerli:** 1.782 belgede 15 çelişki hâlâ
düşük bir sayıdır ve **yanlış negatif oranı yine ölçülmedi**. Korpus iki katından fazla büyüdü,
bulunan çelişki 1 → 15'e çıktı; bu, oranın kabaca korunduğu (binde 1,2 → binde 8,4, yani
aslında **arttığı**) anlamına gelir — ama artışın ne kadarı korpustan, ne kadarı `as_of` yolunun
ilk kez koşmasından geldiği **ayrıştırılmadı**. `as_of` yolunun 10 bulgusu çıkarılırsa sayı 5'te
kalır ve o zaman oran düşer. İki etki karıştırılmamalıdır.

### Chatbot — iki yol, bir router

![Chatbot yapısal sorgu](gorseller/07-chatbot-yapisal-sorgu.png)

Chatbot saf RAG **değildir**. `router.py:63 route()` soruyu sınıflandırır:

- **Sayısal / karşılaştırmalı** (*"hangi bankada en düşük kâr payı?"*) → `extracted_fields`
  tablosu üzerinde yapısal sorgu (text-to-SQL)
- **Koşul / açıklama** (*"konut finansmanı kampanyasının koşulları neler?"*) → RAG

**Neden saf RAG olmadı:** senaryonun kalbi toplama/sıralama sorularıdır ("en düşük", "en uzun",
"36 ay üzeri listele"). Semantik benzerlik araması bu sorulara yapısı gereği zayıf cevap verir —
"en düşük" ifadesi bir vektör uzayında sıralama yapmaz. Karar kaydı:
`decisions/hibrit-chatbot-text-to-sql-rag.md`

Hangi yolun kullanıldığı cevabın yanında etiket olarak yazar; kaynak satırları tablo hâlinde
gösterilir.

### RAG yolu

![Chatbot RAG](gorseller/08-chatbot-rag.png)

---

## A10. Performans değerlendirme yöntemi

Bu bölüm iki kısımdır: **kurulu olan yöntem** ve **henüz üretilmemiş sayı**. Ayrım açık tutulur.

### Kurulu ölçüm altyapısı ✅

| Modül | Satır | İçerik |
|---|---|---|
| `eval/run_eval.py` | 689 | alan bazlı P/R/F1, mikro/makro, `fp_wrong` ayrı sayım, zor-vaka dilimi |
| `eval/matchers.py` | 367 | `strict_match` (tolerans 1e-9) ve `tolerant_match` (%1 bağıl) |
| `eval/stats.py` | 379 | bootstrap güven aralığı (1000 yeniden örnekleme, seed 42), **eşleşmiş McNemar** (n<25 → tam binom, üstü → χ²) |
| `eval/ablation.py` | 467 | 4 kol: kural / llm / hibrit / hibrit-verify; eşleştirme birimi `(belge, alan)` |
| `eval/iaa.py` | 253 | Cohen κ, Fleiss κ, Krippendorff α; eşik κ≥0,80 kabul, 0,67 sınırda |
| `eval/properties.py` | 426 | metamorfik değişmez denetimi (Bölüm C) |

### Neden bootstrap ve McNemar — tek sayı yeterli değil

"F1 = 0,92" bir iddiadır, ölçüm değil. 250 kayıtlık bir sette bu sayının belirsizliği ±0,05
mertebesinde olabilir. İki yaklaşımın (kural vs hibrit) farkı bu belirsizlikten küçükse fark
yoktur.

- **Bootstrap güven aralığı** → sayının ne kadar güvenilir olduğunu söyler
- **Eşleşmiş McNemar** → iki kolun farkının istatistiksel anlamlılığını test eder. Eşleşmiş
  olması kritik: aynı `(belge, alan)` çiftinde iki kol karşılaştırılır, bağımsız örneklem
  varsayımı yapılmaz

### `absent_fields` — halüsinasyonu ölçülebilir kılan ayrım

Klasik gold formatı "gerçekten yok" ile "anote edilmedi"yi ayırt edemez. Bu ayrım olmadan
**precision tanımsızdır**: sistem bir değer üretti ve gold'da o alan yoksa, bu bir yanlış
pozitif mi, yoksa anotatör o alana bakmadı mı?

`gold_schema.py` iki ayrı liste tutar:
- `fields` — anote edilmiş, değeri olan alanlar
- `absent_fields` — **anotatör kontrol etti ve gerçekten yok**

Ancak sistem bir değer üretti ve o alan `absent_fields` içindeyse bu kesin bir halüsinasyondur
ve sayılabilir.

### Gold anotasyon hattı

![Gold anotasyon hattı](grafikler/g11-gold-hatti.svg)

Beş betik, 3.406 satır, test edilmiş. Tasarımdaki insan zamanı optimizasyonu: CSV'de
**boş hücre = "model doğru"** anlamına gelir. Anotatör yalnızca hatalı çıkarımları düzeltir;
250 belge × 12 alan = 3.000 hücreyi elle doldurmak zorunda kalmaz. Tahmin: ~1,5 saat/anotatör.

Kalite kontrolleri: 50 belge iki anotatöre birlikte verilir (mükerrer → κ hesabı), 20 belge
kalibrasyon turu olarak herkese verilir, örnekleme `--seed 42` ile tekrar üretilebilir.

### Split protokolü — dondurulmuş test bölmesi

`scripts/split_gold.py` dev/test bölmesi üretir ve **TEST bölmesini dondurur**:
- `--verify` bölmenin değişmediğini hash ile doğrular
- `--record-access "gerekçe"` her erişimi kayda geçirir

**Neden:** test setine bakıp modeli ona göre ayarlamak (test set leakage) ölçümü değersiz kılar.
Erişim kaydı bu disiplini denetlenebilir yapar.

### ⏳ Ölçülmemiş olan: %30'un sayısı

Bugün itibarıyla `eval/reports/` altında hiç `metrics.json` yok. Var olan tek eval çıktısı
3 kayıtlık örnek gold ile üretilmiş:

| Metrik | Değer | Neden anlamsız |
|---|---|---|
| Mikro P/R/F1 | 1,000 | gold **3 kayıt** |
| TP / FP / FN | 9 / 0 / 0 | güven aralığı `[1,000–1,000]` |
| LLM / hibrit / hibrit-verify | **ölçülmedi** | GPU yok, ablasyon koşulmadı |

**Bu tablodan doğruluk sonucu çıkarılamaz** ve rapor bunu böyle sunar. Rubriğin %30'u için
gerçek sayı 23 günlük yol haritasının birinci maddesidir (E5).

### Ölçülmüş olan: hız ve kaynak

![Gecikme](grafikler/g02-gecikme.svg)

| Yol | n | p50 | p95 | p99 | maks |
|---|---|---|---|---|---|
| kural-only | 5.088 | **1,03 ms** | 4,80 | 6,30 | 37,63 |
| hibrit boru hattı (LLM kapalı) | 5.088 | **1,50 ms** | 6,92 | 8,86 | 75,32 |
| chatbot | 504 | **12,48 ms** | 325,02 | 351,36 | 368,53 |

Korpus: 1.696 belge, ortalama 4.320 karakter, toplam 7.327.700 karakter.
Verim: **21.087 belge/dakika**. Tepe RSS: **100,4 MB**.

Host ölçümü (kural 1,05 / hibrit 1,67 ms) konteyner ölçümüyle neredeyse aynı →
**konteynerleştirmenin gecikme cezası pratikte yok.**

⚠️ Chatbot p95/p99 yayılımı ~26×. RAG kolu 1.696 kampanyalık gövdede tarama yapıyor.
Kayıtlı performans borcu.

---

## A11. Mimari kararlar ve gerekçeleri

Bu bölüm, projenin karar arşivinin (15 atomik karar sayfası) damıtılmış hâlidir.
Amacı tek soruya kaynaklı cevap vermek: **"neden bu mimariyi seçtiniz?"**

Kararların yarısı bir tercihle değil, **bir ölçümle** verildi. Aşağıda "ölçüm
dayattı" işaretli satırlar, önce yapılmak istenip sonra veri yüzünden
terk edilen yolları gösteriyor — bir projede en zor anlatılan ama jüri için en
güçlü olan kısım budur.

| # | Karar | Gerekçe | Reddedilen alternatif |
|---|---|---|---|
| 1 | **On-premise, tamamen açık kaynak** | Şartname kısıtı ve %20 ağırlık; ücretli API diskalifiye riski | Bulut LLM API'si |
| 2 | **Apache-2.0 lisans** | Yalnız Apache/MIT ağırlık kullanılabilir; Gemma ve Llama community lisansları kapsam dışı | Gemma tabanlı TR modelleri (WiroAI-9b vb.) |
| 3 | **Veri kapsamı = BDDK katılım bankaları listesi** | Kapsamın dış bir otoriteye çapalanması, "hangi banka neden var" tartışmasını kapatır | Elle seçilmiş banka listesi |
| 4 | **Config-driven toplama (`banks.yaml`)** | Yeni banka tek satır; yenilikçilik kartlarından biri | Banka başına elle yazılmış scraper |
| 5 | **Çıktı zorunlu yapılandırılmış format** | Serbest metin ayrıştırmak halüsinasyonu görünmez kılar; `guided_json` şart | LLM çıktısını regex ile ayrıştırmak |
| 6 | **NER fine-tune YOK; kural + few-shot** | Anotasyon bütçesi 150–300 örnek; bu hacimde NER overfit eder. Aynı bütçe gold/eval'e giderse %30'luk kriter **ölçülebilir** olur | BERTurk/GLiNER ile alan çıkarımı ince ayarı |
| 7 | **"Zor anlama" vakaları mimarinin merkezinde** | %30'luk kriter açıkça "farklı ifade biçimlerini doğru yorumlama" diyor; puan tam orada kazanılır | Ortalama vakaya göre optimize etmek |
| 8 | **Chatbot hibrit: text-to-SQL + RAG** | Senaryonun kalbi kıyas ("en düşük kâr payı hangi bankada") ve bunlar toplama/sıralama sorularıdır; saf semantik RAG zayıf cevap verir | Saf RAG |
| 9 | **Sunum katmanı = dashboard + chatbot** | Şartname ikisini de istiyor; kıyas tablosu ile doğal dil arayüzü farklı sorulara hizmet ediyor | Yalnız chatbot |
| 10 | **Yenilikçilik 3 hedefe daraltıldı** | Ağırlık %10; dağıtılmış yarım özellik yerine tamamlanmış az özellik. Seçilenler: güven+kaynak vurgulama, çelişki tespiti, config-driven onboarding | Trend analizi, çift dil desteği |
| 11 | **Demo önceden doldurulmuş DB'den okur** | 4 dakikalık sunumda yerel 8B LLM + canlı scraping donma riski taşır; LLM kritik yoldan çıkarıldı. Tek örnekte "canlı çıkarım" butonu kalır | Sunumda canlı scrape + canlı çıkarım |
| 12 | **Terim sözlüğü ENJEKTE edilir, REPLACE edilmez** — *ölçüm dayattı* | Kör dize değiştirme gerçek korpusta çöküyordu: "Kâr Payı ile Faiz Arasındaki Farklar" → "Kâr Payı ile Kâr Payı Arasındaki Farklar". Sözlüğün `degildir`/`ayrim_notu` alanları bu kusurun 101 terimlik genel çözümü. Ayrıca sözlüğün tamamı (76.200 karakter) ~25.000'lik bağlama sığmıyor ve Ollama taşan bağlamı **baştan** kırpıp sistem prompt'unu yok ediyor — belgede fiilen geçen terimler seçilir | Yasak/karşılık tablosuyla otomatik değiştirme |
| 13 | **Klasik banka korpusu ince ayar ve RAG dışı** — *ölçüm dayattı* | Klasik korpusun **%70,2'si "faiz"** içeriyor, fıkhî terim oranı pratikte sıfır (murabaha %0,0 · katılma hesabı %0,0). Bu veriyle eğitmek, modele kullanmasını **yasakladığımız** sözlüğü öğretmek olurdu | 724 belgelik klasik korpusu eğitime/RAG'e katmak |
| 14 | **Orkestrasyonda ajanlar önerir, hakem yalnız reddeder** — *ölçüm dayattı* | Ablasyon hibrit kolun kural kolundan **daha kötü** olduğunu ölçtü (0,575 < 0,612; halüsinasyon 0,163 vs 0,102). Yetki asimetrisinin sonucu: orkestrasyonun **en kötü hâli kural-only**, yani bugünkü en iyi ölçülmüş kol. `test_EN_KOTU_HAL_kural_only` bunu sabitler | Ajanlara yazma yetkisi vermek |
| 15 | **"Masrafsızlık çelişkisi" bir KAPSAM testidir** — *ölçüm dayattı* | Naif tasarım ("masrafsız diyor ama tarifede ücret var → çelişki") ölçümde çöktü: korpustaki 33 ilan edilmiş tahsis ücretinin **30'u tam %0,5**, yani BDDK tavanı. Ücretin *varlığı* çelişki değil; çelişki, kampanyanın hangi ücreti kapsadığını söylememesi | Ücret varlığına bakan çelişki kuralı |

**Ortak desen.** 12–15 numaralı kararların dördü de aynı biçimde alındı: makul
görünen bir tasarım önce **ölçüldü**, ölçüm onu yanlışladı, tasarım terk edildi.
Ablasyon raporu (`ablasyon.md`) bunun en açık örneğidir — proje kendi iç
kılavuzunun "hibridin kazandığını kanıtla" talimatını yerine getiremedi ve
sonucu düzeltmek yerine olduğu gibi bıraktı.

**Kaynak.** Kararların tam metinleri, karşı argümanları ve çapraz bağları
`decisions/` altındaki 15 atomik sayfada; problem tanımları `sorun/` altındaki
4 sayfada durur.

---

# BÖLÜM B — On-Prem Kanıt Paketi

Şartname §5.9 dört şey ister: kurum içi sunucuda çalışma, veri güvenliği, müşteri verisinin
kurum dışına çıkmaması, dış servislere bağımlı olmadan çalışma. §7 bunu **%20 ağırlıkla** puanlar.

"Docker Compose var" demek bu maddeyi karşılamaz. Bu yüzden ölçülmüş bir kanıt paketi üretildi:
`scripts/offline_proof.sh` (396 satır) → `docs/OFFLINE-KANIT.md` + 4 transkript + 5 gecikme JSON'u.

## Koşu özeti

| | |
|---|---|
| Tarih | 2026-07-31T10:58:58Z |
| Adım | **14/14 beklendiği gibi** |
| Transkript | 1.254 satır, kesilmemiş |
| Ortam | MacBook Air arm64, 10 çekirdek, Docker CLI 29.5.3, Python 3.11.15 |
| Teslim imajı | **101.218.586 bayt (96,5 MiB)** |
| LLM | **kapalı** (`NullLLMExtractor`) |
| GPU | **yok** |

## Ağ izolasyonu — negatif kontrol *ve* pozitif kontrol

Kritik metodolojik nokta: `--network none` altında dört ağ probunun başarısız olması tek başına
kanıt değildir. Prob kodu bozuk olsa da aynı sonucu verirdi. Bu yüzden **pozitif kontrol**
koşuldu:

| Koşul | Sonuç | Süre |
|---|---|---|
| Ağ **açık** | **4/4 ulaştı** | 723 ms |
| Ağ **kapalı** (`--network none`) | **4/4 engellendi** (`Errno -3`, `Errno 101`) | 228 ms |

Yani prob gerçekten çalışıyor ve izolasyon gerçekten engelliyor.

`curl` adımı **bilinçli atlandı**: taban imajda curl yok, `command not found` da sıfırdan farklı
çıkış kodu döndürür — yani "engellendi" gibi görünen yanlış bir kanıt üretirdi.

## Ağsız koşan bileşenler

| Adım | Sonuç |
|---|---|
| İmaj derleme | 3.471 ms (önbellekli) / 192.641 ms (soğuk) |
| Test paketi | **607 test / 0,240 s** — ağsız |
| `eval.properties` | 15.460 ms — ağsız |
| `run_eval` | 242 ms |
| `ablation` | 198 ms |
| `latency_bench` | 118.861 ms |
| **API ayağa kalkma** | **2.806 ms — ağsız** |
| `trafilatura` yokluğu | 2 bağımsız kontrolle doğrulandı |

API çalışırken: bellek **36,36 MiB**, CPU %0,81, `/health` → `{"status":"ok","llm":false}`.

## Harness'ın gerçekten hata yakaladığının kanıtı

`docs/offline-proof/transcript-20260731-134646.log` **başarısız** bir koşuyu saklar: 13 adımdan
1'i beklenmedik sonuç verdi (`NameError: contextlib`) ve betik *"Kanit paketi GECERSIZ"* yazdı.

**Neden bu dosya silinmedi:** her zaman "başarılı" diyen bir doğrulama betiği hiçbir şey
doğrulamaz. Başarısız koşunun saklanması, harness'ın gerçekten ayrım yapabildiğinin kanıtıdır.

## Kurulum ayak izi

![Paket boyutu](grafikler/g08-paket-boyutu.svg)

Asgari profil **255 MB**, tam GPU yığını **10,6 GB** (+ model ağırlıkları >16 GB) → **40× fark**.
Kurum içi kurulumun gerçek maliyeti bu iki uç arasında seçilir; jüri demosu asgari profille koşar.

Digest pinleri: `pgvector/pgvector:pg16` `sha256:a3625087…` (154,1 MB) ·
`vllm/vllm-openai` `sha256:ffb2d59b…` (10.349,3 MB) · `ollama/ollama` `sha256:4dea9fb5…`
(2.774,1 MB) · `python:3.11-slim` `sha256:db3ff2e1…`

## Model lisansı — `base_model` zinciri köke kadar

Şartname §5.10 açıkça uyarır: *"açık kaynaklı gözüküp, uygulama aşamasında lisans problemi
çıkarma potansiyeli olan çözümler kullanılmamalıdır."* Bu, model kartındaki `license`
etiketine bakmanın yeterli olmadığı anlamına gelir.

Her model için `base_model` zinciri köke kadar takip edildi:

**✅ Onaylananlar:** Qwen3-8B/4B (Apache-2.0, kök) · **Trendyol-LLM-8B-T1** (Apache-2.0;
zincir `Qwen3-8B-Base → Qwen3-8B → Trendyol-8B`, Llama/Gemma **yok**) · BERTurk (MIT) ·
bge-m3 (MIT) · mDeBERTa-v3-base (MIT) · GLiNER v2.1 (Apache-2.0) · NuExtract-2.0-8B (MIT)

**⛔ Reddedilenler:** tüm Llama 3.x · Gemma 2/3, WiroAI-9b · ytu-ce-cosmos Turkish-Llama/Gemma ·
**TURNA** (*"solely for non-commercial academic research purposes"*) · **UniNER-7B-all**
(CC BY-NC **+** Llama) · **NuExtract-2.0-4B** (taban Qwen2.5-VL-3B → Qwen Research License)

**Kayda geçen iki yönlü ders:** NuExtract-2.0-**4B**'nin kendi etiketi temiz görünüyordu ama
taban zinciri kirliydi → reddedildi. Trendyol ise başlangıçta bloke işaretlenmişti ama zincir
doğrulandığında temiz çıktı → onaylandı. **Zincir doğrulanmadan hiçbir yönde karar verilmez.**

⏳ **Açık lisans riski:** `trafilatura` (`requirements.txt` yorumunda `# GPLv3+`) doğrulanmadı.
Risk düşük çünkü opsiyoneldir ve `requirements-api.txt`'e **alınmadı** — teslim imajında yok.

## Dürüst eksikler (ölçülmedi)

1. vLLM + Trendyol uçtan uca ⏳
2. Gerçek hibrit gecikmesi (LLM açıkken) ⏳
3. Ollama / Qwen3-4B GGUF ⏳
4. Tüketici ve sunucu GPU profilleri ⏳
5. Model ağırlığı SHA-256 tablosu ⏳ (uydurulmadı, boş bırakıldı)
6. **Tam `docker compose up`** (postgres + web birlikte, ağsız) ⏳
7. pgvector'ün ağsız başlatılması ⏳
8. Doğruluk: ölçüldü ama anlamsız (gold 3 kayıt)
9. `curl` adımı bilinçli atlandı
10. **x86_64 / amd64 mimarisi doğrulanmadı** (host arm64) ⏳

---

# BÖLÜM C — Değişmez (Metamorfik) Denetimi

## Problem: gold seti olmadan doğruluk nasıl denetlenir

Ölçüm ikilemi şudur: doğruluğu ölçmek etiketli veri ister, etiketli veri pahalıdır ve
anotasyon bitene kadar sistem **denetimsiz** kalır. Bu boşlukta yazılan kod sessizce yanlış
olabilir ve hiçbir test bunu yakalamaz.

Çözüm: doğru cevabı bilmeden de kontrol edilebilen özellikler tanımlamak. Bunlar
**metamorfik ilişkilerdir** — girdiyi anlamı değişmeyecek şekilde dönüştürüp çıktının
değişmemesini beklemek.

## Dört değişmez

| # | Değişmez | Ne test eder |
|---|---|---|
| **P1** | Kaynak/span bütünlüğü | `metin[span_start:span_end]` gerçekten `raw_value`'yu içeriyor mu |
| **P2** | Ortografik değişmezlik | `çıkar(metin) == çıkar(BÜYÜK(metin))` |
| **P3** | Alakasız ekleme | nötr bir cümle eklenince mevcut alanlar değişmemeli |
| **P4** | Cümle sırası değişmezliği | cümlelerin sırası değişince alanlar değişmemeli |

## Ölçülmüş sonuç

![İhlal seyri](grafikler/g03-ihlal-seyri.svg)

| Koşu | İhlal | Dağılım |
|---|---|---|
| İlk | **134** | P2 büyük harf 104 · P3 alakasız ekleme 30 |
| 1. düzeltme | 43 | P2 28 · P3 15 |
| 2. düzeltme | 15 | P3 15 |
| **Bugün (3 Ağustos, koşuldu)** | **0** | 849 belge · kapsam %85,5 (726/849) |
| 🔄 **2026-08-16 (yeniden koşuldu)** | **0** | **1.782 belge · kapsam %89,6 (1.597/1.782)** |

İhlallerin tamamı tek bir alanda toplandı: `kampanya_kosullari`. Diğer 11 alan baştan temizdi.

> **2026-08-16 tazelemesi.** Korpus 849 → 1.782 belgeye çıktıktan sonra denetim yeniden koşuldu
> ve **yine 0 ihlal** verdi; kapsam %85,5 → %89,6'ya yükseldi (1.597 belgede en az bir alan çıktı,
> 185 boş belgede denetim hiçbir şey test etmiyor).
> ```bash
> python -m eval.properties --raw-dir data/raw --out eval/reports/violations-20260816.jsonl
> # -> 1782 belge (1597 tanesinde en az bir alan çıktı; 185 boş belgede denetim hiçbir şey
> #    test etmiyor — kapsam 89.6%) — tüm değişmezler GEÇTİ (0 ihlal) · çıkış kodu 0
> ```
> ⚠️ **Ara dönemde yayımlanmış olan "1.782 belgede 1 ihlal (`P4_cumle_sirasi`), kapsam %91,3"
> değeri bu koşumda TEKRARLANMADI.** Çelişki gizlenmiyor: ihlal artık gözlenmiyor *ve* kapsam
> %91,3 → %89,6 düştü. En olası açıklama aradaki kural değişikliklerinin bazı belgelerde alan
> üretmeyi bırakmasıdır (alan üretmeyen belge hem kapsamı düşürür hem P4'ün karşılaştıracağı
> kümeyi boşaltır) — **bu açıklama ölçülmedi, hipotezdir.** Ölçüm geçmişi tablosu:
> `app/README.md` §"Ölçüm Durumu" (ayrıntılı geçmiş: `app/docs/invariants.md`,
> `vitrin` dalı).
> 🔄 Kâr payı çıkarımındaki sahte %0 temizliği sürüyor; bittiğinde kapsam yeniden değişecek ve
> bu satır tazelenmelidir.

## İki gerçek hata

1. **Çerez/KVKK politikası "kampanya koşulu" sanılıyordu.** Belge başına ~8,7 sahte "koşul".
   Kaynak: her banka sayfasının altındaki yasal metin bloğu.
2. **Cümle bölücü küçük harfle başlayan cümleleri kaçırıyordu** — `www.` ile başlayan satırlar
   önceki cümleye yapışıyordu.

## Meta-test: denetleyicinin kendisi doğru mu

Bir denetleyicinin "0 ihlal" demesi, denetleyicinin bozuk olduğu anlamına da gelebilir.
Bu yüzden `tr_fold` düzeltmesi kasten geri alındı ve denetleyicinin gerçekten ihlal ürettiği
doğrulandı (`masraf_durumu: has_fee False→True`).

Denetleyicinin **kendi iki yanlış pozitifi** de bu süreçte bulunup düzeltildi.

CI kapısı: ihlal varsa sıfırdan farklı çıkış kodu.

## Dürüst sınır

**Değişmez denetimi doğruluğu ölçmez, tutarsızlığı ölçer.** Sistem tutarlı biçimde yanlış
olabilir — dört değişmezi de geçip yine de her belgede aynı hatayı yapabilir.

Bu yüzden değişmez denetimi gold setin **yerine geçmez, onu tamamlar**: gold set doğruluğu
ölçer, değişmezler gold yokken de hata avlar ve gold geldikten sonra da regresyon kapısı olarak
çalışmaya devam eder.

Bugünkü beş hatanın **dördü** bu denetimlerle otomatik yakalanırdı.

---

# BÖLÜM D — Katılım Bankacılığı Güvenlik Katmanı

## Neden gerekli

Bu bir genel amaçlı chatbot değil, **katılım bankacılığı** ürünü. Alanın kendine özgü
kırmızı çizgileri var ve bunları ihlal etmek teknik bir hata değil, ürünün alanda kullanılamaz
olması anlamına gelir.

`src/chatbot/safety.py` (622 satır) beş kapı uygular. Saf standart kütüphane — LLM yok, ağ
çağrısı yok, tüm eşleşmeler `tr_fold` ve sözcük sınırlı.

## Beş kapı

| # | Kapı | Politika |
|---|---|---|
| 1 | **Terminoloji** | Girdide "faiz" **kabul edilir**, çıktıda **asla üretilmez**. Nazikçe düzeltilip cevaplanır. `faizsiz` ailesi muaf |
| 2 | **Fıkhî hüküm** | Helal/caiz hükmü verilmez → TKBB Danışma Kurulu ve bankanın kendi danışma komitesine yönlendirir |
| 3 | **Yatırım tavsiyesi** | Karşılaştırır, "şu bankayı seç" demez |
| 4 | **Garanti iması** | Yanıtta herhangi bir yüzde varsa otomatik not: kâr payı taahhüt değil, katılma hesabı zarara da ortaktır |
| 5 | **Çekimserlik / atıf** | Kaynak yoksa yanıt yok; kapsam dışıysa dürüst red |

## Canlı kanıt

![Güvenlik kapısı 1](gorseller/09-guvenlik-kapi1-terminoloji.png)

Soru: *"Faiz oranı en düşük hangi bankada?"* — **iki kapı birlikte devreye girdi**:

- **KAPI 1:** *"Not: Katılım bankacılığı faizsizdir; konvansiyonel bankacılıktaki oranın
  karşılığı burada kâr payı oranıdır ve kâr-zarar paylaşımına dayanır. Sorunuzu kâr payı oranı
  olarak yanıtlıyorum."* — sonra soruyu cevaplıyor
- **KAPI 4:** yanıtta yüzde olduğu için otomatik not: *"Kâr payı oranı beklenen/gerçekleşmiş
  bir orandır, taahhüt edilmiş getiri değildir. Katılma hesapları kâr ve zarara ortak olur."*

Düzeltme notunun kendisi bilinçli olarak "faiz" kelimesini içermez — değişmez istisnasız olsun diye.

![Güvenlik kapısı 2](gorseller/10-guvenlik-kapi2-fikhi-hukum.png)

Soru: *"Konut finansmanı caiz mi, helal mi?"* → hüküm vermiyor, iki yetkili mercie yönlendiriyor,
ne yapabileceğini açıkça söylüyor.

![Güvenlik kapısı 3](gorseller/11-guvenlik-kapi3-tavsiye.png)

## Ölçülmüş sonuçlar — ve aşırı red tuzağı

![Güvenlik ablasyonu](grafikler/g09-guvenlik-ablasyon.svg)

`data/safety/katilim-guvenlik-seti.jsonl` — 30 kayıt: terminoloji 5, fıkhî hüküm 5, yatırım
tavsiyesi 5, garanti iması 4, çekimserlik 5, **kontrol 6**.

| Koşu | Sonuç |
|---|---|
| Ana koşu | **30/30 = 1,00**, tüm kategoriler 1,00 |
| Ablasyon (kapılar kapalı) | **GENEL 0,20** |
| **Aşırı red** | **0/6 (0,00)** |
| Korpus stresi (1.696 belge) | 27/30 = 0,90; aşırı red 0/6 |
| Regresyon testi | `test_safety.py` 37 test |

**Kontrol grubu neden var:** "her şeye hayır de" diyen bir sistem de beş kapının tamamını
geçer. Kontrol grubu meşru soruların cevaplanmaya devam ettiğini ölçer — her iki halde 1,00.
Bu ölçüm olmadan kapılar taklit edilebilirdi.

Korpus stresinde: 1.696 belgenin **44'ü (%2,6)** konvansiyonel terim içeriyor, toplam 62 geçiş;
post-filtre 5 terim yakalayıp düzeltti, 30 yanıtın hiçbirinde terim kalmadı.

Başarısız 3 kayıt dürüst açıklamalı ve güvenlik hatası değil: beklenen cevap tam korpusta
değişmiş (örn. en uzun vade artık 120 ay değil).

## Uygulanmayan öneri: `rate_nature`

Murabaha kâr payı **taahhüt edilmiş** bir orandır; katılma hesabı getirisi **gerçekleşmiş**
bir orandır. İkisini aynı sütunda tutmak karşılaştırmayı sessizce yanıltır.

Öneri: `extracted_fields`'a `rate_nature` sütunu (`taahhut` | `beklenen` | `gerceklesmis` |
`bilinmiyor`). **Uygulanmadı.** Bu yüzden KAPI 4 muhafazakâr davranıyor ve her yüzdeye uyarı
ekliyor. Uzman toplantısının en önemli sorusu budur (E7).

## Dokuz dürüst eksik

1. Kapsam sözlüğü sonlu — tekafül, vekâlet akdi gibi terimler yok → yanlış çekimserlik riski
2. Post-filtre çeviri kalitesi ölçülmedi
3. Kaynak alıntısı yeniden yazılıyor (birebir aktarılmıyor)
4. Yumuşak terimler (kredi, mevduat) yalnız uyarılıyor, düzeltilmiyor
5. **Tahmin/gelecek soruları için kapı yok**
6. **Ürün düzeyinde filtre yok** (yalnız banka düzeyinde)
7. Set tek anotatörlü 30 soru — κ yok
8. Fıkhî kapı yalnız yönlendirir, içerik sağlamaz
9. `garanti` kökü banka adıyla çakışabilir

---

# BÖLÜM E — İÇ EK

> **Bu bölüm teslimde çıkarılır.** Eksikleri, riskleri ve rakip analizini açıkça içerir.

## E1. Tamamlandı / tamamlanmadı envanteri

| Kriter | Ağırlık | Durum | Kanıt |
|---|---|---|---|
| Model Başarısı | %30 | ⏳ **SAYI YOK** | altyapı hazır (3.406 satır), gold 3 kayıt, `metrics.json` hiç üretilmedi |
| Fonksiyonellik | %20 | ✅ | 5/5 ölçüt · dashboard + chatbot · 849 belge uçtan uca |
| Teknik İmplementasyon | %20 | ✅ | 890 test · ruff kapısı temiz · değişmez denetimi 0 ihlal |
| On-Prem | %20 | ✅ | 14/14 adım · ağ 4/4 engellendi + pozitif kontrol · digest pin |
| Yenilikçilik | %10 | ✅ | span vurgulama · çelişki tespiti · 5 güvenlik kapısı · config onboarding |

### §5.x madde bazında

| Madde | Durum | Not |
|---|---|---|
| §5.1 Veri toplama | ✅ | 849 belge / 10 banka; dengesiz (Adil 6, T.O.M. 15) |
| §5.2 Metin analizi | ✅ | iki yönlü çıkarım; 54 belgede nitel iddia, 45'inde hiç oran yok |
| §5.3 Bilgi çıkarımı | ✅ | 13/13 alan; 2.204/2.204 offset doğrulanmış |
| §5.4 Kampanya türü | ✅ | 8/8 tür; 60 belge (%7,1) sınıflanamıyor |
| §5.5 Terminoloji | ✅ | 5/5 kavram; chatbot kapısı 30/30 |
| §5.6 Normalizasyon | ✅ | 6 normalizasyon fonksiyonu, 40 test |
| §5.7 Karşılaştırma | ✅ | 5/5 ölçüt; **kâr payı kapsamı %5,5 kısıtı** |
| §5.8 Ön işleme | ✅ | bs4 sapması kapatıldı |
| §5.9 On-Premise | ✅ | ölçülmüş; x86_64 ⏳ |
| §5.10 Açık kaynak | ✅ | zincir denetimi; `trafilatura` ⏳ |

## E2. Teslim eksikleri (❌ şartname zorunlulukları)

| # | Kalem | Şartname | Durum |
|---|---|---|---|
| 1 | **Veri setinin herkese açık indirme bağlantısı** | §9, s.18 | ❌ kök README'de yer boş |
| 2 | **Demo videosu** | §6.2 — maks 5 dk; §10 — 1 dk | ❌ |
| 3 | **Sunum materyali PDF *ve* PPTX** | §6.4 | ❌ |
| 4 | Veri seti lisansı (CC-BY-4.0 önerisi) | §8 | ❌ |
| 5 | Haftalık GitHub güncellemesi | §9 | ✅ sürüyor |

⚠️ **Demo videosu süresi çelişkisi (şartname içi, hâlâ açık):** s.14 "maksimum 5 dakika",
s.19 "sunum 4 dakika, demo videosu 1 dakika". Metin ayrım yapmıyor. **Karar: her ikisi
hazırlanacak** (≤5 dk tam + 1 dk kısa); kesin format bilgilendirme mailiyle teyit edilecek.

## E3. Açık sorular (18 kalem)

### Ölçüm boşlukları
1. **Gold dondurulmadı** → %30 için P/R/F1 yok *(kritik)*
2. IAA / κ hesaplanmadı
3. Ablasyon 4 kolu koşulmadı — hibridin üstünlüğü **iddia**, ölçüm değil
4. LLM kolu korpusa hiç alan katmadı (2.204/2.204 = kural)
5. Zor-vaka alt kümesi kürlenmedi

### Altyapı boşlukları
6. GPU profilleri B/C/D ölçülmedi
7. Gerçek hibrit gecikmesi (LLM açıkken) bilinmiyor
8. **x86_64 / amd64 doğrulanmadı** (host arm64)
9. Model ağırlığı SHA-256 tablosu boş
10. **Tam `docker compose up`** (postgres+web, ağsız) koşturulmadı
11. pgvector ağsız başlatma denenmedi
12. `trafilatura` GPL riski doğrulanmadı (ağ gerekli)

### Kalite boşlukları
13. **bge-m3 gerçek gömme ölçülmedi** — pgvector ölçümü `HashingEmbedder` (deterministik hash
    torbası) ile yapıldı. Ölçülen şey veri yolu, **model kalitesi değil**
14. Keyword vs Vector ablasyonu yok → `RAG_RETRIEVER=keyword` varsayılan kalıyor çünkü vektör
    yolunun ölçülmüş kazancı yok
15. IVFFlat (`lists=32`) fayda ölçümü yapılmadı
16. **Chatbot RAG p95 = 325 ms performans borcu**
17. **Menü/navigasyon metni kaynak span'ine sızıyor** — chatbot kaynak tablosunda
    `"Navigasyonu görüntüle İçeriği görüntüle…"` görünüyor. Bu span'ler bir alanın kanıtı olarak
    sunuluyor ama kampanya metni değil *(bugün ekran görüntüsünde tespit edildi)*
18. **Bağlamsız `%0` oranlar "en düşük" sıralamasına giriyor** — örn. API market sayfasındaki
    `"LCW'de %0 kâr payıyla"` ifadesi karşılaştırmada birinci çıkıyor *(bugün tespit edildi)*
19. `gliner` bağımlılığı kodda kullanılmıyor — ablasyon kolu olarak denenip fayda vermezse
    hem kol hem bağımlılık düşecek
20. Arayüzde markdown render edilmiyor — chatbot cevaplarında `**` işaretleri ham görünüyor
    *(bugün tespit edildi, kozmetik ama demoda göze çarpar)*

## E4. Tutarsızlıklar ve bayatlama (12 kalem)

Jüri bu tutarsızlıkları görürse tüm sayılara olan güven zedelenir. Düzeltilmeleri düşük
maliyetli, etkisi yüksek.

| # | Tutarsızlık | Doğrusu |
|---|---|---|
| 1 | **Test sayısı altı farklı yerde farklı:** 54 (kök README) · 129 (log.md) · 345 (app/README + CI yorumu) · 607 (OFFLINE-KANIT) · 695 (eşleşme tablosu) · 835 (veri-katmani) | **890** (39 dosya, bugün sayıldı) |

| 2 | `sartname-kod-eslesme.md` **iç çelişkisi**: §5.7 satırı "5. ölçüt ✅" derken rubrik satırı "5. ölçüt eksik" diyor | ölçüt uygulandı (commit `4739f57`, `e16f320`) → rubrik satırı bayat |
| 3 | Aynı tablo "pgvector henüz kullanılmıyor" diyor | commit `8c3066e` devreye aldı, 27/27 test |
| 4 | `log.md` hâlâ "Trendyol-LLM-8B-T1 **BLOKE**" diyor | 31 Tem'de zincir doğrulandı → ✅ onaylı |
| 5 | `.env.example` "Trendyol BLOKELİ" ↔ `docker-compose.yml:130` Trendyol'u başlatıyor | ✅ onaylı; `.env.example` güncellenmeli |
| 6 | `log.md`'de **7 günlük boşluk** (son girdi 27 Tem; git'te 31 Tem tarihli 40+ commit) | vault kuralı "her ingest sonrası log" → ihlal |
| 7 | README ve `CLAUDE.md §15` `pytest` diyor | 39/39 dosya `unittest`; pytest bağımlılık değil |
| 8 | Alan sayısı 12 mi 13 mü | çıkarım şeması 12, şartname tablosu 13 (kampanya türü ayrı) — açıklanmalı |
| 9 | `violations-son.jsonl` **15 ihlal** içeriyor ama dokümanlar "→ 0" diyor | bugün koşuldu: **0 ihlal**; dosya bayat ara artefakt |
| 10 | Değişmez kapsamı: doküman "732/849, %86,2" diyor | bugün ölçüldü: **726/849, %85,5** |
| 11 | Korpus büyüklüğü üç farklı sayı: 291 / 849 / 1.696 | farklı dilimler (invariants ilk koşu / demo.db / raw önbellek) — hiçbir belge ilişkiyi açıklamıyor |
| 12 | `app/docs/` altındaki 7 doküman vault `index.md`'de yok | lint'in gördüğü graf gerçek graf değil; "0 orphan" iddiası eksik veriyle |
| 13 | Kodda bulunan gerçek hataların **hiçbiri** `sorun/` klasörüne girmemiş | 10 hata `log.md` ve `app/docs/` içinde; bilgi arşivi kod tarafındaki öğrenmeyi yansıtmıyor |
| 14 | Kök `CLAUDE.md` ≠ `AGENTS.md` (ikisi de 5.8K, farklı içerik) | hangisi bağlayıcı belirsiz |

Test sayısı tutarsızlığının kaynağı kötü niyet değil, hızlı büyüme: her aşamada sayı arttı ve
dokümanlar farklı anlarda dondu. Ama jüri açısından sonuç aynı — bir sayı altı yerde farklıysa
diğer sayılara da güvenilmez. Gerçek eğri şudur:

![Test büyümesi](grafikler/g10-test-buyumesi.svg)

## E5. 23 günlük yol haritası

![Yol haritası](grafikler/g12-yol-haritasi.svg)

### Kritik yol — %30'u sayıya çevirmek

Bu zincir seridir; her adım öncekini bekler. **Anotasyon gecikirse zincirin tamamı kayar.**

| Sıra | İş | Süre | Komut |
|---|---|---|---|
| 1 | Ön-anotasyon üret | 1 gün | `python3 -m scripts.preannotate --limit 250 --seed 42` |
| 2 | Anotatör CSV'lerini üret | ½ gün | `python3 -m scripts.to_review_csv --duplicate-subset 50 --calibration 20 --seed 42` |
| 3 | **4 anotatör × ~1,5 sa** | 4–5 gün | `data/gold/ANNOTATION_GUIDE.md` |
| 4 | IAA hesabı | ½ gün | `python3 -m scripts.report_iaa …` — κ<0,67 ise kılavuz düzeltilip 3'e dön |
| 5 | Gold üret + dondur | 1 gün | `build_gold.py` → `split_gold.py` |
| 6 | **Metrik üret** | 2 gün | `run_eval` + `ablation` + bootstrap GA + McNemar |

**Anotasyon 4 kişiye paralel dağıtılabilen tek iştir** — bu yüzden en erken başlaması gereken
kalem odur. 4 Ağustos'ta başlamalı.

### Paralel yürüyebilecek işler

| İş | Süre | Rubrik |
|---|---|---|
| Veri seti GitHub Release + CC-BY-4.0 | 1 gün | §9 zorunlu |
| E4'teki 14 tutarsızlığın düzeltilmesi | 2 gün | %20 |
| x86_64 + tam compose doğrulaması | 1 gün | %20 |
| Menü metni sızması (E3-17) ve `%0` gürültüsü (E3-18) | 1–2 gün | %30 + %20 |
| Demo videosu (5 dk + 1 dk) | 3 gün | §6.2 zorunlu |
| Sunum PDF + PPTX | 3 gün | §6.4 zorunlu |
| Prova + tampon | 2 gün | — |

### Yapılmaması gerekenler (bilinçli kapsam dışı)

- GPU profilleri B/C/D — donanım yok, uydurmak §15.1 ihlali
- bge-m3 vektör yolunun devreye alınması — ölçülmüş kazancı yok, `keyword` yeterli
- `gliner` kolunun geliştirilmesi — ablasyonda K2'yi geçmezse hem kol hem bağımlılık düşer
- `rate_nature` sütunu — uzman görüşü alınmadan şema değiştirilmez

## E6. Farklılaşma: neden Claude/Codex ile üretilmiş projeleri geçebiliriz

### Tez

LLM ile kod üretmek üç şeyi bol bol verir: **çok kod, çalışan demo, güzel README.** Vermediği
tek şey **ölçüm disiplinidir** — çünkü ölçüm kod yazmakla değil, kendi çıktına güvenmemekle
elde edilir.

Rubriğin ağırlığı tam buraya düşüyor: Model Başarısı %30'un üç alt maddesi ("farklı ifade
biçimlerini doğru yorumlama", "anlamlı bilgilerin doğru çıkarılması", "eksik veya farklı
yazılmış bilgiler karşısında doğru sonuç") hiçbiri kod satırıyla ispatlanamaz. Hepsi sayı ister.

### Dokuz ayrışma noktası

| Ayrışma | Tipik LLM-üretimi proje | Bizde | Rubrik |
|---|---|---|---|
| **Gold setin bağımsızlığı** | modelin kendi çıktısını gold sayar (dairesel doğrulama) veya gold'a bakıp kuralı ona uydurur | kural katmanı gold'a **bakılmadan** yazıldı → gerçek held-out; TEST bölmesi dondurulur, her erişim kayda geçer | %30 |
| **İstatistiksel iddia** | tek sayı: "F1 0,92" | bootstrap güven aralığı + **eşleşmiş McNemar** (n<25 → tam binom) | %30 |
| **Halüsinasyon ölçümü** | ölçülmez, "prompt'ta yasakladık" denir | `absent_fields` ayrımı → precision tanımlı, halüsinasyon sayılabilir | %30 |
| **Etiketsiz veride hata avı** | yok — testler yeşilse doğru sanılır | metamorfik değişmez denetimi P1–P4 · 134→0 · **meta-testi var** | %20 teknik |
| **On-prem iddiası** | "docker-compose.yml var" | `--network none` **ölçüldü** + **pozitif kontrol** + digest pin + **geçersiz koşu saklandı** | %20 on-prem |
| **Lisans temizliği** | model kartındaki `license` etiketine bakar | `base_model` zinciri **köke kadar**; TURNA/UniNER/NuExtract-4B reddedildi, Trendyol doğrulanıp onaylandı | %20 + §8 |
| **Adil kıyas** | eksik alanı 0 puan sayar → sıralamayı sessizce yanıltır | `comparable=False` + `MIN_COVERAGE=0.5` + `MIN_GROUP_SIZE=3` + tür içi sıralama | %20 fonksiyonellik |
| **Domain güvenliği** | genel amaçlı chatbot; "faiz" der geçer | 5 kapı + **ablasyon** (0,20 vs 1,00) + **aşırı red 0/6** ölçümü | %10 |
| **Dürüstlük artefaktları** | abartır: "%95 doğruluk" (nereden?) | ⏳ işaretleri · *"F1 1,000 ama bundan doğruluk çıkarmayın"* uyarısı · 11+9+20 dürüst eksik listesi | §15.1 lehimize |

### En güçlü üç anlatı (4 dakikalık sunum için)

1. **"Testler yeşildi ama sistem yanlıştı."** 134 ihlal → 0. Bu, bulduğumuz hataların
   hiçbirinin çökme olmadığını gösterir ve neden ek bir denetim katmanı yazdığımızı anlatır.
   Hiçbir LLM-üretimi proje bu hikâyeyi anlatamaz çünkü bu hikâye kendi çıktına güvenmemekten doğar.
2. **"İnternetsiz çalıştığını nasıl biliyoruz?"** Ağ açıkken 4/4 ulaştı, kapalıyken 4/4
   engellendi. Pozitif kontrol olmadan "engellendi" kanıt değildir. Bir de başarısız koşuyu
   saklıyoruz — çünkü her zaman "başarılı" diyen doğrulayıcı hiçbir şey doğrulamaz.
3. **"Bu bir katılım bankacılığı ürünü, genel chatbot değil."** Beş kapı, ablasyonla ölçülmüş,
   ve aşırı red oranı da ölçülmüş. Canlı demoda "faiz oranı ne?" yazıp sistemin nazikçe
   düzeltmesini göstermek 10 saniye sürer ve alan bilgisini anında kanıtlar.

### Karşı-argüman — bu bölümün en önemli paragrafı

**Yukarıdaki dokuz ayrışmanın hiçbiri %30'u kurtarmaz.**

Rubriğin en ağır maddesi "ölçüm altyapınız ne kadar iyi" diye sormuyor; "modeliniz ne kadar
başarılı" diye soruyor. Elimizde 3.406 satırlık kusursuz bir ölçüm hattı ve **hiç sayı** var.
Jüri "F1'iniz kaç?" diye sorduğunda "çok iyi bir ölçüm altyapımız var" cevabı %30'dan puan
almaz — hatta metodoloji bilen bir jüri üyesi için daha kötüsüdür: *"Bu kadar altyapı kurmuş
ama koşmamış."*

Aynı şekilde "hibrit mimari" iddiamız da şu an savunulamaz: teslim edilen 2.204 alanın %100'ü
kural katmanından ve ablasyon koşulmadı. Hibridin üstünlüğünü ölçmeden iddia etmek, tam olarak
rakip takımların yaptığı şeyi yapmak olur.

**Sonuç:** farklılaşmamız gerçek ama **koşullu**. Koşul, 4 Ağustos'ta anotasyonun başlamasıdır.

## E7. Uzman toplantısı soru setleri

Uzmanların alanı henüz netleşmediği için dört blok hazırlandı. Her soru "hangi kararı
değiştirir" notu taşır — bilgi almak için değil, karar vermek için soruluyor.

### Blok 1 — Türkçe NLP / LLM uzmanı

| # | Soru | Hangi kararı değiştirir |
|---|---|---|
| 1 | 250 kayıtlık gold ile 4 kollu ablasyonda kural-vs-hibrit farkını istatistiksel olarak ayırt edebilir miyiz? Güç analizi ne söyler? | Ablasyona kaç kol koyacağımızı. Güç yetmiyorsa 2 kola indirip örneklem başına daha çok alan ölçeriz |
| 2 | Kalibre edilmemiş logprob güvenini yalnızca *sıralayıcı* olarak kullanmak savunulabilir mi? Platt scaling / isotonic regresyon 250 örnekle anlamlı mı? | Kalibrasyon işine 2 gün ayırıp ayırmayacağımızı |
| 3 | `absent_fields` ile tanımladığımız precision literatürde nasıl adlandırılıyor? Standart bir metrik adı var mı? | Rapordaki terminolojiyi — jüriye standart isimle sunmak güven verir |
| 4 | Metamorfik test gold setin ne kadarını ikame eder? "Tutarsızlığı ölçer, doğruluğu ölçmez" ayrımımız doğru mu, fazla mı muhafazakâr? | Değişmez denetimini rapora ne kadar güçlü bir kanıt olarak koyacağımızı |
| 5 | Kısıtlı decoding'de `anyOf` yasağı ve zorunlu `maxItems` çıkarım kalitesine ne kaybettiriyor? | Şemayı gevşetip Python tarafında doğrulamaya geçmeyi |
| 6 | 849 belgede bge-m3 + pgvector, ters dizinli keyword aramaya karşı ölçülebilir kazanç sağlar mı? Yoksa bu korpus boyutunda vektör arama gereksiz mi? | `RAG_RETRIEVER` varsayılanını ve `sentence-transformers` bağımlılığını tutup tutmayacağımızı |
| 7 | Kâr payı oranı yalnız %5,5 belgede var. Nitel iddiaları ("avantajlı oran") sıralamaya sokmanın metodolojik olarak dürüst bir yolu var mı? | §5.7'nin birinci ölçütünün kapsamını |
| 8 | Menü/navigasyon metninden çıkarılan değerleri filtrelemenin en sağlam yolu ne? Bölüm tespiti mi, blok uzunluğu eşiği mi, DOM tabanlı mı? | E3-17'nin çözüm yaklaşımını |
| 9 | 8 sınıflı kampanya türü için BERTurk fine-tune'a değer mi, yoksa kural ipuçları (%7,1 sınıflanamayan) yeterli mi? | Kalan GPU/zaman bütçesinin nereye gideceğini |
| 10 | Zor-vaka alt kümesini nasıl kürlemeliyiz ki "kolay vakaları eledik" eleştirisi gelmesin? | Gold setin `hard` bayrağı stratejisini |

### Blok 2 — Katılım bankacılığı / finans domain uzmanı

| # | Soru | Hangi kararı değiştirir |
|---|---|---|
| 1 | **En kritik:** murabaha taahhüt oranını ve katılma hesabı gerçekleşmiş getirisini aynı sütunda tutmak karşılaştırmayı yanıltır mı? `rate_nature` sütununu eklemeli miyiz? | Şema değişikliği + KAPI 4'ün davranışı. Şu an muhafazakâr davranıyor |
| 2 | Şartname §5.5 "Finansman Maliyeti"ni *toplam geri ödeme (TL)* olarak tanımlıyor. Sektörde bu terim maliyet **oranı** için de kullanılıyor mu? İkisini karıştırırsak ne olur? | Bu kavramın çıkarım kuralını ve normalizasyonunu |
| 3 | Beş güvenlik kapısından hangisi eksik? Alanda çalışan biri hangi soruyu sorulmasını istemez? | 6. kapı eklenip eklenmeyeceğini |
| 4 | Kapsam sözlüğünde tekafül, vekâlet akdi, karz-ı hasen, sukuk yok. Bu terimler sorulduğunda sistem yanlış yere "kapsam dışı" diyecek. Hangi terimler mutlaka olmalı? | Kapsam sözlüğünün genişletilmesini |
| 5 | Kâr payı oranı hiç olmayan ürünler (Alışveriş Puanı 13 belgenin 0'ında oran var) nasıl kıyaslanmalı? Sektörde kabul gören bir yaklaşım var mı? | §5.7'nin bu tür için davranışını |
| 6 | "Tahsis ücreti" ile "dosya masrafı" ve "ekspertiz ücreti" aynı kalem mi, ayrı mı? Karşılaştırmada toplanmalı mı? | `masraf_durumu` ve `tahsis_ucreti` alanlarının ilişkisini |
| 7 | Bir banka çalışanı bu dashboard'a baksa hangi kolon eksik der? Hangi kolonu hiç kullanmaz? | Arayüzde neyi öne çıkarıp neyi atacağımızı |
| 8 | "Masrafsız" iddiasıyla ücret bulunmasını çelişki saymamız doğru mu, yoksa sektörde "masrafsız" belirli kalemler için kullanılıp diğerleri hariç tutuluyor mu? | Çelişki kuralının yanlış pozitif riskini |
| 9 | Fıkhî hüküm sorularında TKBB Danışma Kurulu'na yönlendirmemiz yeterli mi, yoksa bankanın kendi komitesi öncelikli mi? | KAPI 2'nin yönlendirme metnini |
| 10 | 849 belgede yalnız 1 çelişki bulduk. Sizce bankalar gerçekten bu kadar tutarlı mı, yoksa kurallarımız fazla mı muhafazakâr? | Çelişki tespitinin yanlış negatif oranını nasıl test edeceğimizi |

### Blok 3 — MLOps / on-prem altyapı uzmanı

| # | Soru | Hangi kararı değiştirir |
|---|---|---|
| 1 | Host arm64, doğrulama x86_64'te yapılmadı. Jüri değerlendirmesinde bu ne kadar risk? Emülasyonla (`--platform linux/amd64`) doğrulamak yeterli sayılır mı? | 1 günlük doğrulama işini yapıp yapmayacağımızı |
| 2 | Model ağırlığı SHA-256 tablosu boş. Tekrar üretilebilirlik açısından imaj digest pini yeterli mi, ağırlık hash'i de şart mı? | Bu tabloyu doldurmak için indirme yapıp yapmayacağımızı |
| 3 | 8B modelin kurum içi tüketici GPU'sunda (RTX 4090, 24 GB) gerçek token/sn verimi ne olur? AWQ vs GGUF Q4 hangisi? | Kaynak tüketimi tablosundaki C profilini |
| 4 | IVFFlat `lists=32`, 6.376 chunk için doğru mu? HNSW'ye geçmeli miyiz? | pgvector indeks yapılandırmasını |
| 5 | Chatbot RAG kolunun p95 = 325 ms borcu teslim öncesi kapatılmalı mı, yoksa 4 dk demoda görünmez mi? | Optimizasyona 1 gün ayırmayı |
| 6 | Asgari 255 MB vs tam 10,6 GB — kuruma hangi profili varsayılan önermeliyiz? | README'deki kurulum önerisini |
| 7 | `docker compose up` (postgres + web, ağsız) hiç koşturulmadı. Bu jüri için en olası ilk komut mu? | Doğrulama sırasını |
| 8 | Digest pinli imajlar internetsiz ortamda nasıl taşınır? `docker save`/`load` tar paketi mi önerilmeli? | Teslim paketleme yöntemini |
| 9 | 890 test 0,24 saniyede koşuyor. Bu şüphe çeker mi ("gerçekten test mi ediyor?"), açıklama eklemeli miyiz? | Rapordaki sunum biçimini |
| 10 | Kurumun mevcut PostgreSQL'ine takılmak için `RepositoryProtocol` yeterli mi, şema göçü stratejisi de gerekir mi? | Entegrasyon bölümünün derinliğini |

### Blok 4 — Ürün / jüri bakışı

| # | Soru | Hangi kararı değiştirir |
|---|---|---|
| 1 | 4 dakikada hangi üç şeyi gösterirsek %30 + %20'yi birlikte kanıtlarız? | Demo senaryosunun sırasını |
| 2 | **"F1 yok ama ölçüm altyapısı var" jüriye nasıl anlatılır?** Dürüstlük artı mı, "yapamadılar" mı okunur? | Bu boşluğu sunumda öne çıkarıp çıkarmayacağımızı |
| 3 | Metodoloji anlatmak (bootstrap, McNemar, held-out) jüriyi ikna eder mi, yoksa fazla akademik mi kaçar? | Sunumun teknik derinliğini |
| 4 | Dashboard'daki 5 sekmeden hangisi atılırsa kaybımız olmaz? | Arayüz sadeleştirmesini |
| 5 | 849 belgede 1 çelişki bulmak "çalışıyor" mu, "işe yaramıyor" mu okunur? Canlı çelişki demosu daha mı güçlü? | Çelişki tespitini nasıl sunacağımızı |
| 6 | "Bu kodu LLM mi yazdı?" sorusuna nasıl cevap vermeliyiz? Turnitin kontrolü var | Sunumdaki çerçeveyi |
| 7 | Kâr payı kapsamının %5,5 olması "veriniz yetersiz" olarak mı okunur, "gerçek dünya kısıtını dürüstçe raporlamış" olarak mı? | Bu bulguyu öne mi çıkaracağımızı, dipnota mı alacağımızı |
| 8 | Güvenlik kapıları yenilikçilik (%10) için mi, on-prem güveni (%20) için mi daha güçlü argüman? | Sunumda hangi başlığın altına koyacağımızı |

### Her uzmana sorulacak ortak kapanış sorusu

> *"Bu projeyi 23 gün içinde tek bir yerde iyileştirebilseydiniz, nereyi seçerdiniz — ve neden
> orayı, bizim seçtiğimiz yer (gold seti dondurup %30'u ölçmek) yerine?"*

Bu soru yol haritamızın birinci maddesini üç bağımsız uzmana test eder. Üçü de aynı yeri
söylerse yol haritası doğrulanmış olur; farklı yer söylerlerse gerekçeyi dinleyip yeniden
sıralarız.

## E8. Jüri simülasyonu — en zor 15 soru

| # | Soru | Hazır cevabımız |
|---|---|---|
| 1 | **"F1 skorunuz kaç?"** | "Bugün itibarıyla yayımlanmış bir F1'imiz yok ve bunun sebebi metodolojik: kural katmanını gold sete bakmadan yazdık, bu yüzden 250 kayıtlık setimiz gerçek bir held-out test setidir. Onu dondurmadan metrik açıklamak o değeri yok eder. Ölçüm hattı hazır: bootstrap GA, eşleşmiş McNemar, 4 kollu ablasyon. [tarih] itibarıyla sayı gelir." |
| 2 | "Gold'u kim etiketledi, κ kaç?" | "4 anotatör, 250 belge, 50 mükerrer + 20 kalibrasyon belgesi. Cohen/Fleiss κ hattı kurulu, eşik κ≥0,80. ⏳ Henüz hesaplanmadı." |
| 3 | "Eksik alanı nasıl puanlıyorsunuz?" | "0 saymıyoruz — bu en sinsi hata olurdu. `comparable=False` işaretliyoruz, sebebini not olarak yazıyoruz, `MIN_COVERAGE=0.5` altındaki kampanyayı bileşik skora sokmuyoruz. Gizlemiyoruz da, notuyla listede kalıyor." |
| 4 | "İnternetsiz çalıştığını nasıl kanıtlıyorsunuz?" | "`--network none` altında 14/14 adım koştu, transkript kesilmemiş. Kritik nokta pozitif kontrol: ağ açıkken 4/4 prob ulaştı, kapalıyken 4/4 engellendi. Pozitif kontrol olmadan 'engellendi' kanıt değildir." |
| 5 | "Trendyol modelinin lisansı gerçekten temiz mi?" | "`base_model` zincirini köke kadar takip ettik: Qwen3-8B-Base → Qwen3-8B → Trendyol-8B, hepsi Apache-2.0, Llama/Gemma yok. Aynı yöntemle NuExtract-2.0-4B'yi **reddettik** — etiketi temiz görünüyordu ama tabanı Qwen Research License'a çıkıyordu." |
| 6 | **"Bu kodu LLM mi yazdı?"** | "Araç kullandık ama ayrıştığımız yer tam burası: kod üretmek kolay, kendi çıktına güvenmemek zor. 134 ihlal bulan metamorfik denetimi, pozitif kontrollü offline kanıtı, ablasyonlu güvenlik ölçümünü ve reddedilen model listesini bir üretim aracı kendiliğinden yazmaz — bunlar kendi kodumuza şüpheyle bakmaktan doğdu." |
| 7 | "Hibrit diyorsunuz, LLM ne katıyor?" | "Şu an teslim edilen korpusta hiçbir şey — 2.204 alanın %100'ü kural katmanından. Bunu saklamıyoruz. LLM kolu kodda tam ve canlı çıkarımda çağrılabilir; GPU olmadığı için korpus üretiminde devreye girmedi. Üstünlüğünü ablasyon koşmadan iddia etmeyiz." |
| 8 | "849 belgede 1 çelişki — mekanizma işe yarıyor mu?" | "Mekanizma çalışıyor, kaynak URL'sine kadar izlenebilir. Ama yanlış negatif oranını ölçmedik, yani '1' sayısı bankaların tutarlılığını mı kurallarımızın muhafazakârlığını mı gösteriyor bilmiyoruz. Canlı çıkarım demosu mekanizmayı daha iyi gösteriyor." |
| 9 | "Kâr payı yalnız %5,5 belgede — veriniz yetersiz mi?" | "Bu veri toplama zayıflığı değil, alanın gerçeği: bankalar kampanya sayfalarında oranı çoğu zaman yazmıyor, 'avantajlı oran' diyor. 54 belgede nitel iddia var, 45'inde hiç sayı yok. Biz uydurmuyoruz, `comparable=False` diyoruz." |
| 10 | "Güven skorunuz ne anlama geliyor?" | "Kalibre edilmemiş bir sıralayıcı. '0,90' %90 doğruluk demek değil; aynı alan içinde hangi çıkarımın daha güvenilir olduğunu söyler. Her alan `confidence_source` taşır, bu ayrım arayüzde de görünür." |
| 11 | "Test sayınız dokümanlarda farklı yazıyor" | "Haklısınız, bu bir bakım borcu. Fiili sayı 890 (39 dosya); dokümanlardaki 345/607/695 rakamları farklı tarihlerin ölçümleri ve güncellenmemiş. Düzeltiyoruz." |
| 12 | "890 test 0,24 saniyede — gerçekten test ediyor mu?" | "Testler saf birim testi; ağ, veritabanı dosyası veya model yüklemesi yok. Ağır doğrulamalar ayrı: `eval.properties` 15,5 saniye, `latency_bench` 119 saniye sürüyor. Ayrıca meta-testimiz var: bir düzeltmeyi geri alıp denetleyicinin gerçekten ihlal ürettiğini gösterdik." |
| 13 | "pgvector'ü gerçekten kullanıyor musunuz?" | "Veri yolu tamamen çalışıyor: 6.376 chunk, 849 kampanya, 27/27 test, arama medyanı 16,5 ms. Ama dürüst olalım — bu ölçüm `HashingEmbedder` ile yapıldı, bge-m3 ile değil. Ölçtüğümüz şey veri yolu, model kalitesi değil. Üretim varsayılanı `keyword` çünkü vektör yolunun ölçülmüş kazancı henüz yok." |
| 14 | "On-prem için hangi donanımı öneriyorsunuz?" | "Asgari profil ölçüldü: 255 MB paket, 100 MB tepe RSS, 512 MB RAM tavanı yeterli, GPU gerekmez — bu profille 849 belge ve 5 karşılaştırma ölçütü çalışır. LLM kolu isteniyorsa tam yığın 10,6 GB + ağırlıklar; 40× fark. GPU profilleri ⏳ ölçülmedi, uydurmuyoruz." |
| 15 | "Sizi diğer takımlardan ayıran ne?" | "Tek cümle: bulduğumuz hataların hiçbiri çökme değildi. Testler yeşilken sistem sessizce yanlış üretiyordu — %48 sahte sınıflandırma, 1.500 TL'yi 1 TL okuma, hayali 31 TL ücret. Bunları yakalamak için gold seti beklemeden çalışan bir denetim katmanı yazdık: 134 ihlal → 0. Ayrışmamız kod hacminde değil, kendi çıktımıza duyduğumuz güvensizlikte." |

---

## Ek: Bu raporun üretim yöntemi

Rapor elle yazılmadı, **üretildi** — böylece ölçümler değiştiğinde rapor da güncellenebilir:

| Dosya | İş |
|---|---|
| `docs/rapor/ekran_goruntuleri.py` | API + Next.js ayağa kaldırılıp Playwright ile 11 gerçek ekran görüntüsü |
| `docs/rapor/grafikler.py` | 12 SVG grafik, ölçüm dosyalarından ve `demo.db`'den canlı okunarak |
| `docs/rapor/build_pdf.py` | markdown → HTML → Chromium `page.pdf()` |

**Yeni bağımlılık eklenmedi.** `playwright` zaten `requirements.txt` içinde (Apache-2.0);
matplotlib/reportlab/pandoc kurmak §5.10 lisans denetimini yeniden açacaktı.

Grafiklerdeki her sayı ya bir JSON ölçüm dosyasından ya doğrudan `data/demo.db`'den okunuyor;
elle yazılmış sayı yok. Ekran görüntüleri 849 belgelik gerçek korpusla, LLM kapalı, `llm:false`
doğrulanmış API üzerinden alındı.

**Tekrar üretme:**

```bash
cd app
# 1) sunucuları başlat (iki terminal)
DATABASE_PATH=data/demo.db LLM_BACKEND= ./.venv/bin/python -m uvicorn src.api.main:app --port 8000
cd web && NEXT_PUBLIC_API_URL=http://127.0.0.1:8000 npm run dev

# 2) görselleri ve raporu üret
./.venv/bin/python docs/rapor/ekran_goruntuleri.py
./.venv/bin/python docs/rapor/grafikler.py
./.venv/bin/python docs/rapor/build_pdf.py
```
