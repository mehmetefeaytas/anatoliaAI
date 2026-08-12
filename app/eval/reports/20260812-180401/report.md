# Değerlendirme raporu — konfig `kural`

yalnız kural katmanı (regex + normalizasyon), LLM kapalı — RESMÎ VARSAYILAN (K-2)

## Künye (tekrar-üretim)

| künye | değer |
|---|---|
| konfig | kural |
| gold dosyası | data/gold/gold.v2.json |
| gold sha256 | af1d4f1b7ab2470a… |
| gold kayıt sayısı | 48 |
| alt küme (split) | all |
| eşleştirici(ler) | strict |
| seed | 42 |
| git sha | d8eec7d886f5ef240737e9aaf0dc9897b79abfb1 |
| commit'lenmemiş değişiklik | EVET (dikkat: sayı bir commit'e karşılık gelmiyor) |
| Python | 3.14.6 |
| platform | macOS-26.5.2-arm64-arm-64bit-Mach-O |
| bağımlılık | yalnız Python stdlib (numpy/scipy/sklearn YOK) |
| üretim zamanı (UTC) | 2026-08-12T18:04:01.686831+00:00 |

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
| TÜMÜ | 0.416 | 0.464 | 0.439 | 0.534 | — | 0.074 |
| ZOR (40 belge) | 0.444 | 0.473 | 0.458 | 0.542 | — | 0.074 |
| YAPILANDIRILMIŞ (11 alan) | 0.584 | 0.658 | 0.619 | 0.588 | — | 0.063 |
| ZOR + YAPILANDIRILMIŞ (40 belge) | 0.605 | 0.667 | 0.634 | 0.596 | — | 0.070 |

> **«YAPILANDIRILMIŞ» satırı neyi dışarıda bırakıyor:** `kampanya_kosullari`. Bu alan serbest cümle listesi döndürür; span/jeton eşleşmesiyle F1 ölçmek metodolojik olarak yanlıştır — aynı koşulu farklı sözcüklerle yazan iki anotatör bile birbirini «yanlış» bulurdu. Alan GİZLENMİYOR: aşağıda kendi bölümünde, kalem düzeyi ölçütle raporlanıyor ve iki sayı yan yana duruyor.

### Alan bazında

| alan | P | R | F1 | TP | FP | FN | TN | uydurma | atlanan |
|---|---|---|---|---|---|---|---|---|---|
| alisveris_puani | 1.000 | 0.500 | 0.667 | 4 | 0 | 4 | 38 | 0 | 0 |
| finansman_tutari | 0.667 | 0.500 | 0.571 | 2 | 1 | 2 | 43 | 0 | 0 |
| hedef_kitle | 0.333 | 0.222 | 0.267 | 4 | 8 | 14 | 24 | 5 | 0 |
| indirim_orani | 0.333 | 0.500 | 0.400 | 1 | 2 | 1 | 44 | 1 | 0 |
| kampanya_kosullari | 0.000 | 0.000 | 0.000 | 0 | 36 | 33 | 8 | 6 | 0 |
| kampanya_suresi | 0.917 | 0.957 | 0.936 | 22 | 2 | 1 | 22 | 1 | 0 |
| kar_payi_orani | 1.000 | 0.667 | 0.800 | 2 | 0 | 1 | 43 | 0 | 0 |
| masraf_durumu | 0.333 | 0.833 | 0.476 | 5 | 10 | 1 | 30 | 9 | 0 |
| odul_miktari | 0.364 | 0.800 | 0.500 | 4 | 7 | 1 | 33 | 6 | 0 |
| tahsis_ucreti | 0.000 | 0.000 | 0.000 | 0 | 0 | 0 | 47 | 0 | 0 |
| taksit_sayisi | 0.556 | 1.000 | 0.714 | 5 | 4 | 0 | 38 | 4 | 0 |
| vade_ay | 0.500 | 0.600 | 0.545 | 3 | 3 | 2 | 41 | 1 | 0 |

### Zor-vaka etiketi kırılımı

Etiketler çok değerlidir; tablolar ÖRTÜŞÜR.

| etiket | mikro-F1 | makro-F1 | TP | FP | FN |
|---|---|---|---|---|---|
| celiskili | 0.429 | 0.381 | 6 | 7 | 9 |
| eksik_bilgi | 0.333 | 0.500 | 4 | 10 | 6 |
| format_varyant | 0.467 | 0.494 | 42 | 49 | 47 |
| kosullu_aralik | 0.442 | 0.543 | 21 | 25 | 28 |
| terminoloji | 0.491 | 0.642 | 13 | 13 | 14 |
