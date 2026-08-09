# Kalibrasyondan Gold'a Ne Girer — (b) Seçeneğinin Ölçümü

> **Bu belge KARAR VERMEZ, sayı verir.** (b) seçeneği ekibin tercihine yakın
> duruyordu: *gold yalnız insanın gerçekten karar verdiği satırlardan oluşsun.*
> Aşağıdaki her rakam ölçüldü; üreten komut en sonda.
>
> Ölçüm: 2026-08-09 · `scripts/kalibrasyondan_gold.py`
> Kaynak: `round0_kalibrasyon_{A,B,C,D}.csv` ve `.yedek-hakemlik` kopyaları

---

## 0. Ölçmeden önce: "dolu verdict" ≠ "insan karar verdi"

Bu ayrım bütün ölçümü belirliyor, o yüzden başa alındı.

Güncel `round0_kalibrasyon_*.csv` dosyalarında `verdict` hücrelerinin neredeyse
hepsi dolu. Ama bu doluluğun büyük kısmını **insan yazmadı** —
`kalibrasyon_hakemlik.py` `bos-ok` kuralıyla boş hücrelere `ok` yazdı
(`_kalibrasyon-sonucu.md` §8: A 199, B 136, C 3, D 134 hücre).

| Kaynak | A | B | C | D |
|---|---:|---:|---:|---:|
| **`.yedek-hakemlik`** (hakemlik ÖNCESİ = insan) | **79** | **128** | **260** | **260** |
| güncel `.csv` (hakemlik SONRASI = betik dahil) | 260 | 259 | 260 | 260 |

Güncel dosyada (b)'yi ölçmek, "insanın karar verdiği satır" sorusuna betiğin
yazdığı hücreleri de saymak olurdu. **Bu yüzden (b) ölçümü `.yedek-hakemlik`
üzerinden yapıldı.**

> **Not — B'nin 128'i.** `_kalibrasyon-sonucu.md` §6 B için 89 diyor; o sayı
> yalnız dolu `verdict` hücrelerini sayıyor. Buradaki ölçüt daha geniş:
> **dolu `verdict` YA DA dolu `gold_value`**. B'nin 39 satırında karar sütunu
> boş ama düzeltme yazılmış (§8'in "korunan 39"u) ve `build_gold` bunları `fix`
> sayar. 89 + 39 = 128. Bir düzeltmeyi "karar verilmedi" saymak, elle girilmiş
> en değerli veriyi ölçüm dışına atmak olurdu.

---

## 1. Kaç satırda kaç anotatörün açık kararı var

260 ortak satır (20 belge × 13 alan — dağılım birebir eşit, hiçbir alan eksik değil):

| Açık karar veren anotatör sayısı | satır | pay |
|---|---:|---:|
| 4 (dördü de) | **62** | %24 |
| 3 | 83 | %32 |
| 2 | 115 | %44 |
| 1 ya da 0 | **0** | %0 |

**En az iki anotatörün açık kararı olan satır: 260/260 (%100).**

Bu sonucun sebebi mekanik: **C ve D 260 satırın hepsine karar verdi.** Yani
"en az iki karar" eşiği hiçbir satırı elemiyor — (b) seçeneği ≥2 eşiğinde
kalibrasyonun tamamını gold'a alır, hiçbir şey süzmez.

Süzme ancak eşik yükseltilince başlar:

| Eşik | satır | belge | alan |
|---|---:|---:|---:|
| ≥2 | **260** | 20 | 13 |
| ≥3 | **145** | 20 | 13 |
| ≥4 | **62** | 19 | 12 |

---

## 2. Bu alt kümelerde κ kaç

İki ayrı okuma var ve ikisi de raporlanmalı, çünkü farklı soruları cevaplıyorlar.

### 2a. Ham insan etiketiyle (hakemlik kuralları UYGULANMADAN)

| Eşik | satır | Fleiss κ | Krippendorff α |
|---|---:|---:|---:|
| ≥2 | 260 | **−0,172** | 0,495 |
| ≥3 | 145 | 0,006 | — |
| ≥4 | 62 | 0,072 | — |

**κ negatif.** Rastgele atamadan kötü. Bu bir hesap hatası değil, ölçütün
dürüstleşmesinin sonucu: `_kalibrasyon-sonucu.md`'deki **0,051** rakamı v1
okumasıyla üretilmişti ve orada **boş hücre `ok` sayılır** — yani A'nın
bakmadığı 181, B'nin bakmadığı 132 satır sessizce "onay" olarak uyuma
giriyordu. Bakılmamış satırları uyumdan çıkarınca geriye kalan, gerçekten
bakılmış ve gerçekten ayrışmış satırlardır; D'nin 134 hatalı `absent`'i de
düzeltilmeden orada durur.

> Bu, (b) seçeneğinin en önemli bulgusu: **v1'in "sessizlik = onay" kuralı
> κ'yı 0,051'e kadar ŞİŞİRİYORDU.** Ham insan uyumu daha da kötüydü.

### 2b. Hakemlik sonrası etiketle (insan maskesi + iki kılavuz kuralı)

Maske `.yedek-hakemlik`ten (kim gerçekten baktı), etiketler güncel dosyadan
(`bos-ok` + `absent-ok` uygulanmış hâli). Karar açısından ilgili sayı budur.

| Eşik | satır | belge | alan | **Fleiss κ** | Krippendorff α |
|---|---:|---:|---:|---:|---:|
| **≥2** | **260** | 20 | 13 | **0,393** | 0,547 |
| ≥3 | 145 | 20 | 13 | 0,130 | 0,484 |
| ≥4 | 62 | 19 | 12 | 0,186 | 0,303 |

Karşılaştırma için, süzmesiz güncel dosya (herkesin her satırı, betik yazdıkları
dahil): κ = **0,303** · α = 0,619.

### 2c. Eşik yükseldikçe κ NİÇİN düşüyor

Sezgiye aykırı ve tesadüf değil: **A ve B yalnız sorunlu gördükleri satırlara
karar yazdı.** Dolayısıyla "dördü de baktı" alt kümesi, kalibrasyonun *en
tartışmalı* 62 satırıdır — kolay satırlar (model doğru, kimse itiraz etmiyor)
o kümede yok, çünkü A ve B onları boş geçti.

Sonuç: **en "saf" alt küme aynı zamanda en zor alt kümedir.** ≥4 eşiğiyle
kurulan bir gold, sistemin en zor %24'ünde ölçülür ve F1'i haksız yere düşük
çıkar. Bu, ölçüm tasarımı açısından bir tuzaktır ve (b) tartışılırken masaya
konmalıdır.

---

## 3. Kapsam: 62 satırlık çekirdek ne içeriyor

≥4 alt kümesi 19 belge · 12 alan. Düşen: 1 belge ve 1 alan
(`indirim_orani` — dördünün birden karar verdiği hiçbir satırı yok).

≥3 ve ≥2 alt kümeleri 20 belgenin ve 13 alanın hepsini koruyor.

---

## 4. Bu alt kümeyi gold'a çeviren komut ne olurdu

`scripts/build_gold.py` **okundu, koşturulmadı.** Bulgular:

1. `build_gold`un **satır süzme seçeneği yok**. Arayüzü: `--csv` (tekrarlanabilir),
   `--csv-dir`, `--out`, `--report`, `--excluded-out`, `--allow-errors`.
   "Yalnız N anotatörün karar verdiği satırları al" diye bir bayrak yok.

2. Ama süzme zaten **protokolün işi**. `build_gold` v2'de boş `verdict` + boş
   `gold_value` satırını `SKIPPED_DECISION` sayar ve gold'a hiç almaz. Yani
   (b) seçeneği v2 protokolünün **doğal davranışıdır**, ayrı bir süzgeç
   gerektirmez.

3. Taşıma aracı da hazır: `scripts/protokol_yukselt.py --tasi` v1'de verilmiş
   **açık** kararları v2 dosyasına kopyalar, **boş hücreleri taşımaz** — bu tam
   olarak (b)'nin istediği ayrımdır. `round0_kalibrasyon_v2_{A,B,C,D}.csv`
   dosyaları zaten mevcut.

Buna göre (b) için komut zinciri — **çalıştırılmadı, öneri**:

```bash
# 1) İnsan kararlarını v2 dosyalarına taşı (boşlar taşınmaz = (b)'nin süzgeci)
for A in A B C D; do
  .venv/bin/python -m scripts.protokol_yukselt --tasi \
      --kaynak data/gold/review/round0_kalibrasyon_$A.csv.yedek-hakemlik \
      --hedef  data/gold/review/round0_kalibrasyon_v2_$A.csv
done

# 2) Biçim kapısı (HATA kalmamalı; bkz. _onarim-recetesi.md)
.venv/bin/python -m scripts.lint_review_csv \
    'data/gold/review/round0_kalibrasyon_v2_[ABCD].csv' --eksiksiz

# 3) Derle — v2'de karar verilmemiş satır gold'a GİRMEZ
.venv/bin/python -m scripts.build_gold \
    --csv data/gold/review/round0_kalibrasyon_v2_A.csv \
    --csv data/gold/review/round0_kalibrasyon_v2_B.csv \
    --csv data/gold/review/round0_kalibrasyon_v2_C.csv \
    --csv data/gold/review/round0_kalibrasyon_v2_D.csv \
    --out data/gold/gold.kalibrasyon.json
```

**Kaynak seçimi kritik.** Adım 1'de `.yedek-hakemlik` okunuyor, güncel `.csv`
değil. Güncel dosya okunursa betiğin yazdığı 472 `ok` hücresi "insan kararı"
diye v2'ye taşınır ve (b) seçeneği kendi amacını yok eder.

> **Uyarı — 2. adım şu an geçmez.** 64 biçim hatası duruyor
> (`_onarim-recetesi.md`). `--eksiksiz` bayrağı olmadan da `build_gold`
> `fix` + boş `gold_value` satırlarında durur (7 satır).

---

## 5. Karar için masaya konan sayılar

Karar ekibindir. Ölçülenler:

| Soru | Cevap |
|---|---|
| En az 2 anotatörün açık kararı olan satır | **260 / 260 (%100)** |
| Dördünün de karar verdiği satır | **62 (%24)** |
| (b) ≥2 eşiğinde gold kaç satır olur | **260** — süzme YOK |
| (b) ≥2 alt kümesinde κ (hakemlik sonrası etiket) | **0,393** |
| (b) ≥2 alt kümesinde κ (ham insan etiketi) | **−0,172** |
| (b) ≥4 eşiğinde gold kaç satır olur | **62** (19 belge · 12 alan) |
| (b) ≥4 alt kümesinde κ | **0,186** |
| Eşik (önceden ilan edilmiş) | 0,67 — **hiçbir alt küme geçmiyor** |

İki gözlem, ikisi de ölçülmüş:

1. **≥2 eşiği hiçbir şey süzmüyor** (C ve D her satıra baktı). (b)'nin "yalnız
   insanın karar verdiği satırlar" vaadi, ≥2'de bugünkü 260 satırın aynısını
   verir.
2. **Eşiği yükseltmek κ'yı düşürüyor** (0,393 → 0,130 → 0,186), çünkü A ve B
   yalnız sorunlu satırlara baktı ve saf alt küme zor alt küme oldu.

Hiçbir alt küme 0,67 eşiğini geçmiyor. Bu belge o eşiği tartışmaz —
`ANNOTATION_GUIDE.md` §7 gereği eşik anotasyon başlamadan ilan edildi ve
sayıya bakıp değiştirilmez.

---

## Üreten komut

```bash
.venv/bin/python -m scripts.kalibrasyondan_gold          # eşik ≥2 (varsayılan)
.venv/bin/python -m scripts.kalibrasyondan_gold --esik 4
```

Betik `build_gold`u **koşturmaz** ve hiçbir CSV'ye **yazmaz**; yalnız okur ve sayar.
