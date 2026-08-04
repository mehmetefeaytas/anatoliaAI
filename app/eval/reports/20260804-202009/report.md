# Değerlendirme raporu — konfig `kural`

yalnız kural katmanı (regex + normalizasyon), LLM kapalı

## Künye (tekrar-üretim)

| künye | değer |
|---|---|
| konfig | kural |
| gold dosyası | data/gold/gold.v1.json |
| gold sha256 | ea04e44475521057… |
| gold kayıt sayısı | 20 |
| alt küme (split) | all |
| eşleştirici(ler) | strict, tolerant |
| seed | 42 |
| git sha | 28f8246f3a2be7fb2b906f29f80a1ade13959588 |
| commit'lenmemiş değişiklik | EVET (dikkat: sayı bir commit'e karşılık gelmiyor) |
| Python | 3.14.6 |
| platform | macOS-26.5.2-arm64-arm-64bit-Mach-O |
| bağımlılık | yalnız Python stdlib (numpy/scipy/sklearn YOK) |
| üretim zamanı (UTC) | 2026-08-04T20:20:09.766816+00:00 |

## Metrik tanımları

- **TP**: gold'da değer var, tahmin eşleşti.
- **FP**: tahmin var ama yanlış (`fp_wrong`) ya da gold "YOK" diyor (`fp_hallucinated`).
- **FN**: gold'da değer var, tahmin yok ya da yanlış.
- **TN**: gold "YOK" diyor, model de üretmedi (doğru çekimserlik).
- **ATL (atlanan)**: gold bu alan hakkında KARAR VERMEMİŞ — metriğe girmez. Bilmediğimizi lehimize saymıyoruz.
- **halüsinasyon oranı** = `fp_hallucinated / (tn + fp_hallucinated)`; gold'da hiç `absent_fields` kararı yoksa TANIMSIZDIR (0,0 yazmak yalan olurdu).
- **makro-F1**: alanların F1 ortalaması (yalnız gold desteği olan alanlar). Mikro seyrek alanları gizler, makro gizlemez.
- **%95 GA**: belge düzeyinde küme bootstrap. Aynı belgeden çıkan 12 alan bağımsız değildir; alan düzeyinde örneklemek GA'yı yapay olarak daraltır (bkz. `eval/stats.py`).

## Eşleştirici: `strict`

| alt küme | P (mikro) | R (mikro) | F1 (mikro) | F1 (makro) | mikro-F1 %95 GA | halüsinasyon |
|---|---|---|---|---|---|---|
| TÜMÜ | 0.557 | 0.600 | 0.578 | 0.523 | 0.578 [0.423–0.692] | 0.114 |
| ZOR (1 belge) | 0.667 | 0.667 | 0.667 | 0.667 | — | 0.000 |

### Alan bazında

| alan | P | R | F1 | TP | FP | FN | TN | uydurma | atlanan |
|---|---|---|---|---|---|---|---|---|---|
| alisveris_puani | 0.000 | 0.000 | 0.000 | 0 | 2 | 1 | 17 | 2 | 0 |
| finansman_tutari | 0.000 | 0.000 | 0.000 | 0 | 3 | 6 | 13 | 0 | 0 |
| hedef_kitle | 0.667 | 0.800 | 0.727 | 4 | 2 | 1 | 13 | 2 | 0 |
| indirim_orani | 1.000 | 1.000 | 1.000 | 1 | 0 | 0 | 19 | 0 | 0 |
| kampanya_kosullari | 0.611 | 0.917 | 0.733 | 11 | 7 | 1 | 1 | 7 | 0 |
| kampanya_suresi | 0.286 | 0.333 | 0.308 | 2 | 5 | 4 | 13 | 1 | 0 |
| kar_payi_orani | 0.600 | 0.750 | 0.667 | 3 | 2 | 1 | 12 | 2 | 0 |
| masraf_durumu | 0.857 | 0.857 | 0.857 | 6 | 1 | 1 | 13 | 0 | 0 |
| odul_miktari | 0.500 | 0.333 | 0.400 | 1 | 1 | 2 | 16 | 1 | 0 |
| tahsis_ucreti | 0.333 | 0.500 | 0.400 | 1 | 2 | 1 | 15 | 2 | 0 |
| taksit_sayisi | 1.000 | 0.429 | 0.600 | 3 | 0 | 4 | 10 | 0 | 0 |
| vade_ay | 0.538 | 0.636 | 0.583 | 7 | 6 | 4 | 5 | 2 | 0 |

### Zor-vaka etiketi kırılımı

Etiketler çok değerlidir; tablolar ÖRTÜŞÜR.

| etiket | mikro-F1 | makro-F1 | TP | FP | FN |
|---|---|---|---|---|---|
| kosullu_aralik | 0.667 | 0.667 | 2 | 1 | 1 |

## Eşleştirici: `tolerant`

| alt küme | P (mikro) | R (mikro) | F1 (mikro) | F1 (makro) | mikro-F1 %95 GA | halüsinasyon |
|---|---|---|---|---|---|---|
| TÜMÜ | 0.557 | 0.600 | 0.578 | 0.523 | 0.578 [0.423–0.692] | 0.114 |
| ZOR (1 belge) | 0.667 | 0.667 | 0.667 | 0.667 | — | 0.000 |

### Alan bazında

| alan | P | R | F1 | TP | FP | FN | TN | uydurma | atlanan |
|---|---|---|---|---|---|---|---|---|---|
| alisveris_puani | 0.000 | 0.000 | 0.000 | 0 | 2 | 1 | 17 | 2 | 0 |
| finansman_tutari | 0.000 | 0.000 | 0.000 | 0 | 3 | 6 | 13 | 0 | 0 |
| hedef_kitle | 0.667 | 0.800 | 0.727 | 4 | 2 | 1 | 13 | 2 | 0 |
| indirim_orani | 1.000 | 1.000 | 1.000 | 1 | 0 | 0 | 19 | 0 | 0 |
| kampanya_kosullari | 0.611 | 0.917 | 0.733 | 11 | 7 | 1 | 1 | 7 | 0 |
| kampanya_suresi | 0.286 | 0.333 | 0.308 | 2 | 5 | 4 | 13 | 1 | 0 |
| kar_payi_orani | 0.600 | 0.750 | 0.667 | 3 | 2 | 1 | 12 | 2 | 0 |
| masraf_durumu | 0.857 | 0.857 | 0.857 | 6 | 1 | 1 | 13 | 0 | 0 |
| odul_miktari | 0.500 | 0.333 | 0.400 | 1 | 1 | 2 | 16 | 1 | 0 |
| tahsis_ucreti | 0.333 | 0.500 | 0.400 | 1 | 2 | 1 | 15 | 2 | 0 |
| taksit_sayisi | 1.000 | 0.429 | 0.600 | 3 | 0 | 4 | 10 | 0 | 0 |
| vade_ay | 0.538 | 0.636 | 0.583 | 7 | 6 | 4 | 5 | 2 | 0 |

### Zor-vaka etiketi kırılımı

Etiketler çok değerlidir; tablolar ÖRTÜŞÜR.

| etiket | mikro-F1 | makro-F1 | TP | FP | FN |
|---|---|---|---|---|---|
| kosullu_aralik | 0.667 | 0.667 | 2 | 1 | 1 |
