# Değerlendirme raporu — konfig `kural`

yalnız kural katmanı (regex + normalizasyon), LLM kapalı — RESMÎ VARSAYILAN (K-2)

## Künye (tekrar-üretim)

| künye | değer |
|---|---|
| konfig | kural |
| gold dosyası | /private/tmp/claude-501/-Users-mehmetefeaytas-anatoliaaI/d98fb2a0-f3f4-4dee-bc33-bc61256c5e34/scratchpad/gold.v2.ngram.json |
| gold sha256 | fe2734d399e4f2f4… |
| gold kayıt sayısı | 48 |
| alt küme (split) | all |
| eşleştirici(ler) | strict, tolerant |
| seed | 42 |
| git sha | 670c91103145aa930ab3fa48d4dd2c3ec189b84e |
| commit'lenmemiş değişiklik | EVET (dikkat: sayı bir commit'e karşılık gelmiyor) |
| Python | 3.14.6 |
| platform | macOS-26.5.2-arm64-arm-64bit-Mach-O |
| bağımlılık | yalnız Python stdlib (numpy/scipy/sklearn YOK) |
| üretim zamanı (UTC) | 2026-08-07T15:30:37.374036+00:00 |

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
| TÜMÜ | 0.373 | 0.366 | 0.369 | 0.434 | 0.369 [0.304–0.427] | 0.070 |
| ZOR (40 belge) | 0.406 | 0.373 | 0.389 | 0.439 | — | 0.066 |

### Alan bazında

| alan | P | R | F1 | TP | FP | FN | TN | uydurma | atlanan |
|---|---|---|---|---|---|---|---|---|---|
| alisveris_puani | 1.000 | 0.500 | 0.667 | 4 | 0 | 4 | 38 | 0 | 0 |
| finansman_tutari | 0.222 | 0.500 | 0.308 | 2 | 7 | 2 | 37 | 6 | 0 |
| hedef_kitle | 0.400 | 0.222 | 0.286 | 4 | 6 | 14 | 24 | 5 | 0 |
| indirim_orani | 0.000 | 0.000 | 0.000 | 0 | 1 | 2 | 45 | 0 | 0 |
| kampanya_kosullari | 0.000 | 0.000 | 0.000 | 0 | 33 | 33 | 8 | 6 | 0 |
| kampanya_suresi | 0.833 | 0.652 | 0.732 | 15 | 3 | 8 | 22 | 1 | 0 |
| kar_payi_orani | 1.000 | 0.333 | 0.500 | 1 | 0 | 2 | 43 | 0 | 0 |
| masraf_durumu | 0.625 | 0.833 | 0.714 | 5 | 3 | 1 | 37 | 2 | 0 |
| odul_miktari | 0.364 | 0.800 | 0.500 | 4 | 7 | 1 | 33 | 6 | 0 |
| tahsis_ucreti | 0.000 | 0.000 | 0.000 | 0 | 1 | 0 | 46 | 1 | 0 |
| taksit_sayisi | 0.833 | 1.000 | 0.909 | 5 | 1 | 0 | 41 | 1 | 0 |
| vade_ay | 0.125 | 0.200 | 0.154 | 1 | 7 | 4 | 39 | 3 | 0 |

### Zor-vaka etiketi kırılımı

Etiketler çok değerlidir; tablolar ÖRTÜŞÜR.

| etiket | mikro-F1 | makro-F1 | TP | FP | FN |
|---|---|---|---|---|---|
| celiskili | 0.385 | 0.305 | 5 | 6 | 10 |
| eksik_bilgi | 0.273 | 0.417 | 3 | 9 | 7 |
| format_varyant | 0.400 | 0.455 | 33 | 43 | 56 |
| kosullu_aralik | 0.370 | 0.455 | 17 | 26 | 32 |
| terminoloji | 0.314 | 0.323 | 8 | 16 | 19 |

## Eşleştirici: `tolerant`

| alt küme | P (mikro) | R (mikro) | F1 (mikro) | F1 (makro) | mikro-F1 %95 GA | halüsinasyon |
|---|---|---|---|---|---|---|
| TÜMÜ | 0.382 | 0.375 | 0.378 | 0.494 | 0.378 [0.312–0.438] | 0.070 |
| ZOR (40 belge) | 0.416 | 0.382 | 0.398 | 0.500 | — | 0.066 |

### Alan bazında

| alan | P | R | F1 | TP | FP | FN | TN | uydurma | atlanan |
|---|---|---|---|---|---|---|---|---|---|
| alisveris_puani | 1.000 | 0.500 | 0.667 | 4 | 0 | 4 | 38 | 0 | 0 |
| finansman_tutari | 0.222 | 0.500 | 0.308 | 2 | 7 | 2 | 37 | 6 | 0 |
| hedef_kitle | 0.400 | 0.222 | 0.286 | 4 | 6 | 14 | 24 | 5 | 0 |
| indirim_orani | 1.000 | 0.500 | 0.667 | 1 | 0 | 1 | 45 | 0 | 0 |
| kampanya_kosullari | 0.000 | 0.000 | 0.000 | 0 | 33 | 33 | 8 | 6 | 0 |
| kampanya_suresi | 0.833 | 0.652 | 0.732 | 15 | 3 | 8 | 22 | 1 | 0 |
| kar_payi_orani | 1.000 | 0.333 | 0.500 | 1 | 0 | 2 | 43 | 0 | 0 |
| masraf_durumu | 0.625 | 0.833 | 0.714 | 5 | 3 | 1 | 37 | 2 | 0 |
| odul_miktari | 0.364 | 0.800 | 0.500 | 4 | 7 | 1 | 33 | 6 | 0 |
| tahsis_ucreti | 0.000 | 0.000 | 0.000 | 0 | 1 | 0 | 46 | 1 | 0 |
| taksit_sayisi | 0.833 | 1.000 | 0.909 | 5 | 1 | 0 | 41 | 1 | 0 |
| vade_ay | 0.125 | 0.200 | 0.154 | 1 | 7 | 4 | 39 | 3 | 0 |

### Zor-vaka etiketi kırılımı

Etiketler çok değerlidir; tablolar ÖRTÜŞÜR.

| etiket | mikro-F1 | makro-F1 | TP | FP | FN |
|---|---|---|---|---|---|
| celiskili | 0.385 | 0.305 | 5 | 6 | 10 |
| eksik_bilgi | 0.273 | 0.417 | 3 | 9 | 7 |
| format_varyant | 0.400 | 0.455 | 33 | 43 | 56 |
| kosullu_aralik | 0.391 | 0.546 | 18 | 25 | 31 |
| terminoloji | 0.353 | 0.448 | 9 | 15 | 18 |
