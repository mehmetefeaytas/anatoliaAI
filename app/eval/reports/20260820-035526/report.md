# Değerlendirme raporu — konfig `hibrit-verify`

hibrit + düşük güvenli KURAL alanlarını LLM doğrular (reconcile.verify_low_conf) (eşik=0.75)

## Künye (tekrar-üretim)

| künye | değer |
|---|---|
| konfig | hibrit-verify |
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
| üretim zamanı (UTC) | 2026-08-20T03:55:26.695949+00:00 |

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
| TÜMÜ | 0.320 | 0.431 | 0.367 | 0.539 | — | 0.098 |
| ZOR (40 belge) | 0.333 | 0.430 | 0.376 | 0.542 | — | 0.105 |
| YAPILANDIRILMIŞ (11 alan) | 0.439 | 0.618 | 0.514 | 0.592 | — | 0.085 |
| ZOR + YAPILANDIRILMIŞ (40 belge) | 0.447 | 0.613 | 0.517 | 0.597 | — | 0.098 |

> **«YAPILANDIRILMIŞ» satırı neyi dışarıda bırakıyor:** `kampanya_kosullari`. Bu alan serbest cümle listesi döndürür; span/jeton eşleşmesiyle F1 ölçmek metodolojik olarak yanlıştır — aynı koşulu farklı sözcüklerle yazan iki anotatör bile birbirini «yanlış» bulurdu. Alan GİZLENMİYOR: aşağıda kendi bölümünde, kalem düzeyi ölçütle raporlanıyor ve iki sayı yan yana duruyor.

### Alan bazında

| alan | P | R | F1 | TP | FP | FN | TN | uydurma | atlanan |
|---|---|---|---|---|---|---|---|---|---|
| alisveris_puani | 1.000 | 0.500 | 0.667 | 4 | 0 | 4 | 38 | 0 | 0 |
| finansman_tutari | 0.750 | 0.750 | 0.750 | 3 | 1 | 1 | 42 | 1 | 0 |
| hedef_kitle | 0.200 | 0.375 | 0.261 | 6 | 24 | 10 | 17 | 14 | 0 |
| indirim_orani | 0.500 | 0.500 | 0.500 | 1 | 1 | 1 | 44 | 1 | 0 |
| kampanya_kosullari | 0.000 | 0.000 | 0.000 | 0 | 40 | 33 | 7 | 7 | 0 |
| kampanya_suresi | 0.542 | 0.565 | 0.553 | 13 | 11 | 10 | 22 | 1 | 0 |
| kar_payi_orani | 0.333 | 0.667 | 0.444 | 2 | 4 | 1 | 40 | 3 | 0 |
| masraf_durumu | 0.444 | 0.800 | 0.571 | 4 | 5 | 1 | 36 | 4 | 0 |
| odul_miktari | 0.364 | 0.800 | 0.500 | 4 | 7 | 1 | 33 | 6 | 0 |
| tahsis_ucreti | 0.000 | 0.000 | 0.000 | 0 | 3 | 0 | 44 | 3 | 0 |
| taksit_sayisi | 0.833 | 1.000 | 0.909 | 5 | 1 | 0 | 41 | 1 | 0 |
| vade_ay | 0.625 | 1.000 | 0.769 | 5 | 3 | 0 | 39 | 3 | 0 |

### Kalem düzeyi ölçüt (serbest metin alanları)

Aşağıdaki alanlar cümle listesi döndürür. İkili ölçüt bir alanı **ya tamamen doğru ya tamamen yanlış** sayar: beş koşuldan dördü doğru çıkarılsa bile TP=0. Kalem düzeyi ölçüt her koşulu ayrı sayar (jeton-Jaccard ≥ 0.70, 1-1 açgözlü eşleştirme).

**Manşet mikro-F1 bu tablodan ETKİLENMEZ.** İkili ölçüt manşet olarak kalır; buradaki sayı onun yerine geçmez, yanında durur.

| alan | ölçüt | P | R | F1 | TP | FP | FN |
|---|---|---|---|---|---|---|---|
| `kampanya_kosullari` | ikili | 0.000 | 0.000 | 0.000 | 0 | 40 | 33 |
|  | kalem | 0.232 | 0.212 | 0.221 | 29 | 96 | 108 |

Tüm alanlarda mikro-F1: ikili **0.367** · kalem **0.362**.

#### Eşik duyarlılığı

Eşik sayıya bakılarak seçilmedi. Aşağıdaki tablo, seçilen eşiğin sonucu ne kadar taşıdığını gösterir; taşıyorsa bunu okuyucu bilmelidir.

| jaccard eşiği | kalem mikro-F1 | TP | FP | FN |
|---|---|---|---|---|
| 0.60 | 0.375 | 85 | 154 | 129 |
| 0.70 ← ilan edilen | 0.362 | 82 | 157 | 132 |
| 0.80 | 0.358 | 81 | 158 | 133 |

### Zor-vaka etiketi kırılımı

Etiketler çok değerlidir; tablolar ÖRTÜŞÜR.

| etiket | mikro-F1 | makro-F1 | TP | FP | FN |
|---|---|---|---|---|---|
| celiskili | 0.387 | 0.429 | 6 | 11 | 8 |
| eksik_bilgi | 0.276 | 0.583 | 4 | 15 | 6 |
| format_varyant | 0.402 | 0.538 | 38 | 64 | 49 |
| kosullu_aralik | 0.449 | 0.615 | 22 | 29 | 25 |
| terminoloji | 0.312 | 0.434 | 10 | 29 | 15 |

## Eşleştirici: `tolerant`

| alt küme | P (mikro) | R (mikro) | F1 (mikro) | F1 (makro) | mikro-F1 %95 GA | halüsinasyon |
|---|---|---|---|---|---|---|
| TÜMÜ | 0.327 | 0.440 | 0.375 | 0.543 | — | 0.098 |
| ZOR (40 belge) | 0.341 | 0.439 | 0.384 | 0.547 | — | 0.105 |
| YAPILANDIRILMIŞ (11 alan) | 0.449 | 0.632 | 0.525 | 0.597 | — | 0.085 |
| ZOR + YAPILANDIRILMIŞ (40 belge) | 0.456 | 0.627 | 0.528 | 0.601 | — | 0.098 |

> **«YAPILANDIRILMIŞ» satırı neyi dışarıda bırakıyor:** `kampanya_kosullari`. Bu alan serbest cümle listesi döndürür; span/jeton eşleşmesiyle F1 ölçmek metodolojik olarak yanlıştır — aynı koşulu farklı sözcüklerle yazan iki anotatör bile birbirini «yanlış» bulurdu. Alan GİZLENMİYOR: aşağıda kendi bölümünde, kalem düzeyi ölçütle raporlanıyor ve iki sayı yan yana duruyor.

### Alan bazında

| alan | P | R | F1 | TP | FP | FN | TN | uydurma | atlanan |
|---|---|---|---|---|---|---|---|---|---|
| alisveris_puani | 1.000 | 0.500 | 0.667 | 4 | 0 | 4 | 38 | 0 | 0 |
| finansman_tutari | 0.750 | 0.750 | 0.750 | 3 | 1 | 1 | 42 | 1 | 0 |
| hedef_kitle | 0.233 | 0.438 | 0.304 | 7 | 23 | 9 | 17 | 14 | 0 |
| indirim_orani | 0.500 | 0.500 | 0.500 | 1 | 1 | 1 | 44 | 1 | 0 |
| kampanya_kosullari | 0.000 | 0.000 | 0.000 | 0 | 40 | 33 | 7 | 7 | 0 |
| kampanya_suresi | 0.542 | 0.565 | 0.553 | 13 | 11 | 10 | 22 | 1 | 0 |
| kar_payi_orani | 0.333 | 0.667 | 0.444 | 2 | 4 | 1 | 40 | 3 | 0 |
| masraf_durumu | 0.444 | 0.800 | 0.571 | 4 | 5 | 1 | 36 | 4 | 0 |
| odul_miktari | 0.364 | 0.800 | 0.500 | 4 | 7 | 1 | 33 | 6 | 0 |
| tahsis_ucreti | 0.000 | 0.000 | 0.000 | 0 | 3 | 0 | 44 | 3 | 0 |
| taksit_sayisi | 0.833 | 1.000 | 0.909 | 5 | 1 | 0 | 41 | 1 | 0 |
| vade_ay | 0.625 | 1.000 | 0.769 | 5 | 3 | 0 | 39 | 3 | 0 |

### Kalem düzeyi ölçüt (serbest metin alanları)

Aşağıdaki alanlar cümle listesi döndürür. İkili ölçüt bir alanı **ya tamamen doğru ya tamamen yanlış** sayar: beş koşuldan dördü doğru çıkarılsa bile TP=0. Kalem düzeyi ölçüt her koşulu ayrı sayar (jeton-Jaccard ≥ 0.70, 1-1 açgözlü eşleştirme).

**Manşet mikro-F1 bu tablodan ETKİLENMEZ.** İkili ölçüt manşet olarak kalır; buradaki sayı onun yerine geçmez, yanında durur.

| alan | ölçüt | P | R | F1 | TP | FP | FN |
|---|---|---|---|---|---|---|---|
| `kampanya_kosullari` | ikili | 0.000 | 0.000 | 0.000 | 0 | 40 | 33 |
|  | kalem | 0.232 | 0.212 | 0.221 | 29 | 96 | 108 |

Tüm alanlarda mikro-F1: ikili **0.375** · kalem **0.362**.

#### Eşik duyarlılığı

Eşik sayıya bakılarak seçilmedi. Aşağıdaki tablo, seçilen eşiğin sonucu ne kadar taşıdığını gösterir; taşıyorsa bunu okuyucu bilmelidir.

| jaccard eşiği | kalem mikro-F1 | TP | FP | FN |
|---|---|---|---|---|
| 0.60 | 0.375 | 85 | 154 | 129 |
| 0.70 ← ilan edilen | 0.362 | 82 | 157 | 132 |
| 0.80 | 0.358 | 81 | 158 | 133 |

### Zor-vaka etiketi kırılımı

Etiketler çok değerlidir; tablolar ÖRTÜŞÜR.

| etiket | mikro-F1 | makro-F1 | TP | FP | FN |
|---|---|---|---|---|---|
| celiskili | 0.387 | 0.429 | 6 | 11 | 8 |
| eksik_bilgi | 0.276 | 0.583 | 4 | 15 | 6 |
| format_varyant | 0.413 | 0.544 | 39 | 63 | 48 |
| kosullu_aralik | 0.449 | 0.615 | 22 | 29 | 25 |
| terminoloji | 0.312 | 0.434 | 10 | 29 | 15 |
