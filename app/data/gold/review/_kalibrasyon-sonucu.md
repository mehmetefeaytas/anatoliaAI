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

260 ortak satır (`report_iaa`'nın kendi okuyucularıyla):

| | satır | pay |
|---|---:|---:|
| Tam uyum (hem etiket hem değer) | 8 | %3 |
| **Değer AYNI, etiket farklı** | **146** | **%56** |
| Değer gerçekten farklı | 106 | %41 |

Yani ölçülen uyuşmazlığın **yarısından fazlası içerik değil, etiketleme
geleneği**.

## 3. Kök neden: 134 satırlık tek bir kalıp

D, modelin **hiçbir şey üretmediği** 134 satırda `absent` yazmış; bunların
107'sinde A/B/C `ok` bırakmış.

> D'nin `absent`lerinin **10 tanesi meşru**: modelin gerçekten bir değer
> ürettiği ve D'nin onu reddettiği satırlar. Bunlar halüsinasyon (FP)
> iddiasıdır ve normalizasyonda **korunmalıdır**.

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

### Karşı-olgu: kurallar netleşse κ nereye giderdi

Veriye dokunulmadan, etiketler okuma anında normalize edilerek ölçüldü:

| Senaryo | Fleiss κ |
|---|---:|
| Bugünkü | 0,051 |
| 1) Boş `verdict` → `ok` (koşulsuz) | 0,099 |
| 2) Boş `verdict` + yazılan değer = modelin değeri → `ok` | 0,100 |
| **3) Model boş bıraktıysa `absent` ≡ `ok`** | **0,268** |
| 2 + 3 birlikte | 0,337 |

> ### ⚠️ DÜZELTME (2026-08-09)
>
> Bu tablonun ilk sürümü senaryo 3 için **0,482** diyordu. **Yanlıştı.**
> O hesap `ok`/`absent` etiketlerini *"ortaya çıkan değer `__YOK__`"*
> ölçütüyle birleştiriyordu; bu ölçüt, modelin gerçekten bir değer ürettiği ve
> anotatörün onu reddettiği satırları da kapsıyor — yani **meşru halüsinasyon
> iddialarını da** uyum sayıyordu.
>
> Doğru ölçüt kılavuzun kendi ölçütüdür: **`model_value` boş mu**. `absent`
> modelin ÜRETTİĞİ bir değeri reddetmek içindir; üretmediğinde reddedilecek
> bir şey yoktur. Bu ölçütle κ **0,268**.

Hiçbir senaryo eşiği (0,67) geçmiyor: **hakemlik ve yeniden anotasyon
kaçınılmaz.** Ama gündem "252 uyuşmazlığı tek tek konuş"tan "4 kuralı
netleştir"e iniyor.

## 3b. "Boşlar zaten `ok` sayılsın" — bu ZATEN yapılıyor

Boş `verdict` hücresi v1 dosyalarında **hâlihazırda `ok` okunuyor**
(`report_iaa.row_verdict`), yani κ=0,051 bunu zaten içeriyor. 352 boş hücreye
açıkça `ok` yazmak κ'yı 0,051 → 0,099'a taşıyor ve **o kazanç istenen yerden
gelmiyor**:

Tek istisna kuralı var — *boş `verdict` + dolu `gold_value` = `fix`*. Anotatör
düzeltmeyi yazıp karar sütununu atlamıştır ve o düzeltme çöpe atılmaz. B'de
**39 satır** böyle. Koşulsuz `ok` yazmak bu 39 düzeltmeyi **onaya çevirir**:

| alan | modelin değeri | B'nin yazdığı |
|---|---|---|
| `kampanya_suresi` | `2026-01-01` | `01.01.2026 - 31.12.2026` |
| `finansman_tutari` | `{"value": 40000.0}` | `{"value": 100000.0}` |

Yani κ'daki +0,048'in kaynağı, B'nin gerçek düzeltmelerinin sessizce
silinmesidir. **Yapılmamalı.**

Güvenli daraltılmış hâli senaryo 2'dir (yazılan değer modelinkiyle
birebir aynıysa `ok` say) ve κ'ya katkısı +0,001.

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
   bir değer ÜRETTİ ve metinde yoksa. *(134 satır; κ 0,051 → 0,268)*
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
