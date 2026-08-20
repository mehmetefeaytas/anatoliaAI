# Değerlendirme raporu — konfig `kural`

yalnız kural katmanı (regex + normalizasyon), LLM kapalı — RESMÎ VARSAYILAN (K-2)

## Künye (tekrar-üretim)

| künye | değer |
|---|---|
| konfig | kural |
| gold dosyası | data/gold/gold.v2.json |
| gold sha256 | e38a52766cf55e56… |
| gold kayıt sayısı | 48 |
| alt küme (split) | all |
| eşleştirici(ler) | strict, tolerant |
| seed | 42 |
| git sha | 42ea6f23d0664fa0613170fa97a3fca435acb38e |
| commit'lenmemiş değişiklik | EVET (dikkat: sayı bir commit'e karşılık gelmiyor) |
| Python | 3.14.6 |
| platform | macOS-26.5.2-arm64-arm-64bit-Mach-O |
| bağımlılık | yalnız Python stdlib (numpy/scipy/sklearn YOK) |
| üretim zamanı (UTC) | 2026-08-20T10:14:34.688388+00:00 |

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
| TÜMÜ | 0.496 | 0.532 | 0.513 | 0.658 | 0.513 [0.448–0.568] | 0.040 |
| ZOR (40 belge) | 0.528 | 0.533 | 0.530 | 0.665 | — | 0.031 |
| YAPILANDIRILMIŞ (11 alan) | 0.725 | 0.763 | 0.744 | 0.723 | — | 0.032 |
| ZOR + YAPILANDIRILMIŞ (40 belge) | 0.760 | 0.760 | 0.760 | 0.732 | — | 0.029 |

> **«YAPILANDIRILMIŞ» satırı neyi dışarıda bırakıyor:** `kampanya_kosullari`. Bu alan serbest cümle listesi döndürür; span/jeton eşleşmesiyle F1 ölçmek metodolojik olarak yanlıştır — aynı koşulu farklı sözcüklerle yazan iki anotatör bile birbirini «yanlış» bulurdu. Alan GİZLENMİYOR: aşağıda kendi bölümünde, kalem düzeyi ölçütle raporlanıyor ve iki sayı yan yana duruyor.

### Alan bazında

| alan | P | R | F1 | TP | FP | FN | TN | uydurma | atlanan |
|---|---|---|---|---|---|---|---|---|---|
| alisveris_puani | 1.000 | 0.500 | 0.667 | 4 | 0 | 4 | 38 | 0 | 0 |
| finansman_tutari | 1.000 | 0.750 | 0.857 | 3 | 0 | 1 | 43 | 0 | 0 |
| hedef_kitle | 0.526 | 0.625 | 0.571 | 10 | 9 | 6 | 25 | 6 | 0 |
| indirim_orani | 1.000 | 0.500 | 0.667 | 1 | 0 | 1 | 45 | 0 | 0 |
| kampanya_kosullari | 0.000 | 0.000 | 0.000 | 0 | 37 | 33 | 10 | 4 | 0 |
| kampanya_suresi | 0.917 | 0.957 | 0.936 | 22 | 2 | 1 | 22 | 1 | 0 |
| kar_payi_orani | 1.000 | 0.667 | 0.800 | 2 | 0 | 1 | 43 | 0 | 0 |
| masraf_durumu | 0.571 | 0.800 | 0.667 | 4 | 3 | 1 | 38 | 2 | 0 |
| odul_miktari | 0.500 | 0.800 | 0.615 | 4 | 4 | 1 | 36 | 3 | 0 |
| tahsis_ucreti | 0.000 | 0.000 | 0.000 | 0 | 0 | 0 | 47 | 0 | 0 |
| taksit_sayisi | 0.833 | 1.000 | 0.909 | 5 | 1 | 0 | 41 | 1 | 0 |
| vade_ay | 0.500 | 0.600 | 0.545 | 3 | 3 | 2 | 41 | 1 | 0 |

### Kalem düzeyi ölçüt (serbest metin alanları)

Aşağıdaki alanlar cümle listesi döndürür. İkili ölçüt bir alanı **ya tamamen doğru ya tamamen yanlış** sayar: beş koşuldan dördü doğru çıkarılsa bile TP=0. Kalem düzeyi ölçüt her koşulu ayrı sayar (jeton-Jaccard ≥ 0.70, 1-1 açgözlü eşleştirme).

**Manşet mikro-F1 bu tablodan ETKİLENMEZ.** İkili ölçüt manşet olarak kalır; buradaki sayı onun yerine geçmez, yanında durur.

| alan | ölçüt | P | R | F1 | TP | FP | FN |
|---|---|---|---|---|---|---|---|
| `kampanya_kosullari` | ikili | 0.000 | 0.000 | 0.000 | 0 | 37 | 33 |
|  | kalem | 0.479 | 0.569 | 0.520 | 78 | 85 | 59 |

Tüm alanlarda mikro-F1: ikili **0.513** · kalem **0.601**.

#### Eşik duyarlılığı

Eşik sayıya bakılarak seçilmedi. Aşağıdaki tablo, seçilen eşiğin sonucu ne kadar taşıdığını gösterir; taşıyorsa bunu okuyucu bilmelidir.

| jaccard eşiği | kalem mikro-F1 | TP | FP | FN |
|---|---|---|---|---|
| 0.60 | 0.632 | 145 | 100 | 69 |
| 0.70 ← ilan edilen | 0.601 | 138 | 107 | 76 |
| 0.80 | 0.571 | 131 | 114 | 83 |

### Zor-vaka etiketi kırılımı

Etiketler çok değerlidir; tablolar ÖRTÜŞÜR.

| etiket | mikro-F1 | makro-F1 | TP | FP | FN |
|---|---|---|---|---|---|
| celiskili | 0.500 | 0.524 | 7 | 7 | 7 |
| eksik_bilgi | 0.417 | 0.567 | 5 | 9 | 5 |
| format_varyant | 0.547 | 0.615 | 47 | 38 | 40 |
| kosullu_aralik | 0.549 | 0.694 | 25 | 19 | 22 |
| terminoloji | 0.480 | 0.642 | 12 | 13 | 13 |

## Eşleştirici: `tolerant`

| alt küme | P (mikro) | R (mikro) | F1 (mikro) | F1 (makro) | mikro-F1 %95 GA | halüsinasyon |
|---|---|---|---|---|---|---|
| TÜMÜ | 0.538 | 0.578 | 0.558 | 0.671 | 0.558 [0.479–0.636] | 0.040 |
| ZOR (40 belge) | 0.574 | 0.579 | 0.577 | 0.679 | — | 0.031 |
| YAPILANDIRILMIŞ (11 alan) | 0.725 | 0.763 | 0.744 | 0.723 | — | 0.032 |
| ZOR + YAPILANDIRILMIŞ (40 belge) | 0.760 | 0.760 | 0.760 | 0.732 | — | 0.029 |

> **«YAPILANDIRILMIŞ» satırı neyi dışarıda bırakıyor:** `kampanya_kosullari`. Bu alan serbest cümle listesi döndürür; span/jeton eşleşmesiyle F1 ölçmek metodolojik olarak yanlıştır — aynı koşulu farklı sözcüklerle yazan iki anotatör bile birbirini «yanlış» bulurdu. Alan GİZLENMİYOR: aşağıda kendi bölümünde, kalem düzeyi ölçütle raporlanıyor ve iki sayı yan yana duruyor.

### Alan bazında

| alan | P | R | F1 | TP | FP | FN | TN | uydurma | atlanan |
|---|---|---|---|---|---|---|---|---|---|
| alisveris_puani | 1.000 | 0.500 | 0.667 | 4 | 0 | 4 | 38 | 0 | 0 |
| finansman_tutari | 1.000 | 0.750 | 0.857 | 3 | 0 | 1 | 43 | 0 | 0 |
| hedef_kitle | 0.526 | 0.625 | 0.571 | 10 | 9 | 6 | 25 | 6 | 0 |
| indirim_orani | 1.000 | 0.500 | 0.667 | 1 | 0 | 1 | 45 | 0 | 0 |
| kampanya_kosullari | 0.135 | 0.152 | 0.143 | 5 | 32 | 28 | 10 | 4 | 0 |
| kampanya_suresi | 0.917 | 0.957 | 0.936 | 22 | 2 | 1 | 22 | 1 | 0 |
| kar_payi_orani | 1.000 | 0.667 | 0.800 | 2 | 0 | 1 | 43 | 0 | 0 |
| masraf_durumu | 0.571 | 0.800 | 0.667 | 4 | 3 | 1 | 38 | 2 | 0 |
| odul_miktari | 0.500 | 0.800 | 0.615 | 4 | 4 | 1 | 36 | 3 | 0 |
| tahsis_ucreti | 0.000 | 0.000 | 0.000 | 0 | 0 | 0 | 47 | 0 | 0 |
| taksit_sayisi | 0.833 | 1.000 | 0.909 | 5 | 1 | 0 | 41 | 1 | 0 |
| vade_ay | 0.500 | 0.600 | 0.545 | 3 | 3 | 2 | 41 | 1 | 0 |

### Kalem düzeyi ölçüt (serbest metin alanları)

Aşağıdaki alanlar cümle listesi döndürür. İkili ölçüt bir alanı **ya tamamen doğru ya tamamen yanlış** sayar: beş koşuldan dördü doğru çıkarılsa bile TP=0. Kalem düzeyi ölçüt her koşulu ayrı sayar (jeton-Jaccard ≥ 0.70, 1-1 açgözlü eşleştirme).

**Manşet mikro-F1 bu tablodan ETKİLENMEZ.** İkili ölçüt manşet olarak kalır; buradaki sayı onun yerine geçmez, yanında durur.

| alan | ölçüt | P | R | F1 | TP | FP | FN |
|---|---|---|---|---|---|---|---|
| `kampanya_kosullari` | ikili | 0.135 | 0.152 | 0.143 | 5 | 32 | 28 |
|  | kalem | 0.479 | 0.569 | 0.520 | 78 | 85 | 59 |

Tüm alanlarda mikro-F1: ikili **0.558** · kalem **0.601**.

#### Eşik duyarlılığı

Eşik sayıya bakılarak seçilmedi. Aşağıdaki tablo, seçilen eşiğin sonucu ne kadar taşıdığını gösterir; taşıyorsa bunu okuyucu bilmelidir.

| jaccard eşiği | kalem mikro-F1 | TP | FP | FN |
|---|---|---|---|---|
| 0.60 | 0.632 | 145 | 100 | 69 |
| 0.70 ← ilan edilen | 0.601 | 138 | 107 | 76 |
| 0.80 | 0.571 | 131 | 114 | 83 |

### Zor-vaka etiketi kırılımı

Etiketler çok değerlidir; tablolar ÖRTÜŞÜR.

| etiket | mikro-F1 | makro-F1 | TP | FP | FN |
|---|---|---|---|---|---|
| celiskili | 0.571 | 0.560 | 8 | 6 | 6 |
| eksik_bilgi | 0.417 | 0.567 | 5 | 9 | 5 |
| format_varyant | 0.605 | 0.633 | 52 | 33 | 35 |
| kosullu_aralik | 0.549 | 0.694 | 25 | 19 | 22 |
| terminoloji | 0.520 | 0.656 | 13 | 12 | 12 |
