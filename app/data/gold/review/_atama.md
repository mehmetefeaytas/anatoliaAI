# Anotasyon Atama Planı

> `scripts/to_review_csv.py` üretti. Elle düzenlemeyin — yeniden koşuda üzerine yazılır.
>
> **İSTİSNA:** aşağıdaki "v2 kalibrasyon paketi" bölümü elle eklenmiştir ve
> üreteçten gelmez. `to_review_csv.py` yeniden koşulursa bu bölüm KORUNMALIDIR.

---

## ⚠️ ÖNCE BURAYI OKUYUN — κ hangi paketten çıkar

Kılavuz revize edildi (`ANNOTATION_GUIDE.md` v2): **boş hücre artık onay değil**
ve dört anotatörün bağımsız işaretlediği **sekiz boşluk kapatıldı** (§4.13).

κ için iki koşul birden gerekir ve ikisi de sessizce bozulabilir:
**(1)** en az iki dosya AYNI `(doc_id, field)` kümesini taşımalı, **(2)** o
ortak satırlarda ikisinin de açık kararı olmalı. Durumu tek komutla görün:

```bash
.venv/bin/python -m scripts.kappa_durum
```

### κ üretebilecek iki paket

| paket | dosyalar | belge | satır | protokol | ne ölçer |
|---|---|---:|---:|---|---|
| **kalibrasyon** | `round0_kalibrasyon_v2_A..D` | 20 | 260 | **v2** | Fleiss κ (4 anotatör) |
| **çift anotasyon** | `round1_A` + `round1_B` | **50** | **650** | **v2** | Cohen κ — **asıl paket** |

`round1_A` ile `round1_B` birebir aynı 50 belgeyi ve aynı 650 satırı taşır;
ölçüldü ve doğrulandı. Daha geniş olduğu için κ'nın **manşet kaynağı budur**.
Satır kümesi sabittir; değiştirilirse κ birimleri hizalanmaz.
(`parca/parca-1..4.json` tamamen ayrık — 48 benzersiz belge, sıfır tekrar —
bu yüzden ondan κ çıkmaz.)

- En az **iki** dosya dolduğunda κ hesaplanır (Cohen). Dördü de dolarsa Fleiss.
- Dosyalarda salt-okunur bir **`protokol`** sütunu var (`v2`). Silmeyin;
  araçlar boş hücrenin anlamını buradan okur.
- **Her satıra `verdict` yazılır.** Boş = "karar verilmedi", gold'a girmez.
- v1 ve v2 dosyaları **aynı κ koşusuna girmez**. v1'de dokunulmamış satır
  "onay" sayılır, dört anotatör de dokunmadıysa tam uyum üretir ve κ olduğundan
  iyi çıkar (ANNOTATION_GUIDE.md §11). `kappa_durum` grupları protokole göre
  ayırır, `report_iaa` karıştırılırsa uyarır.

### ⚠️ v1 dosyasında not var, karar yok

`round0_kalibrasyon_A.csv` v1 protokolündedir ve ölçüldü: **134 satırda**
anotatör bir not yazmış (*"Ödül tutarı yok"*, *"Birden fazla vade seçeneği
var"*) ama `verdict` sütununu işaretlememiş. v1'de boş hücre onaydır — yani
bu satırlar, notun içeriği tersini söylemesine rağmen **"model doğru"** olarak
gold'a girer.

Kapatılması anotatörün birkaç dakikasıdır: not zaten kararı söylüyor, yalnız
`verdict` hücresi doldurulacak. Sayı `kappa_durum` çıktısında görünür.

### Dört komut

```bash
# 0) κ'ya ne kadar kaldı — hangi grup hazır
.venv/bin/python -m scripts.kappa_durum

# 1) doldururken — biçim + kalan karar sayısı (uyarı verir, durdurmaz)
.venv/bin/python -m scripts.lint_review_csv 'data/gold/review/round1_[AB].csv'

# 2) κ + Krippendorff α  ->  data/gold/iaa_report.md
.venv/bin/python -m scripts.report_iaa data/gold/review/round1_A.csv \
                                       data/gold/review/round1_B.csv

# 3) derlemeden ÖNCE kapı — boş satır kalmışsa HATA verir
.venv/bin/python -m scripts.lint_review_csv --eksiksiz 'data/gold/review/round1_[AB].csv'
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

> **Protokol durumu (2026-08-08 itibarıyla ölçüldü).** `round0_kalibrasyon_*`
> dosyaları **v1**'dir (boş hücre = onay) ve ekip şu an A'yı dolduruyor.
> `round1_*`, `round1_main_*` ve `round2_zor_vaka` **v2'ye taşındı** —
> taşıma anında hiçbiri etiketlenmemişti, satır kümeleri bozulmadı, her
> dosyanın `.yedek-v1` kopyası alındı
> (`scripts/protokol_yukselt.py --damgala`).

| Anotatör | 1. Kalibrasyon (v1) | 2. Çift anotasyon (v2) | 3. Ana küme (v2) | Toplam satır |
|---|---|---|---|---:|
| A | `round0_kalibrasyon_A.csv` — 79/260 | `round1_A.csv` | — | 910 |
| B | `round0_kalibrasyon_B.csv` | `round1_B.csv` | — | 910 |
| C | `round0_kalibrasyon_C.csv` | — | `round1_main_C.csv` (90 belge) | 833 |
| D | `round0_kalibrasyon_D.csv` | — | `round1_main_D.csv` (90 belge) | 832 |

`round2_zor_vaka.csv` (73 belge, 949 satır) tek anotatörlüdür — κ üretmez,
zor-vaka kapsamını büyütür.

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
