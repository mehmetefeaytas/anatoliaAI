# Değerlendirme raporu — konfig `kural`

yalnız kural katmanı (regex + normalizasyon), LLM kapalı — RESMÎ VARSAYILAN (K-2)

## Künye (tekrar-üretim)

| künye | değer |
|---|---|
| konfig | kural |
| gold dosyası | data/gold/gold.round1.json |
| gold sha256 | e9c24391284a0e8e… |
| gold kayıt sayısı | 134 |
| alt küme (split) | all |
| eşleştirici(ler) | strict, tolerant |
| seed | 42 |
| git sha | 765ee6a5eb53c62741ba6de50d24662c96a7b903 |
| commit'lenmemiş değişiklik | hayır |
| Python | 3.14.6 |
| platform | macOS-26.5.2-arm64-arm-64bit-Mach-O |
| bağımlılık | yalnız Python stdlib (numpy/scipy/sklearn YOK) |
| üretim zamanı (UTC) | 2026-08-21T13:41:25.790141+00:00 |

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
| TÜMÜ | 0.759 | 0.833 | 0.795 | 0.650 | 0.795 [0.732–0.858] | 0.284 |
| ZOR (3 belge) | 0.400 | 0.500 | 0.444 | 0.667 | — | 1.000 |
| YAPILANDIRILMIŞ (11 alan) | 0.793 | 0.862 | 0.826 | 0.707 | — | 0.264 |
| ZOR + YAPILANDIRILMIŞ (3 belge) | 0.400 | 0.500 | 0.444 | 0.667 | — | 1.000 |

> **«YAPILANDIRILMIŞ» satırı neyi dışarıda bırakıyor:** `kampanya_kosullari`. Bu alan serbest cümle listesi döndürür; span/jeton eşleşmesiyle F1 ölçmek metodolojik olarak yanlıştır — aynı koşulu farklı sözcüklerle yazan iki anotatör bile birbirini «yanlış» bulurdu. Alan GİZLENMİYOR: aşağıda kendi bölümünde, kalem düzeyi ölçütle raporlanıyor ve iki sayı yan yana duruyor.

### Alan bazında

| alan | P | R | F1 | TP | FP | FN | TN | uydurma | atlanan |
|---|---|---|---|---|---|---|---|---|---|
| alisveris_puani | 1.000 | 1.000 | 1.000 | 3 | 0 | 0 | 0 | 0 | 131 |
| finansman_tutari | 1.000 | 1.000 | 1.000 | 18 | 0 | 0 | 18 | 0 | 95 |
| hedef_kitle | 0.667 | 0.667 | 0.667 | 2 | 1 | 1 | 0 | 0 | 131 |
| indirim_orani | 0.000 | 0.000 | 0.000 | 0 | 0 | 0 | 0 | 0 | 134 |
| kampanya_kosullari | 0.125 | 0.167 | 0.143 | 1 | 7 | 5 | 0 | 2 | 124 |
| kampanya_suresi | 0.909 | 0.962 | 0.935 | 50 | 5 | 2 | 2 | 4 | 76 |
| kar_payi_orani | 0.750 | 0.857 | 0.800 | 6 | 2 | 1 | 9 | 1 | 117 |
| masraf_durumu | 0.000 | 0.000 | 0.000 | 0 | 3 | 5 | 0 | 0 | 129 |
| odul_miktari | 0.250 | 1.000 | 0.400 | 1 | 3 | 0 | 3 | 3 | 126 |
| tahsis_ucreti | 0.000 | 0.000 | 0.000 | 0 | 0 | 0 | 0 | 0 | 134 |
| taksit_sayisi | 0.929 | 0.812 | 0.867 | 13 | 1 | 3 | 1 | 1 | 116 |
| vade_ay | 0.619 | 0.788 | 0.693 | 26 | 16 | 7 | 20 | 10 | 67 |

### Kalem düzeyi ölçüt (serbest metin alanları)

Aşağıdaki alanlar cümle listesi döndürür. İkili ölçüt bir alanı **ya tamamen doğru ya tamamen yanlış** sayar: beş koşuldan dördü doğru çıkarılsa bile TP=0. Kalem düzeyi ölçüt her koşulu ayrı sayar (jeton-Jaccard ≥ 0.70, 1-1 açgözlü eşleştirme).

**Manşet mikro-F1 bu tablodan ETKİLENMEZ.** İkili ölçüt manşet olarak kalır; buradaki sayı onun yerine geçmez, yanında durur.

| alan | ölçüt | P | R | F1 | TP | FP | FN |
|---|---|---|---|---|---|---|---|
| `kampanya_kosullari` | ikili | 0.125 | 0.167 | 0.143 | 1 | 7 | 5 |
|  | kalem | 0.310 | 0.692 | 0.429 | 9 | 20 | 4 |

Tüm alanlarda mikro-F1: ikili **0.795** · kalem **0.779**.

#### Eşik duyarlılığı

Eşik sayıya bakılarak seçilmedi. Aşağıdaki tablo, seçilen eşiğin sonucu ne kadar taşıdığını gösterir; taşıyorsa bunu okuyucu bilmelidir.

| jaccard eşiği | kalem mikro-F1 | TP | FP | FN |
|---|---|---|---|---|
| 0.60 | 0.779 | 129 | 51 | 22 |
| 0.70 ← ilan edilen | 0.779 | 129 | 51 | 22 |
| 0.80 | 0.779 | 129 | 51 | 22 |

> **Sonuç eşikten bağımsız çıktı.** Denenen eşiklerin hepsinde aynı sayı üretildi; yani bu korpusta kalemler ya neredeyse birebir örtüşüyor ya hiç örtüşmüyor, arada sınır vaka yok. Eşiğin sonucu taşımadığını söylemek, taşıdığını söylemek kadar raporlanmaya değerdir.

### Zor-vaka etiketi kırılımı

Etiketler çok değerlidir; tablolar ÖRTÜŞÜR.

| etiket | mikro-F1 | makro-F1 | TP | FP | FN |
|---|---|---|---|---|---|
| kosullu_aralik | 0.000 | 0.000 | 0 | 2 | 2 |
| terminoloji | 0.800 | 1.000 | 2 | 1 | 0 |

## Eşleştirici: `tolerant`

| alt küme | P (mikro) | R (mikro) | F1 (mikro) | F1 (makro) | mikro-F1 %95 GA | halüsinasyon |
|---|---|---|---|---|---|---|
| TÜMÜ | 0.759 | 0.833 | 0.795 | 0.650 | 0.795 [0.732–0.858] | 0.284 |
| ZOR (3 belge) | 0.400 | 0.500 | 0.444 | 0.667 | — | 1.000 |
| YAPILANDIRILMIŞ (11 alan) | 0.793 | 0.862 | 0.826 | 0.707 | — | 0.264 |
| ZOR + YAPILANDIRILMIŞ (3 belge) | 0.400 | 0.500 | 0.444 | 0.667 | — | 1.000 |

> **«YAPILANDIRILMIŞ» satırı neyi dışarıda bırakıyor:** `kampanya_kosullari`. Bu alan serbest cümle listesi döndürür; span/jeton eşleşmesiyle F1 ölçmek metodolojik olarak yanlıştır — aynı koşulu farklı sözcüklerle yazan iki anotatör bile birbirini «yanlış» bulurdu. Alan GİZLENMİYOR: aşağıda kendi bölümünde, kalem düzeyi ölçütle raporlanıyor ve iki sayı yan yana duruyor.

### Alan bazında

| alan | P | R | F1 | TP | FP | FN | TN | uydurma | atlanan |
|---|---|---|---|---|---|---|---|---|---|
| alisveris_puani | 1.000 | 1.000 | 1.000 | 3 | 0 | 0 | 0 | 0 | 131 |
| finansman_tutari | 1.000 | 1.000 | 1.000 | 18 | 0 | 0 | 18 | 0 | 95 |
| hedef_kitle | 0.667 | 0.667 | 0.667 | 2 | 1 | 1 | 0 | 0 | 131 |
| indirim_orani | 0.000 | 0.000 | 0.000 | 0 | 0 | 0 | 0 | 0 | 134 |
| kampanya_kosullari | 0.125 | 0.167 | 0.143 | 1 | 7 | 5 | 0 | 2 | 124 |
| kampanya_suresi | 0.909 | 0.962 | 0.935 | 50 | 5 | 2 | 2 | 4 | 76 |
| kar_payi_orani | 0.750 | 0.857 | 0.800 | 6 | 2 | 1 | 9 | 1 | 117 |
| masraf_durumu | 0.000 | 0.000 | 0.000 | 0 | 3 | 5 | 0 | 0 | 129 |
| odul_miktari | 0.250 | 1.000 | 0.400 | 1 | 3 | 0 | 3 | 3 | 126 |
| tahsis_ucreti | 0.000 | 0.000 | 0.000 | 0 | 0 | 0 | 0 | 0 | 134 |
| taksit_sayisi | 0.929 | 0.812 | 0.867 | 13 | 1 | 3 | 1 | 1 | 116 |
| vade_ay | 0.619 | 0.788 | 0.693 | 26 | 16 | 7 | 20 | 10 | 67 |

### Kalem düzeyi ölçüt (serbest metin alanları)

Aşağıdaki alanlar cümle listesi döndürür. İkili ölçüt bir alanı **ya tamamen doğru ya tamamen yanlış** sayar: beş koşuldan dördü doğru çıkarılsa bile TP=0. Kalem düzeyi ölçüt her koşulu ayrı sayar (jeton-Jaccard ≥ 0.70, 1-1 açgözlü eşleştirme).

**Manşet mikro-F1 bu tablodan ETKİLENMEZ.** İkili ölçüt manşet olarak kalır; buradaki sayı onun yerine geçmez, yanında durur.

| alan | ölçüt | P | R | F1 | TP | FP | FN |
|---|---|---|---|---|---|---|---|
| `kampanya_kosullari` | ikili | 0.125 | 0.167 | 0.143 | 1 | 7 | 5 |
|  | kalem | 0.310 | 0.692 | 0.429 | 9 | 20 | 4 |

Tüm alanlarda mikro-F1: ikili **0.795** · kalem **0.779**.

#### Eşik duyarlılığı

Eşik sayıya bakılarak seçilmedi. Aşağıdaki tablo, seçilen eşiğin sonucu ne kadar taşıdığını gösterir; taşıyorsa bunu okuyucu bilmelidir.

| jaccard eşiği | kalem mikro-F1 | TP | FP | FN |
|---|---|---|---|---|
| 0.60 | 0.779 | 129 | 51 | 22 |
| 0.70 ← ilan edilen | 0.779 | 129 | 51 | 22 |
| 0.80 | 0.779 | 129 | 51 | 22 |

> **Sonuç eşikten bağımsız çıktı.** Denenen eşiklerin hepsinde aynı sayı üretildi; yani bu korpusta kalemler ya neredeyse birebir örtüşüyor ya hiç örtüşmüyor, arada sınır vaka yok. Eşiğin sonucu taşımadığını söylemek, taşıdığını söylemek kadar raporlanmaya değerdir.

### Zor-vaka etiketi kırılımı

Etiketler çok değerlidir; tablolar ÖRTÜŞÜR.

| etiket | mikro-F1 | makro-F1 | TP | FP | FN |
|---|---|---|---|---|---|
| kosullu_aralik | 0.000 | 0.000 | 0 | 2 | 2 |
| terminoloji | 0.800 | 1.000 | 2 | 1 | 0 |

## Kampanya türü (`campaign_type`) — 8 sınıf

CLAUDE.md §16 bu alan için *accuracy + macro-F1* istiyor. Ölçüt 12 alanın tablosundan AYRIDIR ve niçin ayrı olduğu `run_eval.tur_puanla` başlığında yazılıdır (sınıflandırıcı çıktısı, kapalı 8 elemanlı küme, eşleştirici ayrımı anlamsız).

| ölçüt | değer | payda |
|---|---|---|
| doğruluk (gold ETİKETLİ) | 0.798 | 91/114 |
| doğruluk (TÜM belgeler) | 0.731 | 98/134 |
| makro-F1 (8 sınıf) | 0.702 | — |
| uydurma oranı (gold `null` iken tür üretme) | 0.650 | 13/20 |
| çekimserlik (gold etiketli, tahmin `null`) | 2 | 2/114 |

> **İki doğruluk niçin yan yana:** gold bu alanda "tür yok" ile "anotatör karar vermedi"yi AYIRMIYOR — ölçüldü, `absent_fields` içinde `campaign_type` hiç geçmiyor, kılavuzun §4.13/1 `absent` kararı dosyada düz `null` olarak duruyor. Birinci sayı çekimserliği cezalandırır, ikincisi ödüllendirir; hangisinin doğru olduğu gold şeması netleşene kadar belirsizdir, o yüzden ikisi de yayımlanıyor.

### Sınıf bazında

| sınıf | destek | P | R | F1 |
|---|---|---|---|---|
| Finansman | 25 | 0.667 | 0.800 | 0.727 |
| İhtiyaç Finansmanı | 16 | 0.643 | 0.562 | 0.600 |
| Konut Finansmanı | 6 | 1.000 | 0.500 | 0.667 |
| Taşıt Finansmanı | 6 | 1.000 | 1.000 | 1.000 |
| Kart | 21 | 0.909 | 0.952 | 0.930 |
| Alışveriş Puanı | 14 | 1.000 | 0.643 | 0.783 |
| Yeni Müşteri | 1 | 0.000 | 0.000 | 0.000 |
| Yatırım Ürünü | 25 | 0.857 | 0.960 | 0.906 |

### Karışıklıklar (gold → tahmin)

| gold | tahmin | adet |
|---|---|---|
| (gold null) | Yatırım Ürünü | 6 |
| İhtiyaç Finansmanı | Finansman | 6 |
| (gold null) | Finansman | 4 |
| (gold null) | Kart | 2 |
| Alışveriş Puanı | İhtiyaç Finansmanı | 2 |
| Finansman | Yatırım Ürünü | 2 |
| Finansman | İhtiyaç Finansmanı | 2 |
| Konut Finansmanı | Finansman | 2 |
| (gold null) | Konut Finansmanı | 1 |
| Alışveriş Puanı | (çekimser) | 1 |
| Alışveriş Puanı | Kart | 1 |
| Alışveriş Puanı | Yatırım Ürünü | 1 |
| Finansman | (çekimser) | 1 |
| Kart | Yatırım Ürünü | 1 |
| Konut Finansmanı | İhtiyaç Finansmanı | 1 |
| Yatırım Ürünü | Finansman | 1 |
| Yeni Müşteri | Finansman | 1 |
| İhtiyaç Finansmanı | Kart | 1 |
