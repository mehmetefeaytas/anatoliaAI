# Anotasyon Atama Planı

> `scripts/to_review_csv.py` üretti. Elle düzenlemeyin — yeniden koşuda üzerine yazılır.
>
> **İSTİSNA:** aşağıdaki "v2 kalibrasyon paketi" bölümü elle eklenmiştir ve
> üreteçten gelmez. `to_review_csv.py` yeniden koşulursa bu bölüm KORUNMALIDIR.

---

## ⚠️ ÖNCE BURAYI OKUYUN — v2 kalibrasyon paketi (κ bu paketten hesaplanır)

Kılavuz revize edildi (`ANNOTATION_GUIDE.md` v2): **boş hücre artık onay değil**
ve dört anotatörün bağımsız işaretlediği **sekiz boşluk kapatıldı** (§4.13).
Aşağıdaki tablodaki v1 dosyaları **eski kuralla** üretilmiştir; κ ölçümü onlardan
değil, v2 paketinden yapılır.

| Anotatör | Dosya | Satır | Belge | Durum |
|---|---|---:|---:|---|
| A | `round0_kalibrasyon_v2_A.csv` | 260 | 20 | boş — doldurulacak |
| B | `round0_kalibrasyon_v2_B.csv` | 260 | 20 | boş — doldurulacak |
| C | `round0_kalibrasyon_v2_C.csv` | 260 | 20 | boş — doldurulacak |
| D | `round0_kalibrasyon_v2_D.csv` | 260 | 20 | boş — doldurulacak |

**Dört dosya da AYNI 20 belgeyi ve AYNI 260 `(doc_id, field)` satırını içerir.**
Bu sabittir; değiştirilirse Fleiss κ hesaplanamaz. (Mevcut `parca/parca-1..4.json`
tamamen ayrık — 48 benzersiz belge, sıfır tekrar — bu yüzden ondan κ çıkmaz.)

- En az **iki** dosya dolduğunda κ hesaplanır (Cohen). Dördü de dolarsa Fleiss.
- Dosyalarda salt-okunur bir **`protokol`** sütunu var (`v2`). Silmeyin;
  araçlar boş hücrenin anlamını buradan okur.
- **Her satıra `verdict` yazılır.** Boş = "karar verilmedi", gold'a girmez.

### Üç komut

```bash
# 1) doldururken — biçim + kalan karar sayısı (uyarı verir, durdurmaz)
.venv/bin/python -m scripts.lint_review_csv 'data/gold/review/round0_kalibrasyon_v2_*.csv'

# 2) κ + Krippendorff α  ->  data/gold/iaa_report.md
.venv/bin/python -m scripts.report_iaa data/gold/review/round0_kalibrasyon_v2_*.csv

# 3) derlemeden ÖNCE kapı — boş satır kalmışsa HATA verir
.venv/bin/python -m scripts.lint_review_csv --eksiksiz 'data/gold/review/round0_kalibrasyon_v2_*.csv'
```

Eşik politikası **önceden ilan edilmiştir** ve değiştirilmez
(`ANNOTATION_GUIDE.md` §7): κ ≥ 0,80 kabul · 0,67 ≤ κ < 0,80 notla kabul ·
κ < 0,67 zorunlu hakemlik + kılavuz revizyonu.

Ayrıntı: [`../../../docs/rapor/kilavuz-revizyonu.md`](../../../docs/rapor/kilavuz-revizyonu.md)

---

## v1 planı (arşiv — silinmedi)

- Toplam belge: **250**
- Kalibrasyon (herkes aynı): **20** belge
- Çift anotasyon (A + B): **50** belge
- Tam kapsama (12/12 alan karara bağlı): **100** belge
- Rastgelelik tohumu (seed): `42`
- Ön-anotasyon kaynağı: `data/gold/preannotations.v2.json`

## Kim neyi açacak

> Bu tablodaki dosyaların tamamı **v1 protokolüne** aittir (boş hücre = onay).
> Kalibrasyon için artık yukarıdaki v2 paketi kullanılır. `round1_*` ve
> `round1_main_*` dosyaları henüz doldurulmadıysa, kalibrasyon κ'sı alındıktan
> sonra aynı yöntemle v2'ye taşınacaktır.

| Anotatör | 1. Kalibrasyon | 2. Çift anotasyon | 3. Ana küme | Toplam satır |
|---|---|---|---|---:|
| A | `round0_kalibrasyon_A.csv` ✔ dolu | `round1_A.csv` | — | 910 |
| B | `round0_kalibrasyon_B.csv` | `round1_B.csv` | — | 910 |
| C | `round0_kalibrasyon_C.csv` | — | `round1_main_C.csv` (90 belge) | 833 |
| D | `round0_kalibrasyon_D.csv` | — | `round1_main_D.csv` (90 belge) | 832 |

## Sıra ÖNEMLİ

1. **Kalibrasyon turu birlikte yapılır.** Herkes aynı 20 belgeyi anote eder, `scripts/report_iaa.py` koşulur, uyuşmazlıklar 15 dakika konuşulur, kılavuz düzeltilir. Bu adım ATLANIRSA ana turdaki uyuşmazlıkların yarısı kılavuz belirsizliğinden çıkar ve gold yeniden yapılır.
2. Çift anotasyon (A ve B) — kappa buradan hesaplanır.
3. Ana küme — herkes kendi dosyasını doldurur.

## Üretilen dosyalar

| Dosya | Satır | Durum |
|---|---:|---|
| `round0_kalibrasyon_B.csv` | 260 | bu turda üretildi |
| `round0_kalibrasyon_C.csv` | 260 | bu turda üretildi |
| `round0_kalibrasyon_D.csv` | 260 | bu turda üretildi |
| `round1_A.csv` | 650 | bu turda üretildi |
| `round1_B.csv` | 650 | bu turda üretildi |
| `round1_main_C.csv` | 573 | bu turda üretildi |
| `round1_main_D.csv` | 572 | bu turda üretildi |
| `round0_kalibrasyon_A.csv` | 260 | **korundu** — anotasyon içeriyor, üzerine yazılmadı |

> Korunan dosyalar önceki turda doldurulmuş; üreteç onlara dokunmaz (`scripts/to_review_csv.has_annotations`). Kalibrasyon kümesi de bu dosyaya SABİTLENİR, yoksa dört anotatör farklı belgelere bakar ve Fleiss kappa hesaplanamaz.

## Korunan dosyada YENİDEN bakılacak satırlar

Ön-anotasyon tazelendi; aşağıdaki satırlarda modelin değeri değişti. `build_gold` model değerini GÜNCEL ön-anotasyondan okur, bu yüzden boş bırakılmış (= onaylanmış) bir satır artık anotatörün görmediği bir değeri onaylar.

### `round0_kalibrasyon_A.csv`

**Yeniden karara bağlanmalı (1 satır)** — boş bırakılmış, model değeri değişmiş:
- `vakif-katilim--detay-espressolab-hediye-kahve-kampanyasi · indirim_orani: (boş) -> 15.0`

Kararı yazılmış, etkilenmeyen satır: 13 (anotatörün kararı korunur).


## Doldurulduktan sonra

```bash
python -m scripts.lint_review_csv 'data/gold/review/round*.csv'
python -m scripts.build_gold --pre data/gold/preannotations.v2.json \
    --csv-dir data/gold/review
```

`--pre` MUTLAKA `data/gold/preannotations.v2.json` olmalı — CSV'ler bu dosyadan üretildi, varsayılan başka bir ön-anotasyonu gösteriyor ve belgelerin çoğu "bilinmeyen doc_id" diye atlanır.

Belge tam metinleri: `belgeler/<doc_id>.txt`

Kılavuz: [`../ANNOTATION_GUIDE.md`](../ANNOTATION_GUIDE.md) — **anotasyona başlamadan okunacak.**
