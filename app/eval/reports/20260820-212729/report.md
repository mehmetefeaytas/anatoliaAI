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
| eşleştirici(ler) | strict |
| seed | 42 |
| git sha | 18000cb14c67a115c29c8dd77ae8747d045c758f |
| commit'lenmemiş değişiklik | EVET (dikkat: sayı bir commit'e karşılık gelmiyor) |
| Python | 3.14.6 |
| platform | macOS-26.5.2-arm64-arm-64bit-Mach-O |
| bağımlılık | yalnız Python stdlib (numpy/scipy/sklearn YOK) |
| üretim zamanı (UTC) | 2026-08-20T21:27:29.773121+00:00 |

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
| TÜMÜ | 0.546 | 0.596 | 0.570 | 0.765 | 0.570 [0.492–0.632] | 0.034 |
| ZOR (40 belge) | 0.577 | 0.598 | 0.587 | 0.767 | — | 0.025 |
| YAPILANDIRILMIŞ (11 alan) | 0.793 | 0.855 | 0.823 | 0.841 | — | 0.025 |
| ZOR + YAPILANDIRILMIŞ (40 belge) | 0.821 | 0.853 | 0.837 | 0.844 | — | 0.023 |

> **«YAPILANDIRILMIŞ» satırı neyi dışarıda bırakıyor:** `kampanya_kosullari`. Bu alan serbest cümle listesi döndürür; span/jeton eşleşmesiyle F1 ölçmek metodolojik olarak yanlıştır — aynı koşulu farklı sözcüklerle yazan iki anotatör bile birbirini «yanlış» bulurdu. Alan GİZLENMİYOR: aşağıda kendi bölümünde, kalem düzeyi ölçütle raporlanıyor ve iki sayı yan yana duruyor.

### Alan bazında

| alan | P | R | F1 | TP | FP | FN | TN | uydurma | atlanan |
|---|---|---|---|---|---|---|---|---|---|
| alisveris_puani | 1.000 | 0.875 | 0.933 | 7 | 0 | 1 | 38 | 0 | 0 |
| finansman_tutari | 1.000 | 1.000 | 1.000 | 4 | 0 | 0 | 43 | 0 | 0 |
| hedef_kitle | 0.526 | 0.625 | 0.571 | 10 | 9 | 6 | 25 | 6 | 0 |
| indirim_orani | 1.000 | 0.500 | 0.667 | 1 | 0 | 1 | 45 | 0 | 0 |
| kampanya_kosullari | 0.000 | 0.000 | 0.000 | 0 | 37 | 33 | 10 | 4 | 0 |
| kampanya_suresi | 0.917 | 0.957 | 0.936 | 22 | 2 | 1 | 22 | 1 | 0 |
| kar_payi_orani | 1.000 | 1.000 | 1.000 | 3 | 0 | 0 | 43 | 0 | 0 |
| masraf_durumu | 0.571 | 0.800 | 0.667 | 4 | 3 | 1 | 38 | 2 | 0 |
| odul_miktari | 0.667 | 0.800 | 0.727 | 4 | 2 | 1 | 38 | 1 | 0 |
| tahsis_ucreti | 0.000 | 0.000 | 0.000 | 0 | 0 | 0 | 47 | 0 | 0 |
| taksit_sayisi | 0.833 | 1.000 | 0.909 | 5 | 1 | 0 | 41 | 1 | 0 |
| vade_ay | 1.000 | 1.000 | 1.000 | 5 | 0 | 0 | 42 | 0 | 0 |

### Kalem düzeyi ölçüt (serbest metin alanları)

Aşağıdaki alanlar cümle listesi döndürür. İkili ölçüt bir alanı **ya tamamen doğru ya tamamen yanlış** sayar: beş koşuldan dördü doğru çıkarılsa bile TP=0. Kalem düzeyi ölçüt her koşulu ayrı sayar (jeton-Jaccard ≥ 0.70, 1-1 açgözlü eşleştirme).

**Manşet mikro-F1 bu tablodan ETKİLENMEZ.** İkili ölçüt manşet olarak kalır; buradaki sayı onun yerine geçmez, yanında durur.

| alan | ölçüt | P | R | F1 | TP | FP | FN |
|---|---|---|---|---|---|---|---|
| `kampanya_kosullari` | ikili | 0.000 | 0.000 | 0.000 | 0 | 37 | 33 |
|  | kalem | 0.479 | 0.569 | 0.520 | 78 | 85 | 59 |

Tüm alanlarda mikro-F1: ikili **0.570** · kalem **0.629**.

#### Eşik duyarlılığı

Eşik sayıya bakılarak seçilmedi. Aşağıdaki tablo, seçilen eşiğin sonucu ne kadar taşıdığını gösterir; taşıyorsa bunu okuyucu bilmelidir.

| jaccard eşiği | kalem mikro-F1 | TP | FP | FN |
|---|---|---|---|---|
| 0.60 | 0.659 | 152 | 95 | 62 |
| 0.70 ← ilan edilen | 0.629 | 145 | 102 | 69 |
| 0.80 | 0.599 | 138 | 109 | 76 |

### Zor-vaka etiketi kırılımı

Etiketler çok değerlidir; tablolar ÖRTÜŞÜR.

| etiket | mikro-F1 | makro-F1 | TP | FP | FN |
|---|---|---|---|---|---|
| celiskili | 0.500 | 0.524 | 7 | 7 | 7 |
| eksik_bilgi | 0.522 | 0.733 | 6 | 7 | 4 |
| format_varyant | 0.609 | 0.711 | 53 | 34 | 34 |
| kosullu_aralik | 0.653 | 0.819 | 31 | 17 | 16 |
| terminoloji | 0.510 | 0.767 | 13 | 13 | 12 |

## Kampanya türü (`campaign_type`) — 8 sınıf

CLAUDE.md §16 bu alan için *accuracy + macro-F1* istiyor. Ölçüt 12 alanın tablosundan AYRIDIR ve niçin ayrı olduğu `run_eval.tur_puanla` başlığında yazılıdır (sınıflandırıcı çıktısı, kapalı 8 elemanlı küme, eşleştirici ayrımı anlamsız).

| ölçüt | değer | payda |
|---|---|---|
| doğruluk (gold ETİKETLİ) | 0.769 | 30/39 |
| doğruluk (TÜM belgeler) | 0.729 | 35/48 |
| makro-F1 (8 sınıf) | 0.775 | — |
| uydurma oranı (gold `null` iken tür üretme) | 0.444 | 4/9 |
| çekimserlik (gold etiketli, tahmin `null`) | 3 | 3/39 |

> **İki doğruluk niçin yan yana:** gold bu alanda "tür yok" ile "anotatör karar vermedi"yi AYIRMIYOR — ölçüldü, `absent_fields` içinde `campaign_type` hiç geçmiyor, kılavuzun §4.13/1 `absent` kararı dosyada düz `null` olarak duruyor. Birinci sayı çekimserliği cezalandırır, ikincisi ödüllendirir; hangisinin doğru olduğu gold şeması netleşene kadar belirsizdir, o yüzden ikisi de yayımlanıyor.

### Sınıf bazında

| sınıf | destek | P | R | F1 |
|---|---|---|---|---|
| Finansman | 5 | 0.800 | 0.800 | 0.800 |
| İhtiyaç Finansmanı | 1 | 0.333 | 1.000 | 0.500 |
| Konut Finansmanı | 1 | 1.000 | 1.000 | 1.000 |
| Taşıt Finansmanı | 1 | 1.000 | 1.000 | 1.000 |
| Kart | 13 | 0.917 | 0.846 | 0.880 |
| Alışveriş Puanı | 7 | 1.000 | 0.714 | 0.833 |
| Yeni Müşteri | 5 | 1.000 | 0.200 | 0.333 |
| Yatırım Ürünü | 6 | 0.750 | 1.000 | 0.857 |

### Karışıklıklar (gold → tahmin)

| gold | tahmin | adet |
|---|---|---|
| (gold null) | Finansman | 2 |
| (gold null) | Yatırım Ürünü | 2 |
| Kart | İhtiyaç Finansmanı | 2 |
| Yeni Müşteri | (çekimser) | 2 |
| Alışveriş Puanı | Kart | 1 |
| Alışveriş Puanı | Yatırım Ürünü | 1 |
| Finansman | (çekimser) | 1 |
| Yeni Müşteri | Finansman | 1 |
| Yeni Müşteri | Yatırım Ürünü | 1 |
