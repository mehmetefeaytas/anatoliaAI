# Anotasyon Atama Planı

> `scripts/to_review_csv.py` üretti. Elle düzenlemeyin — yeniden koşuda üzerine yazılır.

- Toplam belge: **250**
- Kalibrasyon (herkes aynı): **20** belge
- Çift anotasyon (A + B): **50** belge
- Tam kapsama (12/12 alan karara bağlı): **100** belge
- Rastgelelik tohumu (seed): `42`

## Kim neyi açacak

| Anotatör | 1. Kalibrasyon | 2. Çift anotasyon | 3. Ana küme |
|---|---|---|---|
| A | `round0_kalibrasyon_A.csv` | `round1_A.csv` | `round1_main_A.csv` (20 belge) |
| B | `round0_kalibrasyon_B.csv` | `round1_B.csv` | `round1_main_B.csv` (20 belge) |
| C | `round0_kalibrasyon_C.csv` | — | `round1_main_C.csv` (70 belge) |
| D | `round0_kalibrasyon_D.csv` | — | `round1_main_D.csv` (70 belge) |

## Sıra ÖNEMLİ

1. **Kalibrasyon turu birlikte yapılır.** Herkes aynı 20 belgeyi anote eder, `scripts/report_iaa.py` koşulur, uyuşmazlıklar 15 dakika konuşulur, kılavuz düzeltilir. Bu adım ATLANIRSA ana turdaki uyuşmazlıkların yarısı kılavuz belirsizliğinden çıkar ve gold yeniden yapılır.
2. Çift anotasyon (A ve B) — kappa buradan hesaplanır.
3. Ana küme — herkes kendi dosyasını doldurur.

## Üretilen dosyalar

| Dosya | Satır |
|---|---:|
| `round0_kalibrasyon_A.csv` | 260 |
| `round0_kalibrasyon_B.csv` | 260 |
| `round0_kalibrasyon_C.csv` | 260 |
| `round0_kalibrasyon_D.csv` | 260 |
| `round1_A.csv` | 650 |
| `round1_B.csv` | 650 |
| `round1_main_A.csv` | 107 |
| `round1_main_B.csv` | 159 |
| `round1_main_C.csv` | 435 |
| `round1_main_D.csv` | 420 |

Belge tam metinleri: `belgeler/<doc_id>.txt`

Kılavuz: [`../ANNOTATION_GUIDE.md`](../ANNOTATION_GUIDE.md) — **anotasyona başlamadan okunacak.**
