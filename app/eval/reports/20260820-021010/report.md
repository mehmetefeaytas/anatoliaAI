# Değerlendirme raporu — konfig `hibrit`

kural birincil + eksikleri LLM doldurur (API canlı çıkarım ucunun yolu; K-2 ile resmî varsayılan olmaktan çıktı)

## Künye (tekrar-üretim)

| künye | değer |
|---|---|
| konfig | hibrit |
| gold dosyası | data/gold/gold.v2.json |
| gold sha256 | e38a52766cf55e56… |
| gold kayıt sayısı | 48 |
| alt küme (split) | all |
| eşleştirici(ler) | strict, tolerant |
| seed | 42 |
| git sha | 0728bc445d1682cc8c33796347c77be7ceefe30b |
| commit'lenmemiş değişiklik | hayır |
| Python | 3.14.6 |
| platform | macOS-26.5.2-arm64-arm-64bit-Mach-O |
| bağımlılık | yalnız Python stdlib (numpy/scipy/sklearn YOK) |
| üretim zamanı (UTC) | 2026-08-20T02:10:10.427413+00:00 |

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
| TÜMÜ | 0.380 | 0.523 | 0.440 | 0.548 | — | 0.103 |
| ZOR (40 belge) | 0.397 | 0.523 | 0.452 | 0.550 | — | 0.110 |
| YAPILANDIRILMIŞ (11 alan) | 0.518 | 0.750 | 0.613 | 0.602 | — | 0.090 |
| ZOR + YAPILANDIRILMIŞ (40 belge) | 0.528 | 0.747 | 0.619 | 0.605 | — | 0.104 |

> **«YAPILANDIRILMIŞ» satırı neyi dışarıda bırakıyor:** `kampanya_kosullari`. Bu alan serbest cümle listesi döndürür; span/jeton eşleşmesiyle F1 ölçmek metodolojik olarak yanlıştır — aynı koşulu farklı sözcüklerle yazan iki anotatör bile birbirini «yanlış» bulurdu. Alan GİZLENMİYOR: aşağıda kendi bölümünde, kalem düzeyi ölçütle raporlanıyor ve iki sayı yan yana duruyor.

### Alan bazında

| alan | P | R | F1 | TP | FP | FN | TN | uydurma | atlanan |
|---|---|---|---|---|---|---|---|---|---|
| alisveris_puani | 1.000 | 0.625 | 0.769 | 5 | 0 | 3 | 38 | 0 | 0 |
| finansman_tutari | 0.600 | 0.750 | 0.667 | 3 | 2 | 1 | 41 | 2 | 0 |
| hedef_kitle | 0.267 | 0.500 | 0.348 | 8 | 22 | 8 | 17 | 14 | 0 |
| indirim_orani | 0.333 | 0.500 | 0.400 | 1 | 2 | 1 | 43 | 2 | 0 |
| kampanya_kosullari | 0.000 | 0.000 | 0.000 | 0 | 40 | 33 | 7 | 7 | 0 |
| kampanya_suresi | 0.917 | 0.957 | 0.936 | 22 | 2 | 1 | 22 | 1 | 0 |
| kar_payi_orani | 0.400 | 0.667 | 0.500 | 2 | 3 | 1 | 41 | 2 | 0 |
| masraf_durumu | 0.400 | 0.800 | 0.533 | 4 | 6 | 1 | 35 | 5 | 0 |
| odul_miktari | 0.364 | 0.800 | 0.500 | 4 | 7 | 1 | 33 | 6 | 0 |
| tahsis_ucreti | 0.000 | 0.000 | 0.000 | 0 | 3 | 0 | 44 | 3 | 0 |
| taksit_sayisi | 0.833 | 1.000 | 0.909 | 5 | 1 | 0 | 41 | 1 | 0 |
| vade_ay | 0.375 | 0.600 | 0.462 | 3 | 5 | 2 | 39 | 3 | 0 |

### Kalem düzeyi ölçüt (serbest metin alanları)

Aşağıdaki alanlar cümle listesi döndürür. İkili ölçüt bir alanı **ya tamamen doğru ya tamamen yanlış** sayar: beş koşuldan dördü doğru çıkarılsa bile TP=0. Kalem düzeyi ölçüt her koşulu ayrı sayar (jeton-Jaccard ≥ 0.70, 1-1 açgözlü eşleştirme).

**Manşet mikro-F1 bu tablodan ETKİLENMEZ.** İkili ölçüt manşet olarak kalır; buradaki sayı onun yerine geçmez, yanında durur.

| alan | ölçüt | P | R | F1 | TP | FP | FN |
|---|---|---|---|---|---|---|---|
| `kampanya_kosullari` | ikili | 0.000 | 0.000 | 0.000 | 0 | 40 | 33 |
|  | kalem | 0.239 | 0.241 | 0.240 | 33 | 105 | 104 |

Tüm alanlarda mikro-F1: ikili **0.440** · kalem **0.403**.

#### Eşik duyarlılığı

Eşik sayıya bakılarak seçilmedi. Aşağıdaki tablo, seçilen eşiğin sonucu ne kadar taşıdığını gösterir; taşıyorsa bunu okuyucu bilmelidir.

| jaccard eşiği | kalem mikro-F1 | TP | FP | FN |
|---|---|---|---|---|
| 0.60 | 0.424 | 99 | 154 | 115 |
| 0.70 ← ilan edilen | 0.403 | 94 | 159 | 120 |
| 0.80 | 0.385 | 90 | 163 | 124 |

### Zor-vaka etiketi kırılımı

Etiketler çok değerlidir; tablolar ÖRTÜŞÜR.

| etiket | mikro-F1 | makro-F1 | TP | FP | FN |
|---|---|---|---|---|---|
| celiskili | 0.452 | 0.476 | 7 | 10 | 7 |
| eksik_bilgi | 0.250 | 0.444 | 4 | 18 | 6 |
| format_varyant | 0.474 | 0.539 | 46 | 61 | 41 |
| kosullu_aralik | 0.465 | 0.587 | 23 | 29 | 24 |
| terminoloji | 0.387 | 0.502 | 12 | 25 | 13 |

## Eşleştirici: `tolerant`

| alt küme | P (mikro) | R (mikro) | F1 (mikro) | F1 (makro) | mikro-F1 %95 GA | halüsinasyon |
|---|---|---|---|---|---|---|
| TÜMÜ | 0.387 | 0.532 | 0.448 | 0.552 | — | 0.103 |
| ZOR (40 belge) | 0.404 | 0.533 | 0.460 | 0.554 | — | 0.110 |
| YAPILANDIRILMIŞ (11 alan) | 0.527 | 0.763 | 0.624 | 0.607 | — | 0.090 |
| ZOR + YAPILANDIRILMIŞ (40 belge) | 0.538 | 0.760 | 0.630 | 0.610 | — | 0.104 |

> **«YAPILANDIRILMIŞ» satırı neyi dışarıda bırakıyor:** `kampanya_kosullari`. Bu alan serbest cümle listesi döndürür; span/jeton eşleşmesiyle F1 ölçmek metodolojik olarak yanlıştır — aynı koşulu farklı sözcüklerle yazan iki anotatör bile birbirini «yanlış» bulurdu. Alan GİZLENMİYOR: aşağıda kendi bölümünde, kalem düzeyi ölçütle raporlanıyor ve iki sayı yan yana duruyor.

### Alan bazında

| alan | P | R | F1 | TP | FP | FN | TN | uydurma | atlanan |
|---|---|---|---|---|---|---|---|---|---|
| alisveris_puani | 1.000 | 0.625 | 0.769 | 5 | 0 | 3 | 38 | 0 | 0 |
| finansman_tutari | 0.600 | 0.750 | 0.667 | 3 | 2 | 1 | 41 | 2 | 0 |
| hedef_kitle | 0.300 | 0.562 | 0.391 | 9 | 21 | 7 | 17 | 14 | 0 |
| indirim_orani | 0.333 | 0.500 | 0.400 | 1 | 2 | 1 | 43 | 2 | 0 |
| kampanya_kosullari | 0.000 | 0.000 | 0.000 | 0 | 40 | 33 | 7 | 7 | 0 |
| kampanya_suresi | 0.917 | 0.957 | 0.936 | 22 | 2 | 1 | 22 | 1 | 0 |
| kar_payi_orani | 0.400 | 0.667 | 0.500 | 2 | 3 | 1 | 41 | 2 | 0 |
| masraf_durumu | 0.400 | 0.800 | 0.533 | 4 | 6 | 1 | 35 | 5 | 0 |
| odul_miktari | 0.364 | 0.800 | 0.500 | 4 | 7 | 1 | 33 | 6 | 0 |
| tahsis_ucreti | 0.000 | 0.000 | 0.000 | 0 | 3 | 0 | 44 | 3 | 0 |
| taksit_sayisi | 0.833 | 1.000 | 0.909 | 5 | 1 | 0 | 41 | 1 | 0 |
| vade_ay | 0.375 | 0.600 | 0.462 | 3 | 5 | 2 | 39 | 3 | 0 |

### Kalem düzeyi ölçüt (serbest metin alanları)

Aşağıdaki alanlar cümle listesi döndürür. İkili ölçüt bir alanı **ya tamamen doğru ya tamamen yanlış** sayar: beş koşuldan dördü doğru çıkarılsa bile TP=0. Kalem düzeyi ölçüt her koşulu ayrı sayar (jeton-Jaccard ≥ 0.70, 1-1 açgözlü eşleştirme).

**Manşet mikro-F1 bu tablodan ETKİLENMEZ.** İkili ölçüt manşet olarak kalır; buradaki sayı onun yerine geçmez, yanında durur.

| alan | ölçüt | P | R | F1 | TP | FP | FN |
|---|---|---|---|---|---|---|---|
| `kampanya_kosullari` | ikili | 0.000 | 0.000 | 0.000 | 0 | 40 | 33 |
|  | kalem | 0.239 | 0.241 | 0.240 | 33 | 105 | 104 |

Tüm alanlarda mikro-F1: ikili **0.448** · kalem **0.403**.

#### Eşik duyarlılığı

Eşik sayıya bakılarak seçilmedi. Aşağıdaki tablo, seçilen eşiğin sonucu ne kadar taşıdığını gösterir; taşıyorsa bunu okuyucu bilmelidir.

| jaccard eşiği | kalem mikro-F1 | TP | FP | FN |
|---|---|---|---|---|
| 0.60 | 0.424 | 99 | 154 | 115 |
| 0.70 ← ilan edilen | 0.403 | 94 | 159 | 120 |
| 0.80 | 0.385 | 90 | 163 | 124 |

### Zor-vaka etiketi kırılımı

Etiketler çok değerlidir; tablolar ÖRTÜŞÜR.

| etiket | mikro-F1 | makro-F1 | TP | FP | FN |
|---|---|---|---|---|---|
| celiskili | 0.452 | 0.476 | 7 | 10 | 7 |
| eksik_bilgi | 0.250 | 0.444 | 4 | 18 | 6 |
| format_varyant | 0.485 | 0.544 | 47 | 60 | 40 |
| kosullu_aralik | 0.465 | 0.587 | 23 | 29 | 24 |
| terminoloji | 0.387 | 0.502 | 12 | 25 | 13 |
