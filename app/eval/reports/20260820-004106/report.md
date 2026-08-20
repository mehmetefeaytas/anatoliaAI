# Değerlendirme raporu — konfig `llm`

yalnız LLM katmanı (kısıtlı decoding), kural kapalı

## Künye (tekrar-üretim)

| künye | değer |
|---|---|
| konfig | llm |
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
| üretim zamanı (UTC) | 2026-08-20T00:41:06.673122+00:00 |

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
| TÜMÜ | 0.252 | 0.257 | 0.255 | 0.259 | — | 0.058 |
| ZOR (40 belge) | 0.245 | 0.252 | 0.249 | 0.257 | — | 0.074 |
| YAPILANDIRILMIŞ (11 alan) | 0.350 | 0.368 | 0.359 | 0.285 | — | 0.058 |
| ZOR + YAPILANDIRILMIŞ (40 belge) | 0.342 | 0.360 | 0.351 | 0.282 | — | 0.072 |

> **«YAPILANDIRILMIŞ» satırı neyi dışarıda bırakıyor:** `kampanya_kosullari`. Bu alan serbest cümle listesi döndürür; span/jeton eşleşmesiyle F1 ölçmek metodolojik olarak yanlıştır — aynı koşulu farklı sözcüklerle yazan iki anotatör bile birbirini «yanlış» bulurdu. Alan GİZLENMİYOR: aşağıda kendi bölümünde, kalem düzeyi ölçütle raporlanıyor ve iki sayı yan yana duruyor.

### Alan bazında

| alan | P | R | F1 | TP | FP | FN | TN | uydurma | atlanan |
|---|---|---|---|---|---|---|---|---|---|
| alisveris_puani | 0.000 | 0.000 | 0.000 | 0 | 0 | 8 | 38 | 0 | 0 |
| finansman_tutari | 0.000 | 0.000 | 0.000 | 0 | 2 | 4 | 42 | 1 | 0 |
| hedef_kitle | 0.320 | 0.500 | 0.390 | 8 | 17 | 8 | 22 | 9 | 0 |
| indirim_orani | 0.000 | 0.000 | 0.000 | 0 | 1 | 2 | 45 | 0 | 0 |
| kampanya_kosullari | 0.000 | 0.000 | 0.000 | 0 | 31 | 33 | 13 | 1 | 0 |
| kampanya_suresi | 0.391 | 0.391 | 0.391 | 9 | 14 | 14 | 22 | 1 | 0 |
| kar_payi_orani | 0.000 | 0.000 | 0.000 | 0 | 4 | 3 | 41 | 2 | 0 |
| masraf_durumu | 0.200 | 0.200 | 0.200 | 1 | 4 | 4 | 37 | 3 | 0 |
| odul_miktari | 0.364 | 0.800 | 0.500 | 4 | 7 | 1 | 33 | 6 | 0 |
| tahsis_ucreti | 0.000 | 0.000 | 0.000 | 0 | 2 | 0 | 45 | 2 | 0 |
| taksit_sayisi | 1.000 | 0.400 | 0.571 | 2 | 0 | 3 | 42 | 0 | 0 |
| vade_ay | 0.800 | 0.800 | 0.800 | 4 | 1 | 1 | 41 | 1 | 0 |

### Kalem düzeyi ölçüt (serbest metin alanları)

Aşağıdaki alanlar cümle listesi döndürür. İkili ölçüt bir alanı **ya tamamen doğru ya tamamen yanlış** sayar: beş koşuldan dördü doğru çıkarılsa bile TP=0. Kalem düzeyi ölçüt her koşulu ayrı sayar (jeton-Jaccard ≥ 0.70, 1-1 açgözlü eşleştirme).

**Manşet mikro-F1 bu tablodan ETKİLENMEZ.** İkili ölçüt manşet olarak kalır; buradaki sayı onun yerine geçmez, yanında durur.

| alan | ölçüt | P | R | F1 | TP | FP | FN |
|---|---|---|---|---|---|---|---|
| `kampanya_kosullari` | ikili | 0.000 | 0.000 | 0.000 | 0 | 31 | 33 |
|  | kalem | 0.326 | 0.314 | 0.320 | 43 | 89 | 94 |

Tüm alanlarda mikro-F1: ikili **0.255** · kalem **0.348**.

#### Eşik duyarlılığı

Eşik sayıya bakılarak seçilmedi. Aşağıdaki tablo, seçilen eşiğin sonucu ne kadar taşıdığını gösterir; taşıyorsa bunu okuyucu bilmelidir.

| jaccard eşiği | kalem mikro-F1 | TP | FP | FN |
|---|---|---|---|---|
| 0.60 | 0.385 | 83 | 134 | 131 |
| 0.70 ← ilan edilen | 0.348 | 75 | 142 | 139 |
| 0.80 | 0.320 | 69 | 148 | 145 |

### Zor-vaka etiketi kırılımı

Etiketler çok değerlidir; tablolar ÖRTÜŞÜR.

| etiket | mikro-F1 | makro-F1 | TP | FP | FN |
|---|---|---|---|---|---|
| celiskili | 0.154 | 0.190 | 2 | 10 | 12 |
| eksik_bilgi | 0.174 | 0.139 | 2 | 11 | 8 |
| format_varyant | 0.254 | 0.240 | 22 | 64 | 65 |
| kosullu_aralik | 0.277 | 0.205 | 13 | 34 | 34 |
| terminoloji | 0.138 | 0.167 | 4 | 29 | 21 |

## Eşleştirici: `tolerant`

| alt küme | P (mikro) | R (mikro) | F1 (mikro) | F1 (makro) | mikro-F1 %95 GA | halüsinasyon |
|---|---|---|---|---|---|---|
| TÜMÜ | 0.270 | 0.275 | 0.273 | 0.290 | — | 0.058 |
| ZOR (40 belge) | 0.264 | 0.271 | 0.267 | 0.287 | — | 0.074 |
| YAPILANDIRILMIŞ (11 alan) | 0.375 | 0.395 | 0.385 | 0.319 | — | 0.058 |
| ZOR + YAPILANDIRILMIŞ (40 belge) | 0.367 | 0.387 | 0.377 | 0.316 | — | 0.072 |

> **«YAPILANDIRILMIŞ» satırı neyi dışarıda bırakıyor:** `kampanya_kosullari`. Bu alan serbest cümle listesi döndürür; span/jeton eşleşmesiyle F1 ölçmek metodolojik olarak yanlıştır — aynı koşulu farklı sözcüklerle yazan iki anotatör bile birbirini «yanlış» bulurdu. Alan GİZLENMİYOR: aşağıda kendi bölümünde, kalem düzeyi ölçütle raporlanıyor ve iki sayı yan yana duruyor.

### Alan bazında

| alan | P | R | F1 | TP | FP | FN | TN | uydurma | atlanan |
|---|---|---|---|---|---|---|---|---|---|
| alisveris_puani | 0.000 | 0.000 | 0.000 | 0 | 0 | 8 | 38 | 0 | 0 |
| finansman_tutari | 0.000 | 0.000 | 0.000 | 0 | 2 | 4 | 42 | 1 | 0 |
| hedef_kitle | 0.360 | 0.562 | 0.439 | 9 | 16 | 7 | 22 | 9 | 0 |
| indirim_orani | 0.000 | 0.000 | 0.000 | 0 | 1 | 2 | 45 | 0 | 0 |
| kampanya_kosullari | 0.000 | 0.000 | 0.000 | 0 | 31 | 33 | 13 | 1 | 0 |
| kampanya_suresi | 0.391 | 0.391 | 0.391 | 9 | 14 | 14 | 22 | 1 | 0 |
| kar_payi_orani | 0.250 | 0.333 | 0.286 | 1 | 3 | 2 | 41 | 2 | 0 |
| masraf_durumu | 0.200 | 0.200 | 0.200 | 1 | 4 | 4 | 37 | 3 | 0 |
| odul_miktari | 0.364 | 0.800 | 0.500 | 4 | 7 | 1 | 33 | 6 | 0 |
| tahsis_ucreti | 0.000 | 0.000 | 0.000 | 0 | 2 | 0 | 45 | 2 | 0 |
| taksit_sayisi | 1.000 | 0.400 | 0.571 | 2 | 0 | 3 | 42 | 0 | 0 |
| vade_ay | 0.800 | 0.800 | 0.800 | 4 | 1 | 1 | 41 | 1 | 0 |

### Kalem düzeyi ölçüt (serbest metin alanları)

Aşağıdaki alanlar cümle listesi döndürür. İkili ölçüt bir alanı **ya tamamen doğru ya tamamen yanlış** sayar: beş koşuldan dördü doğru çıkarılsa bile TP=0. Kalem düzeyi ölçüt her koşulu ayrı sayar (jeton-Jaccard ≥ 0.70, 1-1 açgözlü eşleştirme).

**Manşet mikro-F1 bu tablodan ETKİLENMEZ.** İkili ölçüt manşet olarak kalır; buradaki sayı onun yerine geçmez, yanında durur.

| alan | ölçüt | P | R | F1 | TP | FP | FN |
|---|---|---|---|---|---|---|---|
| `kampanya_kosullari` | ikili | 0.000 | 0.000 | 0.000 | 0 | 31 | 33 |
|  | kalem | 0.326 | 0.314 | 0.320 | 43 | 89 | 94 |

Tüm alanlarda mikro-F1: ikili **0.273** · kalem **0.353**.

#### Eşik duyarlılığı

Eşik sayıya bakılarak seçilmedi. Aşağıdaki tablo, seçilen eşiğin sonucu ne kadar taşıdığını gösterir; taşıyorsa bunu okuyucu bilmelidir.

| jaccard eşiği | kalem mikro-F1 | TP | FP | FN |
|---|---|---|---|---|
| 0.60 | 0.390 | 84 | 133 | 130 |
| 0.70 ← ilan edilen | 0.353 | 76 | 141 | 138 |
| 0.80 | 0.325 | 70 | 147 | 144 |

### Zor-vaka etiketi kırılımı

Etiketler çok değerlidir; tablolar ÖRTÜŞÜR.

| etiket | mikro-F1 | makro-F1 | TP | FP | FN |
|---|---|---|---|---|---|
| celiskili | 0.154 | 0.190 | 2 | 10 | 12 |
| eksik_bilgi | 0.174 | 0.139 | 2 | 11 | 8 |
| format_varyant | 0.277 | 0.283 | 24 | 62 | 63 |
| kosullu_aralik | 0.298 | 0.250 | 14 | 33 | 33 |
| terminoloji | 0.172 | 0.230 | 5 | 28 | 20 |
