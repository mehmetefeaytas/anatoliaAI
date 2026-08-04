# Anotasyon Atama Planı

> `scripts/to_review_csv.py` üretti. Elle düzenlemeyin — yeniden koşuda üzerine yazılır.

- Toplam belge: **250**
- Kalibrasyon (herkes aynı): **20** belge
- Çift anotasyon (A + B): **50** belge
- Tam kapsama (12/12 alan karara bağlı): **100** belge
- Rastgelelik tohumu (seed): `42`
- Ön-anotasyon kaynağı: `data/gold/preannotations.v2.json`

## Kim neyi açacak

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
