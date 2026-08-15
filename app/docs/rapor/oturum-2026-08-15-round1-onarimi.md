# Round1 ölçüm zemininin onarımı — 2026-08-15 oturumu

> Bu belge bir oturumun ne yaptığını ve **ne işe yaradığını** kaydeder.
> Her iddia ölçülmüştür; ölçülmemiş olan "ölçülmedi" diye yazılıdır.
> Dal `round1-onarim` (13 commit) `main`'e birleştirildi.

## Başlangıç durumu

Round1 çift anotasyonu bitmişti ve Cohen **κ = 0,274** çıkmıştı. Ama κ'yı
raporlamadan önce ölçüm zemininin kendisinde üç kusur vardı:

1. **509 anotasyon kararının tamamı git HEAD'de yoktu** — yalnız çalışma
   ağacında. Tek `git checkout` dört anotatörün toplam emeğini silerdi.
2. **`gold.round1.json` karışık protokoldü** — `--csv-dir` dizindeki her CSV'yi
   aldığı için round0 kalibrasyon dosyaları (v1: boş hücre = onay, modele
   çapalı) round1 (v2) ile aynı gold'a girmişti. Ayrıca `--allow-errors` ile
   üretilmiş, 52 satır atılmıştı.
3. **`build_gold` anotatörün görmediği değerleri yazıyordu** (K5).

---

## Yapılanlar ve ölçülen karşılıkları

### 1. K5 — gold'un değer kaynağı düzeltildi

`build_gold.resolve_decision`, `verdict=ok` satırında değeri ön-anotasyon
havuzundan okuyordu. CSV'ler 8–9 Ağustos'ta bugünkü çıkarıcıyla tazelenmiş,
havuz 4 Ağustos'tan kalmıştı. **59 hücrede ayrıştılar:**

- 42 tarih sürüklemesi: CSV bitiş (`2026-12-31`), havuz başlangıç (`2026-01-01`)
- 14 `kar_payi_orani`: CSV **boş**, havuz `%50` / `%30` / `%5` — hepsi kâr
  **paylaşım** oranı, kılavuz §4.13/6 `absent` diyor

En zararlısı "onaylanmış yokluk": anotatör boş hücreyi `ok` ile onaylamış
("kontrol ettim, yok"), gold bir DEĞER yazmış — **halüsinasyon ölçümünü
tersine çeviren** bir hata.

**İşe yaradığı yer:** gold artık `report_iaa.row_value_token` ile aynı zemini
okuyor. Bugüne dek Krippendorff α taze CSV'yi, gold bayat havuzu okuyordu.

Mekanizma `onanotasyon_tazele.py` başlığında **zaten yazılıydı**; eksik olan
`build_gold`'un o uyarıyı uygulamasıydı.

### 2. Kör hakemlik — 53 vaka, 6 parti

Alt ajanlara A/B'nin kararları, κ raporu, gümüş ve tüm türetilmiş raporlar
okuma yasağıyla verildi; her partiye yalnız kendi alanının kılavuz paragrafı
gitti.

    A haklı (B düzeldi) : 11
    B haklı (A düzeldi) : 30
    dokunulmayan        : 10   (hakem üçüncü cevap verdi -> ikisine de dokunulmaz)
    unclear atlanan     :  2

**İşe yaradığı yer:** uyuşmazlık **56 → 14**, çelişki **120 → 11**. Ekipten
gelen "muhtemelen B daha doğru" sezgisi ölçüldü ve doğrulandı (30'a 11).

### 3. Şema onarımı — 18 satır kurtarıldı

`build_gold`'un ATTIĞI satırlar: taksonomi dışı `campaign_type`, `fix` deyip
değer yazmamış hücreler, `campaign_type` sütununa yazılmış `hedef_kitle`
değerleri, para alanına yazılmış oran.

6'sında model zaten doğruymuş (`ok`), 9'u onaylanmış halüsinasyonmuş
(`absent`), 4'ü kanonik değere çevrildi, 1'i `unclear`.

**İşe yaradığı yer:** `--allow-errors` kalktı, atılan satır **52 → 0**.

### 4. Ön-anotasyon havuzu tazelendi

**İşe yaradığı yer:** kanıtlı alan **99/148 → 129/148 (%67 → %87)**.
Doğrulandı: 30 kanıt kazanıldı, **0 kanıt kaybedildi, 0 gold değeri değişti,
0 `absent_fields` değişti**.

Bu işlem K5 düzeltmesinden **önce riskliydi** (havuz gold değerini besliyordu),
sonra güvenli hâle geldi. Yani 1. madde 4. maddeyi mümkün kıldı.

### 5. Kabuk bölgesi kapısı — §4.13/8 artık kodda

Kural kılavuzda vardı, kodda yoktu. Gümüşün kör kalite testi ölçmüştü: A ve
B'nin **bağımsız olarak aynı kararı verdiği** 60 hücrenin 9'unda iki insan da
komşu kampanyanın değerini onaylamıştı.

Naif tasarım ("işaretten metin sonuna kadar at") reddedildi — gold'da 16+5
gerçek değer öldürüyor, çünkü bu işaretler belgede medyan **%8–19** konumunda
(üst menüde). Uygulanan tanım **kuyruk kümesi**.

    TP            52 -> 52     KAYIP YOK
    uydurma       26 -> 21
    halüsinasyon 0,059 -> 0,047
    mikro-F1   0,452 -> 0,464
    makro-F1   0,556 -> 0,601

### 6. Oransal tahsis ücretinde türetme kaldırıldı

"Tahsis ücreti finansman tutarının %0,50'si" cümlesi, belgenin başka bir
yerindeki tutarla çarpılıp TL yazıyordu. 6 belgede metinde **hiç geçmeyen**
bir değer üretiliyordu. En açığı: taban olarak alınan 125.000 TL finansman
tutarı bile değil, bir **vade eşiğiydi**.

Gold metrikleri **birebir sabit kaldı** — 2026-08-07'de korunmaya çalışılan TP
bu yoldan gelmiyormuş.

**Beklenmedik yan etki:** `test_p4_kapsam_etkisi` çit belgesi artık çelişki
üretmiyor. Sebebi ölçüldü — o belgedeki `masrafsiz_ama_ucret` çelişkisi
**uydurma 50 TL'ye dayanıyordu**. CLAUDE.md §18/2 (çelişki tespiti) sahte bir
dayanaktan kurtuldu.

### 7. Kalibrasyon ilk kez koştu

`eval/calibration.py` ECE için ≥30 karar istiyordu; gold 48 kayıtken
hesaplanamıyordu. Round1 gold ile **n = 157**:

| Güven kovası | n | Ortalama güven | **Gerçek doğruluk** |
|---|---:|---:|---:|
| 0,70–0,75 | 34 | 0,720 | 0,971 |
| 0,80–0,90 | 76 | 0,844 | 0,763 |
| **0,90–1,01** | **22** | **0,948** | **0,636** |

**En yüksek güven bandı en kötü kalibre banddır.** Kök neden bulundu:
`extract.py`'de **11 çağrı yerinde `trigger_distance=0` sabit yazılmış**;
`confidence.score()` bununla `BASE 0,70 + ADJACENT_BONUS 0,25 = 0,95` üretiyor.
Skor o alanlarda ölçüm değil, sabit.

**İşe yaradığı yer:** kılavuz §2'nin "yüksek güven (≥0,90) → toplu `ok` yazın"
talimatı kaldırıldı. O talimat gold'a aktif olarak hata sokuyordu.

### 8. Lisans denetimi

`qwen2.5:7b-instruct` `OllamaClient`'ın **üretim varsayılanı** olduğu hâlde
`docs/model-license-audit.md`'de kayıtlı değildi. Her iki Ollama modeli de ✅
(zincir köke kadar, üç bağımsız kanıt: HF kartı, Ollama künyesi, yapıta gömülü
lisans metni).

Kök neden yapısaldı: denetim belgesinin §5 maddesi "docker-compose'de
kullanılan her ağırlık" diyordu ve Ollama kolunu hiç görmüyordu.

Yeni tuzak kayda geçti: `Qwen2.5-3B-Instruct` `qwen-research` lisanslı,
Apache-2.0 **değil** — aynı ailede boy değiştirmek lisans değiştiriyor.

### 9. Recall ölçülebilirliği

`gold_report_round1.md` şunu yazıyordu: **"12/12 alan karara bağlı (recall
ÖLÇÜLEBİLİR): 0"**. Elimizde precision vardı, recall yoktu.

Kapsaması en yüksek 10 belge seçildi, kalan 78 hücre iki Opus 5 oturumunda
karara bağlandı ve **ayrı** bir gold'a derlendi (`gold.round1.recall.json`).

    12/12 kapsanan   0 -> 5
    TN (doğru sessizlik)  34 -> 93

Kullanım sınırı `data/gold/GOLD-ROUND1-RECALL.md`'de yazılı: manşet metrik
veremez.

---

## κ — manşet değişmedi

| | değer | dosya |
|---|---:|---|
| **Manşet** (hakemlik ÖNCESİ) | **0,274** | `iaa_report_round1.md` |
| Hakemlik sonrası gold tutarlılığı | 0,844 | `iaa_report_round1_hakemlik_sonrasi.md` |

İkincisi **bağımsız uyum değildir**. Round0 emsali birebir budur (Fleiss κ
0,051 ve 0,268 yan yana yayımlandı).

Yeni: **alan bazlı κ kırılımı**. Toplu κ bir ortalamadır ve sorunun yerini
gizler:

    campaign_type      n=47  κ  0,331  17 uyuşmazlık
    vade_ay            n=32  κ  0,242  15 uyuşmazlık
    kampanya_kosullari n= 9  κ -0,125   6 uyuşmazlık   (rastgeleden KÖTÜ)

---

## Düzeltilen iddialar

Bu oturumda üç kez yanlış bir şey söylendi ve ölçümle düzeltildi. Kayda
geçiyor, çünkü aynı hata sınıfı tekrarlanabilir.

1. **"22 hücre yeniden karara bağlanmalı"** — yanlıştı. K5 bir veri hatası
   değil kod hatasıydı; hiçbir hücre yeniden karara bağlanmadı.
2. **"12 alanın 10'unda κ ≥ 0,67 çıkar"** — çıkmadı. Alanların çoğunun κ'sı
   düşük ve n'i 1–9 arasında; yüksek değil, **ölçülemiyor**. Doğru cümle:
   uyuşmazlıkların %57'si iki alanda toplanıyor, kalanı ölçüm için seyrek.
3. **Üç ayrı ölçüm hatası** — hepsi aynı sınıftan: gerçek sözleşmeye uymayan
   sahte nesne kurmak ya da yanlış alan adı kullanmak (`f.name` yerine
   `f.field_name`; `kanit_alintisi`'nin beklediği `source_span`/`raw_value`/
   `span_start` anahtarlarını atlamak). Üçünde de "0 sonuç" çıktı ve doğru
   bir bulgu yanlışlıkla çürütüldü. **Ders: sahte nesne kurmak yerine gerçek
   yolu koştur.**

---

## Sayı özeti

| Ölçüt | Önce | Sonra |
|---|---:|---:|
| Commit'li anotasyon kararı | 0 | 509 |
| Gold kayıt | 158 (karışık protokol) | 134 (saf v2) |
| Çelişki | 120 | 11 |
| `--allow-errors` | var | **yok** |
| Atılan satır | 52 | 0 |
| Kanıtlı alan | 166/183 (karışık) → 99/148 | **129/148 (%87)** |
| 12/12 kapsanan (recall) | 0 | 5 |
| Halüsinasyon (gold.v2) | 0,059 | **0,047** |
| mikro-F1 / makro-F1 (gold.v2) | 0,452 / 0,556 | **0,464 / 0,601** |
| Test | 2716 | **2777** |
| ECE hesaplanabilir mi | hayır (n<30) | **evet (n=157)** |

---

## Kalanlar

- **R3 — güven skorunun 11 sabit `trigger_distance=0`'ı.** Kök neden bulundu
  ve belgelendi ama düzeltilmedi: F1'e girmiyor, buna karşılık
  `compare.ASGARI_GUVEN = 0.65` kapısının davranışını değiştirir. Teslime
  yakın üretim davranışı değiştirmek yerine bulgu olarak raporlanıyor.
- **Kılavuz revizyonu Öneri 1–6** — ekip kararı bekliyor
  (`_kilavuz-revizyon-onerisi-round1.md`). Öneri 5 (`hedef_kitle` 5. etiket)
  şema kilidine dokunuyor.
- **C'nin 168 kararı** — 21'i havuz karıştırmadan kurtarılabilir; kalan 100'ü
  yalnız v1 havuzunda, round2'ye devredildi.
- **`round1_v2_*` turu** (338 satır ×4, 0 karar) — kılavuz revizyonu sonrası
  κ'yı meşru zeminde yeniden ölçmenin tek yolu. İnsan anotatör emeği ister.
- **Gümüşün ikinci LLM ile çapraz doğrulanması** — lisans denetimi tamamlandı,
  yol açık; tasarımı hazır (ikinci model hakem değil **çelişki avcısı**).
- **78 recall hücresinin insan doğrulaması** — `#recall-opus5` damgasıyla tek
  komutla süzülebilir.

## Sources
- `data/gold/iaa_report_round1.md`, `iaa_report_round1_hakemlik_sonrasi.md`
- `data/gold/gold_report_round1.md`, `GOLD-ROUND1-RECALL.md`
- `data/gold/review/_hakemlik-degisim-round1.md`, `_sema-onarimi-round1.md`
- `data/silver/KALITE-KOR-TEST.md`, `ROUND1-GUMUS.md`
- `docs/model-license-audit.md`
