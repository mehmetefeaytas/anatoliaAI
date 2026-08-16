# Değerlendirme raporu — konfig `kural`

yalnız kural katmanı (regex + normalizasyon), LLM kapalı — RESMÎ VARSAYILAN (K-2)

## Künye (tekrar-üretim)

| künye | değer |
|---|---|
| konfig | kural |
| gold dosyası | data/gold/gold.sample.json |
| gold sha256 | 1219201a31e07c0b… |
| gold kayıt sayısı | 3 |
| alt küme (split) | all |
| eşleştirici(ler) | strict, tolerant |
| seed | 42 |
| git sha | eda8d96f4dddf6345b520fddcd69a8b0851cf720 |
| commit'lenmemiş değişiklik | EVET (dikkat: sayı bir commit'e karşılık gelmiyor) |
| Python | 3.14.6 |
| platform | macOS-26.5.2-arm64-arm-64bit-Mach-O |
| bağımlılık | yalnız Python stdlib (numpy/scipy/sklearn YOK) |
| üretim zamanı (UTC) | 2026-08-16T09:48:41.013119+00:00 |

## Metrik tanımları

- **TP**: gold'da değer var, tahmin eşleşti.
- **FP**: tahmin var ama yanlış (`fp_wrong`) ya da gold "YOK" diyor (`fp_hallucinated`).
- **FN**: gold'da değer var, tahmin yok ya da yanlış.
- **TN**: gold "YOK" diyor, model de üretmedi (doğru çekimserlik).
- **ATL (atlanan)**: gold bu alan hakkında KARAR VERMEMİŞ — metriğe girmez. Bilmediğimizi lehimize saymıyoruz.
- **halüsinasyon oranı** = `fp_hallucinated / (tn + fp_hallucinated)`; gold'da hiç `absent_fields` kararı yoksa TANIMSIZDIR (0,0 yazmak yalan olurdu).

### Hata sınıfları — üçü AYRI ölçülür

Aynı sayıya bakıp "model kötü" demek yerine hangi hatanın yapıldığını ayırıyoruz; üçü farklı düzeltme gerektiriyor:

- **kaçırma** (`fn - fp_wrong`): bilgi metinde VAR, model hiçbir değer üretmedi. Kapsama sorunu — regex ya da prompt eksik.
- **yanlış çıkarım** (`fp_wrong`): bilgi metinde VAR, model YANLIŞ yerden aldı. *Grounding* sorunudur, halüsinasyon DEĞİLDİR — kanun maddesindeki "1 yıl"ı vade sanmak bu sınıfa girer.
- **halüsinasyon** (`fp_hallucinated`): bilgi metinde YOK, model uydurdu. En tehlikelisi; zemin sorunu.

**Paydalar ayrıdır:** çıkarım hatası oranının paydası gold'da DEĞER olan kararlar (`support`), halüsinasyon oranının paydası gold'da "YOK" denen kararlardır (`absent_decisions`). Aynı paydaya bölünürlerse karşılaştırılamaz hale gelirler.
- **makro-F1**: alanların F1 ortalaması (yalnız gold desteği olan alanlar). Mikro seyrek alanları gizler, makro gizlemez.
- **%95 GA**: belge düzeyinde küme bootstrap. Aynı belgeden çıkan 12 alan bağımsız değildir; alan düzeyinde örneklemek GA'yı yapay olarak daraltır (bkz. `eval/stats.py`).

## Eşleştirici: `strict`

| alt küme | P (mikro) | R (mikro) | F1 (mikro) | F1 (makro) | mikro-F1 %95 GA | halüsinasyon |
|---|---|---|---|---|---|---|
| TÜMÜ | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 [1.000–1.000] | ölçülemedi (gold'da absent kararı yok) |
| ZOR (2 belge) | 1.000 | 1.000 | 1.000 | 1.000 | — | ölçülemedi (gold'da absent kararı yok) |
| YAPILANDIRILMIŞ (11 alan) | 1.000 | 1.000 | 1.000 | 1.000 | — | ölçülemedi (gold'da absent kararı yok) |
| ZOR + YAPILANDIRILMIŞ (2 belge) | 1.000 | 1.000 | 1.000 | 1.000 | — | ölçülemedi (gold'da absent kararı yok) |

> **«YAPILANDIRILMIŞ» satırı neyi dışarıda bırakıyor:** `kampanya_kosullari`. Bu alan serbest cümle listesi döndürür; span/jeton eşleşmesiyle F1 ölçmek metodolojik olarak yanlıştır — aynı koşulu farklı sözcüklerle yazan iki anotatör bile birbirini «yanlış» bulurdu. Alan GİZLENMİYOR: aşağıda kendi bölümünde, kalem düzeyi ölçütle raporlanıyor ve iki sayı yan yana duruyor.

### Alan bazında

| alan | P | R | F1 | TP | FP | FN | TN | uydurma | atlanan |
|---|---|---|---|---|---|---|---|---|---|
| alisveris_puani | 0.000 | 0.000 | 0.000 | 0 | 0 | 0 | 0 | 0 | 3 |
| finansman_tutari | 0.000 | 0.000 | 0.000 | 0 | 0 | 0 | 0 | 0 | 3 |
| hedef_kitle | 0.000 | 0.000 | 0.000 | 0 | 0 | 0 | 0 | 0 | 3 |
| indirim_orani | 0.000 | 0.000 | 0.000 | 0 | 0 | 0 | 0 | 0 | 3 |
| kampanya_kosullari | 0.000 | 0.000 | 0.000 | 0 | 0 | 0 | 0 | 0 | 3 |
| kampanya_suresi | 1.000 | 1.000 | 1.000 | 1 | 0 | 0 | 0 | 0 | 2 |
| kar_payi_orani | 1.000 | 1.000 | 1.000 | 2 | 0 | 0 | 0 | 0 | 1 |
| masraf_durumu | 1.000 | 1.000 | 1.000 | 2 | 0 | 0 | 0 | 0 | 1 |
| odul_miktari | 0.000 | 0.000 | 0.000 | 0 | 0 | 0 | 0 | 0 | 3 |
| tahsis_ucreti | 1.000 | 1.000 | 1.000 | 1 | 0 | 0 | 0 | 0 | 2 |
| taksit_sayisi | 0.000 | 0.000 | 0.000 | 0 | 0 | 0 | 0 | 0 | 3 |
| vade_ay | 1.000 | 1.000 | 1.000 | 3 | 0 | 0 | 0 | 0 | 0 |

### Kalem düzeyi ölçüt (serbest metin alanları)

Aşağıdaki alanlar cümle listesi döndürür. İkili ölçüt bir alanı **ya tamamen doğru ya tamamen yanlış** sayar: beş koşuldan dördü doğru çıkarılsa bile TP=0. Kalem düzeyi ölçüt her koşulu ayrı sayar (jeton-Jaccard ≥ 0.70, 1-1 açgözlü eşleştirme).

**Manşet mikro-F1 bu tablodan ETKİLENMEZ.** İkili ölçüt manşet olarak kalır; buradaki sayı onun yerine geçmez, yanında durur.

| alan | ölçüt | P | R | F1 | TP | FP | FN |
|---|---|---|---|---|---|---|---|
| `kampanya_kosullari` | ikili | 0.000 | 0.000 | 0.000 | 0 | 0 | 0 |
|  | kalem | 0.000 | 0.000 | 0.000 | 0 | 0 | 0 |

Tüm alanlarda mikro-F1: ikili **1.000** · kalem **1.000**.

#### Eşik duyarlılığı

Eşik sayıya bakılarak seçilmedi. Aşağıdaki tablo, seçilen eşiğin sonucu ne kadar taşıdığını gösterir; taşıyorsa bunu okuyucu bilmelidir.

| jaccard eşiği | kalem mikro-F1 | TP | FP | FN |
|---|---|---|---|---|
| 0.60 | 1.000 | 9 | 0 | 0 |
| 0.70 ← ilan edilen | 1.000 | 9 | 0 | 0 |
| 0.80 | 1.000 | 9 | 0 | 0 |

> **Sonuç eşikten bağımsız çıktı.** Denenen eşiklerin hepsinde aynı sayı üretildi; yani bu korpusta kalemler ya neredeyse birebir örtüşüyor ya hiç örtüşmüyor, arada sınır vaka yok. Eşiğin sonucu taşımadığını söylemek, taşıdığını söylemek kadar raporlanmaya değerdir.

### Zor-vaka etiketi kırılımı

Etiketler çok değerlidir; tablolar ÖRTÜŞÜR.

| etiket | mikro-F1 | makro-F1 | TP | FP | FN |
|---|---|---|---|---|---|
| legacy | 1.000 | 1.000 | 4 | 0 | 0 |

## Eşleştirici: `tolerant`

| alt küme | P (mikro) | R (mikro) | F1 (mikro) | F1 (makro) | mikro-F1 %95 GA | halüsinasyon |
|---|---|---|---|---|---|---|
| TÜMÜ | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 [1.000–1.000] | ölçülemedi (gold'da absent kararı yok) |
| ZOR (2 belge) | 1.000 | 1.000 | 1.000 | 1.000 | — | ölçülemedi (gold'da absent kararı yok) |
| YAPILANDIRILMIŞ (11 alan) | 1.000 | 1.000 | 1.000 | 1.000 | — | ölçülemedi (gold'da absent kararı yok) |
| ZOR + YAPILANDIRILMIŞ (2 belge) | 1.000 | 1.000 | 1.000 | 1.000 | — | ölçülemedi (gold'da absent kararı yok) |

> **«YAPILANDIRILMIŞ» satırı neyi dışarıda bırakıyor:** `kampanya_kosullari`. Bu alan serbest cümle listesi döndürür; span/jeton eşleşmesiyle F1 ölçmek metodolojik olarak yanlıştır — aynı koşulu farklı sözcüklerle yazan iki anotatör bile birbirini «yanlış» bulurdu. Alan GİZLENMİYOR: aşağıda kendi bölümünde, kalem düzeyi ölçütle raporlanıyor ve iki sayı yan yana duruyor.

### Alan bazında

| alan | P | R | F1 | TP | FP | FN | TN | uydurma | atlanan |
|---|---|---|---|---|---|---|---|---|---|
| alisveris_puani | 0.000 | 0.000 | 0.000 | 0 | 0 | 0 | 0 | 0 | 3 |
| finansman_tutari | 0.000 | 0.000 | 0.000 | 0 | 0 | 0 | 0 | 0 | 3 |
| hedef_kitle | 0.000 | 0.000 | 0.000 | 0 | 0 | 0 | 0 | 0 | 3 |
| indirim_orani | 0.000 | 0.000 | 0.000 | 0 | 0 | 0 | 0 | 0 | 3 |
| kampanya_kosullari | 0.000 | 0.000 | 0.000 | 0 | 0 | 0 | 0 | 0 | 3 |
| kampanya_suresi | 1.000 | 1.000 | 1.000 | 1 | 0 | 0 | 0 | 0 | 2 |
| kar_payi_orani | 1.000 | 1.000 | 1.000 | 2 | 0 | 0 | 0 | 0 | 1 |
| masraf_durumu | 1.000 | 1.000 | 1.000 | 2 | 0 | 0 | 0 | 0 | 1 |
| odul_miktari | 0.000 | 0.000 | 0.000 | 0 | 0 | 0 | 0 | 0 | 3 |
| tahsis_ucreti | 1.000 | 1.000 | 1.000 | 1 | 0 | 0 | 0 | 0 | 2 |
| taksit_sayisi | 0.000 | 0.000 | 0.000 | 0 | 0 | 0 | 0 | 0 | 3 |
| vade_ay | 1.000 | 1.000 | 1.000 | 3 | 0 | 0 | 0 | 0 | 0 |

### Kalem düzeyi ölçüt (serbest metin alanları)

Aşağıdaki alanlar cümle listesi döndürür. İkili ölçüt bir alanı **ya tamamen doğru ya tamamen yanlış** sayar: beş koşuldan dördü doğru çıkarılsa bile TP=0. Kalem düzeyi ölçüt her koşulu ayrı sayar (jeton-Jaccard ≥ 0.70, 1-1 açgözlü eşleştirme).

**Manşet mikro-F1 bu tablodan ETKİLENMEZ.** İkili ölçüt manşet olarak kalır; buradaki sayı onun yerine geçmez, yanında durur.

| alan | ölçüt | P | R | F1 | TP | FP | FN |
|---|---|---|---|---|---|---|---|
| `kampanya_kosullari` | ikili | 0.000 | 0.000 | 0.000 | 0 | 0 | 0 |
|  | kalem | 0.000 | 0.000 | 0.000 | 0 | 0 | 0 |

Tüm alanlarda mikro-F1: ikili **1.000** · kalem **1.000**.

#### Eşik duyarlılığı

Eşik sayıya bakılarak seçilmedi. Aşağıdaki tablo, seçilen eşiğin sonucu ne kadar taşıdığını gösterir; taşıyorsa bunu okuyucu bilmelidir.

| jaccard eşiği | kalem mikro-F1 | TP | FP | FN |
|---|---|---|---|---|
| 0.60 | 1.000 | 9 | 0 | 0 |
| 0.70 ← ilan edilen | 1.000 | 9 | 0 | 0 |
| 0.80 | 1.000 | 9 | 0 | 0 |

> **Sonuç eşikten bağımsız çıktı.** Denenen eşiklerin hepsinde aynı sayı üretildi; yani bu korpusta kalemler ya neredeyse birebir örtüşüyor ya hiç örtüşmüyor, arada sınır vaka yok. Eşiğin sonucu taşımadığını söylemek, taşıdığını söylemek kadar raporlanmaya değerdir.

### Zor-vaka etiketi kırılımı

Etiketler çok değerlidir; tablolar ÖRTÜŞÜR.

| etiket | mikro-F1 | makro-F1 | TP | FP | FN |
|---|---|---|---|---|---|
| legacy | 1.000 | 1.000 | 4 | 0 | 0 |
