# Değerlendirme raporu — konfig `kural`

yalnız kural katmanı (regex + normalizasyon), LLM kapalı

## Künye (tekrar-üretim)

| künye | değer |
|---|---|
| konfig | kural |
| gold dosyası | data/gold/gold.v1.json |
| gold sha256 | ba2701cde3ed6fcc… |
| gold kayıt sayısı | 20 |
| alt küme (split) | all |
| eşleştirici(ler) | strict |
| seed | 42 |
| git sha | f3e2ef7eef25dfdd7a6a510a2a5487057cf6c417 |
| commit'lenmemiş değişiklik | EVET (dikkat: sayı bir commit'e karşılık gelmiyor) |
| Python | 3.14.6 |
| platform | macOS-26.5.2-arm64-arm-64bit-Mach-O |
| bağımlılık | yalnız Python stdlib (numpy/scipy/sklearn YOK) |
| üretim zamanı (UTC) | 2026-08-07T12:08:45.726025+00:00 |

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
| TÜMÜ | 0.662 | 0.692 | 0.677 | 0.618 | — | 0.096 |
| ZOR (1 belge) | 0.667 | 0.667 | 0.667 | 0.667 | — | 0.000 |

### Alan bazında

| alan | P | R | F1 | TP | FP | FN | TN | uydurma | atlanan |
|---|---|---|---|---|---|---|---|---|---|
| alisveris_puani | 0.000 | 0.000 | 0.000 | 0 | 1 | 1 | 19 | 0 | 0 |
| finansman_tutari | 0.667 | 0.333 | 0.444 | 2 | 1 | 4 | 13 | 0 | 0 |
| hedef_kitle | 0.667 | 0.800 | 0.727 | 4 | 2 | 1 | 13 | 2 | 0 |
| indirim_orani | 1.000 | 1.000 | 1.000 | 1 | 0 | 0 | 19 | 0 | 0 |
| kampanya_kosullari | 0.611 | 0.917 | 0.733 | 11 | 7 | 1 | 1 | 7 | 0 |
| kampanya_suresi | 1.000 | 1.000 | 1.000 | 6 | 0 | 0 | 14 | 0 | 0 |
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
