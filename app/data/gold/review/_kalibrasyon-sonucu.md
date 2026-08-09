# Kalibrasyon Turu Sonucu (round0, 20 belge · 260 satır · 4 anotatör)

> Ölçüldü: 2026-08-09. Üreten komutlar bu belgenin sonunda.
> Kaynak dosyalar: `round0_kalibrasyon_{A,B,C,D}.csv` (protokol **v1**).
> Ham rapor: [`../iaa_report.md`](../iaa_report.md)

---

## 1. Manşet

| Ölçüt | Ne ölçer | Değer | Eşik |
|---|---|---:|---|
| **Fleiss κ** (karar) | Aynı satırda aynı ETİKETİ mi verdiler | **0,051** | ≥0,67 |
| Krippendorff α (nominal) | Ortaya çıkan gold DEĞERİ aynı mı | 0,575 | — |
| Krippendorff α (ratio) | Sayısal alanlarda değer yakınlığı (42 birim) | 0,782 | — |

**Durum: zorunlu hakemlik + kılavuz netleştirmesi** (eşik politikası anotasyon
başlamadan ilan edilmişti, `ANNOTATION_GUIDE.md` §7 — sayıya bakıp eşik
değiştirilmez).

κ ile α arasındaki uçurum tesadüf değil, **teşhisin kendisidir**: ekip
belgelerin ne söylediği konusunda büyük ölçüde hemfikir (α 0,58/0,78), ama
kararı hangi ETİKETLE yazacağı konusunda değil (κ 0,05).

## 2. Uyuşmazlığın yapısı

260 ortak satır:

| | satır | pay |
|---|---:|---:|
| Tam uyum (hem etiket hem değer) | 24 | %9 |
| **Değer AYNI, etiket farklı** | **120** | **%46** |
| Değer gerçekten farklı | 116 | %45 |

Yani ölçülen uyuşmazlığın **yarısı içerik değil, etiketleme geleneği**.

## 3. Kök neden: 107 satırlık tek bir kalıp

`D='absent'` · `A/B/C='ok'` · dördünün de ürettiği gold değeri `__YOK__`:
**107 satır.**

Kılavuz bu durumu zaten tanımlıyor (`ANNOTATION_GUIDE.md` §3.1 tablosu):

| Satır | Doğru karar | Gold'a ne girer |
|---|---|---|
| `model_value` **boş** | `ok` — "kontrol ettim, bu alan belgede yok" | `absent_fields` |
| `model_value` **dolu**, metinde yok | `absent` — halüsinasyon | FP olarak ölçülür |

`absent` **modelin ürettiği bir değeri reddetmek** içindir. Model hiçbir şey
üretmediğinde `absent` yazmak, olmayan bir halüsinasyonu işaretlemektir.

> Bu bir kılavuz boşluğu DEĞİL, uygulama farkıdır — kural yazılıydı. Ama
> kılavuz "model boş bırakmışsa `absent` YAZMAYIN" cümlesini hiç kurmuyor;
> §3.3 tablosuna bu satırın eklenmesi öneriliyor.

### Karşı-olgu: tek bu kural netleşse κ nereye giderdi

Etiketler `ok` ve `absent`, ortaya çıkan değer `__YOK__` olduğunda
birleştirilerek yeniden hesaplandı (veriye dokunulmadı):

| Senaryo | Fleiss κ |
|---|---:|
| Bugünkü | 0,051 |
| **+ "değer yoksa `ok`" kuralı uygulanmış olsaydı** | **0,482** |
| + campaign_type yazımı da normalize edilseydi | 0,485 |

**+0,431** — ölçülen uyuşmazlığın %85'i tek bir etiketleme farkından geliyor.
0,482 hâlâ eşiğin altında, yani hakemlik yine gerekli; ama toplantı gündemi
"252 uyuşmazlığı konuş"tan "3 kuralı netleştir"e iniyor.

## 4. Biçim ihlalleri (`lint_review_csv`)

4 dosya · **149 hata · 101 uyarı**. Hata olan satır `build_gold`'u durdurur
ya da gold'a yanlış değer sokar.

| Anotatör | hata | uyarı | baskın kalıp |
|---|---:|---:|---|
| A | 0 | 0 | — |
| B | 48 | 90 | `hedef_kitle`de serbest metin (18); tek değerli alana iki değer (18) |
| C | 18 | 5 | tek değerli alana iki değer (5); taksonomi dışı tür |
| D | 83 | 6 | **`verdict=absent` + `gold_value` dolu (69)** |

**D'nin kalıbı:** `gold_value` sütununa belgenin ne hakkında olduğunu yazmış
(ör. `absent` + `"Leasing süreci ve hesaplama aracı"`). O sütun alanın
**değeri** içindir; `build_gold` bu değerleri sessizce atar.

**B'nin kalıbı:** kanonik değer yerine metinden alıntı — `"en fazla 48 aya
kadar"`, `"1-12 ay arası"`, `"0,00%-2,99%"`. Ayrıştırıcı bunları reddeder.

**Tek geçersiz `verdict` hücresi:** B, `dunya-katilim--…-gunes-katilma-hesabi ·
vade_ay` satırında karar sütununa not yazmış
(`"Model bulunmayan bir şeyi arayıp bulamayarak doğru bir iş yapmış"`).
Linter yakalıyor.

## 5. 8-sınıf taksonomi dışı `campaign_type` (14 hücre)

Sınıf kümesi sabittir (`CLAUDE.md` §12): Finansman · İhtiyaç Finansmanı ·
Konut Finansmanı · Taşıt Finansmanı · Kart · Alışveriş Puanı · Yeni Müşteri ·
Yatırım Ürünü.

- **Yazım:** `İhtiyaç finansmanı`, `Konut finansmanı`, `kart`, `altın`,
  `yeni müşteri` — küçük/büyük harf. Zararsız görünür ama κ'yı düşürür.
- **Uydurulmuş sınıf:** `Güneş Katılma Hesabı` (C), `Güneş Yatırım Hesabı` (D),
  `Altın Katılma Hesabı` (D), `Leasing` (C), `Yatırım Hesabı` (C),
  `Hediye / Ödül Kampanyası` (D). Bunların hepsi **`Yatırım Ürünü`** ya da
  8 sınıfın hiçbiri değilse **`absent`** olmalıydı (§9, "kampanya olmayan belge").

## 6. Kalibrasyon TAMAMLANMADI

`verdict` hücresi doldurulmuş satır:

| Anotatör | açık karar | eksik |
|---|---:|---:|
| A | 79/260 | 181 |
| B | 89/260 | 171 |
| C | **260/260** | 0 |
| D | **260/260** | 0 |

v1'de boş hücre "model doğru" sayılır — yani A ve B'nin bakmadığı 352 satır
şu an sessizce modeli onaylıyor. A'nın 134, B'nin 131 satırında **not var ama
karar yok**: anotatör bir sorun görmüş, yazmış, ama kararı işaretlememiş.

Bu yüzden protokol-doğru (v2) ölçüm henüz anlamlı değil: dördünün de açık
kararı olan satır **52/260**.

## 7. Toplantı gündemi (30 dk, sırayla)

1. **`ok` mi `absent` mi** — model boş bıraktıysa `ok`. `absent` yalnız model
   bir değer ÜRETTİ ve metinde yoksa. *(107 satırı, κ'nın 0,43'ünü etkiler)*
2. **`gold_value` alanın değeridir**, belgenin özeti değil. Değer yoksa boş
   kalır. *(D'nin 69 hatası)*
3. **Kanonik biçim** — `48`, `"48 aya kadar"` değil. Aralıklar için
   `_bicim-karti.md`. *(B'nin 27 hatası)*
4. **8 sınıf sabittir** — birebir yazım; uymuyorsa `absent`. *(14 hücre)*
5. A ve B kalibrasyonu **bitirir** (aynı 20 belge, 181 + 171 satır).

Sonra `report_iaa` yeniden koşulur. κ ≥ 0,67 ise ana tura geçilir.

---

## Üreten komutlar

```bash
# 1) .xlsx kararlarını CSV'ye taşı (üreteç sütunlarına dokunmaz)
.venv/bin/python -m scripts.xlsx_to_review_csv \
    --xlsx data/gold/review/round0_kalibrasyon_B.xlsx \
    --csv  data/gold/review/round0_kalibrasyon_B.csv

# 2) biçim denetimi
.venv/bin/python -m scripts.lint_review_csv 'data/gold/review/round0_kalibrasyon_[ABCD].csv'

# 3) uyum ölçümü
.venv/bin/python -m scripts.report_iaa data/gold/review/round0_kalibrasyon_{A,B,C,D}.csv

# 4) κ'nın nereden çıkacağını gör
.venv/bin/python -m scripts.kappa_durum
```
