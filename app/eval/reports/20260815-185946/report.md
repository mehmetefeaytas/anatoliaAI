# Değerlendirme raporu — konfig `kural`

yalnız kural katmanı (regex + normalizasyon), LLM kapalı — RESMÎ VARSAYILAN (K-2)

## Künye (tekrar-üretim)

| künye | değer |
|---|---|
| konfig | kural |
| gold dosyası | data/gold/gold.round1.json |
| gold sha256 | 4d53fe6d4d11fb9b… |
| gold kayıt sayısı | 134 |
| alt küme (split) | all |
| eşleştirici(ler) | strict |
| seed | 42 |
| git sha | fbc078f4deb56327cd2a28f572ce78fb7f5dec8a |
| commit'lenmemiş değişiklik | hayır |
| Python | 3.14.6 |
| platform | macOS-26.5.2-arm64-arm-64bit-Mach-O |
| bağımlılık | yalnız Python stdlib (numpy/scipy/sklearn YOK) |
| üretim zamanı (UTC) | 2026-08-15T18:59:46.201106+00:00 |

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
| TÜMÜ | 0.732 | 0.757 | 0.744 | 0.665 | 0.744 [0.685–0.808] | 0.433 |
| ZOR (3 belge) | 0.400 | 0.500 | 0.444 | 0.667 | — | 1.000 |
| YAPILANDIRILMIŞ (11 alan) | 0.731 | 0.746 | 0.739 | 0.644 | — | 0.414 |
| ZOR + YAPILANDIRILMIŞ (3 belge) | 0.400 | 0.500 | 0.444 | 0.667 | — | 1.000 |

> **«YAPILANDIRILMIŞ» satırı neyi dışarıda bırakıyor:** `kampanya_kosullari`. Bu alan serbest cümle listesi döndürür; span/jeton eşleşmesiyle F1 ölçmek metodolojik olarak yanlıştır — aynı koşulu farklı sözcüklerle yazan iki anotatör bile birbirini «yanlış» bulurdu. Alan GİZLENMİYOR: aşağıda kendi bölümünde, kalem düzeyi ölçütle raporlanıyor ve iki sayı yan yana duruyor.

### Alan bazında

| alan | P | R | F1 | TP | FP | FN | TN | uydurma | atlanan |
|---|---|---|---|---|---|---|---|---|---|
| alisveris_puani | 1.000 | 1.000 | 1.000 | 2 | 0 | 0 | 0 | 0 | 131 |
| finansman_tutari | 0.600 | 0.273 | 0.375 | 6 | 4 | 16 | 4 | 1 | 104 |
| hedef_kitle | 0.667 | 0.667 | 0.667 | 2 | 1 | 1 | 0 | 0 | 131 |
| indirim_orani | 0.000 | 0.000 | 0.000 | 0 | 0 | 0 | 0 | 0 | 134 |
| kampanya_kosullari | 0.750 | 1.000 | 0.857 | 6 | 2 | 0 | 0 | 2 | 124 |
| kampanya_suresi | 0.909 | 0.962 | 0.935 | 50 | 5 | 2 | 2 | 4 | 76 |
| kar_payi_orani | 0.750 | 0.857 | 0.800 | 6 | 2 | 1 | 9 | 1 | 117 |
| masraf_durumu | 0.000 | 0.000 | 0.000 | 0 | 3 | 5 | 0 | 0 | 129 |
| odul_miktari | 0.333 | 1.000 | 0.500 | 2 | 4 | 0 | 1 | 4 | 126 |
| tahsis_ucreti | 0.000 | 0.000 | 0.000 | 0 | 0 | 0 | 0 | 0 | 134 |
| taksit_sayisi | 0.929 | 0.812 | 0.867 | 13 | 1 | 3 | 1 | 1 | 116 |
| vade_ay | 0.568 | 0.758 | 0.649 | 25 | 19 | 8 | 17 | 13 | 67 |

### Kalem düzeyi ölçüt (serbest metin alanları)

Aşağıdaki alanlar cümle listesi döndürür. İkili ölçüt bir alanı **ya tamamen doğru ya tamamen yanlış** sayar: beş koşuldan dördü doğru çıkarılsa bile TP=0. Kalem düzeyi ölçüt her koşulu ayrı sayar (jeton-Jaccard ≥ 0.70, 1-1 açgözlü eşleştirme).

**Manşet mikro-F1 bu tablodan ETKİLENMEZ.** İkili ölçüt manşet olarak kalır; buradaki sayı onun yerine geçmez, yanında durur.

| alan | ölçüt | P | R | F1 | TP | FP | FN |
|---|---|---|---|---|---|---|---|
| `kampanya_kosullari` | ikili | 0.750 | 1.000 | 0.857 | 6 | 2 | 0 |
|  | kalem | 0.556 | 1.000 | 0.714 | 15 | 12 | 0 |

Tüm alanlarda mikro-F1: ikili **0.744** · kalem **0.739**.

#### Eşik duyarlılığı

Eşik sayıya bakılarak seçilmedi. Aşağıdaki tablo, seçilen eşiğin sonucu ne kadar taşıdığını gösterir; taşıyorsa bunu okuyucu bilmelidir.

| jaccard eşiği | kalem mikro-F1 | TP | FP | FN |
|---|---|---|---|---|
| 0.60 | 0.739 | 122 | 51 | 35 |
| 0.70 ← ilan edilen | 0.739 | 122 | 51 | 35 |
| 0.80 | 0.739 | 122 | 51 | 35 |

> **Sonuç eşikten bağımsız çıktı.** Denenen eşiklerin hepsinde aynı sayı üretildi; yani bu korpusta kalemler ya neredeyse birebir örtüşüyor ya hiç örtüşmüyor, arada sınır vaka yok. Eşiğin sonucu taşımadığını söylemek, taşıdığını söylemek kadar raporlanmaya değerdir.

### Zor-vaka etiketi kırılımı

Etiketler çok değerlidir; tablolar ÖRTÜŞÜR.

| etiket | mikro-F1 | makro-F1 | TP | FP | FN |
|---|---|---|---|---|---|
| kosullu_aralik | 0.000 | 0.000 | 0 | 2 | 2 |
| terminoloji | 0.800 | 1.000 | 2 | 1 | 0 |
